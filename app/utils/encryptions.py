# app/utils/encryption.py
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import logging

logger = logging.getLogger(__name__)

# Generate a key from your secret
def get_cipher():
    """Create Fernet cipher from secret key."""
    key = base64.urlsafe_b64encode(settings.ENCRYPTION_SECRET_KEY.encode()[:32].ljust(32))
    return Fernet(key)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    if not data:
        return data
    
    try:
        cipher = get_cipher()
        encrypted_data = cipher.encrypt(data.encode())
        return encrypted_data.decode()
    except Exception as e:
        logger.error(f"Error encrypting data: {str(e)}")
        raise

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    if not encrypted_data:
        return encrypted_data
    
    try:
        cipher = get_cipher()
        decrypted_data = cipher.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Error decrypting data: {str(e)}")
        raise