import logging

from app.providers.base import QueryRewriter
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """Rewrite the follow-up question into a standalone question that can be understood without conversation context.
Use the conversation history only when needed. Output ONLY the rewritten question, nothing else.

Conversation:
{history}

Follow-up question: {query}

Standalone question:"""


class LlmQueryRewriter(QueryRewriter):
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def rewrite(self, query: str, history: list[dict[str, str]]) -> str:
        if not history:
            return query

        history_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in history[-4:])
        prompt = REWRITE_PROMPT.format(history=history_text, query=query)

        try:
            rewritten = await self._llm.fast_complete(
                [{"role": "user", "content": prompt}],
                max_tokens=128,
            )
            result = rewritten.strip().strip('"')
            if result:
                logger.info("Query rewritten: %r → %r", query[:60], result[:60])
                return result
        except Exception:
            logger.exception("Query rewrite failed — using original query")

        return query
