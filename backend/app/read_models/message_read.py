"""CQRS-lite read models — query DTOs decoupled from write ORM entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MessageReadModel:
    """Immutable projection used by message list / history APIs."""

    id: UUID
    project_id: UUID
    role: str
    content: str
    created_at: datetime
    web_search_used: bool
    documents_used: bool
