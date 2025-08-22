"""
URL token authentication provider (API key in query) with database support
"""

import logging
from typing import Optional
from fastapi import Request
import uuid
from datetime import datetime, timezone

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

logger = logging.getLogger(__name__)

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
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("URLTokenProvider initialized with vast_store: %s, fallback_tokens: %d", 
                        "available" if vast_store else "not available", len(self.fallback_tokens))
    
    def get_method(self) -> AuthMethod:
        return AuthMethod.URL_TOKEN
    
    def is_enabled(self) -> bool:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("URLTokenProvider enabled: %s", self._enabled)
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this provider"""
        self._enabled = enabled
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("URLTokenProvider enabled set to: %s", enabled)
    
    async def add_token(self, token: str, user_id: str, username: str, description: str = "API Token"):
        """Add a valid token"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Adding URL token for user: %s, description: %s", username, description)
        
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
            success = await self.vast_store.create_api_token(api_token)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Token added to database: %s", "success" if success else "failed")
            return success
        else:
            # Fallback to in-memory
            self.fallback_tokens[token] = {"user_id": user_id, "username": username}
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Token added to fallback storage for user: %s", username)
            return True
    
    async def remove_token(self, token: str):
        """Remove a token"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Removing URL token: %s", token[:8] + "..." if len(token) > 8 else token)
        
        if self.vast_store:
            # Remove from database
            success = await self.vast_store.delete_api_token(token)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Token removed from database: %s", "success" if success else "failed")
            return success
        else:
            # Fallback to in-memory
            if token in self.fallback_tokens:
                del self.fallback_tokens[token]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Token removed from fallback storage")
                return True
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Token not found in fallback storage")
            return False
    
    async def authenticate(self, request: Request) -> AuthResult:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Attempting URL token authentication")
        
        # Get access_token from query parameters
        access_token = request.query_params.get("access_token")
        
        if not access_token:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("No access_token provided in query parameters")
            return AuthResult(success=False, error="No access_token provided")
        
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Processing URL token authentication for token: %s", access_token[:8] + "..." if len(access_token) > 8 else access_token)
            
            # Try database authentication first
            if self.vast_store:
                api_token = await self.vast_store.get_api_token(access_token)
                if api_token and api_token.is_active:
                    # Check if token is expired
                    if api_token.expires_at and api_token.expires_at < datetime.now(timezone.utc):
                        logger.warning("URL token expired: %s", access_token[:8] + "..." if len(access_token) > 8 else access_token)
                        return AuthResult(success=False, error="Token expired")
                    
                    # Get user details
                    user = await self.vast_store.get_user(api_token.user_id)
                    if user and user.is_active:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Database URL token authentication successful for user: %s", user.username)
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
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("User not found or inactive for token: %s", access_token[:8] + "..." if len(access_token) > 8 else access_token)
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("API token not found or inactive in database: %s", access_token[:8] + "..." if len(access_token) > 8 else access_token)
            
            # Fallback to in-memory authentication
            if access_token in self.fallback_tokens:
                user_info = self.fallback_tokens[access_token]
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Fallback URL token authentication successful for user: %s", user_info["username"])
                
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
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Token not found in fallback storage: %s", access_token[:8] + "..." if len(access_token) > 8 else access_token)
            
            logger.warning("URL token authentication failed for token: %s", access_token[:8] + "..." if len(access_token) > 8 else access_token)
            return AuthResult(success=False, error="Invalid access token")
                
        except Exception as e:
            logger.error("Error during URL token authentication for token %s: %s", 
                        access_token[:8] + "..." if len(access_token) > 8 else access_token, e)
            return AuthResult(success=False, error="Token validation failed: %s" % str(e)) 