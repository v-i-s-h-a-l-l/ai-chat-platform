"""Client-safe error messages — log details server-side, never leak internals."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CLIENT_ERROR_MAX_LEN = 200

GENERIC_CLIENT_ERROR = "An unexpected error occurred. Please try again."
GENERIC_LLM_ERROR = "Failed to generate a response. Please try again."
GENERIC_EXPORT_ERROR = "Export failed. Please try again."
GENERIC_OPTIMIZE_ERROR = "Prompt optimization failed. Please try again."


def truncate_client_error(message: str, *, max_len: int = CLIENT_ERROR_MAX_LEN) -> str:
    text = message.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def sanitize_error_for_client(
    exc: BaseException,
    *,
    context: str,
    public_message: str = GENERIC_CLIENT_ERROR,
    allow_value_error: bool = True,
) -> str:
    """Log the full exception and return a safe client-facing message."""
    logger.exception("%s failed", context)
    if allow_value_error and isinstance(exc, ValueError):
        return str(exc)
    return public_message
