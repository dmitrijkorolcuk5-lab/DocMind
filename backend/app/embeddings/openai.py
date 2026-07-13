from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.embeddings.base import EmbeddingTask


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.OPENAI_API_KEY.get_secret_value()
        api_key = self._api_key or "missing-key"
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS
        self._batch_size = settings.EMBEDDING_BATCH_SIZE

    async def embed_texts(
        self,
        texts: list[str],
        *,
        task: EmbeddingTask = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        del task
        if not self._api_key:
            raise DependencyUnavailableError("OPENAI_API_KEY is required to generate embeddings")
        embeddings: list[list[float]] = []
        try:
            for start in range(0, len(texts), self._batch_size):
                batch = texts[start : start + self._batch_size]
                response = await self._client.embeddings.create(
                    model=self._model,
                    input=batch,
                    dimensions=self._dimensions,
                )
                embeddings.extend([item.embedding for item in response.data])
        except OpenAIError as exc:
            raise DependencyUnavailableError("Embedding provider failed") from exc
        return embeddings
