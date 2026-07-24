from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.model_resolver import normalize_model_id


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    preferred_llm_model: str | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    preferred_llm_model: str | None = Field(default=None, max_length=128)

    @field_validator("preferred_llm_model")
    @classmethod
    def validate_preferred_llm_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_model_id(value)
        if normalized is None:
            raise ValueError("Invalid model id")
        return normalized
