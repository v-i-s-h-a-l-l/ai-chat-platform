from functools import lru_cache

from app.services.groq_provider import GroqProvider
from app.services.llm_provider import LLMProvider


@lru_cache(maxsize=1)
def _get_provider_singleton() -> GroqProvider:
    return GroqProvider()


def get_llm_provider() -> LLMProvider:
    """FastAPI dependency — swap this to change the active LLM backend."""
    return _get_provider_singleton()
