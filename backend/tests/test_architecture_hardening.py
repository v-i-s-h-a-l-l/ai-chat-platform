import pytest

from app.config import Settings
from app.services.ingestion_errors import IngestionQueueUnavailableError
from app.services.ingestion_queue import enqueue_document_ingestion
from app.read_models.message_read import MessageReadModel
from uuid import uuid4
from datetime import datetime, timezone


def test_ingestion_queue_unavailable_error_message():
    err = IngestionQueueUnavailableError("doc-1")
    assert "queue is unavailable" in str(err).lower()
    assert err.document_id == "doc-1"


def test_production_rejects_inline_ingestion_fallback():
    with pytest.raises(ValueError, match="INGESTION_INLINE_FALLBACK"):
        Settings(
            environment="production",
            secret_key="not-the-default-secret-key-value",
            cookie_secure=True,
            groq_api_key="gsk_test",
            ingestion_inline_fallback=True,
            rate_limit_use_redis=True,
            cors_origins="https://app.example.com",
            metrics_token="metrics-secret",
        )


def test_production_requires_redis_rate_limits():
    with pytest.raises(ValueError, match="RATE_LIMIT_USE_REDIS"):
        Settings(
            environment="production",
            secret_key="not-the-default-secret-key-value",
            cookie_secure=True,
            groq_api_key="gsk_test",
            rate_limit_use_redis=False,
            cors_origins="https://app.example.com",
            metrics_token="metrics-secret",
        )


def test_production_rejects_localhost_cors():
    with pytest.raises(ValueError, match="localhost"):
        Settings(
            environment="production",
            secret_key="not-the-default-secret-key-value",
            cookie_secure=True,
            groq_api_key="gsk_test",
            rate_limit_use_redis=True,
            cors_origins="http://localhost:5173",
            metrics_token="metrics-secret",
        )


def test_message_read_model_is_immutable():
    model = MessageReadModel(
        id=uuid4(),
        project_id=uuid4(),
        role="assistant",
        content="hello",
        created_at=datetime.now(timezone.utc),
        web_search_used=False,
        documents_used=True,
    )
    with pytest.raises(Exception):
        model.content = "mutated"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_enqueue_fail_closed_without_redis(monkeypatch):
    monkeypatch.setattr(
        "app.services.ingestion_queue.settings.ingestion_inline_fallback",
        False,
    )

    async def boom():
        raise ConnectionError("redis down")

    monkeypatch.setattr("app.services.ingestion_queue._get_pool", boom)

    with pytest.raises(IngestionQueueUnavailableError):
        await enqueue_document_ingestion(uuid4())
