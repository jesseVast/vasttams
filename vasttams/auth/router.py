"""
Authentication Management Router

This module provides API endpoints for managing authentication provider configurations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from .provider_config import AuthProviderConfig, AuthProviderConfigList, AuthProviderConfigUpdate
from .models import AuthMethod
from .service import AuthProviderService
from .core import AuthManager
from ..core.dependencies import get_vast_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/providers", tags=["auth"])

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
    service: AuthProviderService = Depends(get_auth_service)
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
    service: AuthProviderService = Depends(get_auth_service)
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

