import math

import httpx

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.embeddings.base import EmbeddingTask

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.GEMINI_API_KEY.get_secret_value()
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS
        self._batch_size = settings.EMBEDDING_BATCH_SIZE
        self._timeout = httpx.Timeout(settings.GEMINI_REQUEST_TIMEOUT_SECONDS)
        self._max_retries = settings.GEMINI_MAX_RETRIES

    async def embed_texts(
        self,
        texts: list[str],
        *,
        task: EmbeddingTask = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        if not self._api_key:
            raise DependencyUnavailableError("GEMINI_API_KEY is required to generate embeddings")
        if not texts:
            return []

        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(base_url=GEMINI_BASE_URL, timeout=self._timeout) as client:
            for start in range(0, len(texts), self._batch_size):
                batch = texts[start : start + self._batch_size]
                embeddings.extend(await self._embed_batch(client, batch, task))
        return embeddings

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
        task: EmbeddingTask,
    ) -> list[list[float]]:
        last_error: httpx.HTTPError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._try_embed_batch(client, texts, task)
            except httpx.HTTPStatusError as exc:
                if 500 <= exc.response.status_code < 600 and attempt < self._max_retries:
                    last_error = exc
                    continue
                raise _http_status_error(exc, self._model) from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    raise DependencyUnavailableError("Gemini embedding request timed out") from exc
            except httpx.ConnectError as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    raise DependencyUnavailableError("Gemini API is unreachable") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
        raise DependencyUnavailableError("Gemini embedding provider failed") from last_error

    async def _try_embed_batch(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
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
            raise DependencyUnavailableError(
                "Gemini returned an invalid embedding response"
            ) from exc

        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise DependencyUnavailableError("Gemini returned an invalid embedding response")
        return [self._parse_embedding(item) for item in raw_embeddings]

    def _parse_embedding(self, payload: object) -> list[float]:
        if not isinstance(payload, dict):
            raise DependencyUnavailableError("Gemini returned an invalid embedding response")
        values = payload.get("values")
        if not isinstance(values, list) or not all(
            isinstance(value, int | float) for value in values
        ):
            raise DependencyUnavailableError("Gemini returned an invalid embedding response")
        result = [float(value) for value in values]
        if len(result) != self._dimensions:
            raise DependencyUnavailableError(
                "Gemini embedding dimension mismatch: "
                f"expected {self._dimensions}, got {len(result)}"
            )
        return _normalize(result)


def _normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise DependencyUnavailableError("Gemini returned an invalid zero embedding")
    return [value / norm for value in values]


def _http_status_error(
    exc: httpx.HTTPStatusError, model: str
) -> DependencyUnavailableError:
    status = exc.response.status_code
    if status in {401, 403}:
        return DependencyUnavailableError("Gemini API authentication failed")
    if status == 429:
        return DependencyUnavailableError("Gemini API quota was exceeded")
    if status == 404:
        return DependencyUnavailableError(f"Gemini embedding model '{model}' was not found")
    if 500 <= status < 600:
        return DependencyUnavailableError("Gemini embedding service is unavailable")
    return DependencyUnavailableError("Gemini embedding request was rejected")
