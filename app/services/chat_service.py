from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging
import time as time_module
from datetime import datetime, timedelta
# ===========================

from app.schemas.chat import (
    ChatSessionCreate, ChatMessageCreate,
    MessageRole, ChatSessionResponse, ChatMessageResponse
)
from app.models.chat import ChatSession, ChatMessage
from app.services.ai_service import ai_service
from app.services.redis_service import get_redis_service
logger = logging.getLogger(__name__)

class ChatService:
    """
    Chat service that stores all sessions and messages in Redis only.
    No database persistence - all data is ephemeral based on Redis TTL.
    """
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
        """Create a new chat session for a user (stored only in Redis)."""
        try:
            redis_service = await self._get_redis_service()
            session_id = uuid4()
            
            session_metadata = {
                "id": str(session_id),
                "user_id": str(user_id),
                "title": session_data.title,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "message_count": 0,
                "chart_id": str(session_data.chart_id) if session_data.chart_id else None
            }
            
            success = await redis_service.store_chat_session_metadata(
                str(session_id),
                session_metadata,
                expire_hours=24
            )
            
            if not success:
                logger.error(f"Failed to store session metadata in Redis for session {session_id}")
                return None
            
            user_sessions_key = f"user:{user_id}:chat_sessions"
            await redis_service.redis_pool.sadd(user_sessions_key, str(session_id))
            await redis_service.redis_pool.expire(user_sessions_key, timedelta(hours=24))
            
            await redis_service.store_chat_session(str(session_id), [], expire_hours=24)
            
            chat_session = ChatSession(
                id=session_id,
                user_id=user_id,
                title=session_data.title,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                message_count=0
            )
            
            logger.info(f"Created chat session {session_id} for user {user_id} (Redis only)")
            return chat_session
            
        except Exception as e:
            logger.error(f"Error creating chat session: {str(e)}")
            return None

    async def get_chat_session(self, session_id: UUID, user_id: Optional[UUID] = None) -> Optional[ChatSession]:
        """Get a chat session by ID from Redis, ensuring it belongs to the user."""
        try:
            redis_service = await self._get_redis_service()
    
            metadata = await redis_service.get_chat_session_metadata(str(session_id))
            
            if not metadata:
                return None
            
            if user_id and str(metadata.get("user_id")) != str(user_id):
                return None
            
            return ChatSession(
                id=UUID(metadata["id"]),
                user_id=UUID(metadata["user_id"]),
                title=metadata.get("title", "New Chat"),
                is_active=metadata.get("is_active", True),
                created_at=datetime.fromisoformat(metadata.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(metadata.get("updated_at", datetime.utcnow().isoformat())),
                message_count=metadata.get("message_count", 0)
            )
        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {str(e)}")
            return None

    async def get_user_chat_sessions(self, user_id: UUID, active_only: bool = True) -> List[ChatSession]:
        """Get all chat sessions for a user from Redis."""
        try:
            redis_service = await self._get_redis_service()
            
            sessions_data = await redis_service.get_user_chat_sessions(str(user_id), active_only)
            
            sessions = []
            for session_data in sessions_data:
                try:
                    sessions.append(ChatSession(
                        id=UUID(session_data["id"]),
                        user_id=UUID(session_data["user_id"]),
                        title=session_data.get("title", "New Chat"),
                        is_active=session_data.get("is_active", True),
                        created_at=datetime.fromisoformat(session_data.get("created_at", datetime.utcnow().isoformat())),
                        updated_at=datetime.fromisoformat(session_data.get("updated_at", datetime.utcnow().isoformat())),
                        message_count=session_data.get("message_count", 0)
                    ))
                except Exception as e:
                    logger.warning(f"Error converting session data: {str(e)}")
                    continue
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting chat sessions for user {user_id}: {str(e)}")
            return []

    async def add_message_to_session(self, session_id: UUID, message_data: ChatMessageCreate, metadata: Optional[Dict] = None) -> Optional[ChatMessage]:
        """Add a message to a chat session (stored in Redis)."""
        try:
            redis_service = await self._get_redis_service()
            message_dict = self._message_to_dict(message_data, metadata)
            
            success = await redis_service.update_chat_session(str(session_id), message_dict)
            if not success: return None
            
            session_meta = await redis_service.get_chat_session_metadata(str(session_id)) or {}
            session_meta["message_count"] = session_meta.get("message_count", 0) + 1
            session_meta["updated_at"] = datetime.utcnow().isoformat()
            await redis_service.store_chat_session_metadata(str(session_id), session_meta)
            
            return self._dict_to_message(message_dict, session_id)
        except Exception as e:
            logger.error(f"Redis error in add_message_to_session: {str(e)}")
           
            return None

    async def get_session_messages(self, session_id: UUID, limit: int = 100) -> List[ChatMessage]:
        """Get messages for a chat session from Redis."""
        try:
            redis_service = await self._get_redis_service()
            
            messages_data = await redis_service.get_chat_session(str(session_id))
            
            if not messages_data:
                return []
            
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
        """Update chat session title in Redis."""
        try:
            session = await self.get_chat_session(session_id, user_id)
            if not session:
                return None

            redis_service = await self._get_redis_service()
            await redis_service.update_chat_session_metadata(
                str(session_id),
                {
                    "title": title,
                    "updated_at": datetime.utcnow().isoformat()
                },
                expire_hours=24
            )
            
            session.title = title
            session.updated_at = datetime.utcnow()
            
            return session
            
        except Exception as e:
            logger.error(f"Error updating chat session {session_id}: {str(e)}")
            return None

    async def update_chat_session_chart(
        self,
        session_id: UUID,
        chart_id: Optional[UUID],
        user_id: Optional[UUID] = None
    ) -> Optional[ChatSession]:
        """Update chat session chart_id in Redis."""
        try:
            session = await self.get_chat_session(session_id, user_id)
            if not session:
                return None

            redis_service = await self._get_redis_service()
            metadata = await redis_service.get_chat_session_metadata(str(session_id)) or {}
            metadata["chart_id"] = str(chart_id) if chart_id else None
            metadata["updated_at"] = datetime.utcnow().isoformat()
            await redis_service.store_chat_session_metadata(str(session_id), metadata, expire_hours=24)
            
            session.updated_at = datetime.utcnow()
            
            return session
            
        except Exception as e:
            logger.error(f"Error updating chat session chart {session_id}: {str(e)}")
            return None

    async def get_session_chart_id(self, session_id: UUID) -> Optional[UUID]:
        """Get the chart_id associated with a chat session."""
        try:
            redis_service = await self._get_redis_service()
            metadata = await redis_service.get_chat_session_metadata(str(session_id))
            if metadata and metadata.get("chart_id"):
                return UUID(metadata["chart_id"])
            return None
        except Exception as e:
            logger.error(f"Error getting chart_id for session {session_id}: {str(e)}")
            return None

    async def deactivate_chat_session(self, session_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """Deactivate a chat session in Redis."""
        try:
            session = await self.get_chat_session(session_id, user_id)
            if not session:
                return False

            # Update metadata in Redis
            redis_service = await self._get_redis_service()
            await redis_service.update_chat_session_metadata(
                str(session_id),
                {
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat()
                },
                expire_hours=24
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating chat session {session_id}: {str(e)}")
            return False

    async def delete_chat_session(self, session_id: UUID) -> bool:
        """Delete a chat session and all its messages from Redis."""
        try:
            redis_service = await self._get_redis_service()
            
            # Get session to find user_id for cleanup
            session = await self.get_chat_session(session_id)
            if session:
                # Remove from user's session list
                user_sessions_key = f"user:{session.user_id}:chat_sessions"
                await redis_service.redis_pool.srem(user_sessions_key, str(session_id))
            
            # Delete session and messages from Redis
            await redis_service.delete_chat_session(str(session_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chat session {session_id}: {str(e)}")
            return False

    async def delete_all_user_sessions(self, user_id: UUID) -> int:
        """
        Delete all chat sessions for a user (used on logout).
        Returns the number of sessions deleted.
        """
        try:
            redis_service = await self._get_redis_service()
           
            user_sessions_key = f"user:{user_id}:chat_sessions"
            session_ids = await redis_service.redis_pool.smembers(user_sessions_key)
            
            deleted_count = 0
            
            for session_id in session_ids:
                try:
                    await redis_service.delete_chat_session(session_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Error deleting session {session_id} for user {user_id}: {str(e)}")
                    continue
            
            await redis_service.redis_pool.delete(user_sessions_key)
            
            logger.info(f"Deleted {deleted_count} chat sessions for user {user_id} on logout")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting all sessions for user {user_id}: {str(e)}")
            return 0

    async def process_chat_message(
        self, 
        user_id: UUID, 
        message: str, 
        session_id: Optional[UUID] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        evaluate: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Process chat message with LangChain integration."""
        start_time = time_module.time()
        
        try:
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

            from app.services.user_service import UserService
            user_service = UserService(self.db)
            birth_data = await user_service.get_birth_data(user_id)

            chart_data = None
            chart_id = await self.get_session_chart_id(chat_session.id)
            
            from app.services.chart_service import ChartService
            chart_service = ChartService(self.db)
            
            chart = None
            if chart_id:
                logger.info(f"Found chart_id {chart_id} for session {chat_session.id}, retrieving chart data...")
                chart = await chart_service.get_chart_by_id(chart_id)
                if chart and chart.user_id != user_id:
                    logger.warning(f"Chart {chart_id} does not belong to user {user_id} (chart belongs to {chart.user_id})")
                    chart = None
                elif not chart:
                    logger.warning(f"Chart {chart_id} not found in database for session {chat_session.id}")
            else:
                logger.debug(f"No chart_id associated with session {chat_session.id}, checking for user's chart...")
                user_chart = await chart_service.get_user_chart(user_id)
                if user_chart:
                    chart = user_chart
                    logger.info(f"Using user's chart {chart.id} ({chart.chart_name}) for session {chat_session.id}")
                else:
                    logger.debug(f"No chart found for user {user_id}")
        
            if chart:
                chart_data = {
                    "id": str(chart.id),
                    "chart_type": chart.chart_type.value if hasattr(chart.chart_type, 'value') else str(chart.chart_type),
                    "chart_name": chart.chart_name,
                    "is_primary": chart.is_primary,
                    "birth_date": chart.birth_date.isoformat() if chart.birth_date else None,
                    "birth_time": chart.birth_time.isoformat() if chart.birth_time else None,
                    "birth_location": chart.birth_location,
                    "birth_timezone": chart.birth_timezone,
                    "house_system": chart.house_system.value if hasattr(chart.house_system, 'value') else str(chart.house_system),
                    "zodiac_system": chart.zodiac_system.value if hasattr(chart.zodiac_system, 'value') else str(chart.zodiac_system),
                    "ayanamsa": chart.ayanamsa,
                    "planetary_positions": chart.planetary_positions,
                    "house_positions": chart.house_positions,
                    "aspects": chart.aspects,
                    "summary": chart.summary,
                    "created_at": chart.created_at.isoformat() if chart.created_at else None,
                    "calculation_time": chart.calculation_time
                }
                planet_count = len(chart.planetary_positions) if isinstance(chart.planetary_positions, (list, dict)) else 0
                aspect_count = len(chart.aspects) if isinstance(chart.aspects, list) else 0
                logger.info(f"Retrieved complete chart data for session {chat_session.id}: chart {chart.id} ({chart.chart_name}) - includes {planet_count} planetary positions, {aspect_count} aspects")

            contextual_data = await self.get_contextual_messages(
                chat_session.id,
                recent_count=50,
                max_tokens=3000
            )
            chat_history = contextual_data.get("recent_messages", [])
            
            user_message = await self.add_message_to_session(
                chat_session.id,
                ChatMessageCreate(content=message, role=MessageRole.USER)
            )
            if not user_message:
                return None
            
            logger.info(f"Getting AI response with {len(chat_history)} messages from chat history and chart_data={'present' if chart_data else 'none'}")
            ai_response = await ai_service.get_ai_response(
                user_message=message,
                chat_history=chat_history,
                birth_data=birth_data,
                chart_data=chart_data,
                temperature=temperature,
                max_tokens=max_tokens,
                evaluate=evaluate
            )
            if not ai_response or not ai_response.get("content") or not str(ai_response.get("content")).strip():
                logger.warning(f"AI returned empty response for user message. Injecting fallback.")
                ai_response = {
                    "content": "I apologize, but the connection to the stars seems a bit faint right now. Could you please repeat your question? I'm ready to help.",
                    "role": MessageRole.ASSISTANT,
                    "tokens": 0,
                    "processing_time": 0,
                    "model": "fallback_handler"
                }

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


    async def get_session_messages_with_fallback(
        self,
        session_id: UUID,
        limit: int = 100
    ) -> List[ChatMessage]:
        """Get messages from Redis only."""
        try:
            messages = await self.get_session_messages(session_id, limit)
            return messages
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}")
            return []

    async def get_contextual_messages(
        self,
        session_id: UUID,
        recent_count: int = 20,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get messages optimized for AI context."""
        try:
            messages = await self.get_session_messages_with_fallback(session_id)
            
            if not messages:
                return {
                    "recent_messages": [],
                    "summary": None,
                    "total_messages": 0,
                    "tokens_used": 0
                }
            
            def estimate_tokens(text: str) -> int:
                return len(text) // 4
            
            current_tokens = 0
            
            if max_tokens:
                recent = []
                for msg in reversed(messages):
                    msg_tokens = msg.tokens if msg.tokens else estimate_tokens(msg.content)
                    if current_tokens + msg_tokens <= max_tokens:
                        recent.insert(0, msg)
                        current_tokens += msg_tokens
                    else:
                        break
                logger.info(f"Selected {len(recent)} messages using {current_tokens}/{max_tokens} tokens")
            else:
                recent = messages[-recent_count:] if len(messages) > recent_count else messages
                current_tokens = sum(
                    msg.tokens if msg.tokens else estimate_tokens(msg.content)
                    for msg in recent
                )
                logger.info(f"Selected {len(recent)} messages (count-based, total: {len(messages)}, tokens: {current_tokens})")
            
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
        """Clean up old inactive sessions from Redis."""
        try:
            redis_service = await self._get_redis_service()
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            cleaned = 0
            pattern = "chat:*:metadata"
            cursor = 0
            while True:
                cursor, keys = await redis_service.redis_pool.scan(cursor, match=pattern, count=100)
                
                for key in keys:
                    try:
                        metadata = await redis_service.get_chat_session_metadata(key.split(":")[1])
                        if metadata:
                            is_active = metadata.get("is_active", True)
                            updated_at_str = metadata.get("updated_at")
                            
                            if not is_active and updated_at_str:
                                updated_at = datetime.fromisoformat(updated_at_str)
                                if updated_at < cutoff_date:
                                    session_id = metadata.get("id")
                                    if session_id:
                                        await redis_service.delete_chat_session(session_id)
                                        cleaned += 1
                    except Exception as e:
                        logger.warning(f"Error processing session key {key}: {str(e)}")
                        continue
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleaned up {cleaned} old sessions from Redis")
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {str(e)}")
            return 0