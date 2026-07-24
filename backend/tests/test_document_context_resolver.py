"""Tests for conversation-aware document resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock

from app.services.document_context_resolver import (
    DocumentResolution,
    resolve_target_documents,
)
from app.services.query_classifier import classify_query
from app.providers.types import QueryType


@dataclass
class FakeDoc:
    id: object
    filename: str
    created_at: datetime


def _docs(*names: str) -> list[FakeDoc]:
    base = datetime.now(timezone.utc)
    # First name = newest (list_ready returns newest first)
    return [
        FakeDoc(id=uuid4(), filename=name, created_at=base)
        for name in names
    ]


def test_contextual_this_document_uses_active(monkeypatch):
    docs = _docs("MathCo JD.pdf", "Resume.pdf")
    active = docs[0]

    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )

    result = resolve_target_documents(
        MagicMock(), uuid4(), "What is this document about?", active_document_id=active.id
    )
    assert result.document_ids == [active.id]
    assert result.reason == "contextual_active"


def test_contextual_without_active_uses_latest(monkeypatch):
    docs = _docs("PaperB.pdf", "PaperA.pdf")
    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )
    result = resolve_target_documents(
        MagicMock(), uuid4(), "Summarize this.", active_document_id=None
    )
    assert result.document_ids == [docs[0].id]
    assert result.reason == "contextual_latest"


def test_explicit_filename_overrides_active(monkeypatch):
    docs = _docs("SOP.pdf", "Resume.pdf")
    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )
    result = resolve_target_documents(
        MagicMock(),
        uuid4(),
        "What improvements do you suggest for the SOP?",
        active_document_id=docs[1].id,  # active = Resume
    )
    assert result.document_ids == [docs[0].id]
    assert result.reason == "explicit_reference"


def test_compare_both_uses_all_documents(monkeypatch):
    docs = _docs("PaperB.pdf", "PaperA.pdf")
    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )
    result = resolve_target_documents(
        MagicMock(), uuid4(), "Compare both.", active_document_id=docs[0].id
    )
    assert result.document_ids is None
    assert result.reason == "multi_document"


def test_active_document_scopes_follow_up(monkeypatch):
    docs = _docs("Resume.pdf", "Older.pdf")
    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )
    result = resolve_target_documents(
        MagicMock(),
        uuid4(),
        "What are its strengths?",
        active_document_id=docs[0].id,
    )
    assert result.document_ids == [docs[0].id]
    assert result.reason in {"contextual_active", "active_document"}


def test_semantic_fallback_when_no_active(monkeypatch):
    docs = _docs("A.pdf", "B.pdf")
    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )
    result = resolve_target_documents(
        MagicMock(),
        uuid4(),
        "How do neural networks learn?",
        active_document_id=None,
    )
    assert result.document_ids is None
    assert result.reason == "semantic_all"


def test_classifier_contextual_what_is_this_about_is_document():
    assert classify_query("What is this about?", has_documents=True) == QueryType.DOCUMENT
    assert classify_query("What is this document about?", has_documents=True) == QueryType.DOCUMENT


def test_read_the_doc_resolves_contextually(monkeypatch):
    docs = _docs("NIPS-2017-attention-is-all-you-need-Paper.pdf")
    monkeypatch.setattr(
        "app.services.document_context_resolver.DocumentRepository.list_ready_by_project",
        lambda db, project_id: docs,
    )
    result = resolve_target_documents(
        MagicMock(), uuid4(), "now can you read the doc", active_document_id=docs[0].id
    )
    assert result.document_ids == [docs[0].id]
    assert result.reason == "contextual_active"
    assert classify_query("now can you read the doc", has_documents=True) == QueryType.DOCUMENT


def test_classifier_general_without_docs():
    assert classify_query("What is this about?", has_documents=False) == QueryType.GENERAL
