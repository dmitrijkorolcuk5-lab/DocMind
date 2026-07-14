import httpx
from google.genai import errors

from app.errors.base import AppError, ErrorMetadata
from app.errors.mappers.base import mapped_status_error, normalized_message, source_metadata
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

GEMINI_STATUS_HANDLERS = {
    400: lambda context, metadata, message: _invalid_request(context, metadata),
    401: lambda context, metadata, message: _authentication_failed(context, metadata),
    403: lambda context, metadata, message: _permission_denied(context, metadata),
    404: lambda context, metadata, message: _model_not_found(context, metadata),
    408: lambda context, metadata, message: _timeout(context, metadata),
    422: lambda context, metadata, message: _invalid_request(context, metadata),
    429: lambda context, metadata, message: _quota_or_rate_limit(context, metadata, message),
}

GEMINI_STATUS_RANGE_HANDLERS = (
    (range(500, 600), lambda context, metadata, message: _unavailable(context, metadata)),
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
        if isinstance(exc, httpx.TimeoutException):
            return _timeout(context, metadata)
        mapped = mapped_status_error(
            status_code,
            context=context,
            metadata=metadata,
            normalized_message=normalized,
            handlers=GEMINI_STATUS_HANDLERS,
            range_handlers=GEMINI_STATUS_RANGE_HANDLERS,
        )
        if mapped is not None:
            return mapped
        if isinstance(exc, httpx.ConnectError):
            return DependencyUnavailableError(
                "Gemini API is unreachable",
                "GEMINI_UNAVAILABLE",
                provider=context.provider,
                model=context.model,
                metadata=metadata,
            )
        if _is_model_unavailable(normalized) or _is_model_unavailable(provider_message.lower()):
            return DependencyNotFoundError(
                "GEMINI_MODEL_NOT_FOUND",
                f"{_service_label(context)} model '{context.model}' is unavailable",
                provider=context.provider,
                model=context.model,
                metadata=metadata,
            )
        return DependencyUnavailableError(
            f"{_service_label(context)} provider failed",
            "GEMINI_UNAVAILABLE",
            provider=context.provider,
            model=context.model,
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


def _authentication_failed(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyAuthenticationError:
    return DependencyAuthenticationError(
        "GEMINI_AUTHENTICATION_FAILED",
        "Gemini API authentication failed",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _permission_denied(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyPermissionError:
    return DependencyPermissionError(
        "GEMINI_PERMISSION_DENIED",
        "Gemini API permission denied",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _model_not_found(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyNotFoundError:
    return DependencyNotFoundError(
        "GEMINI_MODEL_NOT_FOUND",
        f"{_service_label(context)} model '{context.model}' was not found",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _timeout(context: ProviderErrorContext, metadata: ErrorMetadata) -> DependencyTimeoutError:
    return DependencyTimeoutError(
        "GEMINI_TIMEOUT",
        f"{_service_label(context)} request timed out",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _quota_or_rate_limit(
    context: ProviderErrorContext,
    metadata: ErrorMetadata,
    message: str,
) -> DependencyQuotaExceededError | DependencyRateLimitError:
    if _is_quota(message):
        return DependencyQuotaExceededError(
            "GEMINI_QUOTA_EXCEEDED",
            f"{_service_label(context)} quota was exceeded",
            provider=context.provider,
            model=context.model,
            metadata=metadata,
        )
    return DependencyRateLimitError(
        "GEMINI_RATE_LIMITED",
        f"{_service_label(context)} rate limit was exceeded",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _invalid_request(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyInvalidRequestError:
    return DependencyInvalidRequestError(
        "GEMINI_INVALID_REQUEST",
        f"{_service_label(context)} request was rejected",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _unavailable(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyUnavailableError:
    return DependencyUnavailableError(
        f"{_service_label(context)} service is unavailable",
        "GEMINI_UNAVAILABLE",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )
