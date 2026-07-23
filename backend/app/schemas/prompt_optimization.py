from pydantic import BaseModel, Field


class PromptOptimizationRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(..., min_length=1, max_length=10000)


class PromptOptimizationResponse(BaseModel):
    safe: bool
    reason: str | None = None
    original_prompt: str
    improved_prompt: str | None = None
    changes: list[str] = Field(default_factory=list)
