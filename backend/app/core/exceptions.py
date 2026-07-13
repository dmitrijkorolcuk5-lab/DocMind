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


class DependencyUnavailableError(ApplicationError):
    def __init__(self, message: str = "A required dependency is unavailable") -> None:
        super().__init__("DEPENDENCY_UNAVAILABLE", message, 503)

