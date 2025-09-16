# app/services/redis_service.py
import redis.asyncio as redis
from redis.exceptions import RedisError
from typing import Optional, Dict, Any, List, Union
import json
import logging
from datetime import datetime, timedelta
from app.core.config import settings
import asyncio

logger = logging.getLogger(__name__)

class RedisService:
    """Redis service for caching, session storage, and real-time features."""
    
    def __init__(self):
        self.redis_pool = None
        self.connected = False
    
    async def initialize(self):
        """Initialize Redis connection pool."""
        try:
            self.redis_pool = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                health_check_interval=30,
            )
            
            # Test connection
            await self.redis_pool.ping()
            self.connected = True
            logger.info("✅ Redis connection established successfully")
            
        except RedisError as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            self.connected = False
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_pool:
            await self.redis_pool.close()
            self.connected = False
            logger.info("Redis connection closed")
    
    async def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.redis_pool or not self.connected:
            return False
        
        try:
            await self.redis_pool.ping()
            return True
        except RedisError:
            self.connected = False
            return False
    
    # Key generation helpers
    def _user_key(self, user_id: str, suffix: str = "") -> str:
        """Generate user-specific Redis key."""
        return f"user:{user_id}:{suffix}" if suffix else f"user:{user_id}"
    
    def _chat_key(self, session_id: str, suffix: str = "") -> str:
        """Generate chat session Redis key."""
        return f"chat:{session_id}:{suffix}" if suffix else f"chat:{session_id}"
    
    def _cache_key(self, key: str) -> str:
        """Generate cache key."""
        return f"cache:{key}"
    
    # Session Management
    async def store_chat_session(
        self, 
        session_id: str, 
        messages: List[Dict[str, Any]], 
        expire_hours: int = 24
    ) -> bool:
        """Store chat session messages in Redis."""
        try:
            key = self._chat_key(session_id, "messages")
            # Store messages as JSON with expiration
            await self.redis_pool.setex(
                key,
                timedelta(hours=expire_hours),
                json.dumps(messages)
            )
            return True
        except RedisError as e:
            logger.error(f"Error storing chat session {session_id}: {str(e)}")
            return False
    
    async def get_chat_session(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve chat session messages from Redis."""
        try:
            key = self._chat_key(session_id, "messages")
            data = await self.redis_pool.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving chat session {session_id}: {str(e)}")
            return None
    
    async def update_chat_session(
        self, 
        session_id: str, 
        message: Dict[str, Any],
        max_messages: int = 100
    ) -> bool:
        """Add a message to chat session in Redis."""
        try:
            key = self._chat_key(session_id, "messages")
            
            # Get existing messages or create new list
            existing_data = await self.redis_pool.get(key)
            messages = json.loads(existing_data) if existing_data else []
            
            # Add new message
            messages.append(message)
            
            # Keep only recent messages
            if len(messages) > max_messages:
                messages = messages[-max_messages:]
            
            # Update Redis with new TTL
            ttl = await self.redis_pool.ttl(key)
            if ttl <= 0:
                ttl = 86400  # 24 hours default
            
            await self.redis_pool.setex(key, ttl, json.dumps(messages))
            return True
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error updating chat session {session_id}: {str(e)}")
            return False
    
    async def delete_chat_session(self, session_id: str) -> bool:
        """Delete chat session from Redis."""
        try:
            key = self._chat_key(session_id, "messages")
            await self.redis_pool.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Error deleting chat session {session_id}: {str(e)}")
            return False
    
    # Caching
    async def set_cache(
        self, 
        key: str, 
        value: Any, 
        expire_seconds: int = 3600
    ) -> bool:
        """Set cached value with expiration."""
        try:
            redis_key = self._cache_key(key)
            await self.redis_pool.setex(
                redis_key,
                timedelta(seconds=expire_seconds),
                json.dumps(value)
            )
            return True
        except RedisError as e:
            logger.error(f"Error setting cache {key}: {str(e)}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cached value."""
        try:
            redis_key = self._cache_key(key)
            data = await self.redis_pool.get(redis_key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cache {key}: {str(e)}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """Delete cached value."""
        try:
            redis_key = self._cache_key(key)
            await self.redis_pool.delete(redis_key)
            return True
        except RedisError as e:
            logger.error(f"Error deleting cache {key}: {str(e)}")
            return False
    
    async def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache keys matching pattern."""
        try:
            cache_pattern = self._cache_key(pattern)
            keys = await self.redis_pool.keys(cache_pattern)
            if keys:
                await self.redis_pool.delete(*keys)
            return len(keys)
        except RedisError as e:
            logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")
            return 0
    
    # Rate Limiting
    async def check_rate_limit(
        self, 
        identifier: str, 
        max_requests: int, 
        time_window: int
    ) -> Dict[str, Any]:
        """Implement rate limiting using Redis."""
        try:
            key = f"rate_limit:{identifier}"
            now = datetime.now()
            
            # Use Redis sorted set for rate limiting
            pipeline = self.redis_pool.pipeline()
            pipeline.zremrangebyscore(key, 0, now.timestamp() - time_window)
            pipeline.zadd(key, {now.timestamp(): now.timestamp()})
            pipeline.zcard(key)
            pipeline.expire(key, time_window)
            
            results = await pipeline.execute()
            request_count = results[2]
            
            remaining = max(0, max_requests - request_count)
            reset_time = now + timedelta(seconds=time_window)
            
            return {
                "allowed": request_count <= max_requests,
                "remaining": remaining,
                "reset_time": reset_time.isoformat(),
                "limit": max_requests,
                "window": time_window
            }
            
        except RedisError as e:
            logger.error(f"Error checking rate limit for {identifier}: {str(e)}")
            # Fail open - allow request if Redis is down
            return {
                "allowed": True,
                "remaining": max_requests,
                "reset_time": datetime.now().isoformat(),
                "limit": max_requests,
                "window": time_window
            }
    
    # User Session Management
    async def store_user_session(
        self, 
        user_id: str, 
        session_data: Dict[str, Any],
        expire_hours: int = 24
    ) -> bool:
        """Store user session data."""
        try:
            key = self._user_key(user_id, "session")
            await self.redis_pool.setex(
                key,
                timedelta(hours=expire_hours),
                json.dumps(session_data)
            )
            return True
        except RedisError as e:
            logger.error(f"Error storing user session {user_id}: {str(e)}")
            return False
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        try:
            key = self._user_key(user_id, "session")
            data = await self.redis_pool.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting user session {user_id}: {str(e)}")
            return None
    
    async def delete_user_session(self, user_id: str) -> bool:
        """Delete user session data."""
        try:
            key = self._user_key(user_id, "session")
            await self.redis_pool.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Error deleting user session {user_id}: {str(e)}")
            return False
    
    # Real-time Features
    async def publish_message(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish message to Redis channel."""
        try:
            return await self.redis_pool.publish(
                channel, 
                json.dumps(message)
            )
        except RedisError as e:
            logger.error(f"Error publishing to channel {channel}: {str(e)}")
            return 0
    
    async def subscribe_to_channel(self, channel: str):
        """Subscribe to Redis channel and yield messages."""
        try:
            pubsub = self.redis_pool.pubsub()
            await pubsub.subscribe(channel)
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        yield json.loads(message['data'])
                    except json.JSONDecodeError:
                        yield message['data']
                        
        except RedisError as e:
            logger.error(f"Error subscribing to channel {channel}: {str(e)}")
            yield {"error": "Subscription failed"}
    
    # Statistics and Monitoring
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment counter in Redis."""
        try:
            return await self.redis_pool.incrby(f"counter:{key}", amount)
        except RedisError as e:
            logger.error(f"Error incrementing counter {key}: {str(e)}")
            return 0
    
    async def get_counter(self, key: str) -> int:
        """Get counter value."""
        try:
            value = await self.redis_pool.get(f"counter:{key}")
            return int(value) if value else 0
        except (RedisError, ValueError) as e:
            logger.error(f"Error getting counter {key}: {str(e)}")
            return 0
    
    async def store_analytics(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Store analytics event."""
        try:
            timestamp = datetime.now().isoformat()
            event_key = f"analytics:{event_type}:{timestamp}"
            await self.redis_pool.setex(
                event_key,
                timedelta(days=7),  # Keep analytics for 7 days
                json.dumps(data)
            )
            return True
        except RedisError as e:
            logger.error(f"Error storing analytics event {event_type}: {str(e)}")
            return False
    
    # Health check
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health status."""
        try:
            start_time = datetime.now()
            await self.redis_pool.ping()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected": True,
                "timestamp": datetime.now().isoformat()
            }
        except RedisError as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
                "timestamp": datetime.now().isoformat()
            }

# Global Redis service instance
redis_service = RedisService()

# Async initialization function
async def initialize_redis():
    """Initialize Redis service on application startup."""
    await redis_service.initialize()
    return redis_service

# Dependency for FastAPI
async def get_redis_service() -> RedisService:
    """Get Redis service dependency."""
    if not await redis_service.is_connected():
        await redis_service.initialize()
    return redis_service