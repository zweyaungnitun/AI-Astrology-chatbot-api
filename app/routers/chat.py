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
    ChatMessageResponse, ChatSessionCreate, ChatSessionWithMessages
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

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
    
    return Chat