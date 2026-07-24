"""Tests for centralized domain exception handlers."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.ingestion_errors import IngestionQueueUnavailableError
from app.services.upload_validation.exceptions import UploadConfirmationRequiredError
from app.guardrails.exceptions import GuardrailViolationError


def test_guardrail_violation_returns_400(api_client):
    project_id = uuid4()
    with patch(
        "app.routes.documents.DocumentService.upload_document",
        new_callable=AsyncMock,
        side_effect=GuardrailViolationError("Blocked content"),
    ):
        response = api_client.post(
            f"/projects/{project_id}/documents",
            files={"file": ("bad.pdf", b"%PDF-1.4", "application/pdf")},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
    assert response.status_code == 400
    assert "Blocked content" in response.json()["detail"]


def test_upload_confirmation_returns_409(api_client):
    project_id = uuid4()
    with patch(
        "app.routes.documents.DocumentService.upload_document",
        new_callable=AsyncMock,
        side_effect=UploadConfirmationRequiredError(
            "Confirm upload",
            document_type="legal",
            confidence=0.9,
        ),
    ):
        response = api_client.post(
            f"/projects/{project_id}/documents",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "upload_confirmation_required"


def test_ingestion_queue_unavailable_returns_503(api_client):
    project_id = uuid4()
    with patch(
        "app.routes.documents.DocumentService.upload_document",
        new_callable=AsyncMock,
        side_effect=IngestionQueueUnavailableError("doc-id"),
    ):
        response = api_client.post(
            f"/projects/{project_id}/documents",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
    assert response.status_code == 503
