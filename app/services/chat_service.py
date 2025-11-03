# app/services/chat_service.py
from sqlmodel import select, update, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging
from datetime import datetime
import time

from app.schemas.chat import (
    ChatSessionCreate, ChatMessageCreate,
    MessageRole, ChatSessionResponse, ChatMessageResponse
)
from app.models.chat import ChatSession, ChatMessage
from app.services.ai_service import ai_service
from app.services.redis_service import get_redis_service
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.redis_service = None
    
    async def _get_redis_service(self):
        """Get Redis service instance, initializing if needed."""
        if self.redis_service is None:
            self.redis_service = await get_redis_service()
        return self.redis_service
    
    def _message_to_dict(self, message_data: ChatMessageCreate, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Convert ChatMessageCreate to dictionary for Redis storage."""
        return {
            "id": str(uuid4()),
            "role": message_data.role.value if hasattr(message_data.role, 'value') else str(message_data.role),
            "content": message_data.content,
            "tokens": getattr(message_data, 'tokens', None),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
    
    def _dict_to_message(self, msg_dict: Dict[str, Any], session_id: UUID) -> ChatMessage:
        """Convert dictionary from Redis to ChatMessage object."""
        return ChatMessage(
            id=UUID(msg_dict["id"]) if msg_dict.get("id") else None,
            chat_session_id=session_id,
            role=MessageRole(msg_dict["role"]),
            content=msg_dict["content"],
            tokens=msg_dict.get("tokens"),
            created_at=datetime.fromisoformat(msg_dict.get("created_at", datetime.utcnow().isoformat())),
            message_metadata=msg_dict.get("metadata", {})
        )

    async def create_chat_session(self, user_id: UUID, session_data: ChatSessionCreate) -> Optional[ChatSession]:
        """Create a new chat session for a user."""
        try:
            chat_session = ChatSession(
                user_id=user_id,
                title=session_data.title,
                is_active=True
            )
            
            self.db.add(chat_session)
            await self.db.commit()
            await self.db.refresh(chat_session)
            
            logger.info(f"Created chat session {chat_session.id} for user {user_id}")
            return chat_session
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating chat session: {str(e)}")
            return None

    async def get_chat_session(self, session_id: UUID, user_id: UUID) -> Optional[ChatSession]:
        """Get a chat session by ID, ensuring it belongs to the user."""
        try:
            result = await self.db.exec(
                select(ChatSession).where(
                    (ChatSession.id == session_id) &
                    (ChatSession.user_id == user_id)
                )
            )
            return result.first()
        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {str(e)}")
            return None

    async def get_user_chat_sessions(self, user_id: UUID, active_only: bool = True) -> List[ChatSession]:
        """Get all chat sessions for a user."""
        try:
            query = select(ChatSession).where(ChatSession.user_id == user_id)
            
            if active_only:
                query = query.where(ChatSession.is_active == True)
                
            query = query.order_by(ChatSession.updated_at.desc())
            
            result = await self.db.exec(query)
            return result.all()
        except Exception as e:
            logger.error(f"Error getting chat sessions for user {user_id}: {str(e)}")
            return []

    async def add_message_to_session(
        self, 
        session_id: UUID, 
        message_data: ChatMessageCreate,
        metadata: Optional[Dict] = None
    ) -> Optional[ChatMessage]:
        """Add a message to a chat session (stored in Redis)."""
        try:
            redis_service = await self._get_redis_service()
            
            # Convert message to dict format for Redis
            message_dict = self._message_to_dict(message_data, metadata)
            
            # Store message in Redis
            success = await redis_service.update_chat_session(
                str(session_id),
                message_dict,
                max_messages=100
            )
            
            if not success:
                logger.error(f"Failed to store message in Redis for session {session_id}")
                return None
            
            # Update session message count and timestamp in database
            await self.db.exec(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(
                    message_count=ChatSession.message_count + 1,
                    updated_at=datetime.utcnow()
                )
            )
            
            await self.db.commit()
            
            # Convert back to ChatMessage object for return
            return self._dict_to_message(message_dict, session_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            return None

    async def get_session_messages(self, session_id: UUID, limit: int = 100) -> List[ChatMessage]:
        """Get messages for a chat session from Redis."""
        try:
            redis_service = await self._get_redis_service()
            
            # Get messages from Redis
            messages_data = await redis_service.get_chat_session(str(session_id))
            
            if not messages_data:
                return []
            
            # Convert dict messages to ChatMessage objects
            messages = [
                self._dict_to_message(msg_dict, session_id)
                for msg_dict in messages_data[:limit]
            ]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}")
            return []

    async def update_chat_session_title(self, session_id: UUID, title: str) -> Optional[ChatSession]:
        """Update chat session title."""
        try:
            session = await self.get_chat_session(session_id)
            if not session:
                return None

            session.title = title
            session.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(session)
            
            return session
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating chat session {session_id}: {str(e)}")
            return None

    async def deactivate_chat_session(self, session_id: UUID) -> bool:
        """Deactivate a chat session."""
        try:
            session = await self.get_chat_session(session_id)
            if not session:
                return False

            session.is_active = False
            session.updated_at = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deactivating chat session {session_id}: {str(e)}")
            return False

    async def delete_chat_session(self, session_id: UUID) -> bool:
        """Delete a chat session and all its messages from both Redis and database."""
        try:
            redis_service = await self._get_redis_service()
            
            # Delete messages from Redis
            await redis_service.delete_chat_session(str(session_id))
            
            # Delete the session from database
            await self.db.exec(
                delete(ChatSession).where(ChatSession.id == session_id)
            )
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting chat session {session_id}: {str(e)}")
            return False

    async def process_chat_message(
        self, 
        user_id: UUID, 
        message: str, 
        session_id: Optional[UUID] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        evaluate: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Process chat message with LangChain and LangCheck integration."""
        start_time = time.time()
        
        try:
            # Get or create chat session
            if session_id:
                chat_session = await self.get_chat_session(session_id, user_id)
                if not chat_session:
                    return None
            else:
                title = message[:50] + "..." if len(message) > 50 else message
                chat_session = await self.create_chat_session(
                    user_id, 
                    ChatSessionCreate(title=title)
                )
                if not chat_session:
                    return None

            # Add user message to session
            user_message = await self.add_message_to_session(
                chat_session.id,
                ChatMessageCreate(content=message, role=MessageRole.USER)
            )
            if not user_message:
                return None

            # Get user context
            from app.services.user_service import UserService
            user_service = UserService(self.db)
            birth_data = await user_service.get_birth_data(user_id)

            # Get chat history
            chat_history = await self.get_session_messages(chat_session.id)
            
            # Get AI response using LangChain
            ai_response = await ai_service.get_ai_response(
                user_message=message,
                chat_history=chat_history,
                birth_data=birth_data,
                temperature=temperature,
                max_tokens=max_tokens,
                evaluate=evaluate
            )

            # Add AI response to session
            ai_message = await self.add_message_to_session(
                chat_session.id,
                ChatMessageCreate(
                    content=ai_response["content"],
                    role=MessageRole.ASSISTANT,
                    tokens=ai_response.get("tokens")
                ),
                metadata={
                    "model": ai_response.get("model"),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "processing_time": ai_response.get("processing_time"),
                    "evaluation": ai_response.get("evaluation", {})
                }
            )

            return {
                "user_message": user_message,
                "ai_message": ai_message,
                "chat_session": chat_session,
                "tokens_used": ai_response.get("tokens"),
                "processing_time": ai_response.get("processing_time"),
                "evaluation": ai_response.get("evaluation")
            }
            
        except Exception as e:
            logger.error(f"Chat processing error: {str(e)}")
            return None