from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(default="", max_length=10000)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    system_prompt: str
    created_at: str

    model_config = {"from_attributes": True}
