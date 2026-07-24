"""Classify desired response depth (brief / standard / comprehensive).

Priority:
1. Explicit user instruction in the message
2. Task type and complexity
3. General conversational adaptation
"""

from __future__ import annotations

import re
from enum import Enum

from app.services.coding_intent import CodingIntent, CodingRequestContext


class ResponseDepth(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


EXPLICIT_BRIEF = re.compile(
    r"\b("
    r"briefly|brief answer|short answer|keep it short|keep this short|"
    r"tldr|tl;dr|too long|one sentence|in a nutshell|quick answer|"
    r"just answer|no fluff|be concise|concise answer"
    r")\b",
    re.IGNORECASE,
)

EXPLICIT_COMPREHENSIVE = re.compile(
    r"\b("
    r"explain in detail|in detail|deep dive|deep-dive|teach me|"
    r"complete guide|comprehensive|comprehensively|from scratch|"
    r"step by step|step-by-step|in depth|detailed explanation|"
    r"full explanation|walk me through everything|everything about|"
    r"architecture|architectural|design a|design the|design an|"
    r"implementation plan|project plan|roadmap|research|"
    r"production ready|production-ready|production readiness|"
    r"best practices|trade-?offs|end to end|end-to-end"
    r")\b",
    re.IGNORECASE,
)

COMPREHENSIVE_TOPICS = re.compile(
    r"\b("
    r"system design|software architecture|ai architecture|rag design|rag pipeline|"
    r"retrieval augmented|prompt engineering|database design|schema design|"
    r"backend design|frontend design|ui design|ux design|"
    r"security design|threat model|deployment strategy|deploy to production|"
    r"scalability|high availability|fault tolerance|disaster recovery|"
    r"microservices|distributed system|event driven|message queue design|"
    r"performance optimization|capacity planning|load balancing|"
    r"technical documentation|code review|refactor plan|migration plan|"
    r"business plan|go-to-market|interview prep|interview preparation|"
    r"learning path|study plan|tutorial series|course outline|"
    r"multi-?step implementation|full implementation|build the entire|"
    r"design doc|design document|engineering plan"
    r")\b",
    re.IGNORECASE,
)

COMPREHENSIVE_TASK = re.compile(
    r"\b("
    r"design|architect|plan|research|evaluate|analyze|compare approaches|"
    r"propose a solution|recommend an architecture|build a system|"
    r"implement a complete|implement the entire|create a roadmap"
    r")\b",
    re.IGNORECASE,
)

SIMPLE_DEFINITION = re.compile(
    r"^(?:what is|what's|what are|define|meaning of)\s+(.+?)\??$",
    re.IGNORECASE,
)

SIMPLE_COMPARISON = re.compile(
    r"\b(difference between|differences between|vs\.?|versus|compare)\b",
    re.IGNORECASE,
)

SMALL_CODING_FIX = re.compile(
    r"\b("
    r"fix this|fix the|bug in|syntax error|typo|one line|small fix|"
    r"quick fix|why isn'?t this working|what'?s wrong with"
    r")\b",
    re.IGNORECASE,
)

BASIC_API_QUESTION = re.compile(
    r"^(?:how (?:do i|to)|what is the)\s+(?:use|call|send|make)\s+.+\b(?:api|endpoint|request)\b",
    re.IGNORECASE,
)

GREETING_WORDS = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank",
        "you",
        "ok",
        "okay",
        "yes",
        "no",
        "sure",
        "cool",
        "great",
        "bye",
        "morning",
        "night",
        "good",
        "howdy",
        "yo",
    }
)


def _is_greeting_or_small_talk(text: str) -> bool:
    normalized = re.sub(r"[^\w\s']", " ", text.lower()).strip()
    words = [w for w in normalized.split() if w]
    if not words or len(words) > 8:
        return False
    return all(w in GREETING_WORDS for w in words)


def _is_simple_yes_no(text: str) -> bool:
    return text.strip().lower() in {
        "yes",
        "no",
        "y",
        "n",
        "yeah",
        "nope",
        "sure",
        "ok",
        "okay",
    }


def _is_simple_definition(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 120:
        return False
    match = SIMPLE_DEFINITION.match(stripped)
    if not match:
        return False
    subject = match.group(1).strip()
    # Long multi-clause questions are not "simple definitions"
    return len(subject.split()) <= 8 and subject.count(",") == 0


def _is_simple_comparison(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 120:
        return False
    return bool(SIMPLE_COMPARISON.search(stripped))


def _is_quick_recommendation(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 100:
        return False
    return bool(re.search(r"\b(which .+ (?:is )?better|should i (?:use|choose|pick)|recommend)\b", stripped, re.I))


def classify_response_depth(
    message: str,
    coding_context: CodingRequestContext | None = None,
) -> ResponseDepth:
    text = message.strip()
    if not text:
        return ResponseDepth.STANDARD

    if EXPLICIT_BRIEF.search(text):
        return ResponseDepth.BRIEF
    if EXPLICIT_COMPREHENSIVE.search(text):
        return ResponseDepth.COMPREHENSIVE

    if COMPREHENSIVE_TOPICS.search(text):
        return ResponseDepth.COMPREHENSIVE

    if len(text) > 100 and COMPREHENSIVE_TASK.search(text):
        return ResponseDepth.COMPREHENSIVE

    if _is_greeting_or_small_talk(text):
        return ResponseDepth.BRIEF
    if _is_simple_yes_no(text):
        return ResponseDepth.BRIEF
    if _is_simple_definition(text):
        return ResponseDepth.BRIEF
    if _is_simple_comparison(text):
        return ResponseDepth.BRIEF
    if _is_quick_recommendation(text):
        return ResponseDepth.BRIEF
    if BASIC_API_QUESTION.match(text):
        return ResponseDepth.BRIEF

    if coding_context and coding_context.is_coding_related:
        if SMALL_CODING_FIX.search(text):
            return ResponseDepth.BRIEF
        if coding_context.intent in {
            CodingIntent.WRITE_CODE,
            CodingIntent.COMPARE_ALGORITHMS,
            CodingIntent.CONVERT_CODE,
        }:
            return ResponseDepth.STANDARD

    return ResponseDepth.STANDARD


BRIEF_DEPTH_INSTRUCTIONS = """RESPONSE DEPTH — BRIEF
Keep this reply concise and conversational (ChatGPT-style for everyday messages).
- Answer directly in 1–4 short paragraphs OR a tight bullet list
- Skip long section stacks, roadmaps, exhaustive breakdowns, and repeated summaries
- Do not force multi-part templates unless the user asked for them
- Stay friendly and natural; prioritize clarity over completeness"""

STANDARD_DEPTH_INSTRUCTIONS = """RESPONSE DEPTH — STANDARD
Use balanced technical depth: clear and complete without turning every answer into a full course.
- Match structure to the question — headings/lists when they help, not by default
- Be proportional: ordinary technical questions deserve solid but not exhaustive answers"""

COMPREHENSIVE_DEPTH_INSTRUCTIONS = """RESPONSE DEPTH — COMPREHENSIVE
Provide a thorough, high-quality answer. Do NOT shorten artificially.
Include where relevant:
- Clear sections and logical organization
- Examples, best practices, and trade-offs
- Step-by-step implementation or planning guidance
- Recommendations and production considerations
- Text-based architecture diagrams when they clarify the design
Treat this like a professional engineering or teaching response."""


def build_depth_instructions(depth: ResponseDepth) -> str:
    if depth is ResponseDepth.BRIEF:
        return BRIEF_DEPTH_INSTRUCTIONS
    if depth is ResponseDepth.COMPREHENSIVE:
        return COMPREHENSIVE_DEPTH_INSTRUCTIONS
    return STANDARD_DEPTH_INSTRUCTIONS


def build_project_identity(system_prompt: str, description: str) -> str:
    """Preserve user-defined project instructions as the highest-priority persona."""
    parts: list[str] = []
    prompt = (system_prompt or "").strip()
    desc = (description or "").strip()

    if prompt:
        parts.append(prompt)
    if desc:
        parts.append(f"Project description (follow strictly):\n{desc}")

    if not parts:
        return "You are a helpful assistant."

    return (
        "\n\n".join(parts)
        + "\n\nPROJECT IDENTITY RULE: Always honor the project system prompt and description above. "
        "They define role, tone, constraints, and domain focus. Do not override them with generic "
        "style defaults unless the user's current message explicitly requests a different format."
    )


def should_apply_coding_template(depth: ResponseDepth, coding_context: CodingRequestContext | None) -> bool:
    """Structured coding templates apply only for standard-depth coding tasks."""
    if coding_context is None or not coding_context.is_coding_related:
        return False
    return depth is ResponseDepth.STANDARD
