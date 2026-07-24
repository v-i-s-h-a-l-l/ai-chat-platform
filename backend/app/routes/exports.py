from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.export import ExportFormatsResponse
from app.services.workspace_export_service import WorkspaceExportService
from app.utils.errors import GENERIC_EXPORT_ERROR, sanitize_error_for_client
from app.workspace_export.models import ExportFormat

router = APIRouter(prefix="/projects", tags=["workspace-export"])

_export_service = WorkspaceExportService()


@router.get(
    "/{project_id}/messages/{message_id}/export/formats",
    response_model=ExportFormatsResponse,
)
def get_export_formats(
    project_id: UUID,
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        message, _ = _export_service.get_message_for_export(
            db, project_id, message_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _export_service.list_formats(message.content)


@router.get("/{project_id}/messages/{message_id}/export")
def export_message(
    project_id: UUID,
    message_id: UUID,
    format: ExportFormat = Query(..., alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data, filename, media_type = _export_service.export_message(
            db, project_id, message_id, current_user.id, format
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if "not found" in detail.lower():
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=sanitize_error_for_client(
                exc, context="Workspace export", public_message=GENERIC_EXPORT_ERROR
            ),
        ) from exc

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
