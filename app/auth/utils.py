"""Authentication utility functions for TAMS application"""

import hashlib
import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_TOKEN_EXPIRE_MINUTES = 30  # Default token expiration time
DEFAULT_PASSWORD_MIN_LENGTH = 8  # Minimum password length
DEFAULT_SALT_LENGTH = 16  # Length of salt for password hashing
DEFAULT_TOKEN_LENGTH = 32  # Length of generated tokens

def generate_user_id() -> str:
    """Generate a unique user ID"""
    user_id = secrets.token_urlsafe(16)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Generated user ID: %s", user_id)
    return user_id

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (use bcrypt in production)"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Hashing password (length: %d)", len(password))
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Password hashed successfully")
    
    return password_hash

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Verifying password against hash")
    
    is_valid = hash_password(password) == password_hash
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Password verification result: %s", "valid" if is_valid else "invalid")
    
    return is_valid

def generate_api_token() -> str:
    """Generate a secure API token"""
    token = secrets.token_urlsafe(32)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Generated API token: %s", token[:8] + "...")
    return token

def is_token_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a token is expired"""
    if expires_at is None:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Token has no expiration date")
        return False
    
    is_expired = datetime.utcnow() > expires_at
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Token expiration check: %s (expires: %s)", 
                   "expired" if is_expired else "valid", expires_at)
    
    return is_expired

def calculate_token_expiry(minutes: int = DEFAULT_TOKEN_EXPIRE_MINUTES) -> datetime:
    """Calculate token expiry time"""
    expiry = datetime.utcnow() + timedelta(minutes=minutes)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Calculated token expiry: %s (in %d minutes)", expiry, minutes)
    return expiry 