"""
TAMS Flow Segment Models

This module contains models related to Flow Segments in the TAMS API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..common.models import validate_tams_uuid, TimeRange, Timestamp


class GetUrl(BaseModel):
    """GetUrl model extending storage-backend.json schema"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # storage-backend.json fields
    store_type: str = Field(default="http_object_store", description="The generic store type")
    provider: str = Field(..., description="The cloud provider of the storage")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    store_product: str = Field(..., description="The storage product name")
    
    # Additional required fields from flow-segment.json
    url: str = Field(..., description="A URL to which a GET request can be made to directly retrieve the contents of the segment")
    storage_id: str = Field(..., description="Storage backend identifier")
    presigned: Optional[bool] = Field(None, description="If true, this URL is pre-signed")
    label: Optional[str] = Field(None, description="Label identifying this URL")
    controlled: Optional[bool] = Field(None, description="If true, this URL is on a storage backend controlled by this service instance")
    
    @field_validator('storage_id')
    @classmethod
    def validate_storage_id(cls, v: str) -> str:
        return validate_tams_uuid(v)


class FlowSegment(BaseModel):
    """Flow segment model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    object_id: str = Field(..., description="The object store identifier for the media object")
    timerange: TimeRange = Field(..., description="The timerange for the samples contained in the segment")
    ts_offset: Optional[Timestamp] = Field(None, description="Timestamp offset between sample timestamps and segment timestamps")
    last_duration: Optional[Timestamp] = Field(None, description="Difference between exclusive end of timerange and last sample timestamp")
    sample_offset: Optional[int] = Field(None, description="Start of segment as count of samples from start of object")
    sample_count: Optional[int] = Field(None, description="Count of samples in the segment")
    get_urls: Optional[List[GetUrl]] = Field(None, description="List of URLs for direct segment retrieval")
    key_frame_count: Optional[int] = Field(None, description="Number of key frames in the segment")
