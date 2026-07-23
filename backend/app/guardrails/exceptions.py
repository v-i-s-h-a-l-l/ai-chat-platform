"""Guardrail exceptions."""


class GuardrailViolationError(Exception):
    """Raised when content violates guardrails (PII, profanity, harmful intent)."""

    def __init__(self, message: str, code: str = "guardrail_violation"):
        self.message = message
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:
        return self.message
