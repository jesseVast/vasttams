from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Annotated
from pydantic import BaseModel, Field, RootModel, UUID4, field_validator, field_serializer
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


def validate_hierarchical_path(v: str) -> str:
    """Validate hierarchical path format"""
    if not isinstance(v, str):
        raise ValueError('Hierarchical path must be a string')
    
    # Check for valid characters (alphanumeric, hyphens, underscores, forward slashes)
    pattern = r'^[a-zA-Z0-9\-_/]+$'
    if not re.match(pattern, v):
        raise ValueError('Invalid characters in hierarchical path. Only alphanumeric, hyphens, underscores, and forward slashes allowed')
    
    # Check for consecutive separators
    if '//' in v:
        raise ValueError('Invalid hierarchical path: consecutive separators not allowed')
    
    # Check for leading/trailing separators
    if v.startswith('/') or v.endswith('/'):
        raise ValueError('Invalid hierarchical path: leading or trailing separators not allowed')
    
    return v


# Type aliases with validation
ContentFormat = Annotated[str, field_validator('*')(validate_content_format)]
MimeType = Annotated[str, field_validator('*')(validate_mime_type)]
TimeRange = Annotated[str, field_validator('*')(validate_time_range)]
HierarchicalPathStr = Annotated[str, field_validator('*')(validate_hierarchical_path)]


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
    
    @field_serializer('created', 'updated')
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
    # Storage path field - stores the actual S3 object key used for storage
    storage_path: Optional[str] = None  # The actual S3 object key where data is stored


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
    
    @field_serializer('created', 'updated')
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
    
    @field_serializer('created', 'updated')
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
    
    @field_serializer('created', 'updated')
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
    
    @field_serializer('created', 'updated')
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
    
    @field_serializer('created', 'updated')
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
    api_version: str = "7.0"
    service_version: Optional[str] = None
    media_store: MediaStore
    event_stream_mechanisms: Optional[List[EventStreamMechanism]] = None


class Webhook(BaseModel):
    """Webhook configuration"""
    url: str
    api_key_name: str
    api_key_value: Optional[str] = None
    events: List[str]
    # Ownership fields for TAMS API v7.0 compliance
    owner_id: Optional[str] = None
    created_by: Optional[str] = None
    created: Optional[datetime] = None


class WebhookPost(BaseModel):
    """Webhook registration request"""
    url: str
    api_key_name: str
    api_key_value: str
    events: List[str]
    # Ownership fields for TAMS API v7.0 compliance
    owner_id: Optional[str] = None
    created_by: Optional[str] = None


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
    object_id: str = Field(..., description="The object store identifier for the media object")
    put_url: HttpRequest = Field(..., description="PUT URL for uploading the media object")
    put_cors_url: Optional[HttpRequest] = None
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata including storage path")


class FlowStorage(BaseModel):
    """Flow storage response"""
    pre: Optional[List[PreAction]] = Field(None, description="Actions that need to be taken before the media object can be written")
    media_objects: List[MediaObject] = Field(..., description="List of information for identifying and uploading media objects")


class StorageBackend(BaseModel):
    """Storage backend information"""
    id: str = Field(..., description="Storage backend identifier", pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    store_type: str = Field(..., description="The generic store type")
    provider: str = Field(..., description="The cloud provider of the storage")
    store_product: str = Field(..., description="The storage product name")
    region: Optional[str] = Field(None, description="The region in the cloud this storage backend resides")
    availability_zone: Optional[str] = Field(None, description="The availability zone in the cloud region")
    label: Optional[str] = Field(None, description="Freeform string label for a storage backend")
    default_storage: bool = Field(False, description="If set to true, this is the default storage backend")


class StorageBackendsList(BaseModel):
    """List of storage backends"""
    backends: List[StorageBackend] = Field(..., description="Information about the storage backends available on this service instance")


class Object(BaseModel):
    """Media object information"""
    object_id: str
    flow_references: List[Dict[str, Any]]
    size: Optional[int] = None
    created: Optional[datetime] = None
    
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