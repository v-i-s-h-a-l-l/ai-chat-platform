import pytest

from app.services.coding_intent import classify_coding_request
from app.services.message_builder import build_llm_messages
from app.services.response_depth import ResponseDepth, classify_response_depth


@pytest.mark.parametrize(
    "message, expected",
    [
        ("Hi", ResponseDepth.BRIEF),
        ("Thank you!", ResponseDepth.BRIEF),
        ("What is JWT?", ResponseDepth.BRIEF),
        ("Difference between GET and POST?", ResponseDepth.BRIEF),
        ("Which laptop is better?", ResponseDepth.BRIEF),
        ("TL;DR what is Docker?", ResponseDepth.BRIEF),
        (
            "Design a scalable RAG architecture for production with hybrid retrieval",
            ResponseDepth.COMPREHENSIVE,
        ),
        ("Explain system design for a chat platform in detail", ResponseDepth.COMPREHENSIVE),
        ("Teach me prompt engineering from scratch", ResponseDepth.COMPREHENSIVE),
        ("Create a roadmap for backend migration", ResponseDepth.COMPREHENSIVE),
        ("Briefly explain what Redis is", ResponseDepth.BRIEF),
        ("Explain Redis in detail", ResponseDepth.COMPREHENSIVE),
        ("How does a hash map work?", ResponseDepth.STANDARD),
        ("write code for quick sort", ResponseDepth.STANDARD),
    ],
)
def test_classify_response_depth(message: str, expected: ResponseDepth):
    coding = classify_coding_request(message)
    assert classify_response_depth(message, coding) is expected


def test_explicit_brief_overrides_comprehensive_topic():
    message = "Give me a brief answer on system design for my API"
    coding = classify_coding_request(message)
    assert classify_response_depth(message, coding) is ResponseDepth.BRIEF


def test_project_identity_in_system_prompt():
    messages = build_llm_messages(
        system_prompt="You are a wellness coach. Be supportive.",
        description="Focus on mindfulness and stress reduction.",
        history=[],
        user_message="Hi",
        search_results=[],
    )
    system = messages[0]["content"]
    assert "You are a wellness coach" in system
    assert "mindfulness and stress reduction" in system
    assert "PROJECT IDENTITY RULE" in system
    assert "RESPONSE DEPTH — BRIEF" in system


def test_comprehensive_depth_for_architecture_question():
    messages = build_llm_messages(
        system_prompt="You are a helpful assistant.",
        description="",
        history=[],
        user_message="Design a secure backend architecture for a multi-tenant SaaS app",
        search_results=[],
    )
    system = messages[0]["content"]
    assert "RESPONSE DEPTH — COMPREHENSIVE" in system
    assert "Do NOT shorten artificially" in system


def test_brief_chat_skips_coding_template():
    messages = build_llm_messages(
        system_prompt="You are a helpful assistant.",
        description="",
        history=[],
        user_message="Difference between GET and POST?",
        search_results=[],
    )
    system = messages[0]["content"]
    assert "RESPONSE DEPTH — BRIEF" in system
    assert "CODING RESPONSE" not in system


def test_standard_coding_keeps_template():
    messages = build_llm_messages(
        system_prompt="You are a helpful assistant.",
        description="",
        history=[],
        user_message="write code for quick sort",
        search_results=[],
    )
    system = messages[0]["content"]
    assert "RESPONSE DEPTH — STANDARD" in system
    assert "CODING RESPONSE — WRITE CODE" in system
