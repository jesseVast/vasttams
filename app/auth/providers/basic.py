"""
HTTP Basic authentication provider with database support
"""

import base64
import bcrypt
import logging
from typing import Optional
from fastapi import Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

logger = logging.getLogger(__name__)

class BasicAuthProvider(AuthProvider):
    """HTTP Basic authentication provider with database support"""
    
    def __init__(self, vast_store=None, fallback_users: dict = None):
        # Database store for persistent user authentication
        self.vast_store = vast_store
        
        # Fallback in-memory users for development/testing
        self.fallback_users = fallback_users or {
            "admin": "$2b$12$P1HfguryTOezJ3aSyiwYfOLiJQCbmeEmOSdogJBrsCIYP3L8/Lfeq",  # admin123
            "user": "$2b$12$v7SDbmZvU1hZ1Pk4IXjezu5T6Yg1w3sSAy/ICOS/Ug5Il1lGKNvpi",   # user123
            "test": "$2b$12$EXIdqzfdI8pJrUdJagN4qeeMNoeZda/niFkdtCMBh0ROP2qL5tVZS"   # test123
        }
        self.security = HTTPBasic(auto_error=False)
        self._enabled = True
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("BasicAuthProvider initialized with vast_store: %s, fallback_users: %d", 
                        "available" if vast_store else "not available", len(self.fallback_users))
    
    def get_method(self) -> AuthMethod:
        return AuthMethod.BASIC
    
    def is_enabled(self) -> bool:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("BasicAuthProvider enabled: %s", self._enabled)
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable this provider"""
        self._enabled = enabled
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("BasicAuthProvider enabled set to: %s", enabled)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Hashing password for basic auth (length: %d)", len(password))
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Password hashed successfully for basic auth")
        
        return hashed
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Password verification result: %s", "valid" if is_valid else "invalid")
            return is_valid
        except Exception as e:
            logger.warning("Error during password verification: %s", e)
            return False
    
    async def add_user(self, username: str, password: str):
        """Add a user for basic authentication"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Adding user for basic auth: %s", username)
        
        if self.vast_store:
            # Add to database
            from app.models.models import User
            import uuid
            
            user = User(
                user_id=str(uuid.uuid4()),
                username=username,
                password_hash=self.hash_password(password),
                is_active=True
            )
            success = await self.vast_store.create_user(user)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("User added to database: %s", "success" if success else "failed")
            return success
        else:
            # Fallback to in-memory
            self.fallback_users[username] = self.hash_password(password)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("User added to fallback storage: %s", username)
            return True
    
    async def remove_user(self, username: str):
        """Remove a user from basic authentication"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Removing user from basic auth: %s", username)
        
        if self.vast_store:
            # Remove from database
            user = await self.vast_store.get_user_by_username(username)
            if user:
                success = await self.vast_store.delete_user(user.user_id)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("User removed from database: %s", "success" if success else "failed")
                return success
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("User not found in database: %s", username)
            return False
        else:
            # Fallback to in-memory
            if username in self.fallback_users:
                del self.fallback_users[username]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("User removed from fallback storage: %s", username)
                return True
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("User not found in fallback storage: %s", username)
            return False
    
    async def authenticate(self, request: Request) -> AuthResult:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Attempting basic authentication")
        
        credentials: HTTPBasicCredentials = await self.security(request)
        
        if not credentials:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("No Basic auth credentials provided in request")
            return AuthResult(success=False, error="No Basic auth credentials provided")
        
        try:
            username = credentials.username
            password = credentials.password
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Processing basic auth for username: %s", username)
            
            # Try database authentication first
            if self.vast_store:
                user = await self.vast_store.get_user_by_username(username)
                if user and user.is_active and user.password_hash:
                    if self.verify_password(password, user.password_hash):
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Database authentication successful for user: %s", username)
                        return AuthResult(
                            success=True,
                            user_id=user.user_id,
                            username=user.username,
                            metadata={
                                "auth_type": "basic", 
                                "auth_source": "database",
                                "is_admin": user.is_admin
                            }
                        )
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Database password verification failed for user: %s", username)
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("User not found or inactive in database: %s", username)
            
            # Fallback to in-memory authentication
            if username in self.fallback_users:
                stored_hash = self.fallback_users[username]
                if self.verify_password(password, stored_hash):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Fallback authentication successful for user: %s", username)
                    return AuthResult(
                        success=True,
                        user_id=username,
                        username=username,
                        metadata={
                            "auth_type": "basic", 
                            "auth_source": "fallback",
                            "is_admin": username == "admin"
                        }
                    )
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Fallback password verification failed for user: %s", username)
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("User not found in fallback storage: %s", username)
            
            logger.warning("Basic authentication failed for user: %s", username)
            return AuthResult(success=False, error="Invalid credentials")
                
        except Exception as e:
            logger.error("Error during basic authentication for user %s: %s", username, e)
            return AuthResult(success=False, error="Authentication failed: %s" % str(e)) 