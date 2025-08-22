"""Authentication models for TAMS application"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
from enum import Enum

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_JWT_EXPIRE_MINUTES = 30  # Default JWT token expiration time
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7  # Default refresh token expiration time
DEFAULT_MAX_LOGIN_ATTEMPTS = 5  # Maximum failed login attempts before lockout
DEFAULT_LOCKOUT_DURATION_MINUTES = 15  # Duration of account lockout

class AuthMethod(str, Enum):
    """Authentication methods from TAMS 7.0 spec"""
    BEARER = "bearer"      # JWT Bearer tokens
    BASIC = "basic"        # HTTP Basic auth
    URL_TOKEN = "url_token"  # API key in query
    NONE = "none"          # No authentication

class AuthResult(BaseModel):
    """Result of authentication attempt"""
    success: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    auth_method: Optional[AuthMethod] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

class AuthConfig(BaseModel):
    """Authentication configuration"""
    enabled_methods: list[AuthMethod] = [AuthMethod.NONE]
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=DEFAULT_JWT_EXPIRE_MINUTES, description="JWT token expiration time in minutes")
    basic_auth_enabled: bool = False
    url_token_enabled: bool = False
    require_auth: bool = False

class UserSession(BaseModel):
    """Simple user session (no roles/permissions)"""
    user_id: str
    username: str
    auth_method: AuthMethod
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {} 