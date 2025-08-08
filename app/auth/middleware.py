"""
Authentication middleware for TAMS API 7.0
"""

from typing import Optional
from fastapi import Request, HTTPException, Depends
from datetime import datetime

from .core import AuthManager
from .models import UserSession, AuthMethod

class AuthMiddleware:
    """Authentication middleware"""
    
    def __init__(self, auth_manager: AuthManager, require_auth: bool = False):
        self.auth_manager = auth_manager
        self.require_auth = require_auth
    
    async def __call__(self, request: Request, call_next):
        """Process request through authentication middleware"""
        
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Try to authenticate the request
        auth_result = await self.auth_manager.authenticate(request)
        
        if not auth_result.success:
            if self.require_auth:
                raise HTTPException(status_code=401, detail=auth_result.error)
            # Continue without authentication
            request.state.user_session = None
        else:
            # Create user session
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
    return getattr(request.state, 'user_session', None)

async def require_authentication(user_session: Optional[UserSession] = Depends(get_current_user_session)) -> UserSession:
    """Require authentication for endpoint"""
    if not user_session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_session 