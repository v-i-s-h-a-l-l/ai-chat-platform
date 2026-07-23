from functools import lru_cache

from app.services.groq_prompt_optimization_provider import GroqPromptOptimizationProvider
from app.services.prompt_optimization_provider import PromptOptimizationProvider
from app.services.prompt_optimization_service import PromptOptimizationService


@lru_cache(maxsize=1)
def _get_provider_singleton() -> GroqPromptOptimizationProvider:
    return GroqPromptOptimizationProvider()


def get_prompt_optimization_provider() -> PromptOptimizationProvider:
    """FastAPI dependency — swap implementation to change optimization backend."""
    return _get_provider_singleton()


def get_prompt_optimization_service() -> PromptOptimizationService:
    return PromptOptimizationService(get_prompt_optimization_provider())
