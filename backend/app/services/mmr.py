"""Maximum Marginal Relevance — reduce duplicate chunks, increase diversity."""

import logging
import time

import numpy as np

from app.config import settings
from app.providers.types import RetrievedChunk

logger = logging.getLogger(__name__)


def _simple_embed(text: str) -> np.ndarray:
    """Fast bag-of-words vector for MMR (no model call — keeps latency low)."""
    tokens = text.lower().split()
    if not tokens:
        return np.zeros(128)
    vec = np.zeros(128)
    for token in tokens:
        vec[hash(token) % 128] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def apply_mmr(chunks: list[RetrievedChunk], top_k: int, lambda_param: float | None = None) -> list[RetrievedChunk]:
    if len(chunks) <= top_k:
        return chunks

    t0 = time.perf_counter()
    lam = lambda_param if lambda_param is not None else settings.rag_mmr_lambda

    embeddings = [_simple_embed(c.content) for c in chunks]
    relevance = np.array([c.score for c in chunks])
    if relevance.max() > 0:
        relevance = relevance / relevance.max()

    selected: list[int] = []
    remaining = list(range(len(chunks)))

    while len(selected) < top_k and remaining:
        if not selected:
            best = int(np.argmax(relevance[remaining]))
            selected.append(remaining.pop(best))
            continue

        mmr_scores = []
        for idx in remaining:
            rel = relevance[idx]
            max_sim = max(
                float(np.dot(embeddings[idx], embeddings[s]))
                for s in selected
            )
            mmr_scores.append(lam * rel - (1 - lam) * max_sim)

        best = int(np.argmax(mmr_scores))
        selected.append(remaining.pop(best))

    result = [chunks[i] for i in selected]
    logger.info("MMR: %.1fms (%d → %d)", (time.perf_counter() - t0) * 1000, len(chunks), len(result))
    return result
