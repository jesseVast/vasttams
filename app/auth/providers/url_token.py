"""
URL token authentication provider (API key in query)
"""

from typing import Optional
from fastapi import Request

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

class URLTokenProvider(AuthProvider):
    """URL token authentication provider (API key in query)"""
    
    def __init__(self, valid_tokens: dict = None):
        self.valid_tokens = valid_tokens or {
            "test-token": {"user_id": "test-user", "username": "test"},
            "admin-token": {"user_id": "admin-user", "username": "admin"},
            "user-token": {"user_id": "user-1", "username": "user"}
        }
        self._enabled = True
    
    def get_method(self) -> AuthMethod:
        return AuthMethod.URL_TOKEN
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this provider"""
        self._enabled = enabled
    
    def add_token(self, token: str, user_id: str, username: str):
        """Add a valid token"""
        self.valid_tokens[token] = {"user_id": user_id, "username": username}
    
    def remove_token(self, token: str):
        """Remove a token"""
        if token in self.valid_tokens:
            del self.valid_tokens[token]
    
    async def authenticate(self, request: Request) -> AuthResult:
        # Get access_token from query parameters
        access_token = request.query_params.get("access_token")
        
        if not access_token:
            return AuthResult(success=False, error="No access_token provided")
        
        try:
            # Validate access token
            if access_token in self.valid_tokens:
                user_info = self.valid_tokens[access_token]
                
                return AuthResult(
                    success=True,
                    user_id=user_info["user_id"],
                    username=user_info["username"],
                    metadata={"access_token": access_token, "auth_type": "url_token"}
                )
            else:
                return AuthResult(success=False, error="Invalid access token")
                
        except Exception as e:
            return AuthResult(success=False, error="Token validation failed") 