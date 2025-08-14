"""Authentication utility functions for TAMS application"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_TOKEN_EXPIRE_MINUTES = 30  # Default token expiration time
DEFAULT_PASSWORD_MIN_LENGTH = 8  # Minimum password length
DEFAULT_SALT_LENGTH = 16  # Length of salt for password hashing
DEFAULT_TOKEN_LENGTH = 32  # Length of generated tokens

def generate_user_id() -> str:
    """Generate a unique user ID"""
    return secrets.token_urlsafe(16)

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash

def generate_api_token() -> str:
    """Generate a secure API token"""
    return secrets.token_urlsafe(32)

def is_token_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a token is expired"""
    if expires_at is None:
        return False
    return datetime.utcnow() > expires_at

def calculate_token_expiry(minutes: int = DEFAULT_TOKEN_EXPIRE_MINUTES) -> datetime:
    """Calculate token expiry time"""
    return datetime.utcnow() + timedelta(minutes=minutes) 