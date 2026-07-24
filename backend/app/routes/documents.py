from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.guardrails import GuardrailViolationError
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services.document_service import DocumentService
from app.services.ingestion_errors import IngestionQueueUnavailableError
from app.services.upload_validation import UploadConfirmationRequiredError
from app.utils.mime_validation import detect_mime
from app.utils.rate_limit import limiter
from app.utils.upload_reader import read_upload_capped

router = APIRouter(prefix="/projects", tags=["documents"])


def _serialize_document(doc) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        project_id=doc.project_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@router.post(
    "/{project_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    project_id: UUID,
    file: UploadFile = File(...),
    x_upload_confirm: str | None = Header(default=None, alias="X-Upload-Confirm"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    data = await read_upload_capped(file)
    confirmed = (x_upload_confirm or "").lower() in {"1", "true", "yes"}

    try:
        mime = detect_mime(data, file.filename, file.content_type)
        doc = await DocumentService.upload_document(
            db,
            project_id,
            current_user.id,
            file.filename,
            mime,
            data,
            confirmed=confirmed,
        )
    except UploadConfirmationRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": exc.message,
                "code": exc.code,
                "document_type": exc.document_type,
                "confidence": exc.confidence,
            },
        ) from exc
    except GuardrailViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionQueueUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    return DocumentUploadResponse(document=_serialize_document(doc))


@router.post(
    "/{project_id}/documents/{document_id}/reprocess",
    response_model=DocumentResponse,
)
async def reprocess_document(
    project_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        doc = await DocumentService.reprocess_document(
            db, project_id, current_user.id, document_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_document(doc)


@router.get("/{project_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        docs = await DocumentService.list_documents_with_recovery(
            db, project_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_document(d) for d in docs]


@router.delete("/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await DocumentService.delete_document(db, project_id, current_user.id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
