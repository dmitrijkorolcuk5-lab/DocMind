from app.errors.base import ApplicationError


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource: str) -> None:
        super().__init__("RESOURCE_NOT_FOUND", f"{resource} was not found", status_code=404)


class InvalidRequestError(ApplicationError):
    def __init__(self, message: str, code: str = "INVALID_REQUEST") -> None:
        super().__init__(code, message, status_code=400)


class UnsupportedMediaTypeError(ApplicationError):
    def __init__(self, message: str = "Unsupported file type") -> None:
        super().__init__("UNSUPPORTED_MEDIA_TYPE", message, status_code=415)


class FileTooLargeError(ApplicationError):
    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(
            "FILE_TOO_LARGE",
            f"File is too large. Maximum allowed size is {max_size_bytes} bytes",
            status_code=413,
        )
