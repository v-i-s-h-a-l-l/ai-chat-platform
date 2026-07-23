"""PII and sensitive financial data detection using regex + Luhn validation."""

import re
from typing import Optional


# Credit card number pattern: 13-19 digits with optional spaces/dashes
_CARD_PATTERN = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,7}\b")

# CVV/CVC patterns near keywords
_CVV_KEYWORDS = re.compile(
    r"\b(cvv|cvc|security\s*code|card\s*password|verification\s*value)\b", re.IGNORECASE
)
_CVV_DIGITS = re.compile(r"\b\d{3,4}\b")

# MPIN/PIN patterns near keywords
_PIN_KEYWORDS = re.compile(
    r"\b(mpin|upi\s*pin|atm\s*pin|card\s*pin|banking\s*pin)\b", re.IGNORECASE
)
_PIN_DIGITS = re.compile(r"\b\d{4,6}\b")

# OTP patterns near keywords
_OTP_KEYWORDS = re.compile(
    r"\b(otp|one\s*time\s*password|verification\s*code|auth\s*code|confirmation\s*code)\b",
    re.IGNORECASE,
)
_OTP_DIGITS = re.compile(r"\b\d{4,8}\b")

# Explicit card labels
_CARD_LABELS = re.compile(
    r"\b(card\s*number|card\s*no|credit\s*card|debit\s*card|expiry|valid\s*thru|exp\s*date)\b",
    re.IGNORECASE,
)


def _luhn_check(card_number: str) -> bool:
    """Validate card number using Luhn algorithm."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


def detect_sensitive_financial_data(text: str) -> Optional[str]:
    """
    Detect sensitive payment/authentication data in text.

    Returns violation message if found, None otherwise.
    Runs all checks; stops at first match to minimize latency.
    """
    # Check for credit/debit card numbers with Luhn validation
    for match in _CARD_PATTERN.finditer(text):
        candidate = match.group()
        if _luhn_check(candidate):
            return "credit/debit card number detected"

    # Check for CVV near keywords
    if _CVV_KEYWORDS.search(text):
        # Look for 3-4 digit numbers within ~100 chars
        window_start = max(0, _CVV_KEYWORDS.search(text).start() - 50)
        window_end = min(len(text), _CVV_KEYWORDS.search(text).end() + 50)
        window = text[window_start:window_end]
        if _CVV_DIGITS.search(window):
            return "CVV/CVC detected"

    # Check for MPIN/PIN near keywords
    if _PIN_KEYWORDS.search(text):
        window_start = max(0, _PIN_KEYWORDS.search(text).start() - 50)
        window_end = min(len(text), _PIN_KEYWORDS.search(text).end() + 50)
        window = text[window_start:window_end]
        if _PIN_DIGITS.search(window):
            return "MPIN/PIN detected"

    # Check for OTP near keywords
    if _OTP_KEYWORDS.search(text):
        window_start = max(0, _OTP_KEYWORDS.search(text).start() - 50)
        window_end = min(len(text), _OTP_KEYWORDS.search(text).end() + 50)
        window = text[window_start:window_end]
        if _OTP_DIGITS.search(window):
            return "OTP detected"

    # Check for explicit card labels with nearby digit groups
    if _CARD_LABELS.search(text):
        window_start = max(0, _CARD_LABELS.search(text).start() - 50)
        window_end = min(len(text), _CARD_LABELS.search(text).end() + 100)
        window = text[window_start:window_end]
        if _CARD_PATTERN.search(window):
            return "card details identified"

    return None
