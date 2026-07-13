from dataclasses import dataclass


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource: str) -> None:
        super().__init__("RESOURCE_NOT_FOUND", f"{resource} was not found", 404)


class InvalidRequestError(ApplicationError):
    def __init__(self, message: str, code: str = "INVALID_REQUEST") -> None:
        super().__init__(code, message, 400)


class UnsupportedMediaTypeError(ApplicationError):
    def __init__(self, message: str = "Unsupported file type") -> None:
        super().__init__("UNSUPPORTED_MEDIA_TYPE", message, 415)


class FileTooLargeError(ApplicationError):
    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(
            "FILE_TOO_LARGE",
            f"File is too large. Maximum allowed size is {max_size_bytes} bytes",
            413,
        )


class DependencyUnavailableError(ApplicationError):
    def __init__(self, message: str = "A required dependency is unavailable") -> None:
        super().__init__("DEPENDENCY_UNAVAILABLE", message, 503)
