"""
HTTP Basic authentication provider with database support
"""

import base64
import bcrypt
from typing import Optional
from fastapi import Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .base import AuthProvider
from ..models import AuthResult, AuthMethod

class BasicAuthProvider(AuthProvider):
    """HTTP Basic authentication provider with database support"""
    
    def __init__(self, vast_store=None, fallback_users: dict = None):
        # Database store for persistent user authentication
        self.vast_store = vast_store
        
        # Fallback in-memory users for development/testing
        self.fallback_users = fallback_users or {
            "admin": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # admin123
            "user": "$2b$12$8H8N7Y6.vKGHRs8FkB1ZQeJhNhJJqCPr6rLGxwV.fK8D/2G4u8WB.",   # user123
            "test": "$2b$12$7o3TzJzl8FpF6y.oV6K8GeLNfI8rSjRp2r3mN9xE6VvFQ4MrO7BNe"   # test123
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
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    async def add_user(self, username: str, password: str):
        """Add a user for basic authentication"""
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
            return await self.vast_store.create_user(user)
        else:
            # Fallback to in-memory
            self.fallback_users[username] = self.hash_password(password)
            return True
    
    async def remove_user(self, username: str):
        """Remove a user from basic authentication"""
        if self.vast_store:
            # Remove from database
            user = await self.vast_store.get_user_by_username(username)
            if user:
                return await self.vast_store.delete_user(user.user_id)
            return False
        else:
            # Fallback to in-memory
            if username in self.fallback_users:
                del self.fallback_users[username]
                return True
            return False
    
    async def authenticate(self, request: Request) -> AuthResult:
        credentials: HTTPBasicCredentials = await self.security(request)
        
        if not credentials:
            return AuthResult(success=False, error="No Basic auth credentials provided")
        
        try:
            username = credentials.username
            password = credentials.password
            
            # Try database authentication first
            if self.vast_store:
                user = await self.vast_store.get_user_by_username(username)
                if user and user.is_active and user.password_hash:
                    if self.verify_password(password, user.password_hash):
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
            
            # Fallback to in-memory authentication
            if username in self.fallback_users:
                stored_hash = self.fallback_users[username]
                if self.verify_password(password, stored_hash):
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
            
            return AuthResult(success=False, error="Invalid credentials")
                
        except Exception as e:
            return AuthResult(success=False, error=f"Authentication failed: {str(e)}") 