"""Application configuration from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+asyncpg://legalrag:legalrag@localhost:5432/legalrag"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: str | None = None
    qdrant_collection: str = "legal_documents"
    qdrant_prefer_grpc: bool = False

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "legal-documents"
    minio_use_ssl: bool = False

    # Groq (OpenAI-compatible) — set GROQ_API_KEY or LLM_API_KEY in .env
    llm_provider: str = Field(default="groq", validation_alias="LLM_PROVIDER")
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1", validation_alias="LLM_BASE_URL"
    )
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    llm_model: str = Field(default="llama-3.3-70b-versatile", validation_alias="LLM_MODEL")

    # Anthropic
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-latest", validation_alias="ANTHROPIC_MODEL"
    )

    # Google Gemini
    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", validation_alias="GEMINI_MODEL")

    embedding_model_path: str = Field(
        default="BAAI/bge-small-en-v1.5", validation_alias="EMBEDDING_MODEL_PATH"
    )
    embedding_vector_size: int = Field(default=384, validation_alias="EMBEDDING_VECTOR_SIZE")

    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_use_onnx: bool = False
    use_colbert_rerank: bool = False

    semantic_cache_threshold: float = 0.95

    @model_validator(mode="after")
    def _sync_llm_key(self) -> Settings:
        """Use GROQ_API_KEY for LLM when LLM_API_KEY unset; normalize empty strings to None."""
        if not self.llm_api_key and self.groq_api_key:
            self.llm_api_key = self.groq_api_key
        if self.qdrant_api_key is not None and not self.qdrant_api_key.strip():
            self.qdrant_api_key = None
        return self

    def effective_llm_api_key(self) -> str | None:
        """API key for Groq/OpenAI-compatible endpoints."""
        return self.llm_api_key or self.groq_api_key or None

    def effective_anthropic_api_key(self) -> str | None:
        return self.anthropic_api_key or None


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
