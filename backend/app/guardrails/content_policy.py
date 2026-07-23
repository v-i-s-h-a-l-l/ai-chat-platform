"""Content policy: severe profanity and harmful intent detection."""

import re
from typing import Optional


# Severe profanity blocklist (explicit terms only, not mild insults)
_SEVERE_PROFANITY = re.compile(
    r"\b("
    r"motherfucker|mother\s*fucker|m\.?f\.|mf\b|"
    r"son\s*of\s*a\s*bitch|sonofabitch|"
    r"fuck|fucking|fucked|fucker|"
    r"shit\b|shitty|"
    r"bitch(?!es\s+brew|es\s+be\s+crazy)|"  # Block "bitch" as slur, allow rare phrases
    r"cunt|whore|slut|"
    r"asshole|arsehole|"
    r"bastard|"
    r"damn\s*it|dammit|"
    r"piss\s*off|pissed\s*off"
    r")\b",
    re.IGNORECASE,
)

# Obfuscation normalization patterns
_REPEATED_CHARS = re.compile(r"(.)\1{2,}")  # e.g., "fuuuuck" -> "fuck"
_ASTERISK_SUBSTITUTION = re.compile(r"[*@#$]")  # e.g., "f*ck" -> "fck"


def _normalize_light(text: str) -> str:
    """Light normalization to catch common obfuscation."""
    # Collapse repeated characters
    text = _REPEATED_CHARS.sub(r"\1", text)
    # Remove common substitution characters
    text = _ASTERISK_SUBSTITUTION.sub("", text)
    return text


# Harmful intent patterns
_HARMFUL_VIOLENCE = re.compile(
    r"\b(how\s+to\s+(kill|murder|assassinate)|"
    r"ways\s+to\s+(kill|murder|harm)|"
    r"(kill|murder|harm)\s+\d+\s+people|"
    r"(kill|murder|harm)\s+(many|multiple|mass)|"
    r"mass\s+(shooting|killing|murder)|"
    r"(bomb|explosive|weapon)\s+(instructions|tutorial|guide|how))\b",
    re.IGNORECASE,
)

_HARMFUL_SEXUAL = re.compile(
    r"\b(how\s+to\s+(rape|sexually\s+assault)|"
    r"rape\s+(instructions|guide|tutorial))\b",
    re.IGNORECASE,
)

_HARMFUL_ILLEGAL = re.compile(
    r"\b(make\s+(meth|heroin|cocaine|bomb|explosive)|"
    r"(drug|weapon)\s+(manufacturing|production)\s+(guide|instructions))\b",
    re.IGNORECASE,
)


def detect_severe_profanity(text: str) -> bool:
    """Detect severe explicit profanity (NOT mild insults like 'idiot')."""
    normalized = _normalize_light(text)
    return bool(_SEVERE_PROFANITY.search(text) or _SEVERE_PROFANITY.search(normalized))


def detect_harmful_intent(text: str) -> Optional[str]:
    """
    Detect harmful/illegal intent patterns.

    Returns violation type if found, None otherwise.
    """
    if _HARMFUL_VIOLENCE.search(text):
        return "violent harm"

    if _HARMFUL_SEXUAL.search(text):
        return "sexual violence"

    if _HARMFUL_ILLEGAL.search(text):
        return "illegal activity"

    return None
