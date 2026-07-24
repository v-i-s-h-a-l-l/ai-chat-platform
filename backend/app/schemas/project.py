from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.model_resolver import normalize_model_id


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(default="", max_length=10000)
    llm_model: str | None = Field(default=None, max_length=128)

    @field_validator("llm_model")
    @classmethod
    def validate_llm_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_model_id(value)
        if normalized is None:
            raise ValueError("Invalid model id")
        return normalized


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_pinned: bool | None = None
    llm_model: str | None = Field(default=None, max_length=128)

    @field_validator("llm_model")
    @classmethod
    def validate_llm_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_model_id(value)
        if normalized is None:
            raise ValueError("Invalid model id")
        return normalized


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    system_prompt: str
    created_at: str
    last_accessed_at: str | None
    is_pinned: bool
    llm_model: str | None = None

    model_config = {"from_attributes": True}
