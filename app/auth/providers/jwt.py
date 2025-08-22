"""JWT authentication provider for TAMS application"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .base import AuthProvider
from ..models import AuthResult, AuthMethod, User, AuthConfig

logger = logging.getLogger(__name__)

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_JWT_SECRET = "your-secret-key"  # Default JWT secret (should be overridden)
DEFAULT_JWT_ALGORITHM = "HS256"  # Default JWT algorithm
DEFAULT_JWT_EXPIRE_MINUTES = 30  # Default JWT expiration time
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7  # Default refresh token expiration time

class JWTProvider(AuthProvider):
    """JWT Bearer token authentication provider"""
    
    def __init__(self, jwt_secret: str = DEFAULT_JWT_SECRET, jwt_algorithm: str = DEFAULT_JWT_ALGORITHM, jwt_expire_minutes: int = DEFAULT_JWT_EXPIRE_MINUTES):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expire_minutes = jwt_expire_minutes
        self.security = HTTPBearer(auto_error=False)
        self._enabled = True
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("JWTProvider initialized with algorithm: %s, expire_minutes: %d", 
                        jwt_algorithm, jwt_expire_minutes)
    
    def get_method(self) -> AuthMethod:
        return AuthMethod.BEARER
    
    def is_enabled(self) -> bool:
        enabled = self._enabled and self.jwt_secret is not None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("JWTProvider enabled: %s (enabled: %s, secret: %s)", 
                        enabled, self._enabled, "set" if self.jwt_secret else "not set")
        return enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this provider"""
        self._enabled = enabled
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("JWTProvider enabled set to: %s", enabled)
    
    async def authenticate(self, request: Request) -> AuthResult:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Attempting JWT authentication")
        
        credentials: HTTPAuthorizationCredentials = await self.security(request)
        
        if not credentials:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("No Bearer token provided in request")
            return AuthResult(success=False, error="No Bearer token provided")
        
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Decoding JWT token")
            
            payload = jwt.decode(
                credentials.credentials,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("JWT token decoded successfully for user: %s", payload.get("username"))
            
            return AuthResult(
                success=True,
                user_id=payload.get("sub"),
                username=payload.get("username"),
                metadata=payload
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return AuthResult(success=False, error="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token: %s", e)
            return AuthResult(success=False, error="Invalid token")
        except Exception as e:
            logger.error("Unexpected error during JWT authentication: %s", e)
            return AuthResult(success=False, error="Authentication error")
    
    def create_token(self, user_id: str, username: str, **kwargs) -> str:
        """Create a JWT token"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Creating JWT token for user: %s", username)
        
        payload = {
            "sub": user_id,
            "username": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=self.jwt_expire_minutes),
            **kwargs
        }
        
        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("JWT token created successfully for user: %s", username)
        
        return token 