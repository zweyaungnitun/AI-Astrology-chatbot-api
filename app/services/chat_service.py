# app/services/chat_service.py
from sqlmodel import select, update, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging
from datetime import datetime, timedelta
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

    async def get_chat_session(self, session_id: UUID, user_id: Optional[UUID] = None) -> Optional[ChatSession]:
        """Get a chat session by ID, ensuring it belongs to the user."""
        try:
            query = select(ChatSession).where(ChatSession.id == session_id)
            if user_id:
                query = query.where(ChatSession.user_id == user_id)
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
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
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
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
            await self.db.execute(
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

    async def update_chat_session_title(
        self,
        session_id: UUID,
        title: str,
        user_id: Optional[UUID] = None
    ) -> Optional[ChatSession]:
        """Update chat session title."""
        try:
            session = await self.get_chat_session(session_id, user_id)
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

    async def deactivate_chat_session(self, session_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """Deactivate a chat session and optionally persist messages to database."""
        try:
            if user_id:
                session = await self.get_chat_session(session_id, user_id)
            else:
                # Fallback: try to get session without user check
                result = await self.db.execute(
                    select(ChatSession).where(ChatSession.id == session_id)
                )
                session = result.scalar_one_or_none()
            
            if not session:
                return False

            session.is_active = False
            session.updated_at = datetime.utcnow()
            
            # Optionally persist messages to database before deactivating
            # This ensures no data loss when Redis TTL expires
            await self.persist_session_to_db(session_id, user_id)
            
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
            await self.db.execute(
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

            # Get user context
            from app.services.user_service import UserService
            user_service = UserService(self.db)
            birth_data = await user_service.get_birth_data(user_id)

            # Get chat history BEFORE adding current message (so AI can reference past conversations)
            # Use contextual messages for better memory management
            contextual_data = await self.get_contextual_messages(
                chat_session.id,
                recent_count=50,  # Get more messages for better context
                max_tokens=3000  # Token limit for context window
            )
            chat_history = contextual_data.get("recent_messages", [])
            
            # Add user message to session AFTER getting history
            user_message = await self.add_message_to_session(
                chat_session.id,
                ChatMessageCreate(content=message, role=MessageRole.USER)
            )
            if not user_message:
                return None
            
            # Get AI response using LangChain with full chat history
            # The AI will reference past messages from chat_history
            logger.info(f"Getting AI response with {len(chat_history)} messages from chat history")
            ai_response = await ai_service.get_ai_response(
                user_message=message,
                chat_history=chat_history,  # Pass full conversation history
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

    # Memory Management Methods
    
    async def persist_session_to_db(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Persist chat messages from Redis to PostgreSQL database.
        This ensures long-term storage and prevents data loss.
        """
        try:
            redis_service = await self._get_redis_service()
            
            # Get messages from Redis
            messages_data = await redis_service.get_chat_session(str(session_id))
            
            if not messages_data:
                logger.debug(f"No messages in Redis for session {session_id}")
                return False
            
            # Check which messages are already in database
            existing_messages = await self.db.execute(
                select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
            )
            existing_ids = {str(msg.id) for msg in existing_messages.scalars().all()}
            
            # Filter out messages that are already persisted
            new_messages_data = [
                msg for msg in messages_data
                if msg.get('id') not in existing_ids
            ]
            
            if not new_messages_data:
                logger.debug(f"All messages already persisted for session {session_id}")
                return True
            
            # Convert to ChatMessage objects and bulk insert
            db_messages = []
            for msg_dict in new_messages_data:
                try:
                    db_message = ChatMessage(
                        id=UUID(msg_dict['id']) if msg_dict.get('id') else uuid4(),
                        chat_session_id=session_id,
                        role=MessageRole(msg_dict['role']),
                        content=msg_dict['content'],
                        tokens=msg_dict.get('tokens'),
                        created_at=datetime.fromisoformat(
                            msg_dict.get('created_at', datetime.utcnow().isoformat())
                        ),
                        message_metadata=msg_dict.get('metadata', {})
                    )
                    db_messages.append(db_message)
                except Exception as e:
                    logger.warning(f"Error converting message {msg_dict.get('id')}: {str(e)}")
                    continue
            
            if db_messages:
                self.db.add_all(db_messages)
                await self.db.commit()
                logger.info(f"Persisted {len(db_messages)} messages to DB for session {session_id}")
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error persisting session {session_id} to DB: {str(e)}")
            return False

    async def get_session_messages_with_fallback(
        self,
        session_id: UUID,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get messages from Redis, with fallback to database if Redis is empty.
        This ensures messages are available even if Redis cache expires.
        """
        try:
            # Try Redis first (fast path)
            messages = await self.get_session_messages(session_id, limit)
            
            if messages:
                return messages
            
            # Fallback to database
            logger.info(f"Redis cache miss for session {session_id}, loading from database")
            result = await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.chat_session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(limit)
            )
            db_messages = result.scalars().all()
            
            # Optionally restore to Redis for future access
            if db_messages:
                redis_service = await self._get_redis_service()
                messages_data = [
                    {
                        "id": str(msg.id),
                        "role": msg.role.value,
                        "content": msg.content,
                        "tokens": msg.tokens,
                        "created_at": msg.created_at.isoformat(),
                        "metadata": msg.message_metadata or {}
                    }
                    for msg in db_messages
                ]
                await redis_service.store_chat_session(
                    str(session_id),
                    messages_data,
                    expire_hours=24
                )
            
            return list(db_messages)
            
        except Exception as e:
            logger.error(f"Error getting messages with fallback for session {session_id}: {str(e)}")
            return []

    async def get_contextual_messages(
        self,
        session_id: UUID,
        recent_count: int = 20,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get messages optimized for AI context.
        Returns recent messages + optional summary of older messages.
        Uses token-based filtering when max_tokens is specified for better context management.
        """
        try:
            messages = await self.get_session_messages_with_fallback(session_id)
            
            if not messages:
                return {
                    "recent_messages": [],
                    "summary": None,
                    "total_messages": 0,
                    "tokens_used": 0
                }
            
            # Estimate tokens for messages without token count
            # Rough estimate: ~4 characters per token
            def estimate_tokens(text: str) -> int:
                return len(text) // 4
            
            current_tokens = 0
            
            # If token limit specified, use token-based filtering
            if max_tokens:
                recent = []
                
                # Start from most recent and work backwards
                for msg in reversed(messages):
                    # Use stored token count if available, otherwise estimate
                    msg_tokens = msg.tokens if msg.tokens else estimate_tokens(msg.content)
                    
                    if current_tokens + msg_tokens <= max_tokens:
                        recent.insert(0, msg)
                        current_tokens += msg_tokens
                    else:
                        # If adding this message would exceed limit, stop
                        break
                
                logger.info(f"Selected {len(recent)} messages using {current_tokens}/{max_tokens} tokens")
            else:
                # Use count-based filtering
                recent = messages[-recent_count:] if len(messages) > recent_count else messages
                # Calculate tokens for logging
                current_tokens = sum(
                    msg.tokens if msg.tokens else estimate_tokens(msg.content)
                    for msg in recent
                )
                logger.info(f"Selected {len(recent)} messages (count-based, total: {len(messages)}, tokens: {current_tokens})")
            
            # Get summary for older messages if needed
            summary = None
            if len(messages) > len(recent):
                redis_service = await self._get_redis_service()
                summary_key = f"chat:{session_id}:summary"
                summary = await redis_service.get_cache(summary_key)
                if summary:
                    logger.info(f"Using conversation summary for older messages")
            
            return {
                "recent_messages": recent,
                "summary": summary,
                "total_messages": len(messages),
                "truncated": len(messages) > len(recent),
                "tokens_used": current_tokens
            }
            
        except Exception as e:
            logger.error(f"Error getting contextual messages for session {session_id}: {str(e)}")
            return {
                "recent_messages": [],
                "summary": None,
                "total_messages": 0,
                "tokens_used": 0
            }

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Clean up old inactive sessions from Redis.
        Messages should already be persisted to database.
        """
        try:
            redis_service = await self._get_redis_service()
            
            # Get inactive sessions older than N days
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = await self.db.execute(
                select(ChatSession)
                .where(
                    (ChatSession.is_active == False) &
                    (ChatSession.updated_at < cutoff_date)
                )
            )
            old_sessions = result.scalars().all()
            
            cleaned = 0
            for session in old_sessions:
                # Ensure messages are persisted before cleanup
                await self.persist_session_to_db(session.id)
                
                # Remove from Redis
                await redis_service.delete_chat_session(str(session.id))
                cleaned += 1
            
            logger.info(f"Cleaned up {cleaned} old sessions from Redis")
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {str(e)}")
            return 0