from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
import uuid
import re


class UUID(str):
    """UUID type with validation"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError('UUID must be a string')
        
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid UUID format')
        
        return v


class ContentFormat(str):
    """Content format URN with validation"""
    
    VALID_FORMATS = [
        "urn:x-nmos:format:video",
        "urn:x-tam:format:image", 
        "urn:x-nmos:format:audio",
        "urn:x-nmos:format:data",
        "urn:x-nmos:format:multi"
    ]
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError('Content format must be a string')
        
        if v not in cls.VALID_FORMATS:
            raise ValueError(f'Invalid content format. Must be one of: {cls.VALID_FORMATS}')
        
        return v


class MimeType(str):
    """MIME type with validation"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError('MIME type must be a string')
        
        pattern = r'.*/.*'
        if not re.match(pattern, v):
            raise ValueError('Invalid MIME type format. Must be in format: type/subtype')
        
        return v


class TimeRange(str):
    """Time range with validation"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError('Time range must be a string')
        
        pattern = r'^(\[|\()?(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?(_(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?)?(\]|\))?$'
        if not re.match(pattern, v):
            raise ValueError('Invalid time range format')
        
        return v


class Tags(BaseModel):
    """Tags model - flexible key-value pairs"""
    __root__: Dict[str, str] = Field(default_factory=dict)
    
    def __getitem__(self, key: str) -> str:
        return self.__root__[key]
    
    def __setitem__(self, key: str, value: str):
        self.__root__[key] = value
    
    def __contains__(self, key: str) -> bool:
        return key in self.__root__


class CollectionItem(BaseModel):
    """Collection item for source collections"""
    id: UUID
    label: Optional[str] = None


class Source(BaseModel):
    """Source model as defined in TAMS API"""
    id: UUID
    format: ContentFormat
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    source_collection: Optional[List[CollectionItem]] = None
    collected_by: Optional[List[UUID]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class GetUrl(BaseModel):
    """Get URL for flow segments"""
    url: str
    label: Optional[str] = None


class FlowSegment(BaseModel):
    """Flow segment model"""
    object_id: str
    timerange: TimeRange
    ts_offset: Optional[str] = None  # Timestamp format
    last_duration: Optional[str] = None  # Timestamp format
    sample_offset: Optional[int] = None
    sample_count: Optional[int] = None
    get_urls: Optional[List[GetUrl]] = None
    key_frame_count: Optional[int] = None


class VideoFlow(BaseModel):
    """Video flow model"""
    id: UUID
    source_id: UUID
    format: ContentFormat = ContentFormat("urn:x-nmos:format:video")
    codec: MimeType
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    frame_width: int
    frame_height: int
    frame_rate: str  # Timestamp format
    interlace_mode: Optional[str] = None
    color_sampling: Optional[str] = None
    color_space: Optional[str] = None
    transfer_characteristics: Optional[str] = None
    color_primaries: Optional[str] = None
    container: Optional[str] = None
    read_only: Optional[bool] = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AudioFlow(BaseModel):
    """Audio flow model"""
    id: UUID
    source_id: UUID
    format: ContentFormat = ContentFormat("urn:x-nmos:format:audio")
    codec: MimeType
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    sample_rate: int
    bits_per_sample: int
    channels: int
    container: Optional[str] = None
    read_only: Optional[bool] = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class DataFlow(BaseModel):
    """Data flow model"""
    id: UUID
    source_id: UUID
    format: ContentFormat = ContentFormat("urn:x-nmos:format:data")
    codec: MimeType
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    container: Optional[str] = None
    read_only: Optional[bool] = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ImageFlow(BaseModel):
    """Image flow model"""
    id: UUID
    source_id: UUID
    format: ContentFormat = ContentFormat("urn:x-tam:format:image")
    codec: MimeType
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    frame_width: int
    frame_height: int
    container: Optional[str] = None
    read_only: Optional[bool] = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MultiFlow(BaseModel):
    """Multi flow model"""
    id: UUID
    source_id: UUID
    format: ContentFormat = ContentFormat("urn:x-nmos:format:multi")
    codec: MimeType
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    container: Optional[str] = None
    read_only: Optional[bool] = False
    flow_collection: List[UUID]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# Union type for all flow types
Flow = Union[VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow]


class MediaStore(BaseModel):
    """Media store configuration"""
    type: str = "http_object_store"


class EventStreamMechanism(BaseModel):
    """Event stream mechanism"""
    name: str
    description: Optional[str] = None


class Service(BaseModel):
    """Service information model"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: str = "urn:x-tams:service:api"
    api_version: str = "6.0"
    service_version: Optional[str] = None
    media_store: MediaStore
    event_stream_mechanisms: Optional[List[EventStreamMechanism]] = None


class Webhook(BaseModel):
    """Webhook configuration"""
    url: str
    api_key_name: str
    api_key_value: Optional[str] = None
    events: List[str]


class WebhookPost(BaseModel):
    """Webhook registration request"""
    url: str
    api_key_name: str
    api_key_value: str
    events: List[str]


class FlowStoragePost(BaseModel):
    """Flow storage allocation request"""
    limit: Optional[int] = None
    object_ids: Optional[List[str]] = None


class StorageLocation(BaseModel):
    """Storage location for media objects"""
    object_id: str
    put_url: str
    bucket_put_url: Optional[str] = None
    cors_put_url: Optional[str] = None


class FlowStorage(BaseModel):
    """Flow storage response"""
    storage_locations: List[StorageLocation]


class Object(BaseModel):
    """Media object information"""
    object_id: str
    flow_references: List[Dict[str, Any]]
    size: Optional[int] = None
    created: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class DeletionRequest(BaseModel):
    """Flow deletion request"""
    request_id: str
    flow_id: UUID
    timerange: TimeRange
    status: str  # "pending", "in_progress", "completed", "failed"
    created: datetime
    updated: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class DeletionRequestsList(BaseModel):
    """List of deletion requests"""
    requests: List[DeletionRequest]


# Paging models
class PagingInfo(BaseModel):
    """Paging information"""
    limit: Optional[int] = None
    next_key: Optional[str] = None


# Response models
class ServiceResponse(BaseModel):
    """Service response wrapper"""
    data: Service


class SourcesResponse(BaseModel):
    """Sources list response"""
    data: List[Source]
    paging: Optional[PagingInfo] = None


class FlowsResponse(BaseModel):
    """Flows list response"""
    data: List[Flow]
    paging: Optional[PagingInfo] = None


class WebhooksResponse(BaseModel):
    """Webhooks list response"""
    data: List[Webhook]


class DeletionRequestsResponse(BaseModel):
    """Deletion requests list response"""
    data: DeletionRequestsList


# Query parameter models
class SourceFilters(BaseModel):
    """Source query filters"""
    label: Optional[str] = None
    format: Optional[ContentFormat] = None
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)


class FlowFilters(BaseModel):
    """Flow query filters"""
    source_id: Optional[UUID] = None
    timerange: Optional[TimeRange] = None
    format: Optional[ContentFormat] = None
    codec: Optional[MimeType] = None
    label: Optional[str] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)


class FlowDetailFilters(BaseModel):
    """Flow detail query filters"""
    include_timerange: bool = False
    timerange: Optional[TimeRange] = None 