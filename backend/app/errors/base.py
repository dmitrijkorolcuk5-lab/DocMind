from collections.abc import Mapping
from types import MappingProxyType

ErrorMetadataValue = str | int | float | bool | None
ErrorMetadata = Mapping[str, ErrorMetadataValue]


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        retryable: bool = False,
        metadata: ErrorMetadata | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.metadata: ErrorMetadata = MappingProxyType(dict(metadata or {}))

    def __str__(self) -> str:
        return self.message


class ApplicationError(AppError):
    """Base class for safe, user-facing application errors."""
