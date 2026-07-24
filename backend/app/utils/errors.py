"""Client-safe error messages — log details server-side, never leak internals."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

GENERIC_CLIENT_ERROR = "An unexpected error occurred. Please try again."
GENERIC_LLM_ERROR = "Failed to generate a response. Please try again."
GENERIC_EXPORT_ERROR = "Export failed. Please try again."
GENERIC_OPTIMIZE_ERROR = "Prompt optimization failed. Please try again."


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
