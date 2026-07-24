import pytest

from app.available_models import DEFAULT_LLM_MODEL
from app.services.model_resolver import resolve_chat_model


class _Project:
    llm_model = "llama-3.3-70b-versatile"


class _User:
    preferred_llm_model = "qwen/qwen3.6-27b"


def test_resolve_chat_model_request_overrides_project_and_user():
    resolved = resolve_chat_model(
        request_model="openai/gpt-oss-120b",
        project=_Project(),
        user=_User(),
    )
    assert resolved == "openai/gpt-oss-120b"


def test_resolve_chat_model_project_overrides_user():
    resolved = resolve_chat_model(
        request_model=None,
        project=_Project(),
        user=_User(),
    )
    assert resolved == "llama-3.3-70b-versatile"


def test_resolve_chat_model_user_preference_before_default():
    project = _Project()
    project.llm_model = None
    resolved = resolve_chat_model(
        request_model=None,
        project=project,
        user=_User(),
    )
    assert resolved == "qwen/qwen3.6-27b"


def test_resolve_chat_model_defaults_when_unset():
    project = _Project()
    project.llm_model = None
    user = _User()
    user.preferred_llm_model = None
    resolved = resolve_chat_model(
        request_model=None,
        project=project,
        user=user,
    )
    assert resolved == DEFAULT_LLM_MODEL
