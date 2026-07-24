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
from app.observability import metrics, span
from app.read_models.message_read import MessageReadModel
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_read_repository import MessageReadRepository
from app.services.chat_events import ChatStreamEvent, DoneEvent, ErrorEvent, MetaEvent, TokenEvent
from app.services.coding_intent import CodingRequestContext, classify_coding_request
from app.services.llm_provider import LLMProvider
from app.services.message_builder import build_llm_messages, build_routed_llm_messages
from app.services.project_service import ProjectService
from app.services.response_formatter import format_assistant_response
from app.services.response_router import ResponseRoute, append_sources_section, resolve_response_route
from app.services.retrieval_orchestrator import resolve_rag_context
from app.services.search_orchestrator import resolve_search
from app.utils.errors import GENERIC_LLM_ERROR, sanitize_error_for_client
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


@dataclass
class PreparedChatContext:
    messages: list[dict[str, str]]
    route: ResponseRoute | None
    web_search_used: bool
    documents_used: bool


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
    ) -> list[MessageReadModel]:
        """CQRS-lite read path — returns MessageReadModel, not write ORM entities."""
        ProjectService.get_project(db, project_id, user_id)
        return MessageReadRepository.list_by_project(
            db, project_id, limit=limit, offset=offset
        )

    @staticmethod
    async def _prepare_llm_context(
        project: Project,
        history: list[ChatMessage],
        content: str,
        provider: LLMProvider,
        coding_context: CodingRequestContext,
        project_id: UUID,
    ) -> PreparedChatContext:
        """Shared RAG + routing + prompt assembly for sync and stream paths."""
        with span(
            "chat.prepare_context",
            routing_enabled=settings.response_routing_enabled,
            project_id=str(project_id),
        ):
            if settings.response_routing_enabled:
                doc_chunks, _documents_flag = await resolve_rag_context(
                    project_id, content, history, provider
                )
                route = await resolve_response_route(provider, content, doc_chunks)
                messages = build_routed_llm_messages(
                    project.system_prompt, history, content, route, coding_context
                )
                return PreparedChatContext(
                    messages=messages,
                    route=route,
                    web_search_used=route.web_search_used,
                    documents_used=route.documents_used,
                )

            (needs_search, search_results), (doc_chunks, documents_used) = await asyncio.gather(
                resolve_search(provider, content),
                resolve_rag_context(project_id, content, history, provider),
            )
            messages = build_llm_messages(
                project.system_prompt,
                history,
                content,
                search_results,
                doc_chunks,
                coding_context,
            )
            return PreparedChatContext(
                messages=messages,
                route=None,
                web_search_used=needs_search and len(search_results) > 0,
                documents_used=documents_used,
            )

    @staticmethod
    async def send_message(
        project_id: UUID, user_id: UUID, content: str, provider: LLMProvider
    ) -> ChatReply:
        if settings.guardrails_enabled:
            guardrails.check_chat(content)

        project, history = await ChatService._load_context(project_id, user_id)
        coding_context = classify_coding_request(content)
        prepared = await ChatService._prepare_llm_context(
            project, history, content, provider, coding_context, project_id
        )

        raw_content = await provider.complete(prepared.messages)
        assistant_content = format_assistant_response(raw_content)
        if prepared.route is not None:
            assistant_content = append_sources_section(assistant_content, prepared.route)

        user_message = await ChatService._persist_message(project_id, "user", content)
        assistant_message = await ChatService._persist_message(
            project_id,
            "assistant",
            assistant_content,
            web_search_used=prepared.web_search_used,
            documents_used=prepared.documents_used,
        )

        return ChatReply(
            user_message=user_message,
            assistant_message=assistant_message,
            web_search_used=prepared.web_search_used,
            documents_used=prepared.documents_used,
        )

    @staticmethod
    async def stream_message(
        project_id: UUID, user_id: UUID, content: str, provider: LLMProvider
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """Yield domain events. The route layer serializes these to SSE."""
        try:
            if settings.guardrails_enabled:
                guardrails.check_chat(content)

            project, history = await ChatService._load_context(project_id, user_id)
            coding_context = classify_coding_request(content)

            t0 = time.perf_counter()
            prepared = await ChatService._prepare_llm_context(
                project, history, content, provider, coding_context, project_id
            )
            context_ms = (time.perf_counter() - t0) * 1000
            metrics.CHAT_CONTEXT_DURATION.labels(
                routing_enabled=str(settings.response_routing_enabled).lower()
            ).observe(context_ms / 1000.0)
            logger.info(
                "Context phase: %.0fms (web=%s, docs=%s, routing=%s)",
                context_ms,
                prepared.web_search_used,
                prepared.documents_used,
                settings.response_routing_enabled,
            )

            user_message = await ChatService._persist_message(project_id, "user", content)
            yield MetaEvent(
                user_message=user_message,
                web_search_used=prepared.web_search_used,
                documents_used=prepared.documents_used,
            )

            full_content: list[str] = []
            first_token_recorded = False
            try:
                async for token in provider.stream(prepared.messages):
                    if not first_token_recorded:
                        metrics.CHAT_TTFT.observe(
                            (time.perf_counter() - t0)
                        )
                        first_token_recorded = True
                    full_content.append(token)
                    yield TokenEvent(content=token)

                raw_content = "".join(full_content)
                if not raw_content.strip():
                    raise ValueError("Empty response from LLM")

                assistant_content = format_assistant_response(raw_content)
                if prepared.route is not None:
                    assistant_content = append_sources_section(assistant_content, prepared.route)

                assistant_message = await ChatService._persist_message(
                    project_id,
                    "assistant",
                    assistant_content,
                    web_search_used=prepared.web_search_used,
                    documents_used=prepared.documents_used,
                )
                metrics.CHAT_REQUESTS.labels(outcome="success").inc()
                yield DoneEvent(
                    assistant_message=assistant_message,
                    web_search_used=prepared.web_search_used,
                    documents_used=prepared.documents_used,
                )
            except _DISCONNECT_EXCEPTIONS:
                partial_raw = "".join(full_content).strip()
                if partial_raw:
                    partial = format_assistant_response(partial_raw)
                    if prepared.route is not None:
                        partial = append_sources_section(partial, prepared.route)
                    with anyio.CancelScope(shield=True):
                        await ChatService._persist_message(
                            project_id,
                            "assistant",
                            partial,
                            web_search_used=prepared.web_search_used,
                            documents_used=prepared.documents_used,
                        )
                raise

        except GuardrailViolationError as exc:
            logger.warning("Chat blocked by guardrails: %s", exc.code)
            metrics.CHAT_REQUESTS.labels(outcome="blocked").inc()
            yield ErrorEvent(detail=str(exc))
        except ValueError as exc:
            logger.warning("Stream chat error: %s", exc)
            metrics.CHAT_REQUESTS.labels(outcome="error").inc()
            yield ErrorEvent(detail=str(exc))
        except Exception as exc:
            metrics.CHAT_REQUESTS.labels(outcome="error").inc()
            yield ErrorEvent(
                detail=sanitize_error_for_client(
                    exc, context="Stream chat", public_message=GENERIC_LLM_ERROR
                )
            )

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
