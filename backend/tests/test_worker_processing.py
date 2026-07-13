from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pytest import MonkeyPatch
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import configure_mappers

from app.core.exceptions import DependencyUnavailableError
from app.documents.models import Document, DocumentStatus
from app.documents.parsers import DocumentParsingError, ParsedBlock, ParsedDocument
from app.embeddings.base import EmbeddingTask
from app.workers import tasks
from app.workers.settings import WorkerSettings


class FakeSessionContext:
    entered = 0

    async def __aenter__(self) -> object:
        type(self).entered += 1
        return object()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeStorage:
    download_error: Exception | None = None

    def __init__(self, settings: object) -> None:
        del settings

    async def download(self, key: str) -> bytes:
        del key
        if self.download_error is not None:
            raise self.download_error
        return b"hello"


class FakeParser:
    parse_error: Exception | None = None

    async def parse(self, data: bytes, filename: str) -> ParsedDocument:
        del data, filename
        if self.parse_error is not None:
            raise self.parse_error
        return ParsedDocument(
            blocks=[ParsedBlock(text="Document text " * 80, order_index=0)],
            page_count=None,
        )


class FakeEmbeddingProvider:
    error: Exception | None = None
    dimensions = 768

    async def embed_texts(
        self,
        texts: list[str],
        *,
        task: EmbeddingTask = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        assert task == "RETRIEVAL_DOCUMENT"
        if self.error is not None:
            raise self.error
        return [[0.1] * self.dimensions for _ in texts]


class FakeRepository:
    document: Document
    replace_error: Exception | None = None
    stale_count = 0

    def __init__(self, session: object) -> None:
        del session

    async def get(self, document_id: UUID) -> Document | None:
        assert document_id == self.document.id
        return self.document

    async def update_status(
        self,
        document: Document,
        status: DocumentStatus,
        *,
        error_message: str | None = None,
        page_count: int | None = None,
        chunk_count: int | None = None,
    ) -> Document:
        document.status = status
        document.error_message = error_message
        if page_count is not None:
            document.page_count = page_count
        if chunk_count is not None:
            document.chunk_count = chunk_count
        return document

    async def replace_chunks_and_mark_ready(
        self,
        document: Document,
        chunks: list[object],
        embeddings: list[list[float]],
        *,
        page_count: int | None,
    ) -> None:
        del embeddings
        if self.replace_error is not None:
            raise self.replace_error
        document.status = DocumentStatus.READY
        document.error_message = None
        document.page_count = page_count
        document.chunk_count = len(chunks)

    async def mark_stale_processing_failed(
        self, *, cutoff: datetime, error_message: str
    ) -> int:
        del cutoff
        if self.stale_count:
            self.document.status = DocumentStatus.FAILED
            self.document.error_message = error_message
        return self.stale_count


def _document() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        original_filename="notes.txt",
        storage_key="key",
        mime_type="text/plain",
        size_bytes=5,
        status=DocumentStatus.PROCESSING,
        chunk_count=0,
        created_at=now,
        updated_at=now,
    )


def _arrange_pipeline(monkeypatch: MonkeyPatch, document: Document) -> None:
    FakeSessionContext.entered = 0
    FakeStorage.download_error = None
    FakeParser.parse_error = None
    FakeEmbeddingProvider.error = None
    FakeEmbeddingProvider.dimensions = 768
    FakeRepository.document = document
    FakeRepository.replace_error = None
    FakeRepository.stale_count = 0
    monkeypatch.setattr(tasks, "async_session_factory", lambda: FakeSessionContext())
    monkeypatch.setattr(tasks, "DocumentRepository", FakeRepository)
    monkeypatch.setattr(tasks, "MinioObjectStorage", FakeStorage)
    monkeypatch.setattr(tasks, "parser_for_document", lambda filename, mime_type: FakeParser())
    monkeypatch.setattr(
        tasks,
        "build_embedding_provider",
        lambda settings: FakeEmbeddingProvider(),
    )


def test_worker_registers_process_document_and_uses_configured_queue() -> None:
    configure_mappers()
    function_names = {function.__name__ for function in WorkerSettings.functions}
    assert "process_document" in function_names
    assert WorkerSettings.queue_name == "arq:queue"
    assert WorkerSettings.redis_settings.database == 0
    assert WorkerSettings.job_timeout == 300


async def test_process_document_success_marks_ready_and_sets_chunks(
    monkeypatch: MonkeyPatch,
) -> None:
    document = _document()
    _arrange_pipeline(monkeypatch, document)

    result = await tasks.process_document({"job_id": "test-job"}, str(document.id))

    assert result["status"] == "ready"
    assert document.status == DocumentStatus.READY
    assert document.chunk_count > 0
    assert FakeSessionContext.entered == 1


@pytest.mark.parametrize(
    ("stage", "expected_message"),
    [
        ("storage", "object storage"),
        ("parser", "could not be parsed"),
        ("embedding", "Gemini API is unreachable"),
        ("dimension", "Embedding dimension mismatch"),
        ("database", "Database error"),
        ("unexpected", "Unexpected document processing error"),
    ],
)
async def test_processing_failures_use_fresh_session_and_mark_failed(
    monkeypatch: MonkeyPatch,
    stage: str,
    expected_message: str,
) -> None:
    document = _document()
    _arrange_pipeline(monkeypatch, document)
    if stage == "storage":
        from app.storage.minio import StorageError

        FakeStorage.download_error = StorageError("internal storage detail")
    elif stage == "parser":
        FakeParser.parse_error = DocumentParsingError("Document could not be parsed")
    elif stage == "embedding":
        FakeEmbeddingProvider.error = DependencyUnavailableError("Gemini API is unreachable")
    elif stage == "dimension":
        FakeEmbeddingProvider.dimensions = 10
    elif stage == "database":
        FakeRepository.replace_error = SQLAlchemyError("insert failed")
    else:
        FakeParser.parse_error = ValueError("unexpected internal detail")

    result = await tasks.process_document({"job_id": "test-job"}, str(document.id))

    assert result["status"] == "failed"
    assert document.status == DocumentStatus.FAILED
    assert document.chunk_count == 0
    assert expected_message in (document.error_message or "")
    assert FakeSessionContext.entered == 2


async def test_stale_processing_recovery_marks_document_failed(
    monkeypatch: MonkeyPatch,
) -> None:
    document = _document()
    _arrange_pipeline(monkeypatch, document)
    FakeRepository.stale_count = 1

    result = await tasks.recover_stale_documents({"job_id": "recovery-job"})

    assert result["failed_count"] == 1
    assert document.status == DocumentStatus.FAILED
    assert document.error_message == tasks.PROCESSING_TIMEOUT_MESSAGE
