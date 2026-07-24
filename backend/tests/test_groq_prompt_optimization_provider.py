from app.services.groq_prompt_optimization_provider import (
    GroqPromptOptimizationProvider,
    _OPTIMIZER_SYSTEM,
)
from app.services.prompt_optimization_provider import PromptOptimizationProviderResult


def test_optimizer_system_includes_profanity_and_typo_rules():
    assert "profanity" in _OPTIMIZER_SYSTEM.lower()
    assert "motherfucker" in _OPTIMIZER_SYSTEM.lower()
    assert "GSOD codr" in _OPTIMIZER_SYSTEM
    assert "good coder" in _OPTIMIZER_SYSTEM


def test_parse_json_content_strips_fences():
    raw = '```json\n{"safe": true, "reason": null, "improvedPrompt": "Hi", "changes": []}\n```'
    parsed = GroqPromptOptimizationProvider._parse_json_content(raw)
    assert parsed["safe"] is True
    assert parsed["improvedPrompt"] == "Hi"


def test_normalize_unsafe_result():
    data = {"safe": False, "reason": "Harmful intent detected."}
    result = GroqPromptOptimizationProvider._normalize_result(data, "original")
    assert result == PromptOptimizationProviderResult(
        safe=False,
        reason="Harmful intent detected.",
        improved_prompt=None,
        changes=[],
    )


def test_normalize_unsafe_profanity_result():
    data = {
        "safe": False,
        "reason": "Vulgar language is not allowed on YelloBot.",
    }
    result = GroqPromptOptimizationProvider._normalize_result(
        data, "You are a certified motherfucker."
    )
    assert result.safe is False
    assert result.improved_prompt is None
    assert "vulgar" in (result.reason or "").lower()


def test_normalize_safe_typo_correction_result():
    data = {
        "safe": True,
        "improvedPrompt": "You are a good coder.",
        "changes": ["Corrected spelling"],
    }
    result = GroqPromptOptimizationProvider._normalize_result(
        data, "You are a GSOD codr."
    )
    assert result.safe is True
    assert result.improved_prompt == "You are a good coder."
    assert result.changes == ["Corrected spelling"]


def test_normalize_safe_result():
    data = {
        "safe": True,
        "improvedPrompt": "You are helpful.",
        "changes": ["Fixed grammar"],
    }
    result = GroqPromptOptimizationProvider._normalize_result(data, "You helpful.")
    assert result.safe is True
    assert result.improved_prompt == "You are helpful."
    assert result.changes == ["Fixed grammar"]
