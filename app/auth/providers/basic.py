"""
HTTP Basic authentication provider
"""

import base64
from typing import Optional
from fastapi import Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

class BasicAuthProvider(AuthProvider):
    """HTTP Basic authentication provider"""
    
    def __init__(self, users: dict = None):
        self.users = users or {
            "admin": "admin123",
            "user": "user123",
            "test": "test123"
        }
        self.security = HTTPBasic(auto_error=False)
        self._enabled = True
    
    def get_method(self) -> AuthMethod:
        return AuthMethod.BASIC
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this provider"""
        self._enabled = enabled
    
    def add_user(self, username: str, password: str):
        """Add a user for basic authentication"""
        self.users[username] = password
    
    def remove_user(self, username: str):
        """Remove a user from basic authentication"""
        if username in self.users:
            del self.users[username]
    
    async def authenticate(self, request: Request) -> AuthResult:
        credentials: HTTPBasicCredentials = await self.security(request)
        
        if not credentials:
            return AuthResult(success=False, error="No Basic auth credentials provided")
        
        try:
            username = credentials.username
            password = credentials.password
            
            # Check if user exists and password matches
            if username in self.users and self.users[username] == password:
                return AuthResult(
                    success=True,
                    user_id=username,
                    username=username,
                    metadata={"auth_type": "basic"}
                )
            else:
                return AuthResult(success=False, error="Invalid credentials")
                
        except Exception as e:
            return AuthResult(success=False, error="Authentication failed") 