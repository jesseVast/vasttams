"""
URL token authentication provider (API key in query) with database support
"""

from typing import Optional
from fastapi import Request
import uuid
from datetime import datetime, timezone

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

class URLTokenProvider(AuthProvider):
    """URL token authentication provider (API key in query) with database support"""
    
    def __init__(self, vast_store=None, fallback_tokens: dict = None):
        # Database store for persistent token authentication
        self.vast_store = vast_store
        
        # Fallback in-memory tokens for development/testing
        self.fallback_tokens = fallback_tokens or {
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
    
    async def add_token(self, token: str, user_id: str, username: str, description: str = "API Token"):
        """Add a valid token"""
        if self.vast_store:
            # Add to database
            from app.models.models import ApiToken
            
            api_token = ApiToken(
                token_id=token,
                user_id=user_id,
                token_name=description,
                token_type="url_token",
                token_hash=token,  # Store the actual token (in production, hash this)
                created_at=datetime.now(timezone.utc),
                expires_at=None,  # No expiration by default
                is_active=True
            )
            return await self.vast_store.create_api_token(api_token)
        else:
            # Fallback to in-memory
            self.fallback_tokens[token] = {"user_id": user_id, "username": username}
            return True
    
    async def remove_token(self, token: str):
        """Remove a token"""
        if self.vast_store:
            # Remove from database
            return await self.vast_store.delete_api_token(token)
        else:
            # Fallback to in-memory
            if token in self.fallback_tokens:
                del self.fallback_tokens[token]
                return True
            return False
    
    async def authenticate(self, request: Request) -> AuthResult:
        # Get access_token from query parameters
        access_token = request.query_params.get("access_token")
        
        if not access_token:
            return AuthResult(success=False, error="No access_token provided")
        
        try:
            # Try database authentication first
            if self.vast_store:
                api_token = await self.vast_store.get_api_token(access_token)
                if api_token and api_token.is_active:
                    # Check if token is expired
                    if api_token.expires_at and api_token.expires_at < datetime.now(timezone.utc):
                        return AuthResult(success=False, error="Token expired")
                    
                    # Get user details
                    user = await self.vast_store.get_user(api_token.user_id)
                    if user and user.is_active:
                        return AuthResult(
                            success=True,
                            user_id=user.user_id,
                            username=user.username,
                            metadata={
                                "access_token": access_token, 
                                "auth_type": "url_token",
                                "auth_source": "database",
                                "is_admin": user.is_admin,
                                "token_description": api_token.token_name
                            }
                        )
            
            # Fallback to in-memory authentication
            if access_token in self.fallback_tokens:
                user_info = self.fallback_tokens[access_token]
                
                return AuthResult(
                    success=True,
                    user_id=user_info["user_id"],
                    username=user_info["username"],
                    metadata={
                        "access_token": access_token, 
                        "auth_type": "url_token",
                        "auth_source": "fallback",
                        "is_admin": user_info["username"] == "admin"
                    }
                )
            
            return AuthResult(success=False, error="Invalid access token")
                
        except Exception as e:
            return AuthResult(success=False, error=f"Token validation failed: {str(e)}") 