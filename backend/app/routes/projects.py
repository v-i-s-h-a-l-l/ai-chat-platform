from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.llm import get_llm_provider
from app.dependencies.prompt_optimization import get_prompt_optimization_service
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatRequest, ChatResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.prompt_optimization import (
    PromptOptimizationRequest,
    PromptOptimizationResponse,
)
from app.services.chat_service import ChatService
from app.services.llm_provider import LLMProvider
from app.services.project_service import ProjectService
from app.services.prompt_optimization_service import PromptOptimizationService
from app.utils.errors import GENERIC_LLM_ERROR, GENERIC_OPTIMIZE_ERROR, sanitize_error_for_client
from app.utils.rate_limit import limiter
from app.utils.serializers import serialize_message, serialize_project
from app.utils.sse import serialize_chat_event

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.create_project(db, current_user.id, data)
    return serialize_project(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = ProjectService.list_projects(db, current_user.id)
    return [serialize_project(p) for p in projects]


@router.post("/optimize-prompt", response_model=PromptOptimizationResponse)
@limiter.limit(settings.rate_limit_optimize)
async def optimize_prompt(
    request: Request,
    data: PromptOptimizationRequest,
    current_user: User = Depends(get_current_user),
    service: PromptOptimizationService = Depends(get_prompt_optimization_service),
):
    """Must be registered before /{project_id} routes to avoid 405 on this path."""
    _ = current_user
    try:
        return await service.optimize_prompt(
            data.project_name,
            data.description,
            data.system_prompt,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not configured" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=sanitize_error_for_client(
                exc, context="Prompt optimization", public_message=GENERIC_OPTIMIZE_ERROR
            ),
        ) from exc


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = ProjectService.get_project(db, project_id, current_user.id, touch=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return serialize_project(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = ProjectService.update_project(db, project_id, current_user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return serialize_project(project)


@router.post("/{project_id}/duplicate", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def duplicate_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = ProjectService.duplicate_project(db, project_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return serialize_project(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await ProjectService.delete_project(db, project_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{project_id}/messages", response_model=list[ChatMessageResponse])
def get_messages(
    project_id: UUID,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        messages = ChatService.get_messages(
            db, project_id, current_user.id, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [serialize_message(m) for m in messages]


@router.post("/{project_id}/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
async def chat(
    request: Request,
    project_id: UUID,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    provider: LLMProvider = Depends(get_llm_provider),
):
    try:
        reply = await ChatService.send_message(
            project_id,
            current_user.id,
            data.message,
            provider,
            request_model=data.model,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=sanitize_error_for_client(
                exc, context="Chat completion", public_message=GENERIC_LLM_ERROR
            ),
        ) from exc

    return ChatResponse(
        user_message=serialize_message(reply.user_message),
        assistant_message=serialize_message(reply.assistant_message),
        web_search_used=reply.web_search_used,
        documents_used=reply.documents_used,
    )


async def _to_sse_stream(events):
    async for event in events:
        yield serialize_chat_event(event)


@router.post("/{project_id}/chat/stream")
@limiter.limit(settings.rate_limit_chat)
async def chat_stream(
    request: Request,
    project_id: UUID,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    provider: LLMProvider = Depends(get_llm_provider),
):
    events = ChatService.stream_message(
        project_id,
        current_user.id,
        data.message,
        provider,
        request_model=data.model,
    )
    return StreamingResponse(
        _to_sse_stream(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
