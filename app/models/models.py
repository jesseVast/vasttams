from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Annotated
from pydantic import BaseModel, Field, RootModel, UUID4, field_validator, field_serializer, validator
import uuid
import re
from enum import Enum


class PathTemplateType(str, Enum):
    """Path template types for hierarchical organization"""
    TIME_BASED = "time_based"  # year/month/day/hour
    SOURCE_BASED = "source_based"  # source_id/flow_id/segment_id
    HYBRID = "hybrid"  # source_id/year/month/day/flow_id/segment_id
    CUSTOM = "custom"  # custom template with placeholders
    FLAT = "flat"  # no hierarchy, just segment_id


class HierarchicalPath(BaseModel):
    """Hierarchical path configuration for media storage"""
    template_type: PathTemplateType = Field(default=PathTemplateType.HYBRID)
    custom_template: Optional[str] = Field(None, description="Custom path template with placeholders")
    include_source: bool = Field(default=True, description="Include source ID in path")
    include_flow: bool = Field(default=True, description="Include flow ID in path")
    include_time: bool = Field(default=True, description="Include time-based hierarchy")
    include_segment: bool = Field(default=True, description="Include segment ID in path")
    time_granularity: str = Field(default="day", description="Time granularity: hour, day, month, year")
    max_depth: int = Field(default=6, description="Maximum path depth")
    separator: str = Field(default="/", description="Path separator character")
    
    @field_validator('custom_template')
    def validate_custom_template(cls, v):
        if v is not None:
            # Validate custom template has valid placeholders
            valid_placeholders = {
                '{source_id}', '{flow_id}', '{segment_id}', 
                '{year}', '{month}', '{day}', '{hour}',
                '{timestamp}', '{format}', '{codec}'
            }
            placeholders = re.findall(r'\{[^}]+\}', v)
            invalid_placeholders = [p for p in placeholders if p not in valid_placeholders]
            if invalid_placeholders:
                raise ValueError(f'Invalid placeholders in custom template: {invalid_placeholders}')
        return v
    
    @field_validator('time_granularity')
    def validate_time_granularity(cls, v):
        valid_granularities = ['hour', 'day', 'month', 'year']
        if v not in valid_granularities:
            raise ValueError(f'Invalid time granularity. Must be one of: {valid_granularities}')
        return v


class PathSegment(BaseModel):
    """Individual path segment with metadata"""
    name: str
    value: str
    type: str  # 'source', 'flow', 'time', 'segment', 'custom'
    metadata: Optional[Dict[str, Any]] = None


class HierarchicalPathResult(BaseModel):
    """Result of hierarchical path generation"""
    full_path: str
    segments: List[PathSegment]
    template_used: str
    normalized: bool = False
    validation_errors: Optional[List[str]] = None


# Enhanced TAMS-specific validators
def validate_content_format(v: str) -> str:
    """Validate content format URN according to TAMS specification"""
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
    """Validate MIME type format according to TAMS specification"""
    if not isinstance(v, str):
        raise ValueError('MIME type must be a string')
    
    pattern = r'^[a-zA-Z0-9!#$&\-\^_]*/[a-zA-Z0-9!#$&\-\^_]*(\+[a-zA-Z0-9!#$&\-\^_]*)?$'
    if not re.match(pattern, v):
        raise ValueError('Invalid MIME type format. Must be in format: type/subtype or type/subtype+format')
    
    return v


def validate_tams_uuid(v: str) -> str:
    """Validate UUID format according to TAMS specification"""
    if not isinstance(v, str):
        raise ValueError('UUID must be a string')
    
    # TAMS UUID pattern: 8-4-4-4-12 hexadecimal characters
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    if not re.match(pattern, v):
        raise ValueError('Invalid UUID format. Must be a valid TAMS UUID')
    
    return v


def validate_tams_timestamp(v: str) -> str:
    """Validate timestamp format according to TAMS specification"""
    if not isinstance(v, str):
        raise ValueError('Timestamp must be a string')
    
    # TAMS timestamp pattern: ISO 8601 with optional timezone
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
    if not re.match(pattern, v):
        raise ValueError('Invalid timestamp format. Must be ISO 8601 format')
    
    return v


def validate_flow_collection_structure(v: Dict[str, Any]) -> Dict[str, Any]:
    """Validate flow collection structure according to TAMS specification"""
    if not isinstance(v, dict):
        raise ValueError('Flow collection must be a dictionary')
    
    required_fields = ['id', 'label', 'description']
    for field in required_fields:
        if field not in v:
            raise ValueError(f'Flow collection missing required field: {field}')
    
    if not isinstance(v['id'], str):
        raise ValueError('Flow collection id must be a string')
    
    if not isinstance(v['label'], str):
        raise ValueError('Flow collection label must be a string')
    
    if not isinstance(v['description'], str):
        raise ValueError('Flow collection description must be a string')
    
    return v


def validate_source_collection_structure(v: Dict[str, Any]) -> Dict[str, Any]:
    """Validate source collection structure according to TAMS specification"""
    if not isinstance(v, dict):
        raise ValueError('Source collection must be a dictionary')
    
    required_fields = ['id', 'label', 'description']
    for field in required_fields:
        if field not in v:
            raise ValueError(f'Source collection missing required field: {field}')
    
    if not isinstance(v['id'], str):
        raise ValueError('Source collection id must be a string')
    
    if not isinstance(v['label'], str):
        raise ValueError('Source collection label must be a string')
    
    if not isinstance(v['description'], str):
        raise ValueError('Source collection description must be a string')
    
    return v


def validate_uuid_list(v: List[str]) -> List[str]:
    """Validate list of UUIDs according to TAMS specification"""
    if not isinstance(v, list):
        raise ValueError('UUID list must be a list')
    
    for uuid_str in v:
        validate_tams_uuid(uuid_str)
    
    return v


def validate_url_list(v: List[str]) -> List[str]:
    """Validate list of URLs according to TAMS specification"""
    if not isinstance(v, list):
        raise ValueError('URL list must be a list')
    
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    for url in v:
        if not isinstance(url, str) or not re.match(url_pattern, url):
            raise ValueError(f'Invalid URL format: {url}')
    
    return v


# Type aliases with validation
ContentFormat = Annotated[str, Field(description="Content format URN", validation_alias="format")]
MimeType = Annotated[str, Field(description="MIME type", validation_alias="mime_type")]
TimeRange = Annotated[str, Field(description="Time range", validation_alias="timerange")]
HierarchicalPathStr = Annotated[str, Field(description="Hierarchical path", validation_alias="path")]


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
    format: str = Field(description="Content format URN")
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    metadata_updated: Optional[datetime] = None
    tags: Optional[Tags] = None
    source_collection: Optional[List[CollectionItem]] = None
    collected_by: Optional[List[UUID4]] = None
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        return validate_content_format(v)
    
    @field_validator('source_collection')
    @classmethod
    def validate_source_collection(cls, v: Optional[List[CollectionItem]]) -> Optional[List[CollectionItem]]:
        if v is not None:
            for item in v:
                if not isinstance(item, CollectionItem):
                    raise ValueError('Source collection items must be CollectionItem instances')
        return v
    
    # Note: Pydantic automatically validates UUID4 types, so no custom validator needed
    
    @field_serializer('created', 'metadata_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class GetUrl(BaseModel):
    """TAMS-compliant GetUrl model extending storage-backend.json schema"""
    
    # storage-backend.json fields
    store_type: str = Field(default="http_object_store", description="The generic store type")
    provider: str = Field(..., description="The cloud (or other) provider of the storage")
    region: str = Field(..., description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region this storage backend resides")
    store_product: str = Field(..., description="The storage product name")
    
    # Additional required fields from flow-segment.json
    url: str = Field(..., description="A URL to which a GET request can be made to directly retrieve the contents of the segment")
    storage_id: str = Field(..., description="Storage backend identifier", pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    presigned: bool = Field(default=True, description="If true, this URL is pre-signed")
    label: Optional[str] = Field(None, description="Label identifying this URL")
    controlled: bool = Field(default=True, description="If true, this URL is on a storage backend controlled by this service instance")


class FlowSegment(BaseModel):
    """Flow segment model - TAMS compliant"""
    id: str = Field(..., description="The object store identifier for the media object")  # Changed from object_id to id for TAMS compliance
    timerange: str = Field(description="Time range")
    ts_offset: Optional[str] = Field(None, description="Timestamp offset between sample timestamps and segment timestamps")  # Fixed description
    last_duration: Optional[str] = Field(None, description="Difference between exclusive end of timerange and last sample timestamp")  # Fixed description
    sample_offset: Optional[int] = Field(None, description="Start of segment as count of samples from start of object")
    sample_count: Optional[int] = Field(None, description="Count of samples in the segment")
    get_urls: Optional[List[GetUrl]] = Field(None, description="List of URLs for direct segment retrieval")
    key_frame_count: Optional[int] = Field(None, description="Number of key frames in the segment")
    # Storage path field - stores the actual S3 object key used for storage
    storage_path: Optional[str] = Field(None, description="The actual S3 object key where data is stored")
    
    @field_validator('timerange')
    @classmethod
    def validate_timerange(cls, v: str) -> str:
        # TAMS timerange validation - simplified for now, can be enhanced later
        if not isinstance(v, str):
            raise ValueError('Timerange must be a string')
        return v


class VideoFlow(BaseModel):
    """Video flow model - TAMS compliant"""
    id: UUID4
    source_id: UUID4
    format: str = Field(default="urn:x-nmos:format:video", description="Content format URN")
    codec: str = Field(description="MIME type identification of the coding used for the flow content")
    label: Optional[str] = Field(None, description="Freeform string label for the flow")
    description: Optional[str] = Field(None, description="Freeform text describing the flow")
    created_by: Optional[str] = Field(None, description="Entity that created the flow")
    updated_by: Optional[str] = Field(None, description="Entity that updated the flow metadata most recently")
    created: Optional[datetime] = Field(None, description="Date-time the flow was created")
    metadata_updated: Optional[datetime] = Field(None, description="Date-time the flow metadata was updated")  # Changed from updated to metadata_updated for TAMS compliance
    segments_updated: Optional[datetime] = Field(None, description="Date-time the flow segments were updated")  # Added missing required field
    tags: Optional[Tags] = Field(None, description="Flow tags")
    
    # TAMS required fields
    metadata_version: Optional[str] = Field(None, description="Flow metadata version for change tracking")  # Added missing required field
    generation: Optional[int] = Field(None, ge=0, description="Number of lossy encodings the flow content has been through")  # Added missing required field
    segment_duration: Optional[Dict[str, int]] = Field(None, description="Target flow segment duration as numerator/denominator")  # Added missing required field
    
    # Video-specific fields
    frame_width: int = Field(gt=0, description="Frame width must be positive")
    frame_height: int = Field(gt=0, description="Frame height must be positive")
    frame_rate: str = Field(description="Frame rate in timestamp format")  # Kept for backward compatibility
    interlace_mode: Optional[str] = Field(None, description="Interlacing mode")
    color_sampling: Optional[str] = Field(None, description="Color sampling format")
    color_space: Optional[str] = Field(None, description="Color space")
    transfer_characteristics: Optional[str] = Field(None, description="Transfer characteristics")
    color_primaries: Optional[str] = Field(None, description="Color primaries")
    container: Optional[str] = Field(None, description="Container MIME type for flow segments")
    read_only: Optional[bool] = Field(False, description="Whether flow is read-only")
    max_bit_rate: Optional[int] = Field(None, ge=0, description="Maximum bit rate in 1000 bits/second")
    avg_bit_rate: Optional[int] = Field(None, ge=0, description="Average bit rate in 1000 bits/second")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        return validate_content_format(v)
    
    @field_validator('codec')
    @classmethod
    def validate_codec(cls, v: str) -> str:
        return validate_mime_type(v)
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class AudioFlow(BaseModel):
    """Audio flow model - TAMS compliant"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:audio", description="Content format URN")
    codec: MimeType = Field(description="MIME type identification of the coding used for the flow content")
    label: Optional[str] = Field(None, description="Freeform string label for the flow")
    description: Optional[str] = Field(None, description="Freeform text describing the flow")
    created_by: Optional[str] = Field(None, description="Entity that created the flow")
    updated_by: Optional[str] = Field(None, description="Entity that updated the flow metadata most recently")
    created: Optional[datetime] = Field(None, description="Date-time the flow was created")
    metadata_updated: Optional[datetime] = Field(None, description="Date-time the flow metadata was updated")  # Changed from updated to metadata_updated for TAMS compliance
    segments_updated: Optional[datetime] = Field(None, description="Date-time the flow segments were updated")  # Added missing required field
    tags: Optional[Tags] = Field(None, description="Flow tags")
    
    # TAMS required fields
    metadata_version: Optional[str] = Field(None, description="Flow metadata version for change tracking")  # Added missing required field
    generation: Optional[int] = Field(None, ge=0, description="Number of lossy encodings the flow content has been through")  # Added missing required field
    segment_duration: Optional[Dict[str, int]] = Field(None, description="Target flow segment duration as numerator/denominator")  # Added missing required field
    
    # Audio-specific fields
    sample_rate: int = Field(gt=0, description="Audio sample rate in Hz")
    bits_per_sample: int = Field(gt=0, description="Bits per audio sample")
    channels: int = Field(gt=0, description="Number of audio channels")
    container: Optional[str] = Field(None, description="Container MIME type for flow segments")
    read_only: Optional[bool] = Field(False, description="Whether flow is read-only")
    max_bit_rate: Optional[int] = Field(None, ge=0, description="Maximum bit rate in 1000 bits/second")
    avg_bit_rate: Optional[int] = Field(None, ge=0, description="Average bit rate in 1000 bits/second")
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class DataFlow(BaseModel):
    """Data flow model - TAMS compliant"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:data", description="Content format URN")
    codec: MimeType = Field(description="MIME type identification of the coding used for the flow content")
    label: Optional[str] = Field(None, description="Freeform string label for the flow")
    description: Optional[str] = Field(None, description="Freeform text describing the flow")
    created_by: Optional[str] = Field(None, description="Entity that created the flow")
    updated_by: Optional[str] = Field(None, description="Entity that updated the flow metadata most recently")
    created: Optional[datetime] = Field(None, description="Date-time the flow was created")
    metadata_updated: Optional[datetime] = Field(None, description="Date-time the flow metadata was updated")  # Changed from updated to metadata_updated for TAMS compliance
    segments_updated: Optional[datetime] = Field(None, description="Date-time the flow segments were updated")  # Added missing required field
    tags: Optional[Tags] = Field(None, description="Flow tags")
    
    # TAMS required fields
    metadata_version: Optional[str] = Field(None, description="Flow metadata version for change tracking")  # Added missing required field
    generation: Optional[int] = Field(None, ge=0, description="Number of lossy encodings the flow content has been through")  # Added missing required field
    segment_duration: Optional[Dict[str, int]] = Field(None, description="Target flow segment duration as numerator/denominator")  # Added missing required field
    
    # Data-specific fields
    container: Optional[str] = Field(None, description="Container MIME type for flow segments")
    read_only: Optional[bool] = Field(False, description="Whether flow is read-only")
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class ImageFlow(BaseModel):
    """Image flow model - TAMS compliant"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-tam:format:image", description="Content format URN")
    codec: MimeType = Field(description="MIME type identification of the coding used for the flow content")
    label: Optional[str] = Field(None, description="Freeform string label for the flow")
    description: Optional[str] = Field(None, description="Freeform text describing the flow")
    created_by: Optional[str] = Field(None, description="Entity that created the flow")
    updated_by: Optional[str] = Field(None, description="Entity that updated the flow metadata most recently")
    created: Optional[datetime] = Field(None, description="Date-time the flow was created")
    metadata_updated: Optional[datetime] = Field(None, description="Date-time the flow metadata was updated")  # Changed from updated to metadata_updated for TAMS compliance
    segments_updated: Optional[datetime] = Field(None, description="Date-time the flow segments were updated")  # Added missing required field
    tags: Optional[Tags] = Field(None, description="Flow tags")
    
    # TAMS required fields
    metadata_version: Optional[str] = Field(None, description="Flow metadata version for change tracking")  # Added missing required field
    generation: Optional[int] = Field(None, ge=0, description="Number of lossy encodings the flow content has been through")  # Added missing required field
    segment_duration: Optional[Dict[str, int]] = Field(None, description="Target flow segment duration as numerator/denominator")  # Added missing required field
    
    # Image-specific fields
    frame_width: int = Field(gt=0, description="Image frame width in pixels")
    frame_height: int = Field(gt=0, description="Image frame height in pixels")
    container: Optional[str] = Field(None, description="Container MIME type for flow segments")
    read_only: Optional[bool] = Field(False, description="Whether flow is read-only")
    max_bit_rate: Optional[int] = Field(None, ge=0, description="Maximum bit rate in 1000 bits/second")
    avg_bit_rate: Optional[int] = Field(None, ge=0, description="Average bit rate in 1000 bits/second")
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class MultiFlow(BaseModel):
    """Multi flow model - TAMS compliant"""
    id: UUID4
    source_id: UUID4
    format: ContentFormat = Field(default="urn:x-nmos:format:multi", description="Content format URN")
    codec: MimeType = Field(description="MIME type identification of the coding used for the flow content")
    label: Optional[str] = Field(None, description="Freeform string label for the flow")
    description: Optional[str] = Field(None, description="Freeform text describing the flow")
    created_by: Optional[str] = Field(None, description="Entity that created the flow")
    updated_by: Optional[str] = Field(None, description="Entity that updated the flow metadata most recently")
    created: Optional[datetime] = Field(None, description="Date-time the flow was created")
    metadata_updated: Optional[datetime] = Field(None, description="Date-time the flow metadata was updated")  # Changed from updated to metadata_updated for TAMS compliance
    segments_updated: Optional[datetime] = Field(None, description="Date-time the flow segments were updated")  # Added missing required field
    tags: Optional[Tags] = Field(None, description="Flow tags")
    
    # TAMS required fields
    metadata_version: Optional[str] = Field(None, description="Flow metadata version for change tracking")  # Added missing required field
    generation: Optional[int] = Field(None, ge=0, description="Number of lossy encodings the flow content has been through")  # Added missing required field
    segment_duration: Optional[Dict[str, int]] = Field(None, description="Target flow segment duration as numerator/denominator")  # Added missing required field
    
    # Multi-specific fields
    flow_collection: Optional[List[str]] = Field(None, description="List of Flow IDs that are collected together by this Flow")  # Added missing required field
    collected_by: Optional[List[str]] = Field(None, description="Flows that reference this Flow to include it in a collection")  # Added missing required field
    container: Optional[str] = Field(None, description="Container MIME type for flow segments")
    read_only: Optional[bool] = Field(False, description="Whether flow is read-only")
    max_bit_rate: Optional[int] = Field(None, ge=0, description="Maximum bit rate in 1000 bits/second")
    avg_bit_rate: Optional[int] = Field(None, ge=0, description="Average bit rate in 1000 bits/second")
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
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
    """Service information model - TAMS compliant"""
    name: Optional[str] = Field(None, description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    type: str = Field(default="urn:x-tams:service:api", description="Service type URN")
    api_version: str = Field(default="7.0", description="TAMS API version")
    service_version: Optional[str] = Field(None, description="Service implementation version")
    media_store: MediaStore = Field(..., description="Media store configuration")
    event_stream_mechanisms: Optional[List[EventStreamMechanism]] = Field(None, description="Available event stream mechanisms")
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if not v.startswith('urn:x-tams:service:'):
            raise ValueError('Service type must start with urn:x-tams:service:')
        return v
    
    @field_validator('api_version')
    @classmethod
    def validate_api_version(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('API version cannot be empty')
        return v.strip()
    
    @field_validator('service_version')
    @classmethod
    def validate_service_version(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Service version cannot be empty if provided')
        return v.strip() if v else None


class Webhook(BaseModel):
    """Webhook configuration - TAMS compliant"""
    url: str = Field(..., description="The URL to which the API should make HTTP POST requests with event data")
    api_key_name: str = Field(..., description="The HTTP header name that is added to the event POST")
    api_key_value: Optional[str] = Field(None, description="The value that the HTTP header 'api_key_name' will be set to")
    events: List[str] = Field(..., description="List of event types to receive")
    
    # TAMS-specific filtering fields
    flow_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to Flows in the given list of Flow IDs")
    source_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to Sources in the given list of Source IDs")
    flow_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to those with Flow that is collected by a Flow Collection in the given list of Flow Collection IDs")
    source_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to those with Source that is collected by a Source Collection in the given list of Source Collection IDs")
    
    # TAMS-specific get_urls filtering fields
    accept_get_urls: Optional[List[str]] = Field(None, description="List of labels of URLs to include in the get_urls property in flows/segments_added events")
    accept_storage_ids: Optional[List[str]] = Field(None, description="List of labels of storage_ids to include in the get_urls property in flows/segments_added events")
    presigned: Optional[bool] = Field(None, description="Whether to include presigned/non-presigned URLs in the get_urls property in flows/segments_added events")
    verbose_storage: Optional[bool] = Field(None, description="Whether to include storage metadata in the get_urls property in flows/segments_added events")
    
    # Ownership fields for TAMS API v7.0 compliance
    owner_id: Optional[str] = Field(None, description="Owner identifier for the webhook")
    created_by: Optional[str] = Field(None, description="Entity that created the webhook")
    created: Optional[datetime] = Field(None, description="Date-time the webhook was created")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @field_validator('flow_ids', 'source_ids', 'flow_collected_by_ids', 'source_collected_by_ids', 'accept_storage_ids')
    @classmethod
    def validate_uuid_list(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            return validate_uuid_list(v)
        return v


class WebhookPost(BaseModel):
    """Webhook registration request - TAMS compliant"""
    url: str = Field(..., description="The URL to which the API should make HTTP POST requests with event data")
    api_key_name: str = Field(..., description="The HTTP header name that is added to the event POST")
    api_key_value: str = Field(..., description="The value that the HTTP header 'api_key_name' will be set to")
    events: List[str] = Field(..., description="List of event types to receive")
    
    # TAMS-specific filtering fields
    flow_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to Flows in the given list of Flow IDs")
    source_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to Sources in the given list of Source IDs")
    flow_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to those with Flow that is collected by a Flow Collection in the given list of Flow Collection IDs")
    source_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to those with Source that is collected by a Source Collection in the given list of Source Collection IDs")
    
    # TAMS-specific get_urls filtering fields
    accept_get_urls: Optional[List[str]] = Field(None, description="List of labels of URLs to include in the get_urls property in flows/segments_added events")
    accept_storage_ids: Optional[List[str]] = Field(None, description="List of labels of storage_ids to include in the get_urls property in flows/segments_added events")
    presigned: Optional[bool] = Field(None, description="Whether to include presigned/non-presigned URLs in the get_urls property in flows/segments_added events")
    verbose_storage: Optional[bool] = Field(None, description="Whether to include storage metadata in the get_urls property in flows/segments_added events")
    
    # Ownership fields for TAMS API v7.0 compliance
    owner_id: Optional[str] = Field(None, description="Owner identifier for the webhook")
    created_by: Optional[str] = Field(None, description="Entity that created the webhook")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @field_validator('flow_ids', 'source_ids', 'flow_collected_by_ids', 'source_collected_by_ids', 'accept_storage_ids')
    @classmethod
    def validate_uuid_list(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            return validate_uuid_list(v)
        return v


class FlowStoragePost(BaseModel):
    """Flow storage allocation request"""
    limit: Optional[int] = Field(None, description="Limit the number of storage segments in each response page")
    object_ids: Optional[List[str]] = Field(None, description="Array of object_ids to use")
    storage_id: Optional[str] = Field(None, description="The storage backend to allocate storage in", pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class HttpRequest(BaseModel):
    """HTTP request information"""
    url: str
    headers: Optional[Dict[str, str]] = None


class PreAction(BaseModel):
    """Pre-action for storage preparation"""
    action: str = Field(..., description="Action type")
    bucket_id: Optional[str] = Field(None, description="The name of the bucket that needs to be created")
    put_url: Optional[HttpRequest] = None
    put_cors_url: Optional[HttpRequest] = None


class MediaObject(BaseModel):
    """Media object storage information"""
    id: str = Field(..., description="The object store identifier for the media object")
    put_url: HttpRequest = Field(..., description="PUT URL for uploading the media object")
    put_cors_url: Optional[HttpRequest] = None
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata including storage path")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Object ID cannot be empty')
        return v.strip()


class FlowStorage(BaseModel):
    """Flow storage response"""
    pre: Optional[List[PreAction]] = Field(None, description="Actions that need to be taken before the media object can be written")
    media_objects: List[MediaObject] = Field(..., description="List of information for identifying and uploading media objects")


class StorageBackend(BaseModel):
    """Storage backend information - TAMS compliant"""
    id: str = Field(..., description="Storage backend identifier", pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    store_type: str = Field(..., description="The generic store type")
    provider: str = Field(..., description="The cloud provider of the storage")
    store_product: str = Field(..., description="The storage product name")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    label: Optional[str] = Field(None, description="Freeform string label for a storage backend")
    default_storage: bool = Field(False, description="If set to true, this is the default storage backend")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_tams_uuid(v)
    
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
    
    @field_validator('region')
    @classmethod
    def validate_region(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Region cannot be empty if provided')
        return v.strip() if v else None
    
    @field_validator('availability_zone')
    @classmethod
    def validate_availability_zone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Availability zone cannot be empty if provided')
        return v.strip() if v else None
    
    @field_validator('label')
    @classmethod
    def validate_label(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Label cannot be empty if provided')
        return v.strip() if v else None


class StorageBackendsList(BaseModel):
    """List of storage backends"""
    backends: List[StorageBackend] = Field(..., description="Information about the storage backends available on this service instance")


class Object(BaseModel):
    """Media object information - TAMS compliant"""
    id: str = Field(..., description="The media object identifier")
    referenced_by_flows: List[str] = Field(..., description="List of Flows that reference this media object via Flow Segments in this store")
    first_referenced_by_flow: Optional[str] = Field(None, description="The first Flow that had a Flow Segment reference the media object in this store")
    size: Optional[int] = Field(None, ge=0, description="Size of the media object in bytes")
    created: Optional[datetime] = Field(None, description="Date-time the media object was created")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Object ID cannot be empty')
        return v.strip()
    
    @field_validator('referenced_by_flows')
    @classmethod
    def validate_referenced_by_flows(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('Referenced by flows cannot be empty')
        for flow_id in v:
            if not flow_id or not flow_id.strip():
                raise ValueError('Flow ID cannot be empty')
        return v
    
    @field_validator('first_referenced_by_flow')
    @classmethod
    def validate_first_referenced_by_flow(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('First referenced by flow ID cannot be empty if provided')
        return v.strip() if v else None
    
    @field_validator('size')
    @classmethod
    def validate_size(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError('Size cannot be negative')
        return v
    
    @field_serializer('created')
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


class FlowDetailFilters(BaseModel):
    """Flow detail query filters"""
    include_timerange: bool = False
    timerange: Optional[TimeRange] = None


# Authentication models
class User(BaseModel):
    """User model for authentication"""
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    
    # Authentication fields
    password_hash: Optional[str] = None
    password_salt: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    
    # Security fields
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    
    # Metadata fields
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_serializer('created', 'updated', 'password_changed_at', 'locked_until', 'last_login_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class UserCreate(BaseModel):
    """User creation request"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    is_admin: bool = False
    created_by: Optional[str] = None


class UserUpdate(BaseModel):
    """User update request"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    updated_by: Optional[str] = None


class UserPasswordChange(BaseModel):
    """User password change request"""
    old_password: str
    new_password: str
    updated_by: Optional[str] = None


class ApiToken(BaseModel):
    """API token model"""
    token_id: str
    user_id: str
    token_name: str
    token_type: str  # 'url_token', 'bearer', etc.
    token_hash: Optional[str] = None  # Hashed version of the token for security
    
    # Permissions and scope
    permissions: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    
    # Token lifecycle
    is_active: bool = True
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    usage_count: int = 0
    
    # Security fields
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None
    
    # Metadata
    created_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_serializer('created_at', 'expires_at', 'last_used_at', 'revoked_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class ApiTokenCreate(BaseModel):
    """API token creation request"""
    user_id: str
    token_name: str
    token_type: str = "url_token"
    permissions: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    created_by: Optional[str] = None


class AuthLog(BaseModel):
    """Authentication log entry"""
    log_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Event details
    event_type: str  # 'login', 'logout', 'token_created', etc.
    auth_method: str  # 'basic', 'jwt', 'url_token'
    success: bool
    
    # Request details
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None
    
    # Error details
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Timestamps
    timestamp: Optional[datetime] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    
    @field_serializer('timestamp')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class UsersResponse(BaseModel):
    """Users list response"""
    data: List[User]
    paging: Optional[PagingInfo] = None


class ApiTokensResponse(BaseModel):
    """API tokens list response"""
    data: List[ApiToken]
    paging: Optional[PagingInfo] = None


class AuthLogsResponse(BaseModel):
    """Authentication logs response"""
    data: List[AuthLog]
    paging: Optional[PagingInfo] = None 