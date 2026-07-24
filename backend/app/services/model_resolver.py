"""Resolve which Groq model to use for a chat turn."""

from app.available_models import DEFAULT_LLM_MODEL, get_model_or_default, is_valid_model_id
from app.models.project import Project
from app.models.user import User


def resolve_chat_model(
    *,
    request_model: str | None,
    project: Project,
    user: User,
) -> str:
    """Priority: explicit request → project → user preference → default."""
    if is_valid_model_id(request_model):
        return request_model  # type: ignore[return-value]
    if is_valid_model_id(project.llm_model):
        return project.llm_model  # type: ignore[return-value]
    if is_valid_model_id(user.preferred_llm_model):
        return user.preferred_llm_model  # type: ignore[return-value]
    return DEFAULT_LLM_MODEL


def normalize_model_id(model_id: str | None) -> str | None:
    if model_id is None:
        return None
    return model_id if is_valid_model_id(model_id) else None


def coerce_model_id(model_id: str | None) -> str:
    return get_model_or_default(model_id)
