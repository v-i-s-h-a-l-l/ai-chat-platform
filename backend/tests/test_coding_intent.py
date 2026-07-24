import pytest

from app.services.coding_intent import (
    CodingIntent,
    build_coding_instructions,
    classify_coding_request,
    extract_languages,
)
from app.services.message_builder import FORMATTING_INSTRUCTIONS, build_llm_messages


@pytest.mark.parametrize(
    "message, intent",
    [
        ("write code for quick sort", CodingIntent.WRITE_CODE),
        ("implement binary search", CodingIntent.WRITE_CODE),
        ("explain how quicksort works", CodingIntent.EXPLAIN_CONCEPT),
        ("compare quicksort vs mergesort", CodingIntent.COMPARE_ALGORITHMS),
        ("convert this to Java", CodingIntent.CONVERT_CODE),
        ("what is the weather today", CodingIntent.NONE),
        ("summarize the uploaded document", CodingIntent.NONE),
        ("explain section 3 of the pdf", CodingIntent.NONE),
    ],
)
def test_classify_coding_request(message: str, intent: CodingIntent):
    assert classify_coding_request(message).intent is intent


def test_default_python_when_no_language():
    context = classify_coding_request("write code for quick sort")
    assert context.languages == ()
    instructions = build_coding_instructions(context)
    assert "DEFAULT LANGUAGE: Python" in instructions
    assert "Output code ONLY in Python" in instructions


def test_single_requested_language():
    context = classify_coding_request("implement quicksort in C++")
    assert context.languages == ("cpp",)
    instructions = build_coding_instructions(context)
    assert "Use ONLY cpp" in instructions


def test_multiple_requested_languages():
    context = classify_coding_request("write quicksort in Python and Java")
    assert context.languages == ("python", "java")
    instructions = build_coding_instructions(context)
    assert "python, java" in instructions
    assert "no extra languages" in instructions.lower()


def test_write_code_template_sections():
    context = classify_coding_request("write code for quick sort")
    instructions = build_coding_instructions(context)
    assert "Brief Explanation" in instructions
    assert "Code Implementation" in instructions
    assert "Time Complexity" in instructions
    assert "Space Complexity" in instructions
    assert "Example Usage" in instructions


def test_explain_concept_does_not_force_full_code_template():
    context = classify_coding_request("explain how quicksort works")
    instructions = build_coding_instructions(context)
    assert "EXPLAIN CONCEPT" in instructions
    assert "Example (optional)" in instructions
    assert "Do NOT provide full multi-file implementations" in instructions


def test_compare_algorithms_template():
    context = classify_coding_request("compare iterative vs recursive factorial")
    instructions = build_coding_instructions(context)
    assert "COMPARE ALGORITHMS" in instructions
    assert "Comparison" in instructions


def test_convert_code_template():
    context = classify_coding_request("convert this function to Rust")
    instructions = build_coding_instructions(context)
    assert "CONVERT CODE" in instructions


def test_no_iterative_and_recursive_by_default():
    context = classify_coding_request("write code for quick sort")
    instructions = build_coding_instructions(context)
    assert "Do NOT include both iterative and recursive" in instructions


def test_iterative_and_recursive_when_requested():
    context = classify_coding_request("show both iterative and recursive binary search")
    assert context.wants_multiple_approaches is True
    instructions = build_coding_instructions(context)
    assert "SAME language for every approach" in instructions


def test_extract_languages_in_using_with():
    assert extract_languages("implement dfs in python") == ("python",)
    assert extract_languages("rewrite using Java") == ("java",)


def test_general_chat_does_not_get_coding_instructions():
    messages = build_llm_messages(
        system_prompt="You are a helpful assistant.",
        history=[],
        user_message="what is the capital of France",
        search_results=[],
    )
    system = messages[0]["content"]
    assert "CODING RESPONSE" not in system
    assert "DEFAULT LANGUAGE: Python" not in system


def test_coding_chat_gets_coding_instructions():
    messages = build_llm_messages(
        system_prompt="You are a helpful assistant.",
        history=[],
        user_message="write code for quick sort",
        search_results=[],
    )
    system = messages[0]["content"]
    assert "CODING RESPONSE — WRITE CODE" in system
    assert "DEFAULT LANGUAGE: Python" in system


def test_formatting_instructions_no_longer_include_global_code_blocks():
    assert "CODE BLOCKS" not in FORMATTING_INSTRUCTIONS
