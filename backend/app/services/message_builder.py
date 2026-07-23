from app.models.chat_message import ChatMessage
from app.providers.types import RetrievedChunk
from app.services.search_service import SearchResult, SearchService

HISTORY_MESSAGE_LIMIT = 6

FORMATTING_INSTRUCTIONS = """CRITICAL FORMATTING RULES — always output valid GitHub Flavored Markdown:

GENERAL
- Use ONLY Markdown. NEVER output HTML tags (no <br>, <b>, <i>, <table>, <div>, etc.).
- Never mix HTML and Markdown.
- Line breaks: use a blank line between paragraphs (not <br>).
- Bold: **text**. Italic: *text*. Inline code: `code`.
- Bullet lists: use "- ". Numbered lists: use "1., 2., 3.". Indent nested items with 2 spaces.
- Put a blank line before and after every list and every table.

TABLES (strict — malformed tables break rendering)
- Every row MUST have the same number of columns as the header.
- ALWAYS include a valid separator row directly under the header, e.g.:
  | Column A | Column B | Column C |
  |----------|----------|----------|
  | value 1  | value 2  | value 3  |
- The separator row must have exactly one "---" group per column.
- NEVER use duplicate pipes (||). NEVER emit a partial or truncated table.
- If a cell is empty, still include it (leave it blank between pipes).
- If a table would be very large or complex, use a bulleted list instead of a table.

Prioritize readability over compactness. If unsure whether a table will be valid, use a bulleted list."""

SEARCH_SYNTHESIS_INSTRUCTIONS = """Web search results are provided below. Synthesize a natural Markdown answer.

Rules:
- Extract relevant facts from multiple sources; remove duplicates
- Never dump raw data or copy text verbatim
- Use: ## Answer, ### Key Points (bullets), ### Sources (markdown links)
- Write as the assistant, not as a search engine"""

RAG_SYNTHESIS_INSTRUCTIONS = """Relevant excerpts from the user's uploaded documents are provided below.

Rules:
- Answer ONLY from the provided document excerpts unless the user asks for general knowledge too
- Cite sources using the filename and section when available
- If the excerpts don't contain the answer, say so clearly
- Never invent facts not present in the documents
- Use clear Markdown formatting"""

SAFETY_INSTRUCTIONS = """Refuse harmful, violent, illegal, or sexually exploitative requests. Do not repeat severe profanity or slurs. Do not process or echo payment card numbers, CVV, MPIN, or OTP. Mild rude language (e.g. idiot, stupid) does not require refusal."""


def _format_doc_chunks(chunks: list[RetrievedChunk]) -> str:
    sections: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        heading = f" — {chunk.section_heading}" if chunk.section_heading else ""
        page = f", p.{chunk.page_number}" if chunk.page_number else ""
        sections.append(f"[{i}] {chunk.filename}{heading}{page}\n{chunk.content}")
    return "\n\n".join(sections)


def build_llm_messages(
    system_prompt: str,
    history: list[ChatMessage],
    user_message: str,
    search_results: list[SearchResult],
    doc_chunks: list[RetrievedChunk] | None = None,
) -> list[dict[str, str]]:
    """Assemble the message list sent to the LLM: system prompt + recent history + user turn."""
    messages: list[dict[str, str]] = []

    combined_system = system_prompt or "You are a helpful assistant."
    
    # Add formatting rules first (most critical)
    combined_system = f"{combined_system}\n\n{FORMATTING_INSTRUCTIONS}"
    
    if search_results:
        combined_system = f"{combined_system}\n\n{SEARCH_SYNTHESIS_INSTRUCTIONS}"
    if doc_chunks:
        combined_system = f"{combined_system}\n\n{RAG_SYNTHESIS_INSTRUCTIONS}"
    
    # Add safety instructions as backup (LLM-level filtering)
    combined_system = f"{combined_system}\n\n{SAFETY_INSTRUCTIONS}"
    
    messages.append({"role": "system", "content": combined_system})

    for msg in history[-HISTORY_MESSAGE_LIMIT:]:
        messages.append({"role": msg.role, "content": msg.content})

    context_parts: list[str] = []
    if doc_chunks:
        context_parts.append(f"Document excerpts:\n{_format_doc_chunks(doc_chunks)}")
    if search_results:
        context_parts.append(f"Web search results:\n{SearchService.format_results_for_llm(search_results)}")

    if context_parts:
        joined = "\n\n".join(context_parts)
        messages.append(
            {
                "role": "user",
                "content": f"{joined}\n\nQuestion: {user_message}",
            }
        )
    else:
        messages.append({"role": "user", "content": user_message})

    return messages
