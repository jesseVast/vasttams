"""
TAMS Storage Models

This module contains models related to storage backends and flow storage in the TAMS API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..common.models import HttpRequest, validate_tams_uuid


class StorageBackend(BaseModel):
    """Storage backend information - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    store_type: str = Field(..., description="The generic store type")
    provider: str = Field(..., description="The cloud provider of the storage")
    store_product: str = Field(..., description="The storage product name")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    
    @field_validator('store_type')
    @classmethod
    def validate_store_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Store type cannot be empty')
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


class StorageBackendsList(BaseModel):
    """List of storage backends"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    backends: List[StorageBackend] = Field(..., description="Information about the storage backends available on this service instance")


class MediaObject(BaseModel):
    """Media object storage information"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    object_id: str = Field(..., description="The object store identifier for the media object")
    put_url: HttpRequest = Field(..., description="PUT URL for uploading the media object")
    put_cors_url: Optional[HttpRequest] = Field(None, description="PUT CORS URL for uploading the media object")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata including storage path")
    
    @field_validator('object_id')
    @classmethod
    def validate_object_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Object ID cannot be empty')
        return v.strip()


class PreAction(BaseModel):
    """Pre-action for storage preparation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    action: str = Field(..., description="Action type")
    bucket_id: Optional[str] = Field(None, description="The name of the bucket that needs to be created")
    put_url: Optional[HttpRequest] = Field(None, description="PUT URL for creating bucket")
    put_cors_url: Optional[HttpRequest] = Field(None, description="PUT CORS URL for creating bucket")


class FlowStorage(BaseModel):
    """Flow storage response"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    pre: Optional[List[PreAction]] = Field(None, description="Actions that need to be taken before the media object can be written")
    media_objects: List[MediaObject] = Field(..., description="List of information for identifying and uploading media objects")


class FlowStoragePost(BaseModel):
    """Flow storage allocation request"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    limit: Optional[int] = Field(None, description="Limit the number of storage segments in each response page")
    object_ids: Optional[List[str]] = Field(None, description="Array of object_ids to use")
    storage_id: Optional[str] = Field(None, description="The storage backend to allocate storage in")
    
    @field_validator('storage_id')
    @classmethod
    def validate_storage_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_tams_uuid(v)
        return v
