# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
import logging
import time
from typing import Optional
from fastapi import Header
from app.core.config import settings
from app.core.logging_config import (
    setup_logging,
    get_logger,
    set_request_id,
    get_request_id,
    log_error,
    log_performance,
    RequestLogger
)
from app.database.session import create_db_and_tables, engine
from app.routers import users,admin,charts,chat
from app.dependencies.auth import get_current_user

# Setup enhanced logging
setup_logging()
logger = get_logger(__name__)

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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="AI Astrology Chatbot API - Get personalized astrological insights based on your birth chart",
        routes=app.routes,
    )
    
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Firebase ID Token Authentication\n\n"
                "To get your Firebase ID token:\n"
                "1. Sign in to your Firebase app using email/password\n"
                "2. Get the ID token from the Firebase Auth SDK (user.getIdToken())\n"
                "3. Paste the token here (without 'Bearer' prefix)\n\n"
                "Note: Tokens expire after 1 hour. Get a new token when needed.\n"
                "See SWAGGER_TESTING.md for detailed instructions."
            )
        }
    }
    
    public_paths = [
        "/",
        "/health",
        "/info",
        f"{settings.API_V1_STR}/users/register",
        "/openapi.json",
        "/docs",
        "/redoc"
    ]
    
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "delete", "patch", "options"]:
                if path in public_paths:
                    continue
                
                if "security" not in operation:
                    operation["security"] = [{"Bearer": []}]
                elif not any("Bearer" in sec for sec in operation.get("security", [])):
                    operation["security"].append({"Bearer": []})
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Enhanced middleware to log all requests with request ID tracking."""
    start_time = time.time()
    
    request_id_header = request.headers.get("X-Request-ID")
    request_id = set_request_id(request_id_header)
    skip_detailed_logging = request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]
    
    request_context = {
        "method": request.method,
        "path": request.url.path,
        "query_params": str(request.query_params) if request.query_params else None,
        "client_host": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
    }
    
    if not skip_detailed_logging:
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "extra_fields": {
                    **request_context,
                    "request_id": request_id,
                }
            }
        )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        response.headers["X-Request-ID"] = request_id
        
        if not skip_detailed_logging:
            log_performance(
                logger,
                f"{request.method} {request.url.path}",
                process_time,
                context={
                    **request_context,
                    "status_code": response.status_code,
                }
            )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        log_error(
            logger,
            e,
            context={
                **request_context,
                "request_id": request_id,
                "duration_seconds": round(process_time, 4),
            }
        )
        
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with detailed messages."""
    request_id = get_request_id()
    
    logger.warning(
        f"Validation error: {len(exc.errors())} error(s) in request",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
                "body": str(request.body()) if hasattr(request, 'body') else None,
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request data",
            "errors": jsonable_encoder(exc.errors()),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: Exception):
    """Handle 404 errors."""
    request_id = get_request_id()
    
    logger.warning(
        f"404 Not Found: {request.method} {request.url.path}",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": "Endpoint not found",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle 500 errors gracefully with detailed logging."""
    request_id = get_request_id()
    log_error(
        logger,
        exc,
        context={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "query_params": str(request.query_params) if request.query_params else None,
        }
    )
    
    error_detail = "Internal server error" if settings.IS_PRODUCTION else str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": error_detail,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    request_id = get_request_id()
    log_error(
        logger,
        exc,
        context={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "exception_type": type(exc).__name__,
            "unhandled": True,
        }
    )
    
    error_detail = "An unexpected error occurred" if settings.IS_PRODUCTION else str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": error_detail,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else None,
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
        "public_endpoints": {
            "register": f"{settings.API_V1_STR}/users/register",
            "health": "/health",
            "info": "/info"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint for monitoring."""
    from sqlmodel import text
    from app.services.redis_service import redis_service
    
    health_status = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "timestamp": time.time(),
        "components": {}
    }

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["components"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health_status["components"]["database"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "degraded"
    
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        try:
            await redis_service.redis_pool.ping()
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
    
    @app.get("/debug/verify-token", tags=["Debug"])
    async def verify_token_debug(
        current_user: dict = Depends(get_current_user)
    ):
        """
        Verify if your Firebase token is working correctly (development only).
        
        This endpoint helps you test if your token is valid and properly configured
        in Swagger UI. If you can successfully call this endpoint, your token is working.
        
        Returns decoded token information (safe fields only).
        """
        return {
            "status": "success",
            "message": "Token is valid! You can now use it for other endpoints.",
            "user_info": {
                "uid": current_user.get("uid"),
                "email": current_user.get("email"),
                "email_verified": current_user.get("email_verified", False),
                "auth_time": current_user.get("auth_time"),
            },
            "token_info": {
                "iss": current_user.get("iss"),
                "aud": current_user.get("aud"),
                "exp": current_user.get("exp"),
                "iat": current_user.get("iat"),
            },
            "instructions": {
                "swagger_ui": "If you see this, your token is working in Swagger UI!",
                "next_steps": "You can now test other protected endpoints.",
                "token_expiry": "Remember: Firebase tokens expire after 1 hour.",
            }
        }
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def catch_all(path: str):
    """Catch-all for undefined routes."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": f"Endpoint '{path}' not found"},
    )

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