from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

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

OPENAI_STATUS_HANDLERS = {
    400: lambda context, metadata, message: _invalid_request(context, metadata),
    401: lambda context, metadata, message: _authentication_failed(context, metadata),
    403: lambda context, metadata, message: _permission_denied(context, metadata),
    404: lambda context, metadata, message: _model_not_found(context, metadata),
    408: lambda context, metadata, message: _timeout(context, metadata),
    422: lambda context, metadata, message: _invalid_request(context, metadata),
    429: lambda context, metadata, message: _quota_or_rate_limit(context, metadata, message),
}

OPENAI_STATUS_RANGE_HANDLERS = (
    (range(500, 600), lambda context, metadata, message: _unavailable(context, metadata)),
)


class OpenAIErrorMapper:
    def map(self, exc: Exception, *, context: ProviderErrorContext) -> AppError:
        status_code = _status_code(exc)
        metadata = source_metadata(exc, status_code=status_code)
        message = normalized_message(exc)
        if isinstance(exc, AuthenticationError):
            return _authentication_failed(context, metadata)
        if isinstance(exc, PermissionDeniedError):
            return _permission_denied(context, metadata)
        if isinstance(exc, NotFoundError):
            return _model_not_found(context, metadata)
        if isinstance(exc, RateLimitError):
            return _quota_or_rate_limit(context, metadata, message)
        if isinstance(exc, APITimeoutError):
            return _timeout(context, metadata)
        if isinstance(exc, APIConnectionError):
            return DependencyUnavailableError(
                "OpenAI API is unreachable",
                "OPENAI_UNAVAILABLE",
                provider=context.provider,
                model=context.model,
                metadata=metadata,
            )
        if isinstance(exc, BadRequestError):
            return _invalid_request(context, metadata)
        if isinstance(exc, InternalServerError):
            return _unavailable(context, metadata)
        if isinstance(exc, APIStatusError):
            mapped = mapped_status_error(
                status_code,
                context=context,
                metadata=metadata,
                normalized_message=message,
                handlers=OPENAI_STATUS_HANDLERS,
                range_handlers=OPENAI_STATUS_RANGE_HANDLERS,
            )
            if mapped is not None:
                return mapped
        return DependencyUnavailableError(
            f"{_service_label(context)} provider failed",
            "OPENAI_UNAVAILABLE",
            provider=context.provider,
            model=context.model,
            metadata=metadata,
        )


def _status_code(exc: Exception) -> int | None:
    if isinstance(exc, APIStatusError):
        return exc.status_code
    return None


def _is_quota(message: str) -> bool:
    return "quota" in message or "insufficient_quota" in message


def _service_label(context: ProviderErrorContext) -> str:
    if context.operation == "stream_answer":
        return "OpenAI LLM"
    if context.operation in {"embed_documents", "embed_query"}:
        return "OpenAI embedding"
    return "OpenAI"


def _authentication_failed(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyAuthenticationError:
    return DependencyAuthenticationError(
        "OPENAI_AUTHENTICATION_FAILED",
        "OpenAI API authentication failed",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _permission_denied(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyPermissionError:
    return DependencyPermissionError(
        "OPENAI_PERMISSION_DENIED",
        "OpenAI API permission denied",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _model_not_found(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyNotFoundError:
    return DependencyNotFoundError(
        "OPENAI_MODEL_NOT_FOUND",
        f"{_service_label(context)} model '{context.model}' was not found",
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
            "OPENAI_QUOTA_EXCEEDED",
            "OpenAI API quota was exceeded",
            provider=context.provider,
            model=context.model,
            metadata=metadata,
        )
    return DependencyRateLimitError(
        "OPENAI_RATE_LIMITED",
        "OpenAI API rate limit was exceeded",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _timeout(context: ProviderErrorContext, metadata: ErrorMetadata) -> DependencyTimeoutError:
    return DependencyTimeoutError(
        "OPENAI_TIMEOUT",
        f"{_service_label(context)} request timed out",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )


def _invalid_request(
    context: ProviderErrorContext, metadata: ErrorMetadata
) -> DependencyInvalidRequestError:
    return DependencyInvalidRequestError(
        "OPENAI_INVALID_REQUEST",
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
        "OPENAI_UNAVAILABLE",
        provider=context.provider,
        model=context.model,
        metadata=metadata,
    )
