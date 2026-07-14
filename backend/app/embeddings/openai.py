from openai import AsyncOpenAI

from app.common.batching import batched_items
from app.core.config import Settings
from app.embeddings.base import EmbeddingTask
from app.errors.mappers.openai import OpenAIErrorMapper
from app.errors.provider import (
    DependencyAuthenticationError,
    ProviderErrorContext,
    map_provider_errors,
)


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.OPENAI_API_KEY.get_secret_value()
        api_key = self._api_key or "missing-key"
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS
        self._batch_size = settings.EMBEDDING_BATCH_SIZE
        self._error_mapper = OpenAIErrorMapper()

    async def embed_texts(
        self,
        texts: list[str],
        *,
        task: EmbeddingTask = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        if not self._api_key:
            raise DependencyAuthenticationError(
                "OPENAI_AUTHENTICATION_FAILED",
                "OPENAI_API_KEY is required to generate embeddings",
                provider="openai",
                model=self._model,
            )
        embeddings: list[list[float]] = []
        operation = "embed_query" if task == "RETRIEVAL_QUERY" else "embed_documents"
        context = ProviderErrorContext(
            provider="openai",
            operation=operation,
            model=self._model,
        )
        async with map_provider_errors(self._error_mapper, context):
            for batch in batched_items(texts, self._batch_size):
                response = await self._client.embeddings.create(
                    model=self._model,
                    input=batch,
                    dimensions=self._dimensions,
                )
                embeddings.extend([item.embedding for item in response.data])
        return embeddings
