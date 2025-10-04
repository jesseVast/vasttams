from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Annotated
from pydantic import BaseModel, Field, RootModel, UUID4, field_validator, field_serializer
import uuid
import re


def validate_content_format(v: str) -> str:
    """Validate content format URN"""
    VALID_FORMATS = [
        "urn:x-nmos:format:video",
        "urn:x-tam:format:image", 
        "urn:x-nmos:format:audio",
        "urn:x-nmos:format:data",
        "urn:x-nmos:format:multi"
    ]
    
    if not isinstance(v, str):
        raise ValueError('Content format must be a string')
    
    if v not in VALID_FORMATS:
        raise ValueError(f'Invalid content format. Must be one of: {VALID_FORMATS}')
    
    return v


def validate_mime_type(v: str) -> str:
    """Validate MIME type format"""
    if not isinstance(v, str):
        raise ValueError('MIME type must be a string')
    
    pattern = r'.*/.*'
    if not re.match(pattern, v):
        raise ValueError('Invalid MIME type format. Must be in format: type/subtype')
    
    return v


def validate_time_range(v: str) -> str:
    """Validate time range format"""
    if not isinstance(v, str):
        raise ValueError('Time range must be a string')
    
    pattern = r'^(\[|\()?(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?(_(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?)?(\]|\))?$'
    if not re.match(pattern, v):
        raise ValueError('Invalid time range format')
    
    return v


# Type aliases with validation
ContentFormat = Annotated[str, field_validator('*')(validate_content_format)]
MimeType = Annotated[str, field_validator('*')(validate_mime_type)]
TimeRange = Annotated[str, field_validator('*')(validate_time_range)]


class Tags(RootModel[Dict[str, str]]):
    """Tags model - flexible key-value pairs using Pydantic v2 RootModel"""
    
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
    
    def update(self, other_dict: Dict[str, str]):
        self.root.update(other_dict)


class CollectionItem(BaseModel):
    """Collection item for source collections"""
    id: UUID4
    label: Optional[str] = None


class Source(BaseModel):
    """Source model as defined in TAMS API"""
    id: UUID4
    format: ContentFormat
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    source_collection: Optional[List[CollectionItem]] = None
    collected_by: Optional[List[UUID4]] = None
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


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
    tags: Optional[Tags] = None  # Add tags field
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None


class SegmentTag(BaseModel):
    """Segment tag model"""
    segment_id: str
    tags: Tags


class VideoFlow(BaseModel):
    """Video flow model"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:video")
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
    max_bit_rate: Optional[int] = None
    avg_bit_rate: Optional[int] = None
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class AudioFlow(BaseModel):
    """Audio flow model"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:audio")
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
    max_bit_rate: Optional[int] = None
    avg_bit_rate: Optional[int] = None
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class DataFlow(BaseModel):
    """Data flow model"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:data")
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
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class ImageFlow(BaseModel):
    """Image flow model"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-tam:format:image")
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
    max_bit_rate: Optional[int] = None
    avg_bit_rate: Optional[int] = None
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class MultiFlow(BaseModel):
    """Multi flow model"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:multi")
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
    flow_collection: List[UUID4]
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


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
    # Ownership fields for TAMS API v6.0 compliance
    owner_id: Optional[str] = None
    created_by: Optional[str] = None
    created: Optional[datetime] = None


class WebhookPost(BaseModel):
    """Webhook registration request"""
    url: str
    api_key_name: str
    api_key_value: str
    events: List[str]
    # Ownership fields for TAMS API v6.0 compliance
    owner_id: Optional[str] = None
    created_by: Optional[str] = None


class FlowStoragePost(BaseModel):
    """Flow storage allocation request"""
    limit: Optional[int] = None
    object_ids: Optional[List[str]] = None


class StorageLocation(BaseModel):
    """Storage location for media objects"""
    object_id: str
    put_url: str
    bucket_put_url: Optional[str] = None


class FlowStorage(BaseModel):
    """Flow storage response"""
    storage_locations: List[StorageLocation]


class Object(BaseModel):
    """Media object information"""
    object_id: str
    flow_references: List[Dict[str, Any]]
    size: Optional[int] = None
    created: Optional[datetime] = None
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'deleted_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class DeletionRequest(BaseModel):
    """Flow deletion request"""
    request_id: str
    flow_id: UUID4
    timerange: TimeRange
    status: str  # "pending", "in_progress", "completed", "failed"
    created: datetime
    updated: Optional[datetime] = None
    
    @field_serializer('created', 'updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


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
    # Tag filtering support
    tag_filters: Optional[Dict[str, str]] = None  # tag.{name} = value
    tag_exists_filters: Optional[Dict[str, bool]] = None  # tag_exists.{name} = true/false


class FlowFilters(BaseModel):
    """Flow query filters"""
    source_id: Optional[UUID4] = None
    timerange: Optional[TimeRange] = None
    format: Optional[ContentFormat] = None
    codec: Optional[MimeType] = None
    label: Optional[str] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    # Tag filtering support
    tag_filters: Optional[Dict[str, str]] = None  # tag.{name} = value
    tag_exists_filters: Optional[Dict[str, bool]] = None  # tag_exists.{name} = true/false


class FlowDetailFilters(BaseModel):
    """Flow detail query filters"""
    include_timerange: bool = False
    timerange: Optional[TimeRange] = None


class SegmentFilters(BaseModel):
    """Segment query filters"""
    timerange: Optional[TimeRange] = None
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    # Tag filtering support
    tag_filters: Optional[Dict[str, str]] = None  # tag.{name} = value
    tag_exists_filters: Optional[Dict[str, bool]] = None  # tag_exists.{name} = true/false


# Additional models for TAMS Ingest Client compatibility
class VideoAnalysisResult(BaseModel):
    """Video analysis result from FFmpeg."""
    duration: float = Field(..., description="Video duration in seconds")
    width: int = Field(..., description="Video width")
    height: int = Field(..., description="Video height")
    fps: float = Field(..., description="Frames per second")
    bitrate: int = Field(..., description="Video bitrate in bps")
    audio_bitrate: Optional[int] = Field(default=None, description="Audio bitrate in bps")
    video_codec: str = Field(..., description="Video codec")
    audio_codec: Optional[str] = Field(default=None, description="Audio codec")
    file_size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Container format")
    
    # Additional metadata
    has_audio: bool = Field(default=False, description="Whether video has audio track")
    has_video: bool = Field(default=True, description="Whether file has video track")
    color_space: Optional[str] = Field(default=None, description="Color space")
    pixel_format: Optional[str] = Field(default=None, description="Pixel format")
    
    # Timestamps
    analyzed_at: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")


class TAMSSegment(BaseModel):
    """TAMS segment model for ingest client compatibility."""
    object_id: str = Field(..., description="Segment object ID")
    timerange: str = Field(..., description="Time range in ISO format")
    ts_offset: Optional[str] = Field(default=None, description="Timestamp offset")
    last_duration: Optional[str] = Field(default=None, description="Last duration")
    sample_offset: Optional[int] = Field(default=None, description="Sample offset")
    sample_count: Optional[int] = Field(default=None, description="Sample count")
    key_frame_count: Optional[int] = Field(default=None, description="Key frame count")
    
    # URLs
    get_urls: List[Dict[str, str]] = Field(default_factory=list, description="GET URLs for segment")
    
    # Metadata
    file_path: Optional[str] = Field(default=None, description="Local file path")
    s3_key: Optional[str] = Field(default=None, description="S3 object key")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    duration: Optional[float] = Field(default=None, description="Segment duration in seconds")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class VideoIngestRequest(BaseModel):
    """Video ingestion request."""
    video_path: str = Field(..., description="Path to video file")
    source_config: Optional[Dict[str, Any]] = Field(default=None, description="Source configuration")
    flow_config: Optional[Dict[str, Any]] = Field(default=None, description="Flow configuration")
    
    # Processing options
    chunk_duration: int = Field(default=30, description="Chunk duration in seconds")
    segment_overlap: int = Field(default=0, description="Segment overlap in seconds")
    auto_create_source: bool = Field(default=True, description="Auto-create source if not exists")
    auto_create_flow: bool = Field(default=True, description="Auto-create flow if not exists")
    
    # S3 integration
    upload_to_s3: bool = Field(default=True, description="Upload segments to S3")
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket for uploads")
    s3_prefix: Optional[str] = Field(default=None, description="S3 prefix for uploads")
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class VideoIngestResult(BaseModel):
    """Video ingestion result."""
    success: bool = Field(..., description="Whether ingestion was successful")
    source_id: Optional[str] = Field(default=None, description="Created source ID")
    flow_id: Optional[str] = Field(default=None, description="Created flow ID")
    segments: List[TAMSSegment] = Field(default_factory=list, description="Created segments")
    
    # Processing statistics
    total_duration: float = Field(..., description="Total video duration in seconds")
    segment_count: int = Field(default=0, description="Number of segments created")
    total_file_size: int = Field(default=0, description="Total file size in bytes")
    processing_time: float = Field(..., description="Processing time in seconds")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    
    # Timestamps
    started_at: datetime = Field(..., description="Processing start time")
    completed_at: datetime = Field(..., description="Processing completion time")
    
    # Metadata
    video_analysis: Optional[VideoAnalysisResult] = Field(default=None, description="Video analysis result")
    source_config: Optional[Dict[str, Any]] = Field(default=None, description="Source configuration used")
    flow_config: Optional[Dict[str, Any]] = Field(default=None, description="Flow configuration used")


# Additional models for TAMS Ingest Client compatibility
from enum import Enum
from pathlib import Path
from .constants import TAMS_FORMATS, SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS


class SourceType(str, Enum):
    """Source type enumeration."""
    FILE = "file"
    STREAM = "stream"
    CAMERA = "camera"


class FlowType(str, Enum):
    """Flow type enumeration."""
    VIDEO = "video"
    AUDIO = "audio"
    MULTIMEDIA = "multimedia"


class TAMSSourceConfig(BaseModel):
    """TAMS source configuration."""
    label: str = Field(..., description="Source label")
    description: Optional[str] = Field(default=None, description="Source description")
    format: str = Field(default=TAMS_FORMATS["VIDEO"], description="Source format")
    tags: Dict[str, str] = Field(default_factory=dict, description="Source tags")
    source_type: SourceType = Field(default=SourceType.FILE, description="Source type")
    
    # File-specific settings
    file_path: Optional[str] = Field(default=None, description="File path for file sources")
    stream_url: Optional[str] = Field(default=None, description="Stream URL for stream sources")
    
    # Auto-detection settings
    auto_detect_format: bool = Field(default=True, description="Auto-detect format from file")
    auto_detect_metadata: bool = Field(default=True, description="Auto-detect metadata from file")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in TAMS_FORMATS.values():
            raise ValueError(f'format must be one of {list(TAMS_FORMATS.values())}')
        return v


class TAMSFlowConfig(BaseModel):
    """TAMS flow configuration."""
    source_id: str = Field(..., description="Source ID this flow belongs to")
    label: str = Field(..., description="Flow label")
    description: Optional[str] = Field(default=None, description="Flow description")
    format: str = Field(default=TAMS_FORMATS["VIDEO"], description="Flow format")
    codec: str = Field(default="h264", description="Video codec")
    audio_codec: Optional[str] = Field(default="aac", description="Audio codec")
    tags: Dict[str, str] = Field(default_factory=dict, description="Flow tags")
    flow_type: FlowType = Field(default=FlowType.VIDEO, description="Flow type")
    
    # Video parameters
    frame_width: Optional[int] = Field(default=None, description="Frame width")
    frame_height: Optional[int] = Field(default=None, description="Frame height")
    frame_rate: Optional[float] = Field(default=None, description="Frame rate")
    bitrate: Optional[str] = Field(default=None, description="Video bitrate")
    audio_bitrate: Optional[str] = Field(default=None, description="Audio bitrate")
    
    # Auto-detection settings
    auto_detect_codec: bool = Field(default=True, description="Auto-detect codec from source")
    auto_detect_resolution: bool = Field(default=True, description="Auto-detect resolution from source")
    auto_detect_framerate: bool = Field(default=True, description="Auto-detect framerate from source")
    auto_detect_bitrate: bool = Field(default=True, description="Auto-detect bitrate from source")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in TAMS_FORMATS.values():
            raise ValueError(f'format must be one of {list(TAMS_FORMATS.values())}')
        return v


# Updated VideoIngestRequest and VideoIngestResult with proper types
class VideoIngestRequestUpdated(BaseModel):
    """Video ingestion request with proper config types."""
    video_path: str = Field(..., description="Path to video file")
    source_config: Optional[TAMSSourceConfig] = Field(default=None, description="Source configuration")
    flow_config: Optional[TAMSFlowConfig] = Field(default=None, description="Flow configuration")
    
    # Processing options
    chunk_duration: int = Field(default=30, description="Chunk duration in seconds")
    segment_overlap: int = Field(default=0, description="Segment overlap in seconds")
    auto_create_source: bool = Field(default=True, description="Auto-create source if not exists")
    auto_create_flow: bool = Field(default=True, description="Auto-create flow if not exists")
    
    # S3 integration
    upload_to_s3: bool = Field(default=True, description="Upload segments to S3")
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket for uploads")
    s3_prefix: Optional[str] = Field(default=None, description="S3 prefix for uploads")
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class VideoIngestResultUpdated(BaseModel):
    """Video ingestion result with proper config types."""
    success: bool = Field(..., description="Whether ingestion was successful")
    source_id: Optional[str] = Field(default=None, description="Created source ID")
    flow_id: Optional[str] = Field(default=None, description="Created flow ID")
    segments: List[TAMSSegment] = Field(default_factory=list, description="Created segments")
    
    # Processing statistics
    total_duration: float = Field(..., description="Total video duration in seconds")
    segment_count: int = Field(default=0, description="Number of segments created")
    total_file_size: int = Field(default=0, description="Total file size in bytes")
    processing_time: float = Field(..., description="Processing time in seconds")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    
    # Timestamps
    started_at: datetime = Field(..., description="Processing start time")
    completed_at: datetime = Field(..., description="Processing completion time")
    
    # Metadata
    video_analysis: Optional[VideoAnalysisResult] = Field(default=None, description="Video analysis result")
    source_config: Optional[TAMSSourceConfig] = Field(default=None, description="Source configuration used")
    flow_config: Optional[TAMSFlowConfig] = Field(default=None, description="Flow configuration used") 