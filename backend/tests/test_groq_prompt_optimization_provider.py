from app.services.groq_prompt_optimization_provider import GroqPromptOptimizationProvider
from app.services.prompt_optimization_provider import PromptOptimizationProviderResult


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
