from pytest import MonkeyPatch

from app.core.config import Settings
from app.core.constants import EMBEDDING_DIMENSIONS


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


def test_settings_parses_comma_separated_cors() -> None:
    settings = Settings(CORS_ORIGINS="http://one.test,http://two.test")
    assert settings.CORS_ORIGINS == ["http://one.test", "http://two.test"]


def test_settings_parses_cors_from_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://one.test,http://two.test")
    settings = Settings()
    assert settings.CORS_ORIGINS == ["http://one.test", "http://two.test"]
