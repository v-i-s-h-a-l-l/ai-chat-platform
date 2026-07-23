from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMProvider(ABC):
    """Abstraction over a chat-completion LLM backend.

    Lets ChatService depend on a contract instead of a concrete vendor SDK/API,
    so providers can be swapped or mocked without touching orchestration code.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Return a full completion for the given messages."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Yield content deltas as they arrive from the provider."""

    @abstractmethod
    async def fast_complete(self, messages: list[dict[str, str]], *, max_tokens: int = 8) -> str:
        """Low-latency completion using a smaller/faster model, for classification-style tasks."""
