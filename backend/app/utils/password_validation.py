"""Shared password strength rules for registration."""

from __future__ import annotations

import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_UPPERCASE_RE = re.compile(r"[A-Z]")
PASSWORD_SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")


def validate_password_strength(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters long")
    if not PASSWORD_UPPERCASE_RE.search(password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not PASSWORD_SPECIAL_RE.search(password):
        raise ValueError("Password must contain at least one special character")
    return password
