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
    qdrant_collection: str = "chatbot_chunks"
    document_storage_path: str = "./storage/documents"
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_dimension: int = 1024
    rag_top_k: int = 20
    rag_rerank_top_k: int = 5
    rag_hybrid_dense_weight: float = 0.7
    rag_mmr_lambda: float = 0.5
    rag_max_upload_mb: int = 25
    ingestion_max_retries: int = 3

    # Guardrails
    guardrails_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()

if settings.is_production and settings.secret_key == "change-me-in-production":
    raise RuntimeError(
        "SECRET_KEY is still set to the insecure default. "
        "Set a strong SECRET_KEY in the environment before running in production."
    )
