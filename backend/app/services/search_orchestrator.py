import asyncio
import logging

from app.services.llm_provider import LLMProvider
from app.services.search_heuristics import heuristic_search_decision
from app.services.search_service import SearchResult, SearchService

logger = logging.getLogger(__name__)

SEARCH_DECISION_PROMPT = (
    "Does this question need LIVE internet data (news, prices, weather, recent events)? "
    "Answer ONLY: YES or NO\n\nQuestion: {question}\nAnswer:"
)


async def resolve_search(provider: LLMProvider, question: str) -> tuple[bool, list[SearchResult]]:
    """Decide whether a question needs live web results, and fetch them if so.

    Fast local heuristics short-circuit the common cases; only ambiguous
    questions fall back to an LLM classification call, run in parallel with
    the (speculative) Tavily search to hide its latency.
    """
    heuristic = heuristic_search_decision(question)

    if heuristic is False:
        return False, []
    if heuristic is True:
        return True, await SearchService.search(question)

    return await _decide_and_search_in_parallel(provider, question)


async def _decide_and_search_in_parallel(
    provider: LLMProvider, question: str
) -> tuple[bool, list[SearchResult]]:
    needs_search, results = await asyncio.gather(
        _llm_search_decision(provider, question),
        SearchService.search(question),
    )
    return needs_search, (results if needs_search else [])


async def _llm_search_decision(provider: LLMProvider, question: str) -> bool:
    try:
        decision = await provider.fast_complete(
            [{"role": "user", "content": SEARCH_DECISION_PROMPT.format(question=question)}],
            max_tokens=4,
        )
        return decision.strip().upper().startswith("YES")
    except Exception:
        logger.exception("LLM search decision failed — defaulting to NO")
        return False
