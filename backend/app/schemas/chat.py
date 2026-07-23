from uuid import UUID

from pydantic import BaseModel, Field


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


class ChatResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    web_search_used: bool = False
    documents_used: bool = False
