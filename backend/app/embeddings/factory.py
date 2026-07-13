from app.core.config import Settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.gemini import GeminiEmbeddingProvider
from app.embeddings.openai import OpenAIEmbeddingProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingProvider(settings)
    return GeminiEmbeddingProvider(settings)
