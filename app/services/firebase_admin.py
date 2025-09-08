import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError

from app.core.config import settings
import logging      

logger = logging.getLogger(__name__)

def initialize_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CONFIG)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase admin initialized successfully")
    except FirebaseError as e:
        logger.error(f"Failed to initialize Firebase admin: {e}")
        raise

firebase_app=initialize_firebase()

async def verify_firebase_token(id_token: str)-> dict:
    try: 
        decoded_token= auth.verify_id_token(id_token,app=firebase_app)
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
    
