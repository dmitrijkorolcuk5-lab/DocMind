from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from app.core.config import Settings
from app.storage.minio import MinioObjectStorage, S3Client, build_storage_key


def test_storage_key_is_unique_and_sanitized() -> None:
    first = build_storage_key("../../unsafe report.pdf")
    second = build_storage_key("../../unsafe report.pdf")

    assert first != second
    assert first.endswith("/unsafe-report.pdf")
    assert ".." not in first


async def test_minio_adapter_uploads_to_configured_bucket() -> None:
    client = AsyncMock(spec=S3Client)

    @asynccontextmanager
    async def client_factory() -> AsyncIterator[S3Client]:
        yield client

    storage = MinioObjectStorage(
        Settings(MINIO_BUCKET="test-documents"), client_factory=client_factory
    )

    await storage.upload("key.txt", b"content", "text/plain")

    client.put_object.assert_awaited_once_with(
        Bucket="test-documents", Key="key.txt", Body=b"content", ContentType="text/plain"
    )


async def test_minio_adapter_healthcheck_uses_bucket_head() -> None:
    client = AsyncMock(spec=S3Client)

    @asynccontextmanager
    async def client_factory() -> AsyncIterator[S3Client]:
        yield client

    storage = MinioObjectStorage(
        Settings(MINIO_BUCKET="test-documents"), client_factory=client_factory
    )
    await storage.healthcheck()
    client.head_bucket.assert_awaited_once_with(Bucket="test-documents")

