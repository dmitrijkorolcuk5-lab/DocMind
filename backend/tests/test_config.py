from pytest import MonkeyPatch

from app.core.config import Settings
from app.core.constants import EMBEDDING_DIMENSIONS
from app.embeddings.factory import build_embedding_provider
from app.embeddings.gemini import GeminiEmbeddingProvider
from app.llm.factory import build_llm_provider
from app.llm.gemini import GeminiLLMProvider


def test_settings_build_connection_urls() -> None:
    settings = Settings(
        POSTGRES_HOST="db",
        POSTGRES_PASSWORD="safe-password",
        REDIS_HOST="cache",
        MINIO_ENDPOINT="objects:9000",
        MINIO_SECURE=True,
    )

    assert settings.database_url == (
        "postgresql+asyncpg://docmind:safe-password@db:5432/docmind"
    )
    assert settings.redis_url == "redis://cache:6379/0"
    assert settings.minio_url == "https://objects:9000"
    assert settings.EMBEDDING_DIMENSIONS == EMBEDDING_DIMENSIONS
    assert "safe-password" not in repr(settings)


def test_settings_defaults_to_gemini_without_openai_key() -> None:
    settings = Settings(GEMINI_API_KEY="test-key", OPENAI_API_KEY="")

    assert settings.LLM_PROVIDER == "gemini"
    assert settings.EMBEDDING_PROVIDER == "gemini"
    assert settings.LLM_MODEL == "gemini-3.1-flash-lite"
    assert settings.EMBEDDING_MODEL == "gemini-embedding-001"
    assert settings.EMBEDDING_DIMENSIONS == 768


def test_factories_select_gemini_providers() -> None:
    settings = Settings(
        GEMINI_API_KEY="test-key",
        LLM_PROVIDER="gemini",
        EMBEDDING_PROVIDER="gemini",
    )

    assert isinstance(build_llm_provider(settings), GeminiLLMProvider)
    assert isinstance(build_embedding_provider(settings), GeminiEmbeddingProvider)


def test_settings_parses_comma_separated_cors() -> None:
    settings = Settings(CORS_ORIGINS="http://one.test,http://two.test")
    assert settings.CORS_ORIGINS == ["http://one.test", "http://two.test"]


def test_settings_parses_cors_from_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://one.test,http://two.test")
    settings = Settings()
    assert settings.CORS_ORIGINS == ["http://one.test", "http://two.test"]
