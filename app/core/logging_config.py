"""
Enhanced logging configuration for error tracking and monitoring.

Features:
- Structured logging with JSON format for production
- Request ID correlation for tracking requests across services
- Detailed error context with stack traces
- Performance metrics
- Integration with external logging services
"""
import logging
import sys
import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar
from uuid import uuid4
import inspect

from app.core.config import settings

# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info else None,
            }
        
        # Add extra fields from record
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_data.update(record.extra_fields)
        
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
                "extra_fields"
            ]:
                if not key.startswith("_"):
                    log_data[key] = value
        
        return json.dumps(log_data, default=str)


class EnhancedFormatter(logging.Formatter):
    """Enhanced formatter with colors and detailed information for development."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and enhanced details."""
        # Get color for log level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Get request ID
        request_id = request_id_var.get()
        request_id_str = f"[{request_id[:8]}]" if request_id else "[--------]"
        
        # Base log line
        log_parts = [
            f"{color}{timestamp}{reset}",
            f"{color}{record.levelname:8}{reset}",
            request_id_str,
            f"{record.name}:{record.lineno}",
            f"{record.funcName}()",
            f"- {record.getMessage()}"
        ]
        
        log_line = " | ".join(log_parts)
        
        # Add exception info if present
        if record.exc_info:
            exc_lines = traceback.format_exception(*record.exc_info)
            log_line += f"\n{''.join(exc_lines)}"
        
        # Add stack trace if available
        if record.stack_info:
            log_line += f"\n{record.stack_info}"
        
        return log_line


def setup_logging():
    """
    Configure logging for the application.
    
    Uses JSON format in production for structured logging,
    and enhanced format in development for readability.
    """
    # Determine log level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Choose formatter based on environment
    if settings.IS_PRODUCTION:
        formatter = JSONFormatter()
    else:
        formatter = EnhancedFormatter()
    
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    root_logger.setLevel(log_level)
    
    # Set levels for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_level": logging.getLevelName(log_level),
            "format": "JSON" if settings.IS_PRODUCTION else "Enhanced"
        }
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (defaults to calling module)
        
    Returns:
        Configured logger instance
    """
    if name is None:
        # Get the name of the calling module
        frame = inspect.currentframe().f_back
        if frame:
            name = frame.f_globals.get('__name__', 'app')
    
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID for correlation tracking.
    
    Args:
        request_id: Optional request ID (generates new one if not provided)
        
    Returns:
        The request ID (newly generated or provided)
    """
    if request_id is None:
        request_id = str(uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return request_id_var.get()


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: int = logging.ERROR
):
    """
    Log an error with full context and stack trace.
    
    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context dictionary
        level: Log level (default: ERROR)
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_module": error.__class__.__module__,
    }
    
    # Add stack trace
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_traceback:
        error_context["traceback"] = traceback.format_tb(exc_traceback)
        error_context["stack"] = traceback.format_stack()
    
    # Add custom context
    if context:
        error_context.update(context)
    
    # Add request ID
    request_id = get_request_id()
    if request_id:
        error_context["request_id"] = request_id
    
    # Log with extra fields
    logger.log(
        level,
        f"Error: {type(error).__name__}: {str(error)}",
        exc_info=(exc_type, exc_value, exc_traceback),
        extra={"extra_fields": error_context}
    )


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    context: Optional[Dict[str, Any]] = None
):
    """
    Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Duration in seconds
        context: Additional context
    """
    perf_data = {
        "operation": operation,
        "duration_seconds": round(duration, 4),
        "duration_ms": round(duration * 1000, 2),
    }
    
    if context:
        perf_data.update(context)
    
    request_id = get_request_id()
    if request_id:
        perf_data["request_id"] = request_id
    
    # Log as INFO with performance tag
    logger.info(
        f"Performance: {operation} took {duration:.4f}s",
        extra={"extra_fields": perf_data}
    )


class RequestLogger:
    """Context manager for logging request/response cycles."""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        request_id = get_request_id()
        
        log_msg = f"Starting: {self.operation}"
        if request_id:
            log_msg += f" [Request ID: {request_id[:8]}]"
        
        self.logger.debug(log_msg, extra={"extra_fields": self.context})
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type is None:
            log_msg = f"Completed: {self.operation} in {duration:.4f}s"
            self.logger.info(log_msg, extra={"extra_fields": {**self.context, "duration": duration}})
        else:
            log_error(
                self.logger,
                exc_value,
                context={**self.context, "operation": self.operation, "duration": duration}
            )
