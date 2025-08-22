"""
Authentication middleware for TAMS API 7.0
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from datetime import datetime

from .core import AuthManager
from .models import UserSession, AuthMethod

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication middleware"""
    
    def __init__(self, auth_manager: AuthManager, require_auth: bool = False):
        self.auth_manager = auth_manager
        self.require_auth = require_auth
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("AuthMiddleware initialized with require_auth=%s", require_auth)
    
    async def __call__(self, request: Request, call_next):
        """Process request through authentication middleware"""
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Processing request: %s %s", request.method, request.url.path)
        
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Skipping authentication for path: %s", request.url.path)
            return await call_next(request)
        
        # Try to authenticate the request
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Attempting authentication for path: %s", request.url.path)
        
        auth_result = await self.auth_manager.authenticate(request)
        
        if not auth_result.success:
            if self.require_auth:
                logger.warning("Authentication required but failed for path: %s", request.url.path)
                raise HTTPException(status_code=401, detail=auth_result.error)
            # Continue without authentication
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Authentication failed but continuing without auth for path: %s", request.url.path)
            request.state.user_session = None
        else:
            # Create user session
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Authentication successful for user: %s via %s", 
                           auth_result.username, auth_result.auth_method)
            
            user_session = UserSession(
                user_id=auth_result.user_id,
                username=auth_result.username,
                auth_method=auth_result.auth_method,
                created_at=datetime.utcnow(),
                metadata=auth_result.metadata
            )
            request.state.user_session = user_session
        
        response = await call_next(request)
        return response
    
    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for this path"""
        skip_paths = [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/test"  # Allow testing auth endpoints
        ]
        return any(path.startswith(skip_path) for skip_path in skip_paths)

async def get_current_user_session(request: Request) -> Optional[UserSession]:
    """Get current user session from request"""
    user_session = getattr(request.state, 'user_session', None)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Getting user session: %s", "found" if user_session else "not found")
    return user_session

async def require_authentication(user_session: Optional[UserSession] = Depends(get_current_user_session)) -> UserSession:
    """Require authentication for endpoint"""
    if not user_session:
        logger.warning("Authentication required but no user session found")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Authentication verified for user: %s", user_session.username)
    
    return user_session 