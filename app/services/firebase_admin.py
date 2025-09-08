import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError
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

# Initialize Firebase when this module is imported
initialize_firebase()

# Export the firebase_app so it can be imported
__all__ = ['firebase_app', 'initialize_firebase', 'verify_firebase_token']