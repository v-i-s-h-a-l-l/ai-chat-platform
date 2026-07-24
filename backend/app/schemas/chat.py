from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.model_resolver import normalize_model_id


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: str
    web_search_used: bool = False
    documents_used: bool = False

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    model: str | None = Field(default=None, max_length=128)

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_model_id(value)
        if normalized is None:
            raise ValueError("Invalid model id")
        return normalized


class ChatResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    web_search_used: bool = False
    documents_used: bool = False
