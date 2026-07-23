import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.dependencies.prompt_optimization import get_prompt_optimization_service
from app.main import app
from app.models.user import User
from app.services.prompt_optimization_provider import PromptOptimizationProviderResult
from app.services.prompt_optimization_service import PromptOptimizationService


@pytest.fixture
def mock_user() -> User:
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
    )
    return user


@pytest.fixture
def client(mock_user: User):
    mock_provider = AsyncMock()
    service = PromptOptimizationService(mock_provider)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_prompt_optimization_service] = lambda: service

    with TestClient(app) as test_client:
        test_client._mock_provider = mock_provider  # type: ignore[attr-defined]
        yield test_client

    app.dependency_overrides.clear()
