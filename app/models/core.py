"""
TAMS Core Types and Models

This module contains the fundamental types and models used throughout the TAMS API.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, RootModel, field_validator, field_serializer, ConfigDict
import re
import uuid


# ============================================================================
# TAMS Core Validators
# ============================================================================

def validate_tams_uuid(v: str) -> str:
    """Validate UUID format according to TAMS specification"""
    if not isinstance(v, str):
        raise ValueError('UUID must be a string')
    
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    if not re.match(pattern, v):
        raise ValueError('Invalid UUID format. Must be a valid TAMS UUID')
    
    return v


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
    
    pattern = r'^[^\\s\/]+/[^\\s\/]+$'
    if not re.match(pattern, v):
        raise ValueError('Invalid MIME type format. Must be in format: type/subtype')
    
    return v


def validate_timestamp(v: str) -> str:
    """Validate timestamp format according to TAMS specification"""
    if not isinstance(v, str):
        raise ValueError('Timestamp must be a string')
    
    pattern = r'^-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8})$'
    if not re.match(pattern, v):
        raise ValueError('Invalid timestamp format. Must be in format: seconds:nanoseconds')
    
    return v


def validate_timerange(v: str) -> str:
    """Validate timerange format according to TAMS specification"""
    if not isinstance(v, str):
        raise ValueError('Timerange must be a string')
    
    pattern = r'^(\[|\()?(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?(_(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?)?(\]|\))?$'
    if not re.match(pattern, v):
        raise ValueError('Invalid timerange format')
    
    return v


# ============================================================================
# TAMS Core Models
# ============================================================================

class Timestamp(BaseModel):
    """TAMS timestamp model"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: str = Field(..., description="Timestamp in format seconds:nanoseconds")
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str) -> str:
        return validate_timestamp(v)


class TimeRange(BaseModel):
    """TAMS timerange model"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: str = Field(..., description="Timerange in TAMS format")
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str) -> str:
        return validate_timerange(v)


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
    """Collection item for source and flow collections"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Source or Flow identifier")
    role: str = Field(..., description="Human-readable role of the element in this collection")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_tams_uuid(v)


class ContainerMapping(BaseModel):
    """Container mapping for flow essence data"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    track_index: Optional[int] = Field(None, ge=0, description="Zero-based track index in container")
    format_track_index: Optional[int] = Field(None, ge=0, description="Zero-based track index for flow format")
    
    # Audio track mapping
    audio_track: Optional[Dict[str, Any]] = Field(None, description="Audio track channel mapping")
    
    # Container-specific mappings
    mp2ts_container: Optional[Dict[str, Any]] = Field(None, description="MPEG-2 Transport Stream mapping")
    mxf_container: Optional[Dict[str, Any]] = Field(None, description="MXF container mapping")
    isobmff_container: Optional[Dict[str, Any]] = Field(None, description="ISO Base Media File Format mapping")


class FlowCollectionItem(BaseModel):
    """Flow collection item with container mapping"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Flow identifier")
    role: str = Field(..., description="Role of the flow in this collection")
    container_mapping: Optional[ContainerMapping] = Field(None, description="Container mapping for this flow")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_tams_uuid(v)


class FlowCollection(RootModel[List[FlowCollectionItem]]):
    """Flow collection as array of flow collection items"""
    pass


class EventStreamMechanism(BaseModel):
    """Event stream mechanism configuration"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., description="Name of the event stream mechanism")
    docs: Optional[str] = Field(None, description="Documentation URL for this mechanism")
    description: Optional[str] = Field(None, description="Description of this mechanism")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration options")


class EventData(BaseModel):
    """Base event data structure"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data payload")


class SourceEventData(EventData):
    """Source-specific event data"""
    source_id: str = Field(..., description="Source ID that triggered the event")


class FlowEventData(EventData):
    """Flow-specific event data"""
    flow_id: str = Field(..., description="Flow ID that triggered the event")
    source_id: Optional[str] = Field(None, description="Associated source ID")


class FlowSegmentEventData(EventData):
    """Flow segment-specific event data"""
    flow_id: str = Field(..., description="Flow ID that triggered the event")
    segment_id: Optional[str] = Field(None, description="Segment ID if applicable")


class ObjectEventData(EventData):
    """Object-specific event data"""
    object_id: str = Field(..., description="Object ID that triggered the event")


class CollectionEventData(EventData):
    """Collection-specific event data"""
    collection_id: str = Field(..., description="Collection ID that triggered the event")
    source_id: Optional[str] = Field(None, description="Associated source ID")


class Event(BaseModel):
    """TAMS event structure"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    data: EventData = Field(..., description="Event data payload")
    source: Optional[str] = Field(None, description="Event source")
    version: str = Field(default="1.0", description="Event schema version")


class HttpRequest(BaseModel):
    """HTTP request information"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    url: str = Field(..., description="The URL to make the request to")
    body: Optional[str] = Field(None, description="Request body text")
    content_type: Optional[str] = Field(None, alias="content-type", description="Content type header")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")


class SegmentDuration(BaseModel):
    """Segment duration with numerator/denominator"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    numerator: int = Field(..., gt=0, description="Segment duration numerator")
    denominator: int = Field(default=1, gt=0, description="Segment duration denominator")
