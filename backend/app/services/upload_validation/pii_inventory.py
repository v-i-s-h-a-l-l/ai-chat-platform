"""PII signal inventory for upload decisions (separate from guardrails/pii.py)."""

from __future__ import annotations

import re

from app.services.upload_validation.types import PiiInventory

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s\-]?)?(?:\(\d{2,4}\)[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}(?!\d)"
)
_AADHAAR_RE = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")
_NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b")

_NAME_STOPWORDS = frozenset(
    {
        "United States",
        "New York",
        "San Francisco",
        "Machine Learning",
        "Deep Learning",
        "Attention Is",
        "Large Language",
        "Natural Language",
        "Neural Network",
        "Computer Science",
        "Introduction To",
        "Table Of",
    }
)


def build_pii_inventory(text: str) -> PiiInventory:
    emails = _EMAIL_RE.findall(text)
    phones = [p for p in _PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) >= 10]
    aadhaar = [m for m in _AADHAAR_RE.findall(text) if _looks_like_aadhaar(m)]
    pan = _PAN_RE.findall(text)
    passports = _find_passport_candidates(text)
    names = _estimate_names(text)

    return PiiInventory(
        names=names,
        emails=len(set(emails)),
        phone_numbers=len(set(phones)),
        passport_numbers=len(set(passports)),
        aadhaar_numbers=len(set(aadhaar)),
        pan_numbers=len(set(pan)),
    )


def _looks_like_aadhaar(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) == 12 and not digits.startswith("0")


def _find_passport_candidates(text: str) -> list[str]:
    if not re.search(r"\bpassport\b", text, re.IGNORECASE):
        return []
    return _PASSPORT_RE.findall(text)


def _estimate_names(text: str) -> int:
    matches = []
    for match in _NAME_RE.findall(text):
        if match in _NAME_STOPWORDS:
            continue
        if any(word.lower() in {"the", "and", "for", "with", "from", "this", "that"} for word in match.split()):
            continue
        matches.append(match)
    return len(set(matches))
