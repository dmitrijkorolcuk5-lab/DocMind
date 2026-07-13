import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.exceptions import ApplicationError
from app.database.session import async_session_factory
from app.documents.chunking import DocumentChunker
from app.documents.models import DocumentStatus
from app.documents.parsers import DocumentParsingError, parser_for_document
from app.documents.repository import DocumentRepository
from app.embeddings.factory import build_embedding_provider
from app.storage.minio import MinioObjectStorage, StorageError

logger = structlog.get_logger(__name__)

PROCESSING_TIMEOUT_MESSAGE = "Document processing timed out. Please retry the upload."


async def health_job(ctx: dict[str, object]) -> dict[str, str]:
    """Small executable job used to verify the worker/Redis path."""
    del ctx
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


async def process_document(ctx: dict[str, object], document_id: str) -> dict[str, object]:
    job_id = str(ctx.get("job_id", "unknown"))
    parsed_id: UUID | None = None
    logger.info("document_job_started", document_id=document_id, job_id=job_id)

    try:
        parsed_id = UUID(document_id)
        settings = get_settings()
        storage = MinioObjectStorage(settings)
        embedding_provider = build_embedding_provider(settings)

        async with async_session_factory() as session:
            repository = DocumentRepository(session)
            document = await repository.get(parsed_id)
            if document is None:
                logger.warning(
                    "document_processing_missing_document",
                    document_id=document_id,
                    job_id=job_id,
                )
                return {"status": "missing", "document_id": document_id}

            logger.info("document_loaded", document_id=document_id, job_id=job_id)
            await repository.update_status(
                document,
                DocumentStatus.PROCESSING,
                error_message=None,
                chunk_count=0,
            )

            logger.info(
                "minio_download_started", document_id=document_id, job_id=job_id
            )
            data = await storage.download(document.storage_key)
            logger.info(
                "minio_download_completed",
                document_id=document_id,
                job_id=job_id,
                size_bytes=len(data),
            )

            parser = parser_for_document(document.original_filename, document.mime_type)
            logger.info(
                "parser_selected",
                document_id=document_id,
                job_id=job_id,
                parser=type(parser).__name__,
            )
            parsed = await parser.parse(data, document.original_filename)
            logger.info(
                "document_text_extracted",
                document_id=document_id,
                job_id=job_id,
                block_count=len(parsed.blocks),
                character_count=len(parsed.text),
                page_count=parsed.page_count,
            )

            chunker = DocumentChunker(
                target_tokens=settings.CHUNK_TARGET_TOKENS,
                overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
            )
            chunks = chunker.chunk(document.id, parsed)
            if not chunks:
                raise DocumentParsingError("No chunks could be created from this document")
            logger.info(
                "chunks_created",
                document_id=document_id,
                job_id=job_id,
                chunk_count=len(chunks),
            )

            logger.info(
                "embeddings_started",
                document_id=document_id,
                job_id=job_id,
                chunk_count=len(chunks),
            )
            embeddings = await embedding_provider.embed_texts(
                [chunk.content for chunk in chunks]
            )
            _validate_embeddings(
                embeddings,
                expected_count=len(chunks),
                expected_dimensions=settings.EMBEDDING_DIMENSIONS,
            )
            logger.info(
                "embeddings_completed",
                document_id=document_id,
                job_id=job_id,
                embedding_count=len(embeddings),
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )

            await repository.replace_chunks_and_mark_ready(
                document,
                chunks,
                embeddings,
                page_count=parsed.page_count,
            )
            logger.info(
                "chunks_saved",
                document_id=document_id,
                job_id=job_id,
                chunk_count=len(chunks),
            )
            logger.info(
                "document_marked_ready",
                document_id=document_id,
                job_id=job_id,
                chunk_count=len(chunks),
            )
            return {
                "status": "ready",
                "document_id": document_id,
                "chunk_count": len(chunks),
            }
    except asyncio.CancelledError:
        if parsed_id is not None:
            await asyncio.shield(
                _mark_document_failed(parsed_id, PROCESSING_TIMEOUT_MESSAGE, job_id)
            )
        raise
    except Exception as exc:
        safe_message = _safe_processing_error(exc)
        logger.exception(
            "document_processing_exception",
            document_id=document_id,
            job_id=job_id,
            error_type=type(exc).__name__,
        )
        if parsed_id is not None:
            await _mark_document_failed(parsed_id, safe_message, job_id)
        return {"status": "failed", "document_id": document_id, "error": safe_message}


async def recover_stale_documents(ctx: dict[str, object]) -> dict[str, object]:
    job_id = str(ctx.get("job_id", "stale-recovery"))
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(
        seconds=settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS
    )
    async with async_session_factory() as session:
        count = await DocumentRepository(session).mark_stale_processing_failed(
            cutoff=cutoff,
            error_message=PROCESSING_TIMEOUT_MESSAGE,
        )
    if count:
        logger.warning("stale_documents_marked_failed", job_id=job_id, document_count=count)
    return {"status": "ok", "failed_count": count}


async def _mark_document_failed(document_id: UUID, message: str, job_id: str) -> None:
    """Persist failure using a fresh session after the processing transaction is closed."""
    try:
        async with async_session_factory() as session:
            repository = DocumentRepository(session)
            document = await repository.get(document_id)
            if document is None:
                return
            await repository.update_status(
                document,
                DocumentStatus.FAILED,
                error_message=message,
                chunk_count=0,
            )
        logger.warning(
            "document_marked_failed",
            document_id=str(document_id),
            job_id=job_id,
            error=message,
        )
    except Exception:
        logger.exception(
            "document_failed_status_persistence_failed",
            document_id=str(document_id),
            job_id=job_id,
        )


def _validate_embeddings(
    embeddings: list[list[float]], *, expected_count: int, expected_dimensions: int
) -> None:
    if len(embeddings) != expected_count:
        raise RuntimeError(
            f"Embedding provider returned {len(embeddings)} vectors for {expected_count} chunks"
        )
    invalid_dimensions = [
        len(embedding)
        for embedding in embeddings
        if len(embedding) != expected_dimensions
    ]
    if invalid_dimensions:
        raise RuntimeError(
            "Embedding dimension mismatch: "
            f"expected {expected_dimensions}, got {invalid_dimensions[0]}"
        )


def _safe_processing_error(exc: Exception) -> str:
    if isinstance(exc, (ApplicationError, DocumentParsingError)):
        return (str(exc) or "Document processing failed")[:1000]
    if isinstance(exc, StorageError):
        return "Unable to download the document from object storage"
    if isinstance(exc, SQLAlchemyError):
        return "Database error while saving the processed document"
    if isinstance(exc, RuntimeError):
        return (str(exc) or "Document processing failed")[:1000]
    return "Unexpected document processing error"
