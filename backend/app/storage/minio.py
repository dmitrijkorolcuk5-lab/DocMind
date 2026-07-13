import re
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import uuid4

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings


class StorageError(RuntimeError):
    """Raised when object storage cannot complete an operation."""


class StreamingBody(Protocol):
    async def read(self) -> bytes: ...


class S3Client(Protocol):
    async def head_bucket(self, **kwargs: object) -> Mapping[str, object]: ...

    async def create_bucket(self, **kwargs: object) -> Mapping[str, object]: ...

    async def put_object(self, **kwargs: object) -> Mapping[str, object]: ...

    async def get_object(self, **kwargs: object) -> Mapping[str, object]: ...

    async def delete_object(self, **kwargs: object) -> Mapping[str, object]: ...

    async def head_object(self, **kwargs: object) -> Mapping[str, object]: ...


ClientFactory = Callable[[], AbstractAsyncContextManager[S3Client]]


def build_storage_key(original_filename: str) -> str:
    basename = original_filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", basename).strip(".-") or "document"
    safe_name = safe_name[:180]
    today = datetime.now(UTC).strftime("%Y/%m/%d")
    return f"{today}/{uuid4()}/{safe_name}"


class MinioObjectStorage:
    def __init__(self, settings: Settings, client_factory: ClientFactory | None = None) -> None:
        self._bucket = settings.MINIO_BUCKET
        self._session = aioboto3.Session()
        self._client_factory = client_factory or self._default_client_factory
        self._endpoint_url = settings.minio_url
        self._access_key = settings.MINIO_ACCESS_KEY
        self._secret_key = settings.MINIO_SECRET_KEY.get_secret_value()

    def _default_client_factory(self) -> AbstractAsyncContextManager[S3Client]:
        client = self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )
        return cast(AbstractAsyncContextManager[S3Client], client)

    async def ensure_bucket(self) -> None:
        try:
            async with self._client_factory() as client:
                try:
                    await client.head_bucket(Bucket=self._bucket)
                except ClientError as exc:
                    code = str(exc.response.get("Error", {}).get("Code", ""))
                    if code not in {"404", "NoSuchBucket", "NotFound"}:
                        raise
                    await client.create_bucket(Bucket=self._bucket)
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Unable to ensure object storage bucket") from exc

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            async with self._client_factory() as client:
                await client.put_object(
                    Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
                )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Unable to upload object") from exc

    async def download(self, key: str) -> bytes:
        try:
            async with self._client_factory() as client:
                response = await client.get_object(Bucket=self._bucket, Key=key)
                body = cast(StreamingBody, response["Body"])
                return await body.read()
        except (BotoCoreError, ClientError, OSError, KeyError) as exc:
            raise StorageError("Unable to download object") from exc

    async def delete(self, key: str) -> None:
        try:
            async with self._client_factory() as client:
                await client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Unable to delete object") from exc

    async def exists(self, key: str) -> bool:
        try:
            async with self._client_factory() as client:
                await client.head_object(Bucket=self._bucket, Key=key)
                return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise StorageError("Unable to check object existence") from exc
        except (BotoCoreError, OSError) as exc:
            raise StorageError("Unable to check object existence") from exc

    async def healthcheck(self) -> None:
        try:
            async with self._client_factory() as client:
                await client.head_bucket(Bucket=self._bucket)
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Object storage health check failed") from exc
