from app.errors.base import ErrorMetadataValue


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
