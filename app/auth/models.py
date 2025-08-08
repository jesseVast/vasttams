"""
Authentication models for TAMS API 7.0
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

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
    jwt_expire_minutes: int = 30
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