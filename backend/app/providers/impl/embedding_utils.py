"""Shared helpers for dense + sparse embedding providers."""

import hashlib
import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)


def query_text(text: str) -> str:
    prefix = settings.embedding_query_prefix.strip()
    if not prefix:
        return text
    return f"{prefix}{text}"


def text_to_sparse(text: str) -> dict[int, float]:
    """Lightweight sparse vector for hybrid retrieval (keyword sensitivity)."""
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return {}
    sparse: dict[int, float] = {}
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest, 16) % 100_000
        sparse[idx] = sparse.get(idx, 0.0) + 1.0
    norm = sum(v * v for v in sparse.values()) ** 0.5 or 1.0
    return {k: v / norm for k, v in sparse.items()}


def normalize_dense(vector: list[float]) -> list[float]:
    norm = sum(v * v for v in vector) ** 0.5
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


def pool_embedding(raw) -> list[float]:
    """Convert HF feature-extraction payloads to a single dense vector."""
    if not raw:
        raise ValueError("Empty embedding response")

    if isinstance(raw, (int, float)):
        return [float(raw)]

    if isinstance(raw, list) and raw and isinstance(raw[0], (int, float)):
        return normalize_dense([float(v) for v in raw])

    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        if raw[0] and isinstance(raw[0][0], (int, float)):
            token_vectors = [[float(v) for v in row] for row in raw]
            dim = len(token_vectors[0])
            pooled = [0.0] * dim
            for row in token_vectors:
                for i, value in enumerate(row):
                    pooled[i] += value
            count = len(token_vectors) or 1
            return normalize_dense([v / count for v in pooled])

        return normalize_dense(pool_embedding(raw[0]))

    raise ValueError(f"Unsupported embedding response shape: {type(raw)}")


def parse_batch_embeddings(raw, expected: int) -> list[list[float]]:
    if expected == 1:
        return [pool_embedding(raw)]

    if isinstance(raw, list) and len(raw) == expected:
        if raw and isinstance(raw[0], list):
            if raw[0] and isinstance(raw[0][0], (int, float)):
                return [pool_embedding(item) for item in raw]
            if raw[0] and isinstance(raw[0][0], list):
                return [pool_embedding(item) for item in raw]

    raise ValueError(
        f"Could not parse batch embeddings (expected={expected}, got={type(raw).__name__})"
    )
