from typing import TypedDict
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError

logger = structlog.get_logger(__name__)


class ErrorBody(TypedDict):
    code: str
    message: str
    request_id: str


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid4()))


def _response(code: str, message: str, request_id: str, status_code: int) -> JSONResponse:
    body: dict[str, ErrorBody] = {
        "error": {"code": code, "message": message, "request_id": request_id}
    }
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        logger.warning("application_error", code=exc.code, message=exc.message)
        return _response(exc.code, exc.message, _request_id(request), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("request_validation_error", error_count=len(exc.errors()))
        return _response(
            "VALIDATION_ERROR",
            "The request data is invalid",
            _request_id(request),
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error", exception_type=type(exc).__name__)
        return _response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred",
            _request_id(request),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
