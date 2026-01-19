# app/dependencies/auth.py
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from functools import wraps
import logging
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

# Import your Firebase app instance
from app.services.firebase_admin import firebase_app
from app.core.logging_config import get_logger, get_request_id, log_error

logger = get_logger(__name__)

# HTTP Bearer scheme for extracting tokens from Authorization header
# auto_error=False allows us to handle errors manually for better control
security = HTTPBearer(
    auto_error=False,
    scheme_name="Bearer",
    description="Firebase ID Token - Enter your token (without 'Bearer' prefix)"
)

async def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    """
    Verify a Firebase ID token and return the decoded token payload.
    
    Args:
        id_token (str): The Firebase ID token to verify
        
    Returns:
        Dict[str, Any]: Decoded token payload containing user information
        
    Raises:
        ValueError: If token verification fails for any reason
    """
    try:
        # Verify the ID token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(
            id_token, 
            app=firebase_app,
            check_revoked=True  # Check if token has been revoked
        )
        logger.debug(f"Successfully verified token for user: {decoded_token.get('uid')}")
        return decoded_token
        
    except auth.ExpiredIdTokenError:
        logger.warning("Firebase token has expired")
        raise ValueError("Token has expired. Please refresh your authentication.")
        
    except auth.RevokedIdTokenError:
        logger.warning("Firebase token has been revoked")
        raise ValueError("Token has been revoked. Please sign in again.")
        
    except auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase token provided")
        raise ValueError("Invalid authentication token.")
        
    except auth.CertificateFetchError:
        logger.error("Failed to fetch Firebase certificate for token verification")
        raise ValueError("Authentication service temporarily unavailable.")
        
    except FirebaseError as e:
        logger.error(f"Firebase authentication error: {str(e)}")
        raise ValueError(f"Authentication error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        raise ValueError("Unexpected authentication error.")

async def get_token_from_header(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Extract token from Authorization header using multiple methods for compatibility.
    
    Args:
        authorization: Raw Authorization header value
        credentials: Parsed HTTPBearer credentials
        
    Returns:
        Optional[str]: Extracted token or None if not found
    """
    # First try the HTTPBearer dependency
    if credentials and credentials.scheme.lower() == "bearer":
        logger.debug(f"Token extracted via HTTPBearer: {credentials.credentials[:20]}..." if credentials.credentials else "None")
        return credentials.credentials
    
    # Fallback: manually parse Authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
        logger.debug(f"Token extracted via manual parsing: {token[:20]}..." if token else "None")
        return token
    
    logger.debug("No token found in Authorization header")
    return None

async def get_current_user(
    token: Optional[str] = Depends(get_token_from_header)
) -> Dict[str, Any]:
    """
    FastAPI Dependency that validates Firebase ID tokens and returns user data.
    
    This is the main dependency to use for protecting routes that require authentication.
    
    Args:
        token: Firebase ID token extracted from Authorization header
        
    Returns:
        Dict[str, Any]: Decoded token payload with user information
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    request_id = get_request_id()
    
    if not token or (isinstance(token, str) and not token.strip()):
        logger.warning(
            "No authentication token provided",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "auth_error": "missing_token",
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: No token provided. Please provide a valid authentication token.",
            headers={"WWW-Authenticate": "Bearer", "X-Request-ID": request_id} if request_id else {"WWW-Authenticate": "Bearer"},
        )
    
    try:
        decoded_token = await verify_firebase_token(token)
        
        # Log successful authentication (debug level to avoid noise)
        logger.debug(
            f"Authentication successful for user: {decoded_token.get('uid')}",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "user_id": decoded_token.get('uid'),
                    "email": decoded_token.get('email'),
                }
            }
        )
        
        return decoded_token
        
    except ValueError as e:
        # Log authentication failure with context
        log_error(
            logger,
            e,
            context={
                "request_id": request_id,
                "auth_error": "token_verification_failed",
                "error_type": type(e).__name__,
            },
            level=logging.WARNING
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",  
            headers={"WWW-Authenticate": "Bearer", "X-Request-ID": request_id} if request_id else {"WWW-Authenticate": "Bearer"},
        )

async def get_optional_user(
    token: Optional[str] = Depends(get_token_from_header)
) -> Optional[Dict[str, Any]]:
    """
    Dependency that returns user if authenticated, None otherwise.
    
    Use this for endpoints that should work for both authenticated and anonymous users.
    
    Args:
        token: Firebase ID token extracted from Authorization header
        
    Returns:
        Optional[Dict[str, Any]]: Decoded token payload or None if not authenticated
    """
    if not token:
        return None
    
    try:
        return await verify_firebase_token(token)
    except (ValueError, HTTPException):
        return None

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency that requires the user to be authenticated and active.
    
    Use this when you need to ensure the user account is in good standing.
    
    Args:
        current_user: User data from get_current_user dependency
        
    Returns:
        Dict[str, Any]: User data if active
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if account is disabled
    """
    # Check if user account is disabled (you can add custom checks here)
    if current_user.get('disabled', False):
        logger.warning(f"User account disabled: {current_user.get('uid')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled.",
        )
    
    # Check if email is verified (optional requirement)
    if not current_user.get('email_verified', False):
        logger.warning(f"User email not verified: {current_user.get('uid')}")
        # You might want to allow access but show a warning, or require verification
        # For now, we'll just log it but allow access
    
    return current_user

async def require_email_verified(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency that requires the user to have a verified email address.
    
    Use this for sensitive operations that require email verification.
    
    Args:
        current_user: User data from get_current_user dependency
        
    Returns:
        Dict[str, Any]: User data if email is verified
        
    Raises:
        HTTPException: 403 if email is not verified
    """
    if not current_user.get('email_verified', False):
        logger.warning(f"Email verification required for user: {current_user.get('uid')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email address.",
        )
    
    return current_user

# Utility function to get user ID from token
def get_user_id_from_token(token_payload: Dict[str, Any]) -> str:
    """
    Extract user ID from decoded token payload.
    
    Args:
        token_payload: Decoded Firebase token
        
    Returns:
        str: Firebase user UID
        
    Raises:
        ValueError: If user ID is not found in token
    """
    user_id = token_payload.get('uid')
    if not user_id:
        raise ValueError("User ID not found in authentication token")
    return user_id

# Utility function to get user email from token
def get_user_email_from_token(token_payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract email from decoded token payload.
    
    Args:
        token_payload: Decoded Firebase token
        
    Returns:
        Optional[str]: User email address or None if not available
    """
    return token_payload.get('email')

# Custom decorator for role-based authentication (if you need it later)
def require_role(required_role: str):
    """
    Decorator factory for role-based authentication.
    
    Example usage:
    @router.get("/admin")
    @require_role("admin")
    async def admin_endpoint(user: dict = Depends(get_current_user)):
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # The user should be passed as a parameter to the endpoint
            # We need to find the user in the kwargs
            user = None
            for arg_name, arg_value in kwargs.items():
                if isinstance(arg_value, dict) and 'uid' in arg_value:
                    user = arg_value
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User not found in endpoint parameters",
                )
            
            # Check if user has the required role
            # You'll need to implement your own role checking logic
            user_roles = user.get('roles', [])
            if required_role not in user_roles:
                logger.warning(f"User {user.get('uid')} lacks required role: {required_role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role: {required_role}",
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Quick test function (can be removed in production)
async def test_authentication():
    """Test function to verify authentication is working."""
    try:
        # This would be called with a real token in practice
        return {"status": "Authentication system initialized"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}