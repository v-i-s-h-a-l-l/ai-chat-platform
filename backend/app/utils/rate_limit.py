"""Rate limiting helpers for FastAPI routes."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=settings.rate_limit_enabled,
    storage_uri=settings.redis_url if settings.rate_limit_use_redis else "memory://",
)
