"""Detect coding-related user intent and build response templates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CodingIntent(str, Enum):
    NONE = "none"
    WRITE_CODE = "write_code"
    EXPLAIN_CONCEPT = "explain_concept"
    COMPARE_ALGORITHMS = "compare_algorithms"
    CONVERT_CODE = "convert_code"


# Ordered for extraction; longer aliases first where relevant.
LANGUAGE_ALIASES: tuple[tuple[str, str], ...] = (
    ("javascript", "javascript"),
    ("typescript", "typescript"),
    ("c++", "cpp"),
    ("csharp", "csharp"),
    ("c#", "csharp"),
    ("python", "python"),
    ("java", "java"),
    ("golang", "go"),
    ("kotlin", "kotlin"),
    ("swift", "swift"),
    ("ruby", "ruby"),
    ("rust", "rust"),
    ("node.js", "javascript"),
    ("nodejs", "javascript"),
    ("cpp", "cpp"),
    ("php", "php"),
    ("scala", "scala"),
    ("go", "go"),
    ("js", "javascript"),
    ("ts", "typescript"),
    ("py", "python"),
    ("rb", "ruby"),
    ("rs", "rust"),
    ("kt", "kotlin"),
)

DEFAULT_LANGUAGE = "python"

CONVERT_PATTERNS = re.compile(
    r"\b("
    r"convert(?:\s+this|\s+it|\s+the\s+code|\s+to)?|"
    r"translate(?:\s+to|\s+into)?|"
    r"port(?:\s+to|\s+into)?|"
    r"rewrite(?:\s+in|\s+to|\s+using)?|"
    r"change(?:\s+to|\s+into)?"
    r")\b",
    re.I,
)

WRITE_CODE_PATTERNS = re.compile(
    r"\b("
    r"write(?:\s+me|\s+the|\s+a)?\s+code|"
    r"show(?:\s+me)?(?:\s+the)?\s+code|"
    r"give(?:\s+me)?(?:\s+the)?\s+code|"
    r"implement|"
    r"code\s+for|"
    r"create(?:\s+a)?\s+(?:function|program|script|class|method)|"
    r"build(?:\s+a)?\s+(?:function|program|script|class|app)|"
    r"program(?:\s+for|\s+to|\s+that)|"
    r"help(?:\s+me)?\s+code|"
    r"sample\s+code|"
    r"source\s+code"
    r")\b",
    re.I,
)

COMPARE_PATTERNS = re.compile(
    r"\b("
    r"compare|comparison|difference\s+between|differences\s+between|"
    r"vs\.?|versus|which\s+is\s+(?:better|faster|more\s+efficient)"
    r")\b",
    re.I,
)

EXPLAIN_PATTERNS = re.compile(
    r"\b("
    r"explain|what\s+is|what\s+are|how\s+does|how\s+do|describe|"
    r"walk(?:\s+me)?\s+through|tell\s+me\s+about"
    r")\b",
    re.I,
)

CODING_TOPIC_PATTERNS = re.compile(
    r"\b("
    r"code|coding|algorithm|function|method|class|script|program|"
    r"sort|search|tree|graph|stack|queue|heap|hash|recursion|recursive|"
    r"iterative|loop|array|list|linked\s+list|binary|dynamic\s+programming|"
    r"complexity|big\s*o|data\s+structure|pointer|null|variable|"
    r"quicksort|merge\s+sort|bubble\s+sort|insertion\s+sort|"
    r"bfs|dfs|dijkstra|fibonacci|factorial|palindrome|"
    r"api|endpoint|regex|sql\s+query"
    r")\b",
    re.I,
)

DOCUMENT_CONTEXT_PATTERNS = re.compile(
    r"\b("
    r"document|uploaded|pdf|docx|file|section|chapter|excerpt|"
    r"according\s+to\s+the|from\s+the\s+(?:file|document|pdf|upload)"
    r")\b",
    re.I,
)

MULTI_APPROACH_PATTERNS = re.compile(
    r"\b("
    r"both\s+(?:iterative\s+and\s+recursive|recursive\s+and\s+iterative)|"
    r"iterative\s+(?:and|&|\/)\s+recursive|"
    r"recursive\s+(?:and|&|\/)\s+iterative|"
    r"multiple\s+(?:approaches|implementations|versions)"
    r")\b",
    re.I,
)

MULTI_LANGUAGE_PATTERNS = re.compile(
    r"\b("
    r"multiple\s+languages|"
    r"in\s+both\s+(?:python|java|javascript|js|c\+\+|cpp|typescript|go|rust)|"
    r"(?:python|java|javascript|js|c\+\+|cpp|typescript|go|rust)"
    r"\s+(?:and|&|,|\/)\s+"
    r"(?:python|java|javascript|js|c\+\+|cpp|typescript|go|rust)"
    r")\b",
    re.I,
)


@dataclass(frozen=True)
class CodingRequestContext:
    intent: CodingIntent
    languages: tuple[str, ...]
    wants_multiple_approaches: bool

    @property
    def is_coding_related(self) -> bool:
        return self.intent is not CodingIntent.NONE



def extract_languages(message: str) -> tuple[str, ...]:
    """Return requested languages in order of appearance; empty means default Python."""
    found: list[str] = []
    seen: set[str] = set()
    lower = message.lower()
    prefix_pattern = r"(?:\bin|\busing|\bwith|\bto|\binto)\s+"
    sorted_aliases = sorted(LANGUAGE_ALIASES, key=lambda item: len(item[0]), reverse=True)

    for alias, canonical in sorted_aliases:
        if re.search(prefix_pattern + re.escape(alias) + r"(?:\W|$)", lower):
            if canonical not in seen:
                found.append(canonical)
                seen.add(canonical)

    if MULTI_LANGUAGE_PATTERNS.search(message):
        for alias, canonical in sorted_aliases:
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lower) and canonical not in seen:
                found.append(canonical)
                seen.add(canonical)

    return tuple(found)


def _language_rules(context: CodingRequestContext) -> str:
    if context.languages:
        if len(context.languages) == 1:
            lang = context.languages[0]
            return (
                f"- Use ONLY {lang} for every code block in this response.\n"
                f"- Tag every fence with ```{lang}.\n"
                f"- Do NOT include implementations in any other language."
            )
        langs = ", ".join(context.languages)
        return (
            f"- The user requested multiple languages. Generate code ONLY in: {langs}.\n"
            f"- Provide one implementation per requested language — no extra languages.\n"
            f"- Keep the same algorithm/approach across languages; do not mix approaches."
        )

    return (
        "- DEFAULT LANGUAGE: Python. The user did not specify a language.\n"
        "- Output code ONLY in Python — do NOT include C++, Java, JavaScript, or other languages.\n"
        "- Tag the fence with ```python."
    )


def _approach_rules(context: CodingRequestContext) -> str:
    if context.wants_multiple_approaches:
        return (
            "- The user asked for multiple approaches. You may include each requested approach "
            "(e.g. iterative and recursive).\n"
            "- Use the SAME language for every approach — never mix languages across implementations."
        )
    return (
        "- Provide ONE implementation only (prefer the simplest correct approach).\n"
        "- Do NOT include both iterative and recursive versions unless the user explicitly asked.\n"
        "- Keep the language consistent throughout the entire response."
    )


_WRITE_CODE_TEMPLATE = """CODING RESPONSE — WRITE CODE
Use this exact section order:

## Brief Explanation
2–4 sentences on what the code does and the core idea.

## Code Implementation
One concise, working implementation. Simple, short, efficient — minimal boilerplate.

## Time Complexity
State Big-O and one short justification.

## Space Complexity
State Big-O and one short justification.

## Example Usage
A minimal runnable example showing input → output."""

_EXPLAIN_CONCEPT_TEMPLATE = """CODING RESPONSE — EXPLAIN CONCEPT
The user wants a conceptual explanation, not a full implementation dump.

Use this section order:

## Brief Explanation
Clear explanation of the concept, how it works, and when to use it.

## Key Points
Bullet list of the most important details (steps, properties, trade-offs).

## Complexity (if applicable)
Brief time/space complexity notes when the topic is algorithmic.

## Example (optional)
At most one short illustrative snippet ONLY if it materially helps understanding.
Do NOT provide full multi-file implementations or alternate language versions."""

_COMPARE_ALGORITHMS_TEMPLATE = """CODING RESPONSE — COMPARE ALGORITHMS
The user wants a structured comparison — not unrelated multi-language demos.

Use this section order:

## Brief Explanation
One paragraph framing what is being compared and why it matters.

## Comparison
Use bullets or a compact table for differences (idea, performance, use cases, trade-offs).

## Code Implementation (optional)
Include code ONLY if it clarifies the comparison. Use a single language consistently.

## Time Complexity
Compare time complexity for each approach.

## Space Complexity
Compare space complexity for each approach.

## Example Usage (optional)
One concise example only if it helps illustrate the comparison."""

_CONVERT_CODE_TEMPLATE = """CODING RESPONSE — CONVERT CODE
The user wants code translated to another language.

Use this section order:

## Brief Explanation
1–2 sentences noting the target language and any important translation notes.

## Code Implementation
The converted code only — simple, short, efficient, same behavior as the source.

## Example Usage
A minimal example demonstrating the converted code."""


def build_coding_instructions(context: CodingRequestContext) -> str:
    if not context.is_coding_related:
        return ""

    templates = {
        CodingIntent.WRITE_CODE: _WRITE_CODE_TEMPLATE,
        CodingIntent.EXPLAIN_CONCEPT: _EXPLAIN_CONCEPT_TEMPLATE,
        CodingIntent.COMPARE_ALGORITHMS: _COMPARE_ALGORITHMS_TEMPLATE,
        CodingIntent.CONVERT_CODE: _CONVERT_CODE_TEMPLATE,
    }
    template = templates[context.intent]
    return (
        f"{template}\n\n"
        "LANGUAGE RULES\n"
        f"{_language_rules(context)}\n\n"
        "APPROACH RULES\n"
        f"{_approach_rules(context)}\n\n"
        "GENERAL CODE RULES\n"
        "- Keep code simple, short, and efficient.\n"
        "- Preserve indentation exactly inside fences.\n"
        "- One source line per row — avoid blank lines inside code unless necessary."
    )


def classify_coding_request(message: str) -> CodingRequestContext:
    text = message.strip()
    if not text:
        return CodingRequestContext(CodingIntent.NONE, (), False)

    has_coding_topic = bool(CODING_TOPIC_PATTERNS.search(text))
    has_document_context = bool(DOCUMENT_CONTEXT_PATTERNS.search(text))
    languages = extract_languages(text)
    wants_multiple_approaches = bool(MULTI_APPROACH_PATTERNS.search(text))

    is_convert = bool(CONVERT_PATTERNS.search(text)) and (
        has_coding_topic or bool(languages) or "code" in text.lower()
    )
    is_write = bool(WRITE_CODE_PATTERNS.search(text))
    is_compare = bool(COMPARE_PATTERNS.search(text)) and has_coding_topic
    is_explain = bool(EXPLAIN_PATTERNS.search(text)) and has_coding_topic

    if has_document_context and not (is_write or is_convert):
        return CodingRequestContext(CodingIntent.NONE, languages, wants_multiple_approaches)

    if is_convert:
        intent = CodingIntent.CONVERT_CODE
    elif is_compare and not is_write:
        intent = CodingIntent.COMPARE_ALGORITHMS
    elif is_write or (has_coding_topic and re.search(r"\b(for|of)\b", text, re.I) and re.search(
        r"\b(sort|search|algorithm|function|program|script)\b", text, re.I
    )):
        intent = CodingIntent.WRITE_CODE
    elif is_explain:
        intent = CodingIntent.EXPLAIN_CONCEPT
    elif has_coding_topic and re.search(
        r"\b(write|implement|build|create|show|give)\b", text, re.I
    ):
        intent = CodingIntent.WRITE_CODE
    else:
        intent = CodingIntent.NONE

    return CodingRequestContext(intent, languages, wants_multiple_approaches)
