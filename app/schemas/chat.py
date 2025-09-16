# app/models/chat.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatSessionBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id", description="User who owns this chat session")
    title: str = Field(default="New Chat", description="Chat session title")
    is_active: bool = Field(default=True, description="Whether the chat session is active")

class ChatSession(ChatSessionBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = Field(default=0, description="Number of messages in this session")
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="chat_sessions")
    messages: List["ChatMessage"] = Relationship(back_populates="chat_session")

class ChatMessageBase(SQLModel):
    chat_session_id: UUID = Field(foreign_key="chatsession.id", description="Chat session this message belongs to")
    role: MessageRole = Field(description="Role of the message sender")
    content: str = Field(description="Message content")
    tokens: Optional[int] = Field(default=None, description="Number of tokens used")

class ChatMessage(ChatMessageBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    model: Optional[str] = Field(default=None, description="AI model used for response")
    temperature: Optional[float] = Field(default=None, description="Temperature setting for AI")
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Field(JSON))
    
    # Relationships
    chat_session: Optional[ChatSession] = Relationship(back_populates="messages")

# Request/Response schemas
class ChatMessageCreate(SQLModel):
    content: str
    role: MessageRole = MessageRole.USER

class ChatMessageResponse(SQLModel):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    tokens: Optional[int] = None
    model: Optional[str] = None

class ChatSessionCreate(SQLModel):
    title: Optional[str] = "New Chat"

class ChatSessionResponse(SQLModel):
    id: UUID
    title: str
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime

class ChatSessionWithMessages(ChatSessionResponse):
    messages: List[ChatMessageResponse] = Field(default_factory=list)

class ChatRequest(SQLModel):
    message: str
    chat_session_id: Optional[UUID] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500

class ChatResponse(SQLModel):
    message: ChatMessageResponse
    chat_session: ChatSessionResponse
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None