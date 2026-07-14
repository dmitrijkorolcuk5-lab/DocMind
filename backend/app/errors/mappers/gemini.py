import httpx
from google.genai import errors

from app.errors.base import AppError
from app.errors.mappers.base import normalized_message, source_metadata
from app.errors.provider import (
    DependencyAuthenticationError,
    DependencyInvalidRequestError,
    DependencyNotFoundError,
    DependencyPermissionError,
    DependencyQuotaExceededError,
    DependencyRateLimitError,
    DependencyTimeoutError,
    DependencyUnavailableError,
    ProviderErrorContext,
)


class GeminiErrorMapper:
    def map(self, exc: Exception, *, context: ProviderErrorContext) -> AppError:
        status_code = _status_code(exc)
        provider_status, provider_message = _provider_details(exc)
        normalized_parts = [
            provider_status.lower() if provider_status else "",
            normalized_message(exc),
        ]
        normalized = " ".join(item for item in normalized_parts if item)
        metadata = source_metadata(
            exc,
            status_code=status_code,
            provider_error_status=provider_status,
        )
        provider = context.provider
        model = context.model

        if status_code == 401:
            return DependencyAuthenticationError(
                "GEMINI_AUTHENTICATION_FAILED",
                "Gemini API authentication failed",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if status_code == 403:
            return DependencyPermissionError(
                "GEMINI_PERMISSION_DENIED",
                "Gemini API permission denied",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if status_code == 404:
            return DependencyNotFoundError(
                "GEMINI_MODEL_NOT_FOUND",
                f"{_service_label(context)} model '{model}' was not found",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if status_code == 408 or isinstance(exc, httpx.TimeoutException):
            return DependencyTimeoutError(
                "GEMINI_TIMEOUT",
                f"{_service_label(context)} request timed out",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if status_code == 429:
            if _is_quota(normalized):
                return DependencyQuotaExceededError(
                    "GEMINI_QUOTA_EXCEEDED",
                    f"{_service_label(context)} quota was exceeded",
                    provider=provider,
                    model=model,
                    metadata=metadata,
                )
            return DependencyRateLimitError(
                "GEMINI_RATE_LIMITED",
                f"{_service_label(context)} rate limit was exceeded",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if status_code in {400, 422}:
            return DependencyInvalidRequestError(
                "GEMINI_INVALID_REQUEST",
                f"{_service_label(context)} request was rejected",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(status_code, int) and 500 <= status_code < 600:
            return DependencyUnavailableError(
                f"{_service_label(context)} service is unavailable",
                "GEMINI_UNAVAILABLE",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, httpx.ConnectError):
            return DependencyUnavailableError(
                "Gemini API is unreachable",
                "GEMINI_UNAVAILABLE",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if _is_model_unavailable(normalized) or _is_model_unavailable(provider_message.lower()):
            return DependencyNotFoundError(
                "GEMINI_MODEL_NOT_FOUND",
                f"{_service_label(context)} model '{model}' is unavailable",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        return DependencyUnavailableError(
            f"{_service_label(context)} provider failed",
            "GEMINI_UNAVAILABLE",
            provider=provider,
            model=model,
            metadata=metadata,
        )


def _status_code(exc: Exception) -> int | None:
    if isinstance(exc, errors.APIError):
        code = getattr(exc, "code", None)
        return code if isinstance(code, int) else None
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def _provider_details(exc: Exception) -> tuple[str | None, str]:
    if isinstance(exc, errors.APIError):
        status = getattr(exc, "status", None)
        message = getattr(exc, "message", "")
        safe_status = status if isinstance(status, str) else None
        safe_message = message if isinstance(message, str) else ""
        return safe_status, safe_message
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            payload = exc.response.json()
        except ValueError:
            return None, ""
        if not isinstance(payload, dict):
            return None, ""
        error = payload.get("error")
        if not isinstance(error, dict):
            return None, ""
        status = error.get("status")
        message = error.get("message")
        return (
            status if isinstance(status, str) else None,
            message if isinstance(message, str) else "",
        )
    return None, ""


def _is_quota(message: str) -> bool:
    return "quota" in message or "resource_exhausted" in message


def _is_model_unavailable(message: str) -> bool:
    return "not found" in message or "no longer available" in message


def _service_label(context: ProviderErrorContext) -> str:
    if context.operation == "stream_answer":
        return "Gemini LLM"
    if context.operation in {"embed_documents", "embed_query"}:
        return "Gemini embedding"
    return "Gemini"
