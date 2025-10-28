"""
Event Models for TAMS API

This module defines the data structures for events emitted by the TAMS API.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid


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
    
    # Common fields
    entity_id: str = Field(..., description="Entity ID that triggered the event")
    user_id: Optional[str] = Field(None, description="User who triggered the event")


class SourceEventData(EventData):
    """Source-specific event data"""
    source_id: str = Field(..., description="Source ID that triggered the event")
    label: Optional[str] = None
    format: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class FlowEventData(EventData):
    """Flow-specific event data"""
    flow_id: str = Field(..., description="Flow ID that triggered the event")
    source_id: Optional[str] = Field(None, description="Associated source ID")
    label: Optional[str] = None
    format: Optional[str] = None
    codec: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class FlowSegmentEventData(EventData):
    """Flow segment-specific event data"""
    event_type: str = Field(..., description="Event type")
    segment_id: str = Field(..., description="Segment ID")
    flow_id: str = Field(..., description="Flow ID that contains this segment")
    object_id: Optional[str] = None
    timerange: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None


class ObjectEventData(EventData):
    """Object-specific event data"""
    object_id: str = Field(..., description="Object ID that triggered the event")
    size: Optional[int] = None
    referenced_by_flows: Optional[list] = None
    tags: Optional[Dict[str, Any]] = None


class CollectionEventData(EventData):
    """Collection-specific event data"""
    collection_id: str = Field(..., description="Collection ID that triggered the event")
    collection_type: Optional[str] = None
    source_id: Optional[str] = Field(None, description="Associated source ID")
    label: Optional[str] = None
    member_count: Optional[int] = None
    tags: Optional[Dict[str, Any]] = None


class Event(BaseModel):
    """TAMS event structure"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    data: EventData = Field(..., description="Event data payload")
    source: Optional[str] = Field(None, description="Event source")
    version: str = Field(default="1.0", description="Event schema version")

