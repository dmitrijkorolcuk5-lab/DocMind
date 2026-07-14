from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol, TypedDict, Unpack

import structlog

from app.errors.base import AppError, ApplicationError, ErrorMetadata, ErrorMetadataValue

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProviderErrorContext:
    provider: str
    operation: str
    model: str | None = None


class ProviderErrorMapper(Protocol):
    def map(self, exc: Exception, *, context: ProviderErrorContext) -> AppError: ...


class DependencyErrorKwargs(TypedDict, total=False):
    provider: str | None
    model: str | None
    metadata: ErrorMetadata | None


class DependencyError(ApplicationError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        status_code: int = 503,
        retryable: bool = False,
        metadata: ErrorMetadata | None = None,
    ) -> None:
        merged_metadata: dict[str, ErrorMetadataValue] = dict(metadata or {})
        if provider is not None:
            merged_metadata["provider"] = provider
        if model is not None:
            merged_metadata["model"] = model
        super().__init__(
            code,
            message,
            status_code=status_code,
            retryable=retryable,
            metadata=merged_metadata,
        )
        self.provider = provider
        self.model = model


class DependencyUnavailableError(DependencyError):
    def __init__(
        self,
        message: str = "A required dependency is unavailable",
        code: str = "DEPENDENCY_UNAVAILABLE",
        **kwargs: Unpack[DependencyErrorKwargs],
    ) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=503,
            retryable=True,
            **kwargs,
        )


class DependencyAuthenticationError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=503,
            retryable=False,
            **kwargs,
        )


class DependencyPermissionError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=503,
            retryable=False,
            **kwargs,
        )


class DependencyNotFoundError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=502,
            retryable=False,
            **kwargs,
        )


class DependencyRateLimitError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=429,
            retryable=True,
            **kwargs,
        )


class DependencyQuotaExceededError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=429,
            retryable=False,
            **kwargs,
        )


class DependencyTimeoutError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=504,
            retryable=True,
            **kwargs,
        )


class DependencyInvalidRequestError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=502,
            retryable=False,
            **kwargs,
        )


class DependencyInvalidResponseError(DependencyUnavailableError):
    def __init__(self, code: str, message: str, **kwargs: Unpack[DependencyErrorKwargs]) -> None:
        DependencyError.__init__(
            self,
            code,
            message,
            status_code=502,
            retryable=False,
            **kwargs,
        )


def raise_provider_error(
    exc: Exception,
    *,
    mapper: ProviderErrorMapper,
    context: ProviderErrorContext,
) -> None:
    mapped = mapper.map(exc, context=context)
    log_provider_error(mapped, exc, context=context)
    raise mapped from exc


@asynccontextmanager
async def map_provider_errors(
    mapper: ProviderErrorMapper,
    context: ProviderErrorContext,
) -> AsyncIterator[None]:
    try:
        yield
    except AppError:
        raise
    except Exception as exc:
        raise_provider_error(exc, mapper=mapper, context=context)


def log_provider_error(
    mapped: AppError,
    source: Exception,
    *,
    context: ProviderErrorContext,
) -> None:
    logger.warning(
        "provider_error_mapped",
        provider=context.provider,
        operation=context.operation,
        model=context.model,
        application_error_code=mapped.code,
        retryable=mapped.retryable,
        source_exception_type=type(source).__name__,
        source_status_code=mapped.metadata.get("source_status_code"),
    )
