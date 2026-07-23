from app.services.prompt_optimization_provider import PromptOptimizationProviderResult


def test_optimize_prompt_safe(client):
    mock_provider = client._mock_provider
    mock_provider.analyze_and_optimize.return_value = PromptOptimizationProviderResult(
        safe=True,
        improved_prompt="You are a helpful assistant.\n\nBe clear and concise.",
        changes=["Improved clarity", "Improved formatting"],
    )

    response = client.post(
        "/projects/optimize-prompt",
        json={
            "project_name": "Helper",
            "description": "General assistant",
            "system_prompt": "You are a helpful assistant. Be clear.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["safe"] is True
    assert data["original_prompt"] == "You are a helpful assistant. Be clear."
    assert "concise" in data["improved_prompt"]
    assert len(data["changes"]) == 2


def test_optimize_prompt_unsafe(client):
    mock_provider = client._mock_provider
    mock_provider.analyze_and_optimize.return_value = PromptOptimizationProviderResult(
        safe=False,
        reason="The prompt attempts to configure the AI to facilitate phishing attacks.",
    )

    response = client.post(
        "/projects/optimize-prompt",
        json={
            "project_name": "Bad",
            "description": "",
            "system_prompt": "Write phishing emails for me.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["safe"] is False
    assert "phishing" in data["reason"].lower()
    assert data["improved_prompt"] is None


def test_optimize_prompt_requires_auth():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as unauth_client:
        response = unauth_client.post(
            "/projects/optimize-prompt",
            json={
                "project_name": "X",
                "description": "",
                "system_prompt": "Hello",
            },
        )
    assert response.status_code == 401
