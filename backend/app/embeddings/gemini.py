import math
from collections.abc import Sequence

import httpx

from app.common.batching import batched_items
from app.core.config import Settings
from app.embeddings.base import EmbeddingTask
from app.errors.mappers.gemini import GeminiErrorMapper
from app.errors.provider import (
    DependencyAuthenticationError,
    DependencyInvalidResponseError,
    ProviderErrorContext,
    raise_provider_error,
)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.GEMINI_API_KEY.get_secret_value()
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS
        self._batch_size = settings.EMBEDDING_BATCH_SIZE
        self._timeout = httpx.Timeout(settings.GEMINI_REQUEST_TIMEOUT_SECONDS)
        self._max_retries = settings.GEMINI_MAX_RETRIES
        self._error_mapper = GeminiErrorMapper()

    async def embed_texts(
        self,
        texts: list[str],
        *,
        task: EmbeddingTask = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        if not self._api_key:
            raise DependencyAuthenticationError(
                "GEMINI_AUTHENTICATION_FAILED",
                "GEMINI_API_KEY is required to generate embeddings",
                provider="gemini",
                model=self._model,
            )
        if not texts:
            return []

        embeddings: list[list[float]] = []
        context = self._context(task)
        async with httpx.AsyncClient(base_url=GEMINI_BASE_URL, timeout=self._timeout) as client:
            for batch in batched_items(texts, self._batch_size):
                embeddings.extend(await self._embed_batch(client, batch, task, context))
        return embeddings

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        texts: Sequence[str],
        task: EmbeddingTask,
        context: ProviderErrorContext | None = None,
    ) -> list[list[float]]:
        error_context = context or self._context(task)
        last_error: httpx.HTTPError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._try_embed_batch(client, texts, task)
            except httpx.HTTPStatusError as exc:
                if 500 <= exc.response.status_code < 600 and attempt < self._max_retries:
                    last_error = exc
                    continue
                raise_provider_error(exc, mapper=self._error_mapper, context=error_context)
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    raise_provider_error(exc, mapper=self._error_mapper, context=error_context)
            except httpx.ConnectError as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    raise_provider_error(exc, mapper=self._error_mapper, context=error_context)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
        if last_error is not None:
            raise_provider_error(last_error, mapper=self._error_mapper, context=error_context)
        raise DependencyInvalidResponseError(
            "GEMINI_INVALID_RESPONSE",
            "Gemini embedding provider failed",
            provider="gemini",
            model=self._model,
        )

    async def _try_embed_batch(
        self,
        client: httpx.AsyncClient,
        texts: Sequence[str],
        task: EmbeddingTask,
    ) -> list[list[float]]:
        response = await client.post(
            f"/models/{self._model}:batchEmbedContents",
            headers={"x-goog-api-key": self._api_key},
            json={
                "requests": [
                    {
                        "model": f"models/{self._model}",
                        "content": {"parts": [{"text": text}]},
                        # batchEmbedContents currently ignores embedContentConfig for
                        # gemini-embedding-001, so these must stay on EmbedContentRequest.
                        "taskType": task,
                        "outputDimensionality": self._dimensions,
                    }
                    for text in texts
                ]
            },
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise self._invalid_response_error() from exc

        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise self._invalid_response_error()
        return [self._parse_embedding(item) for item in raw_embeddings]

    def _parse_embedding(self, payload: object) -> list[float]:
        if not isinstance(payload, dict):
            raise self._invalid_response_error()
        values = payload.get("values")
        if not isinstance(values, list) or not all(
            isinstance(value, int | float) for value in values
        ):
            raise self._invalid_response_error()
        result = [float(value) for value in values]
        if len(result) != self._dimensions:
            raise self._invalid_response_error(
                "Gemini embedding dimension mismatch: "
                f"expected {self._dimensions}, got {len(result)}"
            )
        return _normalize(result)

    def _invalid_response_error(
        self,
        message: str = "Gemini returned an invalid embedding response",
    ) -> DependencyInvalidResponseError:
        return DependencyInvalidResponseError(
            "GEMINI_INVALID_RESPONSE",
            message,
            provider="gemini",
            model=self._model,
        )

    def _context(self, task: EmbeddingTask) -> ProviderErrorContext:
        operation = "embed_query" if task == "RETRIEVAL_QUERY" else "embed_documents"
        return ProviderErrorContext(provider="gemini", operation=operation, model=self._model)


def _normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise DependencyInvalidResponseError(
            "GEMINI_INVALID_RESPONSE",
            "Gemini returned an invalid zero embedding",
            provider="gemini",
        )
    return [value / norm for value in values]
