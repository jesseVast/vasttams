#!/usr/bin/env python3
"""
Standalone test application for TAMS API 7.0 authentication
"""

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional

# Import our authentication system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.auth.core import AuthManager
from app.auth.providers.jwt import JWTProvider
from app.auth.providers.basic import BasicAuthProvider
from app.auth.providers.url_token import URLTokenProvider
from app.auth.middleware import AuthMiddleware, get_current_user_session, require_authentication
from app.auth.models import UserSession, AuthResult

# Create FastAPI app
app = FastAPI(
    title="TAMS Auth Test",
    description="Test application for TAMS API 7.0 authentication",
    version="1.0.0"
)

# Initialize auth manager
auth_manager = AuthManager()

# Add providers
jwt_provider = JWTProvider(jwt_secret="test-secret-key-change-in-production")
basic_provider = BasicAuthProvider()
url_token_provider = URLTokenProvider()

auth_manager.add_provider(jwt_provider)
auth_manager.add_provider(basic_provider)
auth_manager.add_provider(url_token_provider)

# Add auth middleware
app.middleware("http")(AuthMiddleware(auth_manager, require_auth=False))

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str

# Test endpoints
@app.get("/")
async def root():
    """Root endpoint - no auth required"""
    return {"message": "TAMS Auth Test API", "status": "running"}

@app.get("/auth/test")
async def test_auth():
    """Test endpoint - no auth required"""
    return {"message": "Auth test endpoint", "auth_required": False}

@app.get("/protected")
async def protected_endpoint(
    user_session: UserSession = Depends(require_authentication)
):
    """Protected endpoint - requires authentication"""
    return {
        "message": "This is a protected endpoint",
        "user_id": user_session.user_id,
        "username": user_session.username,
        "auth_method": user_session.auth_method,
        "metadata": user_session.metadata
    }

@app.post("/auth/login/basic")
async def login_basic(request: LoginRequest):
    """Login with basic authentication"""
    # Check if user exists in basic auth provider
    if request.username in basic_provider.users and basic_provider.users[request.username] == request.password:
        # Create JWT token
        token = jwt_provider.create_token(request.username, request.username)
        return TokenResponse(
            access_token=token,
            user_id=request.username,
            username=request.username
        )
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/login/jwt")
async def login_jwt(request: LoginRequest):
    """Login and get JWT token"""
    # For testing, accept any username/password
    token = jwt_provider.create_token(request.username, request.username)
    return TokenResponse(
        access_token=token,
        user_id=request.username,
        username=request.username
    )

@app.get("/auth/test/jwt")
async def test_jwt_auth(
    user_session: UserSession = Depends(require_authentication)
):
    """Test JWT authentication"""
    return {
        "message": "JWT authentication successful",
        "user_id": user_session.user_id,
        "username": user_session.username,
        "auth_method": user_session.auth_method
    }

@app.get("/auth/test/basic")
async def test_basic_auth(
    user_session: UserSession = Depends(require_authentication)
):
    """Test Basic authentication"""
    return {
        "message": "Basic authentication successful",
        "user_id": user_session.user_id,
        "username": user_session.username,
        "auth_method": user_session.auth_method
    }

@app.get("/auth/test/url-token")
async def test_url_token_auth(
    user_session: UserSession = Depends(require_authentication)
):
    """Test URL token authentication"""
    return {
        "message": "URL token authentication successful",
        "user_id": user_session.user_id,
        "username": user_session.username,
        "auth_method": user_session.auth_method
    }

@app.get("/auth/status")
async def auth_status():
    """Get authentication system status"""
    return {
        "jwt_enabled": jwt_provider.is_enabled(),
        "basic_enabled": basic_provider.is_enabled(),
        "url_token_enabled": url_token_provider.is_enabled(),
        "providers_count": len(auth_manager.providers)
    }

@app.get("/auth/users")
async def list_users():
    """List available users for testing"""
    return {
        "basic_users": list(basic_provider.users.keys()),
        "url_tokens": list(url_token_provider.valid_tokens.keys())
    }

if __name__ == "__main__":
    print("Starting TAMS Auth Test Server...")
    print("Available endpoints:")
    print("  GET  /                    - Root endpoint")
    print("  GET  /auth/test           - Test endpoint")
    print("  GET  /protected           - Protected endpoint (requires auth)")
    print("  POST /auth/login/basic    - Login with basic auth")
    print("  POST /auth/login/jwt      - Login and get JWT token")
    print("  GET  /auth/test/jwt       - Test JWT auth")
    print("  GET  /auth/test/basic     - Test Basic auth")
    print("  GET  /auth/test/url-token - Test URL token auth")
    print("  GET  /auth/status         - Auth system status")
    print("  GET  /auth/users          - List test users")
    print("\nTest users:")
    print("  Basic auth: admin/admin123, user/user123, test/test123")
    print("  URL tokens: test-token, admin-token, user-token")
    print("\nExample usage:")
    print("  curl -X GET 'http://localhost:8000/protected' -H 'Authorization: Bearer <token>'")
    print("  curl -X GET 'http://localhost:8000/protected?access_token=test-token'")
    print("  curl -X GET 'http://localhost:8000/protected' -u admin:admin123")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 