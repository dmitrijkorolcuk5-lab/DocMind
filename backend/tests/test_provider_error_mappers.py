import asyncio

import httpx
import openai
import pytest
from google.genai import errors as gemini_errors

from app.errors import (
    AppError,
    DependencyAuthenticationError,
    DependencyInvalidRequestError,
    DependencyNotFoundError,
    DependencyPermissionError,
    DependencyQuotaExceededError,
    DependencyRateLimitError,
    DependencyTimeoutError,
    DependencyUnavailableError,
)
from app.errors.mappers.gemini import GeminiErrorMapper
from app.errors.mappers.openai import OpenAIErrorMapper
from app.errors.provider import ProviderErrorContext, map_provider_errors

GEMINI_CONTEXT = ProviderErrorContext(
    provider="gemini",
    operation="stream_answer",
    model="gemini-3.1-flash-lite",
)
OPENAI_CONTEXT = ProviderErrorContext(
    provider="openai",
    operation="stream_answer",
    model="gpt-test",
)


def test_gemini_mapper_authentication() -> None:
    error = _gemini_api_error(401, status="UNAUTHENTICATED")

    mapped = GeminiErrorMapper().map(error, context=GEMINI_CONTEXT)

    assert isinstance(mapped, DependencyAuthenticationError)
    assert mapped.code == "GEMINI_AUTHENTICATION_FAILED"


def test_gemini_mapper_permission() -> None:
    mapped = GeminiErrorMapper().map(
        _gemini_api_error(403, status="PERMISSION_DENIED"),
        context=GEMINI_CONTEXT,
    )

    assert isinstance(mapped, DependencyPermissionError)
    assert mapped.code == "GEMINI_PERMISSION_DENIED"


def test_gemini_mapper_model_not_found() -> None:
    mapped = GeminiErrorMapper().map(
        _gemini_api_error(404, status="NOT_FOUND"),
        context=GEMINI_CONTEXT,
    )

    assert isinstance(mapped, DependencyNotFoundError)
    assert mapped.code == "GEMINI_MODEL_NOT_FOUND"
    assert "gemini-3.1-flash-lite" in mapped.message


def test_gemini_mapper_rate_limited() -> None:
    mapped = GeminiErrorMapper().map(
        _gemini_api_error(429, message="Too many requests", status="RATE_LIMIT_EXCEEDED"),
        context=GEMINI_CONTEXT,
    )

    assert isinstance(mapped, DependencyRateLimitError)
    assert mapped.code == "GEMINI_RATE_LIMITED"


def test_gemini_mapper_quota_exceeded() -> None:
    mapped = GeminiErrorMapper().map(
        _gemini_api_error(429, message="Quota exceeded", status="RESOURCE_EXHAUSTED"),
        context=GEMINI_CONTEXT,
    )

    assert isinstance(mapped, DependencyQuotaExceededError)
    assert mapped.code == "GEMINI_QUOTA_EXCEEDED"


def test_gemini_mapper_timeout() -> None:
    mapped = GeminiErrorMapper().map(httpx.ReadTimeout("timeout"), context=GEMINI_CONTEXT)

    assert isinstance(mapped, DependencyTimeoutError)
    assert mapped.code == "GEMINI_TIMEOUT"


def test_gemini_mapper_invalid_request() -> None:
    mapped = GeminiErrorMapper().map(_gemini_api_error(400), context=GEMINI_CONTEXT)

    assert isinstance(mapped, DependencyInvalidRequestError)
    assert mapped.code == "GEMINI_INVALID_REQUEST"


def test_gemini_mapper_unavailable_5xx() -> None:
    mapped = GeminiErrorMapper().map(_gemini_api_error(503), context=GEMINI_CONTEXT)

    assert isinstance(mapped, DependencyUnavailableError)
    assert mapped.code == "GEMINI_UNAVAILABLE"


def test_gemini_mapper_message_fallback() -> None:
    mapped = GeminiErrorMapper().map(
        RuntimeError("model is no longer available"),
        context=GEMINI_CONTEXT,
    )

    assert isinstance(mapped, DependencyNotFoundError)
    assert mapped.code == "GEMINI_MODEL_NOT_FOUND"


def test_gemini_mapper_unknown_exception_fallback() -> None:
    mapped = GeminiErrorMapper().map(RuntimeError("boom"), context=GEMINI_CONTEXT)

    assert isinstance(mapped, DependencyUnavailableError)
    assert mapped.code == "GEMINI_UNAVAILABLE"


async def test_provider_error_wrapper_does_not_remap_app_error() -> None:
    original = DependencyUnavailableError("already mapped")

    with pytest.raises(DependencyUnavailableError) as raised:
        async with map_provider_errors(GeminiErrorMapper(), GEMINI_CONTEXT):
            raise original

    assert raised.value is original


async def test_provider_error_wrapper_allows_cancellation() -> None:
    with pytest.raises(asyncio.CancelledError):
        async with map_provider_errors(GeminiErrorMapper(), GEMINI_CONTEXT):
            raise asyncio.CancelledError


def _openai_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.test/v1/test")


def _openai_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_openai_request())


@pytest.mark.parametrize(
    ("exception", "expected_type", "expected_code"),
    [
        (
            openai.AuthenticationError("auth", response=_openai_response(401), body=None),
            DependencyAuthenticationError,
            "OPENAI_AUTHENTICATION_FAILED",
        ),
        (
            openai.PermissionDeniedError("denied", response=_openai_response(403), body=None),
            DependencyPermissionError,
            "OPENAI_PERMISSION_DENIED",
        ),
        (
            openai.NotFoundError("missing", response=_openai_response(404), body=None),
            DependencyNotFoundError,
            "OPENAI_MODEL_NOT_FOUND",
        ),
        (
            openai.RateLimitError("slow down", response=_openai_response(429), body=None),
            DependencyRateLimitError,
            "OPENAI_RATE_LIMITED",
        ),
        (
            openai.APITimeoutError(request=_openai_request()),
            DependencyTimeoutError,
            "OPENAI_TIMEOUT",
        ),
        (
            openai.APIConnectionError(message="network down", request=_openai_request()),
            DependencyUnavailableError,
            "OPENAI_UNAVAILABLE",
        ),
        (
            openai.BadRequestError("bad", response=_openai_response(400), body=None),
            DependencyInvalidRequestError,
            "OPENAI_INVALID_REQUEST",
        ),
        (
            openai.InternalServerError("server", response=_openai_response(500), body=None),
            DependencyUnavailableError,
            "OPENAI_UNAVAILABLE",
        ),
        (
            openai.APIStatusError("status", response=_openai_response(422), body=None),
            DependencyInvalidRequestError,
            "OPENAI_INVALID_REQUEST",
        ),
        (
            RuntimeError("boom"),
            DependencyUnavailableError,
            "OPENAI_UNAVAILABLE",
        ),
    ],
)
def test_openai_mapper(
    exception: Exception,
    expected_type: type[AppError],
    expected_code: str,
) -> None:
    mapped = OpenAIErrorMapper().map(exception, context=OPENAI_CONTEXT)

    assert isinstance(mapped, expected_type)
    assert mapped.code == expected_code


def _gemini_api_error(
    status_code: int,
    *,
    message: str = "provider failed",
    status: str = "UNKNOWN",
) -> gemini_errors.APIError:
    return gemini_errors.APIError(
        code=status_code,
        response_json={"error": {"message": message, "status": status}},
        response=None,
    )
