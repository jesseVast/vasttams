"""
Authentication Management Router

This module provides API endpoints for managing authentication provider configurations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from pydantic import BaseModel
from .provider_config import AuthProviderConfig, AuthProviderConfigList, AuthProviderConfigUpdate
from .models import AuthMethod, UserRole, User
from .service import AuthProviderService
from .core import AuthManager
from .user_service import UserService
from ..core.dependencies import get_vast_db
from .rbac import require_admin, require_editor, require_viewer
from .middleware import UserSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tams/v8.0/auth/providers", tags=["auth"])
users_router = APIRouter(prefix="/api/tams/v8.0/users", tags=["users"])

# Global instances
_auth_manager: Optional[AuthManager] = None
_auth_service: Optional[AuthProviderService] = None


def get_auth_service() -> AuthProviderService:
    """Get the auth service instance"""
    global _auth_service
    if _auth_service is None:
        vast_db = get_vast_db()
        _auth_service = AuthProviderService(vast_db, _auth_manager)
    return _auth_service


@router.get("", response_model=List[AuthProviderConfig])
async def list_auth_providers(
    service: AuthProviderService = Depends(get_auth_service),
    user_session: UserSession = Depends(require_viewer)
):
    """List all authentication provider configurations"""
    try:
        configs = await service.get_provider_configs()
        return configs
    except Exception as e:
        logger.error("Failed to list auth providers: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{method}", response_model=AuthProviderConfig)
async def get_auth_provider(
    method: str,
    service: AuthProviderService = Depends(get_auth_service)
):
    """Get a specific authentication provider configuration"""
    try:
        configs = await service.get_provider_configs()
        
        # Find config for this method
        for config in configs:
            if config.method.value == method:
                return config
        
        raise HTTPException(status_code=404, detail="Auth provider not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get auth provider: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{method}")
async def update_auth_provider(
    method: str,
    config_update: AuthProviderConfigUpdate = Body(...),
    service: AuthProviderService = Depends(get_auth_service)
):
    """Update an authentication provider configuration"""
    try:
        # Get current config
        configs = await service.get_provider_configs()
        
        method_enum = None
        current_config = None
        
        for c in configs:
            if c.method.value == method:
                method_enum = c.method
                current_config = c
                break
        
        if not method_enum:
            raise HTTPException(status_code=404, detail="Auth provider not found")
        
        # Apply updates
        if config_update.enabled is not None:
            current_config.enabled = config_update.enabled
        if config_update.config is not None:
            current_config.config.update(config_update.config)
        if config_update.order is not None:
            current_config.order = config_update.order
        
        # Update in database
        success = await service.update_provider_config(method_enum, current_config)
        
        if success:
            return {"message": "Auth provider configuration updated", "method": method}
        else:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update auth provider: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reload")
async def reload_auth_providers(
    service: AuthProviderService = Depends(get_auth_service),
    user_session: UserSession = Depends(require_admin)
):
    """Reload authentication providers with current configurations"""
    try:
        if service.auth_manager:
            await service._reload_auth_manager()
            return {"message": "Auth providers reloaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Auth manager not initialized")
            
    except Exception as e:
        logger.error("Failed to reload auth providers: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Login endpoint models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


# New login router
login_router = APIRouter(prefix="/api/tams/v8.0/auth", tags=["auth"])


@login_router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    vast_db=Depends(get_vast_db)
):
    """Login endpoint for user authentication"""
    try:
        user_service = UserService(vast_db)
        
        # Verify user credentials
        is_valid = await user_service.verify_user_password(login_data.username, login_data.password)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Get user from database
        user = await user_service.get_user_by_username(login_data.username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Create JWT token
        from .providers.jwt import JWTProvider
        jwt_provider = JWTProvider()
        
        token = jwt_provider.create_token(
            user_id=user.user_id,
            username=user.username,
            role=user.role
        )
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.user_id,
            username=user.username,
            role=user.role.value
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Users endpoint models
class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: Optional[UserRole] = UserRole.VIEWER


class UserResponse(BaseModel):
    user_id: str
    username: str
    role: str
    created_at: str
    updated_at: str


@users_router.get("", response_model=List[UserResponse])
async def list_users(
    vast_db=Depends(get_vast_db),
    user_session: UserSession = Depends(require_admin)
):
    """List all users (admin only)"""
    try:
        user_service = UserService(vast_db)
        users = await user_service.list_users()
        
        return [
            UserResponse(
                user_id=user.user_id,
                username=user.username,
                role=user.role.value,
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else ""
            )
            for user in users
        ]
    except Exception as e:
        logger.error("Failed to list users: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@users_router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    vast_db=Depends(get_vast_db),
    user_session: UserSession = Depends(require_admin)
):
    """Create a new user (admin only)"""
    try:
        user_service = UserService(vast_db)
        
        # Check if user already exists
        existing = await user_service.get_user_by_username(user_data.username)
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")
        
        user = await user_service.create_user(user_data.username, user_data.password, user_data.role)
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            role=user.role.value,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create user: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@users_router.delete("/{username}")
async def delete_user(
    username: str,
    vast_db=Depends(get_vast_db),
    user_session: UserSession = Depends(require_admin)
):
    """Delete a user (admin only)"""
    try:
        user_service = UserService(vast_db)
        success = await user_service.delete_user(username)
        
        if success:
            return {"message": f"User {username} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete user: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

