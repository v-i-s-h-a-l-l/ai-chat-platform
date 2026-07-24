"""Classify queries to avoid unnecessary retrieval."""

import logging
import re

from app.providers.types import QueryType

logger = logging.getLogger(__name__)

DOCUMENT_SIGNALS = re.compile(
    r"\b("
    r"documents?|uploaded|upload|file|files|pdfs?|the doc|my doc|this doc|read the doc|"
    r"according to|in the text|from the doc|"
    r"what does it say|summarize|summary of|based on my|my upload|"
    r"in my document|the paper|the report|the article|this paper|this pdf|"
    r"this document|this file|review (it|this)|key points|key topics|main topics|"
    r"weaknesses|strengths|resume|sop|important formulas|formulas|"
    r"explain page|page \d+|uploaded pdf|uploaded document|uploaded file"
    r")\b",
    re.IGNORECASE,
)

# Deictic / pronoun references to an uploaded file — must not skip RAG
CONTEXTUAL_DOC_SIGNALS = re.compile(
    r"\b("
    r"this\s+document|this\s+pdf|this\s+paper|this\s+file|the\s+doc|"
    r"what\s+is\s+(?:this|the)\s+(?:document|pdf|file|paper)\s+about|"
    r"what'?s\s+(?:this|the)\s+(?:document|pdf|file|paper)\s+about|"
    r"what\s+is\s+this|what'?s\s+this|about\s+this|"
    r"summarize\s+(?:this|the|my|it|uploaded)?|explain\s+(?:this|the|my|uploaded)?|"
    r"review\s+this|describe\s+this|"
    r"what\s+does\s+(this|it)\s+say|\bits\b|"
    r"summarize\s+the\s+uploaded|explain\s+the\s+uploaded|"
    r"the\s+uploaded\s+(pdf|document|file)"
    r")\b",
    re.IGNORECASE,
)

# Pure chat / coding — skip RAG even when project has documents
GENERAL_ONLY_SIGNALS = re.compile(
    r"\b("
    r"write code|implement|debug|hello|hi there|thanks|thank you|"
    r"who are you|help me code|good morning|good evening"
    r")\b",
    re.IGNORECASE,
)

GENERAL_TOPIC_SIGNALS = re.compile(
    r"\b("
    r"explain|what is|what are|how to|how do|"
    r"python|javascript|algorithm"
    r")\b",
    re.IGNORECASE,
)


def is_document_intent_query(query: str) -> bool:
    """True when the user expects an answer grounded in uploaded documents."""
    text = query.strip()
    if not text:
        return False

    from app.services.routing_heuristics import is_document_access_query

    if is_document_access_query(text):
        return True
    if CONTEXTUAL_DOC_SIGNALS.search(text):
        return True
    if DOCUMENT_SIGNALS.search(text):
        return True
    return False


def classify_query(query: str, has_documents: bool) -> QueryType:
    if not has_documents:
        return QueryType.GENERAL

    text = query.strip()
    if is_document_intent_query(text):
        return QueryType.DOCUMENT

    if GENERAL_ONLY_SIGNALS.search(text) and not DOCUMENT_SIGNALS.search(text):
        return QueryType.GENERAL

    # Default: project has documents — attempt retrieval
    return QueryType.DOCUMENT
