"""
TAMS Client Models

Pydantic models for request/response validation.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime


class Tags(BaseModel):
    """Tags model - flexible key-value pairs."""
    root: Dict[str, str] = Field(default_factory=dict)
    
    def __getitem__(self, key: str) -> str:
        return self.root[key]
    
    def __setitem__(self, key: str, value: str):
        self.root[key] = value
    
    def __contains__(self, key: str) -> bool:
        return key in self.root
    
    def get(self, key: str, default=None):
        return self.root.get(key, default)
    
    def keys(self):
        return self.root.keys()
    
    def values(self):
        return self.root.values()
    
    def items(self):
        return self.root.items()


class Source(BaseModel):
    """Source model."""
    id: str
    format: str
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Dict[str, str]] = None


class FlowCore(BaseModel):
    """Base flow model."""
    id: str
    source_id: str
    format: str
    codec: str
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    metadata_updated: Optional[datetime] = None
    segments_updated: Optional[datetime] = None
    tags: Optional[Dict[str, str]] = None
    read_only: Optional[bool] = False


class VideoFlow(FlowCore):
    """Video flow model."""
    essence_parameters: Dict[str, Any] = Field(default_factory=dict)


class AudioFlow(FlowCore):
    """Audio flow model."""
    essence_parameters: Dict[str, Any] = Field(default_factory=dict)


class FlowSegment(BaseModel):
    """Flow segment model."""
    object_id: str
    timerange: Dict[str, Any]
    ts_offset: Optional[Dict[str, Any]] = None
    last_duration: Optional[Dict[str, Any]] = None
    sample_offset: Optional[int] = None
    sample_count: Optional[int] = None
    get_urls: Optional[List[Dict[str, Any]]] = None
    key_frame_count: Optional[int] = None


class Object(BaseModel):
    """Media object model."""
    id: str
    referenced_by_flows: List[str]
    first_referenced_by_flow: Optional[str] = None
    timerange: Dict[str, Any]
    size: Optional[int] = None
    created: Optional[datetime] = None


class StorageBackend(BaseModel):
    """Storage backend model."""
    id: str
    label: str
    store_type: str
    provider: str
    store_product: str
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    endpoint_url: Optional[str] = None
    bucket_name: Optional[str] = None
    root_path: Optional[str] = None
    use_ssl: Optional[bool] = None
    default_storage: Optional[bool] = None

