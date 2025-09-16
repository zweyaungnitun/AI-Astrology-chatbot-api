# app/middleware/rate_limiter.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from app.services.redis_service import get_redis_service

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc"]:
            return await call_next(request)
        
        # Get client identifier (IP or user ID)
        client_ip = request.client.host
        user_id = request.headers.get("X-User-ID", client_ip)
        
        # Get Redis service
        redis_service = await get_redis_service()
        
        # Check rate limit
        rate_limit = await redis_service.check_rate_limit(
            identifier=f"api:{user_id}",
            max_requests=100,  # Adjust based on your needs
            time_window=3600   # 1 hour window
        )
        
        if not rate_limit["allowed"]:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {rate_limit['window']} seconds.",
                headers={
                    "X-RateLimit-Limit": str(rate_limit["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit["remaining"]),
                    "X-RateLimit-Reset": rate_limit["reset_time"]
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_limit["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit["remaining"])
        response.headers["X-RateLimit-Reset"] = rate_limit["reset_time"]
        
        return response