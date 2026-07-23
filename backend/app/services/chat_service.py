import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

import anyio
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import SessionLocal
import app.guardrails as guardrails
from app.guardrails import GuardrailViolationError
from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.repositories.chat_repository import ChatRepository
from app.services.chat_events import ChatStreamEvent, DoneEvent, ErrorEvent, MetaEvent, TokenEvent
from app.services.llm_provider import LLMProvider
from app.services.message_builder import build_llm_messages
from app.services.project_service import ProjectService
from app.services.retrieval_orchestrator import resolve_rag_context
from app.services.search_orchestrator import resolve_search

logger = logging.getLogger(__name__)

# Under anyio/Starlette, a client disconnect cancels the streaming task with
# asyncio.CancelledError (not GeneratorExit) — catch both so partial content
# is saved regardless of which one fires. (This app only ever runs on the
# asyncio backend, so the concrete class is used instead of
# anyio.get_cancelled_exc_class(), which requires a running event loop and
# can't be evaluated at import time.)
_DISCONNECT_EXCEPTIONS = (GeneratorExit, asyncio.CancelledError)


@dataclass
class ChatReply:
    user_message: ChatMessage
    assistant_message: ChatMessage
    web_search_used: bool
    documents_used: bool = False


class ChatService:
    """Chat orchestration only — search decisioning lives in search_orchestrator,
    prompt assembly in message_builder, and LLM access behind LLMProvider.

    `send_message`/`stream_message` intentionally do NOT take a request-scoped
    `Session`. Each DB touchpoint opens and closes its own short-lived session
    (via the threadpool helpers below) so no connection is held for the
    30-120s duration of an LLM stream.
    """

    @staticmethod
    def get_messages(
        db: Session, project_id: UUID, user_id: UUID, limit: int = 200, offset: int = 0
    ) -> list[ChatMessage]:
        ProjectService.get_project(db, project_id, user_id)
        return ChatRepository.list_by_project(db, project_id, limit=limit, offset=offset)

    @staticmethod
    async def send_message(
        project_id: UUID, user_id: UUID, content: str, provider: LLMProvider
    ) -> ChatReply:
        # Guardrails: check chat message before any processing
        if settings.guardrails_enabled:
            guardrails.check_chat(content)

        project, history = await ChatService._load_context(project_id, user_id)

        (needs_search, search_results), (doc_chunks, documents_used) = await asyncio.gather(
            resolve_search(provider, content),
            resolve_rag_context(project_id, content, history, provider),
        )
        web_search_used = needs_search and len(search_results) > 0

        messages = build_llm_messages(
            project.system_prompt, history, content, search_results, doc_chunks
        )
        assistant_content = await provider.complete(messages)

        user_message = await ChatService._persist_message(project_id, "user", content)
        assistant_message = await ChatService._persist_message(
            project_id,
            "assistant",
            assistant_content,
            web_search_used=web_search_used,
            documents_used=documents_used,
        )

        return ChatReply(
            user_message=user_message,
            assistant_message=assistant_message,
            web_search_used=web_search_used,
            documents_used=documents_used,
        )

    @staticmethod
    async def stream_message(
        project_id: UUID, user_id: UUID, content: str, provider: LLMProvider
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """Yield domain events. The route layer serializes these to SSE."""
        try:
            # Guardrails: check chat message before any processing
            if settings.guardrails_enabled:
                guardrails.check_chat(content)

            project, history = await ChatService._load_context(project_id, user_id)

            t0 = time.perf_counter()
            (needs_search, search_results), (doc_chunks, documents_used) = await asyncio.gather(
                resolve_search(provider, content),
                resolve_rag_context(project_id, content, history, provider),
            )
            web_search_used = needs_search and len(search_results) > 0
            context_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                "Context phase: %.0fms (web=%s, docs=%s)",
                context_ms,
                web_search_used,
                documents_used,
            )

            user_message = await ChatService._persist_message(project_id, "user", content)
            yield MetaEvent(
                user_message=user_message,
                web_search_used=web_search_used,
                documents_used=documents_used,
            )

            messages = build_llm_messages(
                project.system_prompt, history, content, search_results, doc_chunks
            )

            full_content: list[str] = []
            try:
                async for token in provider.stream(messages):
                    full_content.append(token)
                    yield TokenEvent(content=token)

                assistant_content = "".join(full_content)
                if not assistant_content.strip():
                    raise ValueError("Empty response from LLM")

                assistant_message = await ChatService._persist_message(
                    project_id,
                    "assistant",
                    assistant_content,
                    web_search_used=web_search_used,
                    documents_used=documents_used,
                )
                yield DoneEvent(
                    assistant_message=assistant_message,
                    web_search_used=web_search_used,
                    documents_used=documents_used,
                )
            except _DISCONNECT_EXCEPTIONS:
                partial = "".join(full_content).strip()
                if partial:
                    with anyio.CancelScope(shield=True):
                        await ChatService._persist_message(
                            project_id,
                            "assistant",
                            partial,
                            web_search_used=web_search_used,
                            documents_used=documents_used,
                        )
                raise

        except GuardrailViolationError as exc:
            logger.warning("Chat blocked by guardrails: %s", exc.code)
            yield ErrorEvent(detail=str(exc))
        except ValueError as exc:
            logger.warning("Stream chat error: %s", exc)
            yield ErrorEvent(detail=str(exc))
        except Exception as exc:
            logger.exception("Stream chat failed")
            yield ErrorEvent(detail=f"Failed to generate response: {exc}")

    # -- short-lived session helpers -----------------------------------
    # Each opens its own Session, does one unit of work, and closes it —
    # never held across the LLM call/stream.

    @staticmethod
    async def _load_context(project_id: UUID, user_id: UUID) -> tuple[Project, list[ChatMessage]]:
        def _work() -> tuple[Project, list[ChatMessage]]:
            db = SessionLocal()
            try:
                project = ProjectService.get_project(db, project_id, user_id)
                history = ChatRepository.get_recent(db, project_id)
                db.expunge(project)
                for message in history:
                    db.expunge(message)
                return project, history
            finally:
                db.close()

        return await run_in_threadpool(_work)

    @staticmethod
    async def _persist_message(
        project_id: UUID,
        role: str,
        content: str,
        web_search_used: bool = False,
        documents_used: bool = False,
    ) -> ChatMessage:
        def _work() -> ChatMessage:
            db = SessionLocal()
            try:
                message = ChatRepository.create(
                    db,
                    project_id,
                    role,
                    content,
                    web_search_used=web_search_used,
                    documents_used=documents_used,
                )
                db.expunge(message)
                return message
            finally:
                db.close()

        return await run_in_threadpool(_work)
