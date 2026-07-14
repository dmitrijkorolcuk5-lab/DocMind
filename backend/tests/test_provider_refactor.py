import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import cast

import httpx
import pytest
from google.genai import errors as gemini_errors

from app.core.config import Settings
from app.embeddings.base import EmbeddingTask
from app.embeddings.gemini import GeminiEmbeddingProvider
from app.embeddings.openai import OpenAIEmbeddingProvider
from app.errors import DependencyAuthenticationError, DependencyRateLimitError
from app.llm.base import LLMMessage
from app.llm.gemini import GeminiLLMProvider


async def test_gemini_embedding_provider_uses_shared_batching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiEmbeddingProvider(
        Settings(GEMINI_API_KEY="test-key", EMBEDDING_BATCH_SIZE=2)
    )
    batches_seen: list[tuple[str, ...]] = []

    async def fake_embed_batch(
        client: httpx.AsyncClient,
        texts: Sequence[str],
        task: EmbeddingTask,
        context: object = None,
    ) -> list[list[float]]:
        del client, task, context
        batches_seen.append(tuple(texts))
        return [[1.0] for _ in texts]

    monkeypatch.setattr(provider, "_embed_batch", fake_embed_batch)

    embeddings = await provider.embed_texts(["a", "b", "c"])

    assert embeddings == [[1.0], [1.0], [1.0]]
    assert batches_seen == [("a", "b"), ("c",)]


async def test_openai_embedding_provider_uses_shared_batching() -> None:
    provider = OpenAIEmbeddingProvider(
        Settings(
            GEMINI_API_KEY="test-key",
            OPENAI_API_KEY="test-key",
            EMBEDDING_PROVIDER="openai",
            EMBEDDING_BATCH_SIZE=2,
        )
    )
    fake_embeddings = FakeOpenAIEmbeddings()
    provider._client = cast(object, FakeOpenAIClient(fake_embeddings))

    embeddings = await provider.embed_texts(["a", "b", "c"])

    assert embeddings == [[1.0], [1.0], [1.0]]
    assert fake_embeddings.inputs == [("a", "b"), ("c",)]


async def test_gemini_embedding_provider_translates_sdk_error_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GeminiEmbeddingProvider(
        Settings(GEMINI_API_KEY="test-key", EMBEDDING_BATCH_SIZE=2)
    )
    request = httpx.Request("POST", "https://example.test")
    response = httpx.Response(401, request=request)

    async def fail_batch(
        client: httpx.AsyncClient,
        texts: Sequence[str],
        task: EmbeddingTask,
    ) -> list[list[float]]:
        del client, texts, task
        raise httpx.HTTPStatusError("auth failed", request=request, response=response)

    monkeypatch.setattr(provider, "_try_embed_batch", fail_batch)

    with pytest.raises(DependencyAuthenticationError) as raised:
        await provider.embed_texts(["a"])

    assert raised.value.__cause__ is not None
    assert isinstance(raised.value.__cause__, httpx.HTTPStatusError)


async def test_gemini_streaming_iteration_error_is_mapped() -> None:
    provider = GeminiLLMProvider(
        Settings(GEMINI_API_KEY="test-key", LLM_MODEL="gemini-3.1-flash-lite")
    )
    client = FakeGeminiClient(_failing_gemini_stream())
    provider._client = client

    with pytest.raises(DependencyRateLimitError):
        async for _ in provider.stream_answer([LLMMessage(role="user", content="Hi")]):
            pass


async def test_streaming_cancelled_error_propagates() -> None:
    provider = GeminiLLMProvider(
        Settings(GEMINI_API_KEY="test-key", LLM_MODEL="gemini-3.1-flash-lite")
    )
    client = FakeGeminiClient(_cancelled_stream())
    provider._client = client

    with pytest.raises(asyncio.CancelledError):
        async for _ in provider.stream_answer([LLMMessage(role="user", content="Hi")]):
            pass


class FakeEmbeddingData:
    def __init__(self) -> None:
        self.embedding = [1.0]


class FakeEmbeddingResponse:
    def __init__(self, count: int) -> None:
        self.data = [FakeEmbeddingData() for _ in range(count)]


class FakeOpenAIEmbeddings:
    def __init__(self) -> None:
        self.inputs: list[tuple[str, ...]] = []

    async def create(
        self,
        *,
        model: str,
        input: tuple[str, ...],
        dimensions: int,
    ) -> FakeEmbeddingResponse:
        del model, dimensions
        self.inputs.append(tuple(input))
        return FakeEmbeddingResponse(len(input))


class FakeOpenAIClient:
    def __init__(self, embeddings: FakeOpenAIEmbeddings) -> None:
        self.embeddings = embeddings


class FakeGeminiModels:
    def __init__(self, stream: AsyncIterator[object]) -> None:
        self._stream = stream

    async def generate_content_stream(
        self, *, model: str, contents: object, config: object
    ) -> AsyncIterator[object]:
        del model, contents, config
        return self._stream


class FakeGeminiAio:
    def __init__(self, stream: AsyncIterator[object]) -> None:
        self.models = FakeGeminiModels(stream)


class FakeGeminiClient:
    def __init__(self, stream: AsyncIterator[object]) -> None:
        self.aio = FakeGeminiAio(stream)


async def _failing_gemini_stream() -> AsyncIterator[object]:
    raise gemini_errors.APIError(
        code=429,
        response_json={"error": {"message": "Too many requests", "status": "RATE_LIMITED"}},
        response=None,
    )
    yield object()


async def _cancelled_stream() -> AsyncIterator[object]:
    raise asyncio.CancelledError
    yield object()
