from pydantic import BaseModel, Field, field_serializer, RootModel, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID, uuid4
import re

# Custom validators
def validate_content_format(v: str) -> str:
    """Validate content format URN"""
    if not v.startswith("urn:x-nmos:format:") and not v.startswith("urn:x-tam:format:"):
        raise ValueError("Content format must be a valid URN starting with urn:x-nmos:format: or urn:x-tam:format:")
    return v

def validate_mime_type(v: str) -> str:
    """Validate MIME type format"""
    if not re.match(r'^[^\\s\/]+/[^\\s\/]+$', v):
        raise ValueError("MIME type must be in format 'type/subtype'")
    return v

def validate_time_range(v: str) -> str:
    """Validate time range format"""
    # Basic validation for time range format
    if not v or v == "_":
        return v
    # Add more specific validation as needed
    return v

# Custom types
ContentFormat = str
MimeType = str
TimeRange = str
UUID4 = UUID

class Tags(RootModel[Dict[str, str]]):
    """Tags model for key-value pairs"""
    
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
    
    @field_serializer('created', 'updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

class StorageBackend(BaseModel):
    """Storage backend metadata"""
    storage_id: UUID4
    label: str
    description: Optional[str] = None
    type: str = "http_object_store"

class GetUrl(BaseModel):
    """Get URL for flow segments with storage backend integration"""
    url: str
    storage_id: Optional[UUID4] = None
    presigned: Optional[bool] = None
    label: Optional[str] = None
    controlled: Optional[bool] = True

class FlowSegment(BaseModel):
    """Flow segment model matching the updated schema"""
    object_id: str
    timerange: TimeRange
    ts_offset: Optional[str] = None  # Timestamp format
    last_duration: Optional[str] = None  # Timestamp format
    sample_offset: Optional[int] = None
    sample_count: Optional[int] = None
    get_urls: Optional[List[GetUrl]] = None
    key_frame_count: Optional[int] = None

# Flow Core - Base properties for all flow types
class FlowCore(BaseModel):
    """Base flow properties for all flow types"""
    id: UUID4
    source_id: UUID4
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    tags: Optional[Tags] = None
    metadata_version: Optional[str] = None
    generation: Optional[int] = Field(None, ge=0)
    created: Optional[datetime] = None
    metadata_updated: Optional[datetime] = None
    segments_updated: Optional[datetime] = None
    read_only: Optional[bool] = False
    codec: Optional[MimeType] = None
    container: Optional[MimeType] = None
    avg_bit_rate: Optional[int] = Field(None, ge=0)
    max_bit_rate: Optional[int] = Field(None, ge=0)
    segment_duration: Optional[Dict[str, int]] = None  # numerator/denominator structure
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

class VideoFlow(FlowCore):
    """Video flow model extending FlowCore"""
    format: ContentFormat = Field(default="urn:x-nmos:format:video")
    frame_width: int = Field(..., gt=0)
    frame_height: int = Field(..., gt=0)
    frame_rate: Optional[Dict[str, int]] = None  # numerator/denominator structure
    interlace_mode: Optional[str] = Field(None, pattern="^(progressive|interlaced_tff|interlaced_bff|interlaced_psf)$")
    colorspace: Optional[str] = Field(None, pattern="^(BT601|BT709|BT2020|BT2100)$")
    transfer_characteristic: Optional[str] = Field(None, pattern="^(SDR|HLG|PQ)$")
    aspect_ratio: Optional[Dict[str, int]] = None  # numerator/denominator structure
    bit_depth: Optional[int] = Field(None, gt=0)

class AudioFlow(FlowCore):
    """Audio flow model extending FlowCore"""
    format: ContentFormat = Field(default="urn:x-nmos:format:audio")
    sample_rate: int = Field(..., gt=0)
    bits_per_sample: int = Field(..., gt=0)
    channels: int = Field(..., gt=0)

class DataFlow(FlowCore):
    """Data flow model extending FlowCore"""
    format: ContentFormat = Field(default="urn:x-nmos:format:data")

class ImageFlow(FlowCore):
    """Image flow model extending FlowCore"""
    format: ContentFormat = Field(default="urn:x-tam:format:image")
    frame_width: int = Field(..., gt=0)
    frame_height: int = Field(..., gt=0)

class MultiFlow(FlowCore):
    """Multi flow model extending FlowCore"""
    format: ContentFormat = Field(default="urn:x-nmos:format:multi")
    flow_collection: List[UUID4]

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
    api_version: str = "7.0"
    service_version: Optional[str] = None
    media_store: MediaStore
    event_stream_mechanisms: Optional[List[EventStreamMechanism]] = None

class Webhook(BaseModel):
    """Webhook configuration with enhanced filtering"""
    url: str
    api_key_name: Optional[str] = None
    api_key_value: Optional[str] = None
    events: List[str]
    flow_ids: Optional[List[UUID4]] = None
    source_ids: Optional[List[UUID4]] = None
    flow_collected_by_ids: Optional[List[UUID4]] = None
    source_collected_by_ids: Optional[List[UUID4]] = None
    accept_get_urls: Optional[List[str]] = None
    accept_storage_ids: Optional[List[UUID4]] = None
    presigned: Optional[bool] = None
    verbose_storage: Optional[bool] = None

class WebhookPost(BaseModel):
    """Webhook registration request"""
    url: str
    api_key_name: str
    api_key_value: str
    events: List[str]
    flow_ids: Optional[List[UUID4]] = None
    source_ids: Optional[List[UUID4]] = None
    flow_collected_by_ids: Optional[List[UUID4]] = None
    source_collected_by_ids: Optional[List[UUID4]] = None
    accept_get_urls: Optional[List[str]] = None
    accept_storage_ids: Optional[List[UUID4]] = None
    presigned: Optional[bool] = None
    verbose_storage: Optional[bool] = None

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
    """Media object information matching the updated schema"""
    id: str  # Changed from object_id to id
    referenced_by_flows: List[UUID4]  # Changed from flow_references to referenced_by_flows
    first_referenced_by_flow: Optional[UUID4] = None  # New field
    
    @field_serializer('referenced_by_flows', 'first_referenced_by_flow')
    def serialize_uuids(self, value: Union[List[UUID4], UUID4, None]) -> Union[List[str], str, None]:
        if isinstance(value, list):
            return [str(uuid) for uuid in value]
        elif isinstance(value, UUID):
            return str(value)
        return value

class DeletionRequest(BaseModel):
    """Flow deletion request matching the updated schema"""
    id: UUID4  # Changed from request_id to id
    flow_id: UUID4
    timerange_to_delete: TimeRange  # Changed from timerange to timerange_to_delete
    timerange_remaining: Optional[TimeRange] = None  # New field
    delete_flow: bool  # New field
    created: datetime
    created_by: Optional[str] = None  # New field
    updated: Optional[datetime] = None
    expiry: Optional[datetime] = None  # New field
    status: str = Field(..., pattern="^(created|started|done|error)$")  # Enum values
    error: Optional[Dict[str, Any]] = None  # New field
    
    @field_serializer('created', 'updated', 'expiry')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

class DeletionRequestsList(BaseModel):
    """List of deletion requests"""
    requests: List[DeletionRequest]

class StorageBackendsList(BaseModel):
    """List of storage backends"""
    storage_backends: List[StorageBackend]

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

class StorageBackendsResponse(BaseModel):
    """Storage backends list response"""
    data: StorageBackendsList

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
    accept_get_urls: Optional[str] = None
    accept_storage_ids: Optional[str] = None
    presigned: Optional[bool] = None
    verbose_storage: Optional[bool] = None

class ObjectFilters(BaseModel):
    """Object query filters with pagination"""
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)

class FlowSegmentFilters(BaseModel):
    """Flow segment query filters"""
    timerange: Optional[TimeRange] = None
    object_id: Optional[str] = None
    accept_get_urls: Optional[str] = None
    accept_storage_ids: Optional[str] = None
    presigned: Optional[bool] = None
    verbose_storage: Optional[bool] = None

class FlowSegmentPost(BaseModel):
    """Flow segment creation request"""
    object_id: str
    timerange: TimeRange
    ts_offset: Optional[str] = None
    last_duration: Optional[str] = None
    sample_offset: Optional[int] = None
    sample_count: Optional[int] = None
    get_urls: Optional[List[GetUrl]] = None
    key_frame_count: Optional[int] = None

class FlowSegmentBulkFailure(BaseModel):
    """Bulk segment creation failure response"""
    failed_segments: List[Dict[str, Any]]
    error_count: int
    total_count: int

class Error(BaseModel):
    """Error response model"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None 