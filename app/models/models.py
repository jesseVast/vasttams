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
    # Soft delete fields
    deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None


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
    
    # Soft delete fields
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created', 'updated', 'deleted_at', 'password_changed_at', 'locked_until', 'last_login_at')
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
    
    # Soft delete fields
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('created_at', 'expires_at', 'last_used_at', 'revoked_at', 'deleted_at')
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
    
    # Soft delete fields
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @field_serializer('timestamp', 'deleted_at')
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