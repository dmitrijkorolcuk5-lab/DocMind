import re
from collections.abc import AsyncIterator

import pytest
from google.genai import errors

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.llm.base import LLMMessage
from app.llm.gemini import GeminiLLMProvider


class FakeChunk:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeGeminiModels:
    def __init__(self) -> None:
        self.model: str | None = None
        self.config: object | None = None

    async def generate_content_stream(
        self, *, model: str, contents: object, config: object
    ) -> AsyncIterator[FakeChunk]:
        del contents
        self.model = model
        self.config = config
        return _stream_chunks(["O", "K"])


class FakeGeminiAio:
    def __init__(self) -> None:
        self.models = FakeGeminiModels()


class FakeGeminiClient:
    def __init__(self) -> None:
        self.aio = FakeGeminiAio()


async def test_gemini_llm_uses_exact_configured_model() -> None:
    provider = GeminiLLMProvider(
        Settings(GEMINI_API_KEY="test-key", LLM_MODEL="gemini-3.1-flash-lite")
    )
    client = FakeGeminiClient()
    provider._client = client

    tokens = [
        token
        async for token in provider.stream_answer(
            [
                LLMMessage(role="system", content="System"),
                LLMMessage(role="user", content="Reply with exactly: OK"),
            ]
        )
    ]

    assert "".join(tokens) == "OK"
    assert client.aio.models.model == "gemini-3.1-flash-lite"
    assert client.aio.models.config is not None
    assert client.aio.models.config.temperature == 0.2
    assert client.aio.models.config.system_instruction == "System"


async def test_gemini_llm_api_error_is_safe() -> None:
    error = errors.APIError(
        code=404,
        response_json={"error": {"message": "model unavailable", "status": "NOT_FOUND"}},
        response=None,
    )

    class FailingModels:
        async def generate_content_stream(
            self, *, model: str, contents: object, config: object
        ) -> AsyncIterator[FakeChunk]:
            del model, contents, config
            raise error

    provider = GeminiLLMProvider(
        Settings(GEMINI_API_KEY="test-key", LLM_MODEL="gemini-3.1-flash-lite")
    )
    client = FakeGeminiClient()
    client.aio.models = FailingModels()
    provider._client = client

    with pytest.raises(
        DependencyUnavailableError,
        match=re.escape("Gemini LLM model 'gemini-3.1-flash-lite' was not found"),
    ):
        async for _ in provider.stream_answer([LLMMessage(role="user", content="Hi")]):
            pass


async def _stream_chunks(chunks: list[str]) -> AsyncIterator[FakeChunk]:
    for chunk in chunks:
        yield FakeChunk(chunk)
