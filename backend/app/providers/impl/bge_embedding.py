import hashlib
import logging
import re
import time
from functools import lru_cache

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.types import EmbeddingBatch

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model, trust_remote_code=True)
        logger.info("Embedding model loaded")
    return _model


def _text_to_sparse(text: str) -> dict[int, float]:
    """Lightweight sparse vector for hybrid retrieval (keyword sensitivity).

    Uses a stable MD5-based hash so vectors are consistent across workers
    and process restarts (unlike Python's salted built-in hash()).
    """
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return {}
    sparse: dict[int, float] = {}
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest, 16) % 100_000
        sparse[idx] = sparse.get(idx, 0.0) + 1.0
    norm = sum(v * v for v in sparse.values()) ** 0.5 or 1.0
    return {k: v / norm for k, v in sparse.items()}


class BgeEmbeddingProvider(EmbeddingProvider):
    """Singleton BGE-M3 embeddings via sentence-transformers."""

    async def embed_query(self, text: str) -> tuple[list[float], dict[int, float] | None]:
        t0 = time.perf_counter()

        def _encode() -> tuple[list[float], dict[int, float]]:
            model = _get_model()
            dense = model.encode(text, normalize_embeddings=True).tolist()
            sparse = _text_to_sparse(text)
            return dense, sparse

        result = await run_in_threadpool(_encode)
        logger.info("Query embedding: %.1fms", (time.perf_counter() - t0) * 1000)
        return result

    async def embed_documents(self, texts: list[str]) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(dense=[], sparse=[])

        t0 = time.perf_counter()

        def _encode_batch() -> EmbeddingBatch:
            model = _get_model()
            dense = model.encode(texts, normalize_embeddings=True, batch_size=64).tolist()
            sparse = [_text_to_sparse(t) for t in texts]
            return EmbeddingBatch(dense=dense, sparse=sparse)

        result = await run_in_threadpool(_encode_batch)
        logger.info("Batch embedding (%d texts): %.1fms", len(texts), (time.perf_counter() - t0) * 1000)
        return result


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    return BgeEmbeddingProvider()
