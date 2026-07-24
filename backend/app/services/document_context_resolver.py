"""Conversation-aware document resolution for RAG (pre-retrieval).

Resolves which document(s) a user message refers to using conversation
state and heuristics — no extra LLM or embedding calls.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document import Document
from app.providers.types import DocumentStatus
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

# Pronouns / deictic references → active or latest document
CONTEXTUAL_REF_RE = re.compile(
    r"\b("
    r"this\s+document|this\s+pdf|this\s+paper|this\s+file|this\s+upload|"
    r"the\s+document|the\s+pdf|the\s+paper|the\s+file|the\s+doc|"
    r"read\s+the\s+doc|read\s+the\s+file|can\s+you\s+read|"
    r"summarize\s+(?:this|the|my|it|uploaded)?|explain\s+(?:this|the|my|uploaded)?|"
    r"review\s+this|describe\s+this|"
    r"what\s+is\s+(?:this|the)\s+(?:document|pdf|file|paper)\s+about|"
    r"what'?s\s+(?:this|the)\s+(?:document|pdf|file|paper)\s+about|"
    r"what\s+is\s+this|what'?s\s+this|about\s+this|"
    r"what\s+does\s+(this|it)\s+say|key\s+points|key\s+topics|main\s+topics|"
    r"summarize\s+the\s+uploaded|explain\s+the\s+uploaded|explain\s+page|page\s+\d+|"
    r"the\s+uploaded\s+(pdf|document|file)|uploaded\s+(pdf|document|file)|"
    r"important\s+formulas|list\s+the\s+important|"
    r"\bits\b"  # "its strengths" / "its weaknesses" after upload
    r")\b",
    re.IGNORECASE,
)

# Multi-document compare / use-all intents
MULTI_DOC_RE = re.compile(
    r"\b("
    r"compare\s+both|compare\s+them|compare\s+these|"
    r"both\s+documents|both\s+files|both\s+pdfs|"
    r"all\s+(?:the\s+)?(?:uploaded\s+)?documents|"
    r"all\s+(?:the\s+)?(?:uploaded\s+)?files|"
    r"across\s+(?:all\s+)?(?:my\s+)?documents"
    r")\b",
    re.IGNORECASE,
)

# Strip common chat fluff when matching filenames
_FILENAME_NOISE_RE = re.compile(
    r"[\s_\-]+|\.(pdf|docx?|txt|md|markdown)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentResolution:
    """Result of conversation-aware document selection.

    document_ids:
      - None  → search all project documents (semantic fallback)
      - [..]  → metadata-filter retrieval to these IDs only
    """

    document_ids: list[UUID] | None
    reason: str
    active_document_id: UUID | None = None


def _normalize_name(name: str) -> str:
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return _FILENAME_NOISE_RE.sub("", stem).lower()


def _query_mentions_filename(query: str, filename: str) -> bool:
    """True if the query explicitly mentions this document's name or stem."""
    stem = filename.rsplit(".", 1)[0]
    for token in (filename, stem):
        if len(token.strip()) < 3:
            continue
        # Token boundary: avoid matching "a" inside "neural"
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        if pattern.search(query):
            return True

    # Compact form for multi-word titles ("Attention Is All You Need")
    norm = _normalize_name(filename)
    if len(norm) >= 6:
        q_norm = _normalize_name(query)
        if norm in q_norm:
            return True
    return False


def _find_explicit_matches(query: str, documents: list[Document]) -> list[Document]:
    """Match explicit document names / stems mentioned in the query."""
    if not documents:
        return []

    matched: list[Document] = []
    seen: set[UUID] = set()

    # Longer filenames first to prefer specific matches
    ranked = sorted(documents, key=lambda d: len(d.filename), reverse=True)
    for doc in ranked:
        if _query_mentions_filename(query, doc.filename) and doc.id not in seen:
            matched.append(doc)
            seen.add(doc.id)

    return matched


def resolve_target_documents(
    db: Session,
    project_id: UUID,
    query: str,
    *,
    active_document_id: UUID | None,
) -> DocumentResolution:
    """Apply Priority 1–4 document selection before vector retrieval."""
    ready = DocumentRepository.list_ready_by_project(db, project_id)
    if not ready:
        return DocumentResolution(document_ids=None, reason="no_ready_documents")

    ready_by_id = {d.id: d for d in ready}

    if active_document_id is not None and active_document_id not in ready_by_id:
        logger.info(
            "Document resolve: clearing stale active document %s (not Ready)",
            active_document_id,
        )
        active_document_id = None

    # Priority 1 — explicit document name(s)
    explicit = _find_explicit_matches(query, ready)
    if explicit:
        ids = [d.id for d in explicit]
        logger.info(
            "Document resolve: explicit → %s",
            [d.filename for d in explicit],
        )
        return DocumentResolution(
            document_ids=ids,
            reason="explicit_reference",
            active_document_id=ids[0] if len(ids) == 1 else active_document_id,
        )

    # Multi-doc compare → all ready documents (no single-doc filter)
    if MULTI_DOC_RE.search(query):
        logger.info("Document resolve: multi-doc compare → all ready (%d)", len(ready))
        return DocumentResolution(
            document_ids=None,
            reason="multi_document",
            active_document_id=active_document_id,
        )

    # Priority 2 / 3 — contextual ref or active document context
    has_contextual = bool(CONTEXTUAL_REF_RE.search(query))
    active = ready_by_id.get(active_document_id) if active_document_id else None

    if has_contextual:
        if active is not None:
            logger.info("Document resolve: contextual → active %s", active.filename)
            return DocumentResolution(
                document_ids=[active.id],
                reason="contextual_active",
                active_document_id=active.id,
            )
        # Priority 2: no active stored → most recently uploaded ready doc
        latest = ready[0]  # list_ready ordered by created_at desc
        logger.info("Document resolve: contextual → latest %s", latest.filename)
        return DocumentResolution(
            document_ids=[latest.id],
            reason="contextual_latest",
            active_document_id=latest.id,
        )

    # Priority 3 — active document for any subsequent doc-scoped chat
    # (classifier still gates GENERAL queries out of retrieval)
    if active is not None:
        logger.info("Document resolve: active context → %s", active.filename)
        return DocumentResolution(
            document_ids=[active.id],
            reason="active_document",
            active_document_id=active.id,
        )

    # Priority 4 — semantic across all
    logger.info("Document resolve: semantic fallback (all docs)")
    return DocumentResolution(
        document_ids=None,
        reason="semantic_all",
        active_document_id=None,
    )
