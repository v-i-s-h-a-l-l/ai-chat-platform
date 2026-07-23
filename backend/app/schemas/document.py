from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    mime_type: str
    file_size: int
    status: str
    error_message: str | None = None
    chunk_count: int
    created_at: str

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str = "Document accepted for processing"
