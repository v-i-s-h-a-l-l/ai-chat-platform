from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    text: str = Field(..., min_length=1)
