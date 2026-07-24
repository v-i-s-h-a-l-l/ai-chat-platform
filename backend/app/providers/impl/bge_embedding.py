import logging
import time

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.impl.embedding_utils import query_text as _query_text, text_to_sparse as _text_to_sparse
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


class BgeEmbeddingProvider(EmbeddingProvider):
    """Singleton BGE embeddings via sentence-transformers."""

    async def embed_query(self, text: str) -> tuple[list[float], dict[int, float] | None]:
        t0 = time.perf_counter()
        encoded_text = _query_text(text)

        def _encode() -> tuple[list[float], dict[int, float]]:
            model = _get_model()
            dense = model.encode(encoded_text, normalize_embeddings=True).tolist()
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
