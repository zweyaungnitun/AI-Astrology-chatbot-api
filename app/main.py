# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import logging
import time
from typing import Optional
from app.core.config import settings
from app.database.session import create_db_and_tables, engine
from app.routers import users,admin,charts,chat

logging.basicConfig(
    level=logging.INFO if settings.IS_PRODUCTION else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI.
    Runs on startup and shutdown.
    """
    # Startup code
    startup_message = f"""
    🚀 Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}
    📊 Environment: {settings.ENVIRONMENT}
    🔗 Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'Local'}
    🌐 CORS Origins: {settings.BACKEND_CORS_ORIGINS}
    """
    logger.info(startup_message)
    
    # Create database tables
    try:
        await create_db_and_tables()
        logger.info("✅ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise
    
    # Initialize other services here if needed
    # e.g., Redis connection, Firebase admin, etc.
    
    yield  # Application runs here
    
    # Shutdown code
    logger.info("🛑 Shutting down application...")
    
    # Clean up resources
    try:
        await engine.dispose()
        logger.info("✅ Database engine disposed successfully")
    except Exception as e:
        logger.error(f"❌ Error disposing database engine: {str(e)}")

# Initialize FastAPI with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="AI Astrology Chatbot API - Get personalized astrological insights based on your birth chart",
    docs_url="/docs" if settings.IS_DEVELOPMENT else None,
    redoc_url="/redoc" if settings.IS_DEVELOPMENT else None,
    openapi_url="/openapi.json" if settings.IS_DEVELOPMENT else None,
    lifespan=lifespan,
)

# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all requests."""
    start_time = time.time()
    
    # Skip logging for health checks and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        response = await call_next(request)
        return response
    
    logger.info(f"📥 Incoming request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"📤 Response: {request.method} {request.url.path} "
            f"-> {response.status_code} in {process_time:.3f}s"
        )
        
        # Add process time to headers
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"💥 Error: {request.method} {request.url.path} "
            f"-> Exception: {str(e)} in {process_time:.3f}s"
        )
        raise

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with detailed messages."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request data",
            "errors": jsonable_encoder(exc.errors()),
        },
    )

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: Exception):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Endpoint not found"},
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle 500 errors gracefully."""
    logger.error(f"Internal server error: {str(exc)}")
    
    error_detail = "Internal server error" if settings.IS_PRODUCTION else str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail},
    )

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic information."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.IS_DEVELOPMENT else None,
        "health": "/health",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint for monitoring."""
    from sqlmodel import text
    from app.services.redis_service import redis_pool
    
    health_status = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "timestamp": time.time(),
        "components": {}
    }
    
    # Check database connection
    try:
        async with engine.begin() as conn:
            await conn.exec(text("SELECT 1"))
        health_status["components"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health_status["components"]["database"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "degraded"
    

    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        try:
            await redis_pool.ping()
            health_status["components"]["redis"] = {"status": "healthy", "message": "Connected"}
        except Exception as e:
            health_status["components"]["redis"] = {"status": "unhealthy", "message": str(e)}
            health_status["status"] = "degraded"
    if hasattr(settings, 'FIREBASE_PROJECT_ID') and settings.FIREBASE_PROJECT_ID:
        try:
            from app.services.firebase_admin import firebase_app
            health_status["components"]["firebase"] = {"status": "healthy", "message": "Initialized"}
        except Exception as e:
            health_status["components"]["firebase"] = {"status": "unhealthy", "message": str(e)}
            health_status["status"] = "degraded"
    
    return health_status

@app.get("/info", tags=["Info"])
async def system_info():
    """Get system information and configuration (without sensitive data)."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "cors_origins": settings.BACKEND_CORS_ORIGINS,
        "api_version": settings.API_V1_STR,
    }

app.include_router(users.router, prefix=settings.API_V1_STR, tags=["Users"])
app.include_router(charts.router, prefix=settings.API_V1_STR, tags=["Charts"])
app.include_router(admin.router, prefix=settings.API_V1_STR, tags=["Admin"])
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["Chat"])

if settings.IS_DEVELOPMENT:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Display safe configuration values (development only)."""
        return {
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "project_name": settings.PROJECT_NAME,
            "project_version": settings.PROJECT_VERSION,
            "database": f"PostgreSQL ({'async' if '+asyncpg' in settings.DATABASE_URL else 'sync'})",
            "redis_configured": bool(settings.REDIS_URL),
            "firebase_configured": bool(settings.FIREBASE_PROJECT_ID),
            "openrouter_configured": bool(settings.OPENROUTER_API_KEY),
            "cors_origins": settings.BACKEND_CORS_ORIGINS,
        }
    
    @app.get("/debug/routes", tags=["Debug"])
    async def debug_routes():
        """List all available API routes (development only)."""
        routes = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                routes.append({
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": route.name if hasattr(route, "name") else None,
                })
        return {"routes": routes}
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def catch_all(path: str):
    """Catch-all for undefined routes."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": f"Endpoint '{path}' not found"},
    )
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_db_and_tables()
    
    yield
    
    # Shutdown
    await redis_service.close()

if __name__ == "__main__":
    import uvicorn

    reload = settings.IS_DEVELOPMENT
    
    log_level = "debug" if settings.IS_DEVELOPMENT else "info"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        log_level=log_level,
        timeout_keep_alive=30 if settings.IS_PRODUCTION else 5,
        workers=4 if settings.IS_PRODUCTION else 1,
    )