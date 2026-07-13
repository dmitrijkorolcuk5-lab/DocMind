from pathlib import Path
from uuid import UUID

import structlog
from arq.connections import ArqRedis

from app.core.config import Settings
from app.core.exceptions import (
    DependencyUnavailableError,
    FileTooLargeError,
    InvalidRequestError,
    ResourceNotFoundError,
    UnsupportedMediaTypeError,
)
from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository
from app.documents.schemas import DocumentList, DocumentRead
from app.storage.base import ObjectStorage
from app.storage.minio import StorageError, build_storage_key

logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "text/markdown", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        settings: Settings,
        storage: ObjectStorage | None = None,
        job_queue: ArqRedis | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._storage = storage
        self._job_queue = job_queue

    async def list_documents(self) -> DocumentList:
        documents, total = await self._repository.list_all()
        return DocumentList(
            items=[DocumentRead.model_validate(document) for document in documents], total=total
        )

    async def get_document(self, document_id: UUID) -> DocumentRead:
        document = await self._repository.get(document_id)
        if document is None:
            raise ResourceNotFoundError("Document")
        return DocumentRead.model_validate(document)

    async def upload_document(
        self, *, original_filename: str, mime_type: str, data: bytes
    ) -> DocumentRead:
        self._validate_upload(original_filename, mime_type, data)
        if self._storage is None or self._job_queue is None:
            raise DependencyUnavailableError("Upload dependencies are not available")

        storage_key = build_storage_key(original_filename)
        try:
            await self._storage.upload(storage_key, data, mime_type)
        except StorageError as exc:
            raise DependencyUnavailableError("Object storage is unavailable") from exc

        document = await self._repository.create(
            original_filename=Path(original_filename).name,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=len(data),
            status=DocumentStatus.PROCESSING,
        )
        try:
            job = await self._job_queue.enqueue_job("process_document", str(document.id))
        except Exception as exc:
            await self._repository.update_status(
                document,
                DocumentStatus.FAILED,
                error_message="Document processing job could not be queued",
            )
            raise DependencyUnavailableError(
                "Document processing job could not be queued"
            ) from exc
        if job is None:
            await self._repository.update_status(
                document,
                DocumentStatus.FAILED,
                error_message="Document processing job could not be queued",
            )
            raise DependencyUnavailableError("Document processing job could not be queued")
        logger.info(
            "document_job_enqueued",
            document_id=str(document.id),
            job_id=str(getattr(job, "job_id", "unknown")),
            queue_name=self._settings.ARQ_QUEUE_NAME,
        )
        return DocumentRead.model_validate(document)

    async def delete_document(self, document_id: UUID) -> None:
        document = await self._repository.get(document_id)
        if document is None:
            raise ResourceNotFoundError("Document")
        await self._repository.update_status(document, DocumentStatus.DELETING)
        if self._storage is not None:
            try:
                await self._storage.delete(document.storage_key)
            except StorageError:
                pass
        await self._repository.delete(document)

    def _validate_upload(self, original_filename: str, mime_type: str, data: bytes) -> None:
        suffix = Path(original_filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise UnsupportedMediaTypeError("Only PDF, TXT and DOCX files are supported")
        if mime_type and mime_type not in ALLOWED_EXTENSIONS[suffix]:
            raise UnsupportedMediaTypeError("File MIME type does not match a supported format")
        if not data:
            raise InvalidRequestError("Uploaded file is empty", code="EMPTY_FILE")
        if len(data) > self._settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError(self._settings.MAX_UPLOAD_SIZE_BYTES)
