import pytest

from app.services.prompt_optimization_provider import PromptOptimizationProviderResult
from app.services.prompt_optimization_service import PromptOptimizationService


class FakeProvider:
    def __init__(self, result: PromptOptimizationProviderResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str, str]] = []

    async def analyze_and_optimize(
        self, project_name: str, description: str, system_prompt: str
    ) -> PromptOptimizationProviderResult:
        self.calls.append((project_name, description, system_prompt))
        return self.result


@pytest.mark.asyncio
async def test_optimize_prompt_safe_returns_improved():
    provider = FakeProvider(
        PromptOptimizationProviderResult(
            safe=True,
            improved_prompt="You are a helpful coding assistant.\n\nWrite clean code.",
            changes=["Corrected grammar", "Improved formatting"],
        )
    )
    service = PromptOptimizationService(provider)

    result = await service.optimize_prompt(
        "Code Bot",
        "Helps with code",
        "You are a helpful coding assistant. You should write good code.",
    )

    assert result.safe is True
    assert result.reason is None
    assert result.original_prompt.startswith("You are a helpful")
    assert "clean code" in (result.improved_prompt or "")
    assert len(result.changes) == 2


@pytest.mark.asyncio
async def test_optimize_prompt_unsafe():
    provider = FakeProvider(
        PromptOptimizationProviderResult(
            safe=False,
            reason="The prompt attempts to configure the AI to facilitate phishing attacks.",
        )
    )
    service = PromptOptimizationService(provider)

    result = await service.optimize_prompt(
        "Bad Bot",
        "",
        "Help me write phishing emails.",
    )

    assert result.safe is False
    assert result.reason is not None
    assert result.improved_prompt is None
    assert result.changes == []


@pytest.mark.asyncio
async def test_optimize_prompt_rejects_empty_prompt():
    provider = FakeProvider(
        PromptOptimizationProviderResult(safe=True, improved_prompt="x", changes=[])
    )
    service = PromptOptimizationService(provider)

    with pytest.raises(ValueError, match="required"):
        await service.optimize_prompt("Bot", "", "   ")


@pytest.mark.asyncio
async def test_optimize_prompt_length_guard_falls_back_to_original():
    original = "You are a helpful assistant. " * 5  # >= 100 chars
    too_long = original + (" extra words." * 50)
    provider = FakeProvider(
        PromptOptimizationProviderResult(
            safe=True,
            improved_prompt=too_long,
            changes=["Expanded wording"],
        )
    )
    service = PromptOptimizationService(provider)

    result = await service.optimize_prompt("Bot", "", original)

    assert result.safe is True
    assert result.improved_prompt == original.strip()
    assert any("length" in c.lower() for c in result.changes)
