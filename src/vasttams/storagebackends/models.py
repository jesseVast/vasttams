"""
TAMS Storage Backend Models

This module contains models related to storage backends in the TAMS API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
import re

from ..common.models import validate_tams_uuid


class StorageBackend(BaseModel):
    """Storage backend information - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Storage backend identifier")
    label: Optional[str] = Field(None, description="Freeform string label for a storage backend")
    store_type: str = Field(..., description="The generic store type")
    provider: str = Field(..., description="The cloud provider of the storage")
    store_product: str = Field(..., description="The storage product name")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    endpoint_url: Optional[str] = Field(None, description="S3-compatible endpoint URL for this backend")
    access_key: Optional[str] = Field(None, description="Access key for this backend (write-only)")
    secret_key: Optional[str] = Field(None, description="Secret key for this backend (write-only)")
    default_storage: Optional[bool] = Field(False, description="If true, this is the default storage backend")
    created_at: Optional[datetime] = Field(None, description="Date-time the storage backend was created")
    updated_at: Optional[datetime] = Field(None, description="Date-time the storage backend was last updated")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_tams_uuid(v)
    
    @field_validator('store_type')
    @classmethod
    def validate_store_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Store type cannot be empty')
        
        # Validate against TAMS known types
        valid_types = ['http_object_store']
        if v not in valid_types:
            raise ValueError(f'Store type must be one of: {valid_types}')
        
        return v.strip()
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Provider cannot be empty')
        return v.strip()
    
    @field_validator('store_product')
    @classmethod
    def validate_store_product(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Store product cannot be empty')
        return v.strip()
    
    @field_validator('label')
    @classmethod
    def validate_label(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('Label cannot be empty or whitespace only')
            # Validate label format (alphanumeric, dash, underscore)
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Label can only contain alphanumeric characters, dashes, and underscores')
        return v.strip() if v else v


class StorageBackendPost(BaseModel):
    """Storage backend creation request"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    label: Optional[str] = Field(None, description="Freeform string label for a storage backend")
    store_type: str = Field(..., description="The generic store type")
    provider: str = Field(..., description="The cloud provider of the storage")
    store_product: str = Field(..., description="The storage product name")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    endpoint_url: Optional[str] = Field(None, description="S3-compatible endpoint URL for this backend")
    access_key: Optional[str] = Field(None, description="Access key for this backend (write-only)")
    secret_key: Optional[str] = Field(None, description="Secret key for this backend (write-only)")
    default_storage: Optional[bool] = Field(False, description="If true, this is the default storage backend")


class StorageBackendPatch(BaseModel):
    """Storage backend update request"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    label: Optional[str] = Field(None, description="Freeform string label for a storage backend")
    store_type: Optional[str] = Field(None, description="The generic store type")
    provider: Optional[str] = Field(None, description="The cloud provider of the storage")
    store_product: Optional[str] = Field(None, description="The storage product name")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    endpoint_url: Optional[str] = Field(None, description="S3-compatible endpoint URL for this backend")
    access_key: Optional[str] = Field(None, description="Access key for this backend (write-only)")
    secret_key: Optional[str] = Field(None, description="Secret key for this backend (write-only)")
    default_storage: Optional[bool] = Field(None, description="If true, this is the default storage backend")


class StorageBackendsList(BaseModel):
    """List of storage backends"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    backends: List[StorageBackend] = Field(..., description="Information about the storage backends available on this service instance")

