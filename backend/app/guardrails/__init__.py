"""
Guardrails: zero-latency content filtering for PII, profanity, and harmful intent.

All checks use pre-compiled regex with no external API calls.
Target overhead: <1ms per message.
"""

import logging

from app.guardrails.content_policy import detect_harmful_intent, detect_severe_profanity
from app.guardrails.exceptions import GuardrailViolationError
from app.guardrails.pii import detect_sensitive_financial_data

logger = logging.getLogger(__name__)


def check_chat(message: str) -> None:
    """
    Check chat message for violations. Raises GuardrailViolationError if blocked.

    Runs in order: PII → profanity → harmful intent (fail-fast).
    """
    # 1. Check for sensitive financial data (cards, CVV, MPIN, OTP)
    pii_violation = detect_sensitive_financial_data(message)
    if pii_violation:
        logger.warning("Chat blocked: PII violation (%s)", pii_violation)
        raise GuardrailViolationError(
            "Your message appears to contain sensitive payment or authentication data "
            "(card numbers, CVV, MPIN, or OTP). Please remove it and try again.",
            code="pii_violation",
        )

    # 2. Check for severe profanity (explicit terms only)
    if detect_severe_profanity(message):
        logger.warning("Chat blocked: severe profanity")
        raise GuardrailViolationError(
            "Your message contains language that isn't allowed. Please rephrase.",
            code="profanity_violation",
        )

    # 3. Check for harmful intent (violence, illegal activity)
    harmful = detect_harmful_intent(message)
    if harmful:
        logger.warning("Chat blocked: harmful intent (%s)", harmful)
        raise GuardrailViolationError(
            "I can't help with requests that involve harm, violence, or illegal activity.",
            code="harmful_intent",
        )


def check_document(filename: str, data: bytes) -> None:
    """
    Check document upload for sensitive financial data. Raises GuardrailViolationError if blocked.

    Scans filename + UTF-8 decoded content (lossy decode, no full PDF parse).
    """
    # Check filename
    pii_violation = detect_sensitive_financial_data(filename)
    if pii_violation:
        logger.warning("Upload blocked: PII in filename (%s)", pii_violation)
        raise GuardrailViolationError(
            "Upload rejected: filename appears to contain sensitive payment or authentication data. "
            "Please rename the file and try again.",
            code="pii_violation",
        )

    # Check file content (decode as UTF-8, ignore errors)
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        # If decode fails entirely, allow upload (binary files)
        return

    pii_violation = detect_sensitive_financial_data(text)
    if pii_violation:
        logger.warning("Upload blocked: PII in file content (%s)", pii_violation)
        raise GuardrailViolationError(
            "Upload rejected: file appears to contain sensitive payment or authentication data "
            "(card numbers, CVV, MPIN, or OTP). Please remove it and try again.",
            code="pii_violation",
        )


__all__ = ["check_chat", "check_document", "GuardrailViolationError"]
