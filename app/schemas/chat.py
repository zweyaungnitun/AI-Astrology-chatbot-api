from sqlmodel import SQLModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from app.models.chat import MessageRole

# --- Chat Schemas ---

class ChatMessageCreate(SQLModel):
    """Schema for creating a new chat message."""
    content: str
    role: MessageRole = MessageRole.USER

class ChatMessageResponse(SQLModel):
    """Schema for returning a chat message in an API response."""
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    tokens: Optional[int] = None
    model: Optional[str] = None

class ChatSessionCreate(SQLModel):
    """Schema for creating a new chat session."""
    title: Optional[str] = "New Chat"

class ChatSessionResponse(SQLModel):
    """Schema for returning basic chat session info in an API response."""
    id: UUID
    title: str
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime

class ChatSessionWithMessages(ChatSessionResponse):
    """Extends ChatSessionResponse to include associated messages."""
    messages: List[ChatMessageResponse] = Field(default_factory=list)

class ChatRequest(SQLModel):
    """Schema for a user's request to the main chat endpoint."""
    message: str
    chat_session_id: Optional[UUID] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500

class ChatResponse(SQLModel):
    """Schema for the AI's response from the chat endpoint."""
    message: ChatMessageResponse
    chat_session: ChatSessionResponse
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
