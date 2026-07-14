from collections.abc import Callable, Mapping, Sequence

from app.errors.base import AppError, ErrorMetadata, ErrorMetadataValue
from app.errors.provider import ProviderErrorContext

StatusHandler = Callable[[ProviderErrorContext, ErrorMetadata, str], AppError]
StatusHandlerMap = Mapping[int, StatusHandler]
StatusRangeHandler = tuple[range, StatusHandler]


def normalized_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    if not isinstance(message, str):
        message = str(exc)
    return message.strip().lower()


def source_metadata(
    exc: Exception,
    *,
    status_code: int | None = None,
    provider_error_status: str | None = None,
) -> dict[str, ErrorMetadataValue]:
    metadata: dict[str, ErrorMetadataValue] = {"source_exception_type": type(exc).__name__}
    if status_code is not None:
        metadata["source_status_code"] = status_code
    if provider_error_status is not None:
        metadata["provider_error_status"] = provider_error_status
    return metadata


def mapped_status_error(
    status_code: int | None,
    *,
    context: ProviderErrorContext,
    metadata: ErrorMetadata,
    normalized_message: str,
    handlers: StatusHandlerMap,
    range_handlers: Sequence[StatusRangeHandler] = (),
) -> AppError | None:
    if status_code is None:
        return None
    handler = handlers.get(status_code)
    if handler is not None:
        return handler(context, metadata, normalized_message)
    for status_range, range_handler in range_handlers:
        if status_code in status_range:
            return range_handler(context, metadata, normalized_message)
    return None
