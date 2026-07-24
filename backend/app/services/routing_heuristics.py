"""Heuristics for classifying questions as stable knowledge vs dynamic/current."""

import re

# Time-sensitive or external information — prefer web search when docs are insufficient.
_DYNAMIC_PATTERNS = re.compile(
    r"\b("
    r"salary|salaries|compensation|package|packages|ctc|lpa|pay scale|pay band|"
    r"ceo|cfo|cto|founder|co-founder|leadership|"
    r"funding|funded|valuation|revenue|headcount|employees|company size|"
    r"stock price|share price|market cap|"
    r"acquisition|acquired|merger|"
    r"hiring|openings|job openings|recruiting|"
    r"latest|recent news|breaking|today|current|right now|this year|"
    r"weather|"
    r"interview experience|glassdoor|"
    r"regulation|regulatory|"
    r"2025|2026"
    r")\b",
    re.IGNORECASE,
)

# Stable conceptual knowledge — prefer model knowledge when docs are insufficient.
_STABLE_PATTERNS = re.compile(
    r"\b("
    r"explain|what is|what are|how does|how do|how to|"
    r"difference between|compare|define|concept of|"
    r"machine learning|deep learning|neural network|supervised|unsupervised|"
    r"transformer|transformers|cnn|rnn|docker|kubernetes|"
    r"algorithm|data structure|time complexity|"
    r"python|javascript|typescript|react|sql|"
    r"write code|implement|debug|example of"
    r")\b",
    re.IGNORECASE,
)


def heuristic_question_nature(question: str) -> str | None:
    """
    Fast local classification for routing fallback decisions.

    Returns:
        "dynamic" — time-sensitive / external info
        "stable"  — conceptual / general knowledge
        None      — ambiguous, fall back to LLM
    """
    text = question.strip()
    if not text:
        return "stable"

    is_dynamic = bool(_DYNAMIC_PATTERNS.search(text))
    is_stable = bool(_STABLE_PATTERNS.search(text))

    if is_dynamic and not is_stable:
        return "dynamic"
    if is_stable and not is_dynamic:
        return "stable"
    return None
