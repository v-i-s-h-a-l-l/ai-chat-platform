from functools import lru_cache

from app.config import settings
from app.providers.base import EmbeddingProvider
from app.providers.impl.bge_embedding import BgeEmbeddingProvider
from app.providers.impl.hf_embedding import HuggingFaceEmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider.lower() == "huggingface":
        return HuggingFaceEmbeddingProvider()
    return BgeEmbeddingProvider()
