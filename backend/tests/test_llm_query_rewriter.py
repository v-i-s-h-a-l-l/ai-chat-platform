"""Query rewrite skip rules."""

import pytest

from app.providers.impl.llm_query_rewriter import LlmQueryRewriter


class NoOpLlm:
    async def fast_complete(self, messages, max_tokens=128):
        raise AssertionError("LLM should not be called")


@pytest.mark.asyncio
async def test_rewrite_skips_for_short_standalone_follow_up():
    rewriter = LlmQueryRewriter(NoOpLlm())
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    query = "Explain transformers in detail"
    assert await rewriter.rewrite(query, history) == query


@pytest.mark.asyncio
async def test_rewrite_runs_for_deictic_follow_up():
    called = False

    class RecordingLlm:
        async def fast_complete(self, messages, max_tokens=128):
            nonlocal called
            called = True
            return "What are its weaknesses?"

    rewriter = LlmQueryRewriter(RecordingLlm())
    history = [
        {"role": "user", "content": "Summarize the paper"},
        {"role": "assistant", "content": "It describes attention."},
    ]
    result = await rewriter.rewrite("What about its weaknesses?", history)
    assert called is True
    assert result == "What are its weaknesses?"
