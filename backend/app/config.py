from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/chatbot_db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cors_origins: str = "http://localhost:5173"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_prompt_optimization_model: str = "openai/gpt-oss-20b"
    tavily_api_key: str = ""

    # Database pool
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_recycle: int = 3600

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_use_redis: bool = False
    rate_limit_auth: str = "10/minute"
    rate_limit_chat: str = "30/minute"
    rate_limit_upload: str = "20/minute"
    rate_limit_optimize: str = "10/minute"

    # Prompt optimization (project creation)
    prompt_opt_enabled: bool = True
    prompt_opt_temperature: float = 0.1
    prompt_opt_max_tokens: int = 2048
    prompt_opt_connect_timeout: float = 3.0
    prompt_opt_read_timeout: float = 8.0
    prompt_opt_max_retries: int = 2
    prompt_opt_retry_backoff_seconds: float = 0.5

    # RAG
    rag_enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "chatbot_chunks"
    document_storage_path: str = "./storage/documents"
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_provider: str = "local"  # local | huggingface
    huggingface_api_key: str = ""
    huggingface_api_url: str = "https://router.huggingface.co/hf-inference"
    huggingface_embedding_batch_size: int = 16
    huggingface_timeout_seconds: float = 60.0
    huggingface_max_retries: int = 3
    huggingface_retry_backoff_seconds: float = 2.0
    reranker_model: str = "BAAI/bge-reranker-base"
    rerank_enabled: bool = True
    embedding_dimension: int = 768
    embedding_query_prefix: str = (
        "Represent this sentence for searching relevant passages: "
    )
    rag_top_k: int = 20
    rag_rerank_top_k: int = 5
    rag_hybrid_dense_weight: float = 0.7
    rag_mmr_lambda: float = 0.5
    rag_max_upload_mb: int = 25
    ingestion_max_retries: int = 3
    ingestion_max_jobs: int = 3
    ingestion_stale_minutes: int = 4
    # When False (default), Redis/Arq enqueue failure raises — never run embed in API process.
    # Set True only for local demos without a worker.
    ingestion_inline_fallback: bool = False

    # Observability
    metrics_enabled: bool = True
    metrics_token: str = ""
    otel_enabled: bool = True
    otel_service_name: str = "chatbot-api"
    otel_exporter_otlp_endpoint: str = ""
    otel_console_export: bool = False

    # Guardrails
    guardrails_enabled: bool = True
    upload_validation_gpt_enabled: bool = True

    # Response routing (post-retrieval source selection)
    response_routing_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @field_validator("cookie_samesite")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        return normalized

    @model_validator(mode="after")
    def enforce_production_security(self) -> "Settings":
        if not self.is_production:
            return self

        if self.secret_key == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY is still set to the insecure default. "
                "Set a strong SECRET_KEY before running in production."
            )
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        if not self.groq_api_key.strip():
            raise ValueError("GROQ_API_KEY is required in production")
        if self.ingestion_inline_fallback:
            raise ValueError(
                "INGESTION_INLINE_FALLBACK must be false in production "
                "(heavy embedding must not run in the API process)"
            )
        if not self.rate_limit_use_redis:
            raise ValueError("RATE_LIMIT_USE_REDIS must be true in production")
        if any("localhost" in origin.lower() for origin in self.cors_origins_list):
            raise ValueError("CORS_ORIGINS must not contain localhost in production")
        if self.metrics_enabled and not self.metrics_token.strip():
            raise ValueError("METRICS_TOKEN is required when metrics are enabled in production")
        if self.embedding_provider.lower() == "huggingface" and not self.huggingface_api_key.strip():
            raise ValueError(
                "HUGGINGFACE_API_KEY is required in production when EMBEDDING_PROVIDER=huggingface"
            )
        return self


settings = Settings()
