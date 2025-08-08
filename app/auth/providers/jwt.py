"""
JWT Bearer token authentication provider
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

class JWTProvider(AuthProvider):
    """JWT Bearer token authentication provider"""
    
    def __init__(self, jwt_secret: str = "your-secret-key", jwt_algorithm: str = "HS256", jwt_expire_minutes: int = 30):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expire_minutes = jwt_expire_minutes
        self.security = HTTPBearer(auto_error=False)
        self._enabled = True
    
    def get_method(self) -> AuthMethod:
        return AuthMethod.BEARER
    
    def is_enabled(self) -> bool:
        return self._enabled and self.jwt_secret is not None
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this provider"""
        self._enabled = enabled
    
    async def authenticate(self, request: Request) -> AuthResult:
        credentials: HTTPAuthorizationCredentials = await self.security(request)
        
        if not credentials:
            return AuthResult(success=False, error="No Bearer token provided")
        
        try:
            payload = jwt.decode(
                credentials.credentials,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            return AuthResult(
                success=True,
                user_id=payload.get("sub"),
                username=payload.get("username"),
                metadata=payload
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, error="Token expired")
        except jwt.InvalidTokenError:
            return AuthResult(success=False, error="Invalid token")
    
    def create_token(self, user_id: str, username: str, **kwargs) -> str:
        """Create a JWT token"""
        payload = {
            "sub": user_id,
            "username": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=self.jwt_expire_minutes),
            **kwargs
        }
        
        return jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        ) 