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


class OpenAIErrorMapper:
    def map(self, exc: Exception, *, context: ProviderErrorContext) -> AppError:
        status_code = _status_code(exc)
        metadata = source_metadata(exc, status_code=status_code)
        message = normalized_message(exc)
        provider = context.provider
        model = context.model

        if isinstance(exc, AuthenticationError):
            return DependencyAuthenticationError(
                "OPENAI_AUTHENTICATION_FAILED",
                "OpenAI API authentication failed",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, PermissionDeniedError):
            return DependencyPermissionError(
                "OPENAI_PERMISSION_DENIED",
                "OpenAI API permission denied",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, NotFoundError):
            return DependencyNotFoundError(
                "OPENAI_MODEL_NOT_FOUND",
                f"{_service_label(context)} model '{model}' was not found",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, RateLimitError):
            if _is_quota(message):
                return DependencyQuotaExceededError(
                    "OPENAI_QUOTA_EXCEEDED",
                    "OpenAI API quota was exceeded",
                    provider=provider,
                    model=model,
                    metadata=metadata,
                )
            return DependencyRateLimitError(
                "OPENAI_RATE_LIMITED",
                "OpenAI API rate limit was exceeded",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, APITimeoutError):
            return DependencyTimeoutError(
                "OPENAI_TIMEOUT",
                f"{_service_label(context)} request timed out",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, APIConnectionError):
            return DependencyUnavailableError(
                "OpenAI API is unreachable",
                "OPENAI_UNAVAILABLE",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, BadRequestError):
            return DependencyInvalidRequestError(
                "OPENAI_INVALID_REQUEST",
                f"{_service_label(context)} request was rejected",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, InternalServerError):
            return DependencyUnavailableError(
                f"{_service_label(context)} service is unavailable",
                "OPENAI_UNAVAILABLE",
                provider=provider,
                model=model,
                metadata=metadata,
            )
        if isinstance(exc, APIStatusError):
            return _map_status_error(exc, context=context, status_code=status_code)
        return DependencyUnavailableError(
            f"{_service_label(context)} provider failed",
            "OPENAI_UNAVAILABLE",
            provider=provider,
            model=model,
            metadata=metadata,
        )


def _map_status_error(
    exc: APIStatusError,
    *,
    context: ProviderErrorContext,
    status_code: int | None,
) -> AppError:
    metadata = source_metadata(exc, status_code=status_code)
    provider = context.provider
    model = context.model
    if status_code == 401:
        return DependencyAuthenticationError(
            "OPENAI_AUTHENTICATION_FAILED",
            "OpenAI API authentication failed",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    if status_code == 403:
        return DependencyPermissionError(
            "OPENAI_PERMISSION_DENIED",
            "OpenAI API permission denied",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    if status_code == 404:
        return DependencyNotFoundError(
            "OPENAI_MODEL_NOT_FOUND",
            f"{_service_label(context)} model '{model}' was not found",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    if status_code == 408:
        return DependencyTimeoutError(
            "OPENAI_TIMEOUT",
            f"{_service_label(context)} request timed out",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    if status_code == 429:
        return DependencyRateLimitError(
            "OPENAI_RATE_LIMITED",
            "OpenAI API rate limit was exceeded",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    if status_code in {400, 422}:
        return DependencyInvalidRequestError(
            "OPENAI_INVALID_REQUEST",
            f"{_service_label(context)} request was rejected",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    if isinstance(status_code, int) and 500 <= status_code < 600:
        return DependencyUnavailableError(
            f"{_service_label(context)} service is unavailable",
            "OPENAI_UNAVAILABLE",
            provider=provider,
            model=model,
            metadata=metadata,
        )
    return DependencyUnavailableError(
        f"{_service_label(context)} provider failed",
        "OPENAI_UNAVAILABLE",
        provider=provider,
        model=model,
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
