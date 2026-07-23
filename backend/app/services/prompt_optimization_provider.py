from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptOptimizationProviderResult:
    """Raw result from an LLM prompt-optimization provider."""

    safe: bool
    reason: str | None = None
    improved_prompt: str | None = None
    changes: list[str] = field(default_factory=list)


class PromptOptimizationProvider(ABC):
    """Abstraction for safety review + prompt proofreading backends."""

    @abstractmethod
    async def analyze_and_optimize(
        self,
        project_name: str,
        description: str,
        system_prompt: str,
    ) -> PromptOptimizationProviderResult:
        """Run safety validation and (if safe) prompt optimization in one call."""
