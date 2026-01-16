import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

# Store the Firebase app instance globally
firebase_app = None

def initialize_firebase():
    global firebase_app  # Important: use global keyword
    
    try:
        if not firebase_admin._apps:
            service_account_path = os.getenv(
                'FIREBASE_SERVICE_ACCOUNT_PATH', 
                'config/firebase-service-account.json'
            )
            
            cred = credentials.Certificate(service_account_path)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase admin initialized successfully")
        else:
            firebase_app = firebase_admin.get_app()
            
        return firebase_app
        
    except FirebaseError as e:
        logger.error(f"Failed to initialize Firebase admin: {e}")
        raise
    
async def verify_firebase_token(id_token: str) -> dict:
    try: 
        # Use the global firebase_app instance
        decoded_token = auth.verify_id_token(id_token, app=firebase_app)
        return decoded_token
    except auth.ExpiredIdTokenError:
        logger.error("Firebase token has expired")
        raise
    except auth.InvalidIdTokenError:
        logger.error("Firebase token is invalid")
        raise
    except auth.RevokedIdTokenError:
        logger.error("Firebase token has been revoked")
        raise
    except auth.CertificateFetchError:
        raise ValueError("Error fetching certificate")
    except FirebaseError as e:
        raise ValueError(f"Firebase error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")

def create_firebase_user(
    email: str,
    password: str,
    display_name: Optional[str] = None,
    email_verified: bool = False,
) -> dict:
    """
    Create a new user in Firebase Authentication.
    
    Args:
        email: User's email address
        password: User's password (will be hashed by Firebase)
        display_name: Optional display name
        email_verified: Whether email is verified (default: False)
        photo_url: Optional profile photo URL
    
    Returns:
        Dictionary containing user information including 'uid'
    
    Raises:
        ValueError: If user creation fails (e.g., email already exists)
    """
    try:
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=email_verified,
            app=firebase_app
        )
        
        logger.info(f"Created Firebase user: {email} (UID: {user_record.uid})")
        
        return {
            'uid': user_record.uid,
            'email': user_record.email,
            'display_name': user_record.display_name,
            'email_verified': user_record.email_verified
        }
    
    except auth.EmailAlreadyExistsError:
        logger.error(f"Firebase user with email {email} already exists")
        raise ValueError(f"An account with this email already exists")
    
    except FirebaseError as e:
        logger.error(f"Firebase error creating user: {str(e)}")
        raise ValueError(f"Failed to create user account: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating Firebase user: {str(e)}")
        raise ValueError(f"An unexpected error occurred: {str(e)}")

# Initialize Firebase when this module is imported
initialize_firebase()

# Export the firebase_app so it can be imported
__all__ = ['firebase_app', 'initialize_firebase', 'verify_firebase_token', 'create_firebase_user']