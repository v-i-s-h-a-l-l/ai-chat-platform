import logging
import time
from dataclasses import dataclass

from app.config import settings
from app.utils.http_client import get_async_http_client

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
CACHE_TTL_SECONDS = 600
MAX_SNIPPET_CHARS = 400
DEFAULT_MAX_RESULTS = 3


@dataclass(frozen=True)
class SearchResult:
    title: str
    content: str
    url: str


class SearchService:
    _cache: dict[str, tuple[list[SearchResult], float]] = {}

    @classmethod
    async def search(cls, query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        if not query.strip():
            return []

        cache_key = query.strip().lower()
        cached = cls._get_from_cache(cache_key)
        if cached is not None:
            logger.info("Search cache hit for query: %s", query[:80])
            return cached

        if not settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY is not configured — skipping web search")
            return []

        try:
            results = await cls._fetch_from_tavily(query, max_results)
            cls._store_in_cache(cache_key, results)
            logger.info("Tavily returned %d results for query: %s", len(results), query[:80])
            return results
        except Exception:
            logger.exception("Tavily search failed for query: %s", query[:80])
            return []

    @classmethod
    async def _fetch_from_tavily(cls, query: str, max_results: int) -> list[SearchResult]:
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": max_results,
        }

        client = get_async_http_client()
        response = await client.post(TAVILY_SEARCH_URL, json=payload, timeout=15.0)
        if response.status_code >= 400:
            raise ValueError(
                f"Tavily API error ({response.status_code}): {response.text}"
            )
        data = response.json()

        results: list[SearchResult] = []
        for item in data.get("results", []):
            title = item.get("title", "").strip()
            content = item.get("content", "").strip()
            url = item.get("url", "").strip()
            if content and len(content) > MAX_SNIPPET_CHARS:
                content = content[:MAX_SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"
            if title or content:
                results.append(SearchResult(title=title, content=content, url=url))

        return results

    @classmethod
    def _get_from_cache(cls, key: str) -> list[SearchResult] | None:
        entry = cls._cache.get(key)
        if entry is None:
            return None
        results, stored_at = entry
        if time.time() - stored_at > CACHE_TTL_SECONDS:
            del cls._cache[key]
            return None
        return results

    @classmethod
    def _store_in_cache(cls, key: str, results: list[SearchResult]) -> None:
        cls._cache[key] = (results, time.time())

    @classmethod
    def format_results_for_llm(cls, results: list[SearchResult]) -> str:
        if not results:
            return "No search results were found."

        sections: list[str] = []
        for i, result in enumerate(results, start=1):
            sections.append(
                f"[{i}] {result.title} ({result.url})\n{result.content}"
            )
        return "\n\n".join(sections)
