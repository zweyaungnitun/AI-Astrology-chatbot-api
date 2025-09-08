# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

from app.database.session import create_db_and_tables, get_db_session

from app.routers import auth, users, chat, charts, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI.
    This code runs once on startup and once on shutdown.
    """
    # --- Startup Code ---
    print("Starting up...")
    print(f"Environment: {settings.ENVIRONMENT}")
    
    # Create database tables (if they don't exist)
    await create_db_and_tables()
    print("Database tables verified/created.")
    
    # You could add a connection test for Redis here if needed
    # await test_redis_connection()
    
    yield  # The application runs here
    
    # --- Shutdown Code ---
    print("Shutting down...")
    # Clean up resources if necessary (e.g., close Redis pool)
    # await close_redis_connection()

# Initialize the FastAPI application with lifespan events
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="A conversational AI chatbot that provides astrological insights based on user birth charts.",
    lifespan=lifespan,

)

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# --- Exception Handlers ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    Custom handler for Pydantic validation errors.
    Provides cleaner error messages for invalid requests.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request data.",
            "errors": exc.errors(),
        },
    )

# --- Include Routers (API Endpoints) ---

# Health check endpoint
@app.get("/", tags=["Root"])
async def root():
    """Basic health check endpoint."""
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint for monitoring."""
    from app.services.redis_service import redis_pool
    from sqlmodel import text, Session
    
    # Check database connection
    db_healthy = False
    try:
        async with Session() as session:
            await session.exec(text("SELECT 1"))
            db_healthy = True
    except Exception as e:
        print(f"Database health check failed: {e}")
    
    # Check Redis connection
    redis_healthy = False
    try:
        await redis_pool.ping()
        redis_healthy = True
    except Exception as e:
        print(f"Redis health check failed: {e}")
    
    return {
        "status": "healthy" if db_healthy and redis_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "redis": "connected" if redis_healthy else "disconnected",
        "timestamp": "2024-09-01T00:00:00Z", # You can use datetime.utcnow().isoformat()
    }

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])


# --- Development Debug Routes ---

if settings.IS_DEVELOPMENT:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Display current configuration (ONLY in development)."""
        return {
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "database_url": str(settings.DATABASE_URL).split('@')[0] + '@***',  # Mask password
            "redis_url": settings.REDIS_URL.split('@')[0] + '@***' if '@' in settings.REDIS_URL else settings.REDIS_URL,
            "firebase_project_id": settings.FIREBASE_PROJECT_ID,
            "openrouter_model": settings.OPENROUTER_MODEL,
        }

# This allows running the app directly with: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.IS_DEVELOPMENT,  # Auto-reload in development
        log_level="debug" if settings.IS_DEVELOPMENT else "info",
    )