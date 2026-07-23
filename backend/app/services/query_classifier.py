"""Classify queries to avoid unnecessary retrieval."""

import logging
import re

from app.providers.types import QueryType

logger = logging.getLogger(__name__)

DOCUMENT_SIGNALS = re.compile(
    r"\b("
    r"document|uploaded|file|pdf|according to|in the text|from the doc|"
    r"what does it say|summarize|summary of|based on my|my upload|"
    r"in my document|the paper|the report|the article"
    r")\b",
    re.IGNORECASE,
)

GENERAL_SIGNALS = re.compile(
    r"\b("
    r"write code|implement|debug|explain|what is|how to|how do|"
    r"python|javascript|algorithm|hello|thanks|thank you|"
    r"who are you|help me code"
    r")\b",
    re.IGNORECASE,
)


def classify_query(query: str, has_documents: bool) -> QueryType:
    if not has_documents:
        return QueryType.GENERAL

    text = query.strip()
    has_doc = bool(DOCUMENT_SIGNALS.search(text))
    has_general = bool(GENERAL_SIGNALS.search(text))

    if has_doc and has_general:
        return QueryType.HYBRID
    if has_doc:
        return QueryType.DOCUMENT
    if has_general and not has_doc:
        return QueryType.GENERAL

    # Default: if project has documents, attempt document retrieval
    return QueryType.DOCUMENT
