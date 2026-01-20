from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.chat import MessageRole


class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message."""
    content: str
    role: MessageRole = MessageRole.USER


class ChatMessageResponse(BaseModel):
    """Schema for returning a chat message in an API response."""
    model_config = {"from_attributes": True}

    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    tokens: Optional[int] = None
    model: Optional[str] = None


# ---------------------------------------------------------------------
# Chat Session Schemas
# ---------------------------------------------------------------------

class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session."""
    title: Optional[str] = Field(default="New Chat")


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    """Schema for returning basic chat session info in an API response."""
    model_config = {"from_attributes": True}

    id: UUID
    title: str
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatSessionWithMessages(ChatSessionResponse):
    """Extends ChatSessionResponse to include associated messages."""
    messages: List[ChatMessageResponse]


# ---------------------------------------------------------------------
# Chat Interaction Schemas
# ---------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Schema for a user's request to the main chat endpoint."""
    message: str
    chat_session_id: Optional[UUID] = None
    temperature: float = 0.7
    max_tokens: int = 500


class ChatResponse(BaseModel):
    """Schema for the AI's response from the chat endpoint."""
    message: ChatMessageResponse
    chat_session: ChatSessionResponse
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
