from collections.abc import AsyncIterator, Sequence

import structlog
from google import genai
from google.genai import errors, types

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.llm.base import LLMMessage

logger = structlog.get_logger(__name__)


class GeminiLLMProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.GEMINI_API_KEY.get_secret_value()
        self.model = settings.LLM_MODEL
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None

    async def stream_answer(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        if self._client is None:
            raise DependencyUnavailableError("GEMINI_API_KEY is required to generate answers")

        contents, system_instruction = _build_contents(messages)
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction,
        )
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )
            async for chunk in stream:
                token = _extract_text(chunk)
                if token:
                    yield token
        except errors.APIError as exc:
            raise _gemini_api_error(exc, self.model) from exc
        except Exception as exc:
            logger.warning(
                "gemini_llm_unexpected_error",
                model=self.model,
                exception_type=type(exc).__name__,
            )
            raise DependencyUnavailableError("Gemini LLM provider failed") from exc


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


def _gemini_api_error(exc: errors.APIError, model: str) -> DependencyUnavailableError:
    status_code = getattr(exc, "code", None)
    gemini_status = getattr(exc, "status", None)
    message = str(exc)
    logger.warning(
        "gemini_llm_api_error",
        model=model,
        exception_type=type(exc).__name__,
        status_code=status_code,
        gemini_error_code=status_code,
        gemini_error_status=gemini_status,
    )
    if status_code in {401, 403}:
        return DependencyUnavailableError("Gemini API authentication failed")
    if status_code == 404:
        return DependencyUnavailableError(f"Gemini LLM model '{model}' was not found")
    if status_code == 429:
        return DependencyUnavailableError("Gemini LLM quota was exceeded")
    if isinstance(status_code, int) and 500 <= status_code < 600:
        return DependencyUnavailableError("Gemini LLM service is unavailable")
    if "not found" in message.lower() or "no longer available" in message.lower():
        return DependencyUnavailableError(f"Gemini LLM model '{model}' is unavailable")
    return DependencyUnavailableError("Gemini LLM request was rejected")
