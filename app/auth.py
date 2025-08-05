"""
Authentication module for TAMS API.

Implements the security schemes defined in the API specification:
- Bearer token authentication (JWT)
- URL token authentication (query parameter)
- Basic authentication (username/password)
"""

import logging
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param
import jwt
from datetime import datetime, timedelta
import secrets

logger = logging.getLogger(__name__)

# Security schemes
security_bearer = HTTPBearer(auto_error=False)
security_basic = HTTPBasic(auto_error=False)

class AuthManager:
    """Manages authentication for the TAMS API."""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # In-memory token store (in production, use Redis or database)
        self.valid_tokens = set()
        
        # Basic auth credentials (in production, use database)
        self.users = {
            "admin": {
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "admin-password-change-in-production"),
                "role": "admin"
            }
        }
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        self.valid_tokens.add(encoded_jwt)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token."""
        try:
            if token not in self.valid_tokens:
                return None
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def verify_basic_auth(self, credentials: HTTPBasicCredentials) -> Optional[Dict[str, Any]]:
        """Verify basic authentication credentials."""
        if not credentials:
            return None
        
        user = self.users.get(credentials.username)
        if not user:
            return None
        
        if not secrets.compare_digest(credentials.password, user["password"]):
            return None
        
        return {
            "username": user["username"],
            "role": user["role"]
        }
    
    def verify_url_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify URL token authentication."""
        # In production, validate against a token store
        if token in self.valid_tokens:
            return {"token_type": "url_token", "valid": True}
        return None

# Global auth manager instance
auth_manager = AuthManager()

async def get_current_user_bearer(
    authorization: Optional[str] = Depends(security_bearer)
) -> Optional[Dict[str, Any]]:
    """Get current user from bearer token."""
    if not authorization:
        return None
    
    token = authorization.credentials
    payload = auth_manager.verify_token(token)
    if not payload:
        return None
    
    return payload

async def get_current_user_basic(
    credentials: Optional[HTTPBasicCredentials] = Depends(security_basic)
) -> Optional[Dict[str, Any]]:
    """Get current user from basic authentication."""
    if not credentials:
        return None
    
    return auth_manager.verify_basic_auth(credentials)

async def get_current_user_url_token(
    request: Request
) -> Optional[Dict[str, Any]]:
    """Get current user from URL token."""
    token = request.query_params.get("access_token")
    if not token:
        return None
    
    return auth_manager.verify_url_token(token)

async def get_current_user(
    bearer_user: Optional[Dict[str, Any]] = Depends(get_current_user_bearer),
    basic_user: Optional[Dict[str, Any]] = Depends(get_current_user_basic),
    url_user: Optional[Dict[str, Any]] = Depends(get_current_user_url_token)
) -> Optional[Dict[str, Any]]:
    """Get current user from any valid authentication method."""
    if bearer_user:
        return bearer_user
    elif basic_user:
        return basic_user
    elif url_user:
        return url_user
    return None

async def require_authentication(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require authentication for protected endpoints."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def require_admin(
    current_user: Dict[str, Any] = Depends(require_authentication)
) -> Dict[str, Any]:
    """Require admin role for admin-only endpoints."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Authentication endpoints
async def login_basic(credentials: HTTPBasicCredentials = Depends(security_basic)):
    """Login with basic authentication and return a bearer token."""
    user = auth_manager.verify_basic_auth(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def logout(current_user: Dict[str, Any] = Depends(require_authentication)):
    """Logout and invalidate the current token."""
    # In production, implement token blacklisting
    return {"message": "Logged out successfully"} 