from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.constants import EMBEDDING_DIMENSIONS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_ENV: str = "local"
    APP_NAME: str = "DocMind"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    POSTGRES_DB: str = "docmind"
    POSTGRES_USER: str = "docmind"
    POSTGRES_PASSWORD: SecretStr = SecretStr("docmind")
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DATABASE: int = 0
    ARQ_QUEUE_NAME: str = "arq:queue"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "docmind"
    MINIO_SECRET_KEY: SecretStr = SecretStr("docmind-secret")
    MINIO_BUCKET: str = "documents"
    MINIO_SECURE: bool = False

    LLM_PROVIDER: Literal["gemini", "openai"] = "gemini"
    EMBEDDING_PROVIDER: Literal["gemini", "openai"] = "gemini"

    GEMINI_API_KEY: SecretStr = SecretStr("")
    OPENAI_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = "gemini-3.1-flash-lite"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS: int = EMBEDDING_DIMENSIONS
    GEMINI_REQUEST_TIMEOUT_SECONDS: float = 60.0
    GEMINI_MAX_RETRIES: int = 3
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024
    CHUNK_TARGET_TOKENS: int = 800
    CHUNK_OVERLAP_TOKENS: int = 120
    EMBEDDING_BATCH_SIZE: int = 64
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float | None = None
    RAG_MAX_CONTEXT_TOKENS: int = 6000
    DOCUMENT_PROCESSING_TIMEOUT_SECONDS: int = 300

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("RAG_SCORE_THRESHOLD", mode="before")
    @classmethod
    def parse_optional_score_threshold(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_ai_provider_configuration(self) -> "Settings":
        if self.LLM_PROVIDER == "openai" or self.EMBEDDING_PROVIDER == "openai":
            if not self.OPENAI_API_KEY.get_secret_value():
                raise ValueError("OPENAI_API_KEY is required when an OpenAI provider is selected")
        if self.LLM_PROVIDER == "gemini" or self.EMBEDDING_PROVIDER == "gemini":
            if not self.GEMINI_API_KEY.get_secret_value():
                raise ValueError("GEMINI_API_KEY is required when a Gemini provider is selected")
        if not self.LLM_MODEL:
            raise ValueError("LLM_MODEL is required")
        if not self.EMBEDDING_MODEL:
            raise ValueError("EMBEDDING_MODEL is required")
        return self

    @property
    def database_url(self) -> str:
        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DATABASE}"

    @property
    def minio_url(self) -> str:
        scheme = "https" if self.MINIO_SECURE else "http"
        return f"{scheme}://{self.MINIO_ENDPOINT}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
