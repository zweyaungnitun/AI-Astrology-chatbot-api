from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from uuid import UUID
import logging
import json

from app.dependencies.auth import get_current_user
from app.database.session import get_db_session
from app.schemas.chat import (
    ChatRequest, ChatResponse, ChatSessionResponse, 
    ChatMessageResponse, ChatSessionCreate, ChatSessionUpdate, ChatSessionWithMessages
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

async def _get_internal_user_id(db: AsyncSession, firebase_uid: str) -> UUID:
    """Helper to get internal user ID from Firebase UID."""
    from app.services.user_service import UserService
    user_service = UserService(db)
    user = await user_service.get_user_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record is missing an ID"
        )
    return user.id

@router.post("", response_model=ChatResponse)
async def send_chat_message(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Send a chat message and get AI response."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    result = await chat_service.process_chat_message(
        user_id=user_id,
        message=chat_request.message,
        session_id=chat_request.chat_session_id,
        temperature=chat_request.temperature,
        max_tokens=chat_request.max_tokens
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process chat message"
        )
    
    # Convert result to ChatResponse format
    ai_message = result["ai_message"]
    chat_session = result["chat_session"]
    
    return ChatResponse(
        message=ChatMessageResponse(
            id=ai_message.id,
            role=ai_message.role,
            content=ai_message.content,
            created_at=ai_message.created_at,
            tokens=ai_message.tokens,
            model=ai_message.message_metadata.get("model") if ai_message.message_metadata else None
        ),
        chat_session=ChatSessionResponse(
            id=chat_session.id,
            title=chat_session.title,
            is_active=chat_session.is_active,
            message_count=chat_session.message_count,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at
        ),
        tokens_used=result.get("tokens_used"),
        processing_time=result.get("processing_time")
    )

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat session."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    session = await chat_service.create_chat_session(user_id, session_data)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create chat session"
        )
    
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        message_count=session.message_count,
        created_at=session.created_at,
        updated_at=session.updated_at
    )

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_chat_sessions(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all chat sessions for the current user."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    sessions = await chat_service.get_user_chat_sessions(user_id, active_only=active_only)
    
    return [
        ChatSessionResponse(
            id=session.id,
            title=session.title,
            is_active=session.is_active,
            message_count=session.message_count,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
        for session in sessions
    ]

@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific chat session with messages."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    session = await chat_service.get_chat_session(session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Get messages for this session
    messages = await chat_service.get_session_messages(session_id, limit=100)
    
    return ChatSessionWithMessages(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        message_count=session.message_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            ChatMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                tokens=msg.tokens,
                model=msg.message_metadata.get("model") if msg.message_metadata else None
            )
            for msg in messages
        ]
    )

@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: UUID,
    update_data: ChatSessionUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a chat session (e.g., title)."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    if update_data.title is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required for update"
        )
    
    updated_session = await chat_service.update_chat_session_title(session_id, update_data.title, user_id)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return ChatSessionResponse(
        id=updated_session.id,
        title=updated_session.title,
        is_active=updated_session.is_active,
        message_count=updated_session.message_count,
        created_at=updated_session.created_at,
        updated_at=updated_session.updated_at
    )

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat session."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    # Verify session belongs to user before deleting
    session = await chat_service.get_chat_session(session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    success = await chat_service.delete_chat_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete chat session"
        )
    
    return {"message": "Chat session deleted successfully"}

@router.post("/sessions/{session_id}/deactivate")
async def deactivate_chat_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Deactivate a chat session."""
    chat_service = ChatService(db)
    user_id = await _get_internal_user_id(db, current_user['uid'])
    
    success = await chat_service.deactivate_chat_session(session_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return {"message": "Chat session deactivated successfully"}