"""
Authentication Provider Configuration Models

This module defines models for managing auth provider configurations
via API and database.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from .models import AuthMethod


class AuthProviderConfig(BaseModel):
    """Configuration for a single authentication provider"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    method: AuthMethod = Field(..., description="Authentication method type")
    enabled: bool = Field(default=True, description="Whether this provider is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")
    
    # Provider-specific fields
    # For JWT
    jwt_secret: Optional[str] = Field(None, description="JWT secret key")
    jwt_algorithm: Optional[str] = Field("HS256", description="JWT algorithm")
    jwt_expire_minutes: Optional[int] = Field(30, description="JWT expiration in minutes")
    
    # For Basic Auth
    requires_vast_store: bool = Field(default=False, description="Whether provider requires vast_store for database access")
    
    # Metadata
    description: Optional[str] = Field(None, description="Human-readable description")
    order: int = Field(default=0, description="Order for trying this provider")


class AuthProviderConfigList(BaseModel):
    """List of authentication provider configurations"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    providers: list[AuthProviderConfig] = Field(..., description="List of configured providers")


class AuthProviderConfigUpdate(BaseModel):
    """Update model for auth provider configuration"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    enabled: Optional[bool] = Field(None, description="Enable/disable this provider")
    config: Optional[Dict[str, Any]] = Field(None, description="Provider-specific configuration")
    order: Optional[int] = Field(None, description="Change provider order")

