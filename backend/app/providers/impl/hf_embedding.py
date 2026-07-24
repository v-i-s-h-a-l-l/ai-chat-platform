import asyncio
import logging
import time

import httpx

from app.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.impl.embedding_utils import (
    parse_batch_embeddings,
    query_text,
    text_to_sparse,
)
from app.providers.types import EmbeddingBatch
from app.utils.http_client import get_async_http_client

logger = logging.getLogger(__name__)

_MODEL_LOADING_STATUSES = {503, 524}


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Embeddings via Hugging Face Inference API (no local PyTorch)."""

    async def embed_query(self, text: str) -> tuple[list[float], dict[int, float] | None]:
        t0 = time.perf_counter()
        dense = (await self._embed_texts([query_text(text)]))[0]
        sparse = text_to_sparse(text)
        logger.info("HF query embedding: %.1fms", (time.perf_counter() - t0) * 1000)
        return dense, sparse

    async def embed_documents(self, texts: list[str]) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(dense=[], sparse=[])

        t0 = time.perf_counter()
        dense: list[list[float]] = []
        batch_size = settings.huggingface_embedding_batch_size
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            dense.extend(await self._embed_texts(batch))

        sparse = [text_to_sparse(text) for text in texts]
        logger.info(
            "HF batch embedding (%d texts, batch=%d): %.1fms",
            len(texts),
            batch_size,
            (time.perf_counter() - t0) * 1000,
        )
        return EmbeddingBatch(dense=dense, sparse=sparse)

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not settings.huggingface_api_key.strip():
            raise ValueError("HUGGINGFACE_API_KEY is required when EMBEDDING_PROVIDER=huggingface")

        url = (
            f"{settings.huggingface_api_url.rstrip('/')}/models/"
            f"{settings.embedding_model}"
        )
        headers = {"Authorization": f"Bearer {settings.huggingface_api_key.strip()}"}
        payload = {"inputs": texts[0]} if len(texts) == 1 else {"inputs": texts}

        client = get_async_http_client()
        last_error: Exception | None = None

        for attempt in range(settings.huggingface_max_retries + 1):
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=settings.huggingface_timeout_seconds,
                )
                if response.status_code in _MODEL_LOADING_STATUSES:
                    wait = settings.huggingface_retry_backoff_seconds * (attempt + 1)
                    logger.warning(
                        "HF model loading (HTTP %s) — retry in %.1fs",
                        response.status_code,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return parse_batch_embeddings(response.json(), len(texts))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= settings.huggingface_max_retries:
                    break
                wait = settings.huggingface_retry_backoff_seconds * (attempt + 1)
                logger.warning("HF embedding attempt %d failed: %s", attempt + 1, exc)
                await asyncio.sleep(wait)

        raise RuntimeError(f"Hugging Face embedding failed after retries: {last_error}")
