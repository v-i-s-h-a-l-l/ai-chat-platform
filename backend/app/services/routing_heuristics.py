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


_DOCUMENT_ACCESS_PATTERNS = re.compile(
    r"\b("
    r"can you read|can you see|can you now see|do you see|did you get|have you read|"
    r"are you able to read|are you able to see|"
    r"read the doc|read the file|read my doc|read my file|read this doc|read this file|"
    r"see the doc|see the file|see my doc|see my upload|"
    r"have the file|got the file|received the file|access the doc|access the file|"
    r"can you access|did the upload work|is the file there|is it uploaded|"
    r"now can you read|know see|still see|still can't see|still cannot see|"
    r"document i uploaded|doc i uploaded|file i uploaded|pdf i uploaded|"
    r"i uploaded (?:the |my |a |this )?(?:doc|document|file|pdf)|"
    r"(?:doc|document|file|pdf) i uploaded|"
    r"uploaded (?:the |my |this )?(?:doc|document|file|pdf)"
    r")\b",
    re.IGNORECASE,
)

_UPLOAD_SIGNAL = re.compile(
    r"\b(uploaded|upload|my upload|the upload|i uploaded)\b",
    re.IGNORECASE,
)

_DOC_FILE_SIGNAL = re.compile(
    r"\b(documents?|docs?|files?|pdfs?|papers?)\b",
    re.IGNORECASE,
)

_VISIBILITY_SIGNAL = re.compile(
    r"\b("
    r"see|read|access|visible|have it|got it|received|"
    r"can you|do you|are you able|able to"
    r")\b",
    re.IGNORECASE,
)


def _normalize_query(text: str) -> str:
    """Fix common typos so upload/visibility heuristics still match."""
    normalized = text.lower()
    normalized = re.sub(r"docu?ments?", "document", normalized)
    normalized = re.sub(r"\bdocs?\b", "document", normalized)
    normalized = re.sub(r"\bpdfs?\b", "pdf", normalized)
    return normalized


def is_document_access_query(question: str) -> bool:
    """True when the user asks whether an uploaded document is visible/readable."""
    text = question.strip()
    if not text:
        return False

    if _DOCUMENT_ACCESS_PATTERNS.search(text):
        return True

    normalized = _normalize_query(text)
    if normalized != text.lower() and _DOCUMENT_ACCESS_PATTERNS.search(normalized):
        return True

    has_upload = bool(_UPLOAD_SIGNAL.search(normalized))
    has_doc = bool(_DOC_FILE_SIGNAL.search(normalized))
    has_visibility = bool(_VISIBILITY_SIGNAL.search(normalized))

    # "can you see the CPET document I uploaded" / typos like "docuiment"
    if has_upload and (has_doc or has_visibility):
        return True
    if has_visibility and has_doc:
        return True

    return False


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

    # Upload visibility checks are never dynamic external lookups.
    if is_document_access_query(text):
        return "stable"

    is_dynamic = bool(_DYNAMIC_PATTERNS.search(text))
    is_stable = bool(_STABLE_PATTERNS.search(text))

    if is_dynamic and not is_stable:
        return "dynamic"
    if is_stable and not is_dynamic:
        return "stable"
    return None
