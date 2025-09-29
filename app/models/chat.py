from sqlmodel import SQLModel, Field, Relationship, Column
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from sqlalchemy import JSON

class MessageRole(str, Enum):
    """Enumeration for the role of a message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatSession(SQLModel, table=True):
    """
    Represents the 'chatsession' table in the database.
    """
    __tablename__ = "chatsession"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", description="User who owns this chat session")
    title: str = Field(default="New Chat", description="Chat session title")
    is_active: bool = Field(default=True, description="Whether the chat session is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = Field(default=0, description="Number of messages in this session")
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="chat_sessions")
    messages: List["ChatMessage"] = Relationship(back_populates="chat_session")

class ChatMessage(SQLModel, table=True):
    """
    Represents the 'chatmessage' table in the database.
    """
    __tablename__ = "chatmessage"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    chat_session_id: UUID = Field(foreign_key="chatsession.id", description="Chat session this message belongs to")
    role: MessageRole = Field(description="Role of the message sender")
    content: str = Field(description="Message content")
    tokens: Optional[int] = Field(default=None, description="Number of tokens used")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    model: Optional[str] = Field(default=None, description="AI model used for response")
    temperature: Optional[float] = Field(default=None, description="Temperature setting for AI")
    message_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Relationships
    chat_session: Optional[ChatSession] = Relationship(back_populates="messages")
