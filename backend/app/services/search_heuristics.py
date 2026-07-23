import re

# Time-sensitive signals → search immediately (skip LLM decision)
_SEARCH_YES_PATTERNS = re.compile(
    r"\b("
    r"latest|today|current|recent|recently|this week|this month|this year|"
    r"right now|live|breaking|news|weather|stock price|share price|"
    r"sports score|who won|election result|"
    r"2025|2026|"
    r"announced|released|launched|"
    r"update on|status of"
    r")\b",
    re.IGNORECASE,
)

# Clearly static knowledge → skip search (skip LLM decision)
_SEARCH_NO_PATTERNS = re.compile(
    r"\b("
    r"explain|what is|what are|how does|how do|how to|"
    r"write code|implement|debug|fix this|algorithm|"
    r"data structure|time complexity|space complexity|"
    r"python|javascript|java\b|typescript|react|sql|"
    r"difference between|compare|define|concept of|"
    r"machine learning|deep learning|neural network|"
    r"operating system|dbms|system design|"
    r"example of|show me code|help me code"
    r")\b",
    re.IGNORECASE,
)


def heuristic_search_decision(question: str) -> bool | None:
    """
    Fast local classification — no API call.

    Returns:
        True  → definitely needs web search
        False → definitely does NOT need web search
        None  → ambiguous, fall back to LLM decision
    """
    text = question.strip()
    if not text:
        return False

    has_yes = bool(_SEARCH_YES_PATTERNS.search(text))
    has_no = bool(_SEARCH_NO_PATTERNS.search(text))

    if has_yes:
        return True
    if has_no:
        return False
    return None
