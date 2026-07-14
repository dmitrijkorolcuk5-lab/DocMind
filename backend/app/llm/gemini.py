from collections.abc import AsyncIterator, Sequence

from google import genai
from google.genai import types

from app.core.config import Settings
from app.errors.mappers.gemini import GeminiErrorMapper
from app.errors.provider import (
    DependencyAuthenticationError,
    ProviderErrorContext,
    map_provider_errors,
)
from app.llm.base import LLMMessage


class GeminiLLMProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.GEMINI_API_KEY.get_secret_value()
        self.model = settings.LLM_MODEL
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None
        self._error_mapper = GeminiErrorMapper()

    async def stream_answer(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        if self._client is None:
            raise DependencyAuthenticationError(
                "GEMINI_AUTHENTICATION_FAILED",
                "GEMINI_API_KEY is required to generate answers",
                provider="gemini",
                model=self.model,
            )

        contents, system_instruction = _build_contents(messages)
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction,
        )
        context = ProviderErrorContext(
            provider="gemini",
            operation="stream_answer",
            model=self.model,
        )
        async with map_provider_errors(self._error_mapper, context):
            stream = await self._client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )
            async for chunk in stream:
                token = _extract_text(chunk)
                if token:
                    yield token


def _build_contents(messages: Sequence[LLMMessage]) -> tuple[list[types.Content], str | None]:
    system_parts: list[str] = []
    contents: list[types.Content] = []
    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
            continue
        role = "model" if message.role == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=message.content)]))
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return contents, system_instruction


def _extract_text(chunk: types.GenerateContentResponse) -> str:
    try:
        text = chunk.text
    except ValueError:
        return ""
    return text if isinstance(text, str) else ""
