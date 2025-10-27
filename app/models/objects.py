"""
TAMS Object Models

This module contains models related to media objects in the TAMS API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict

from .core import TimeRange


class Object(BaseModel):
    """Media object information - TAMS 8.0 compliant with timerange support"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="The media object identifier")
    referenced_by_flows: List[str] = Field(..., description="List of Flows that reference this media object via Flow Segments in this store")
    first_referenced_by_flow: Optional[str] = Field(None, description="The first Flow that had a Flow Segment reference the media object in this store")
    timerange: TimeRange = Field(..., description="The timerange covering the sample timestamps embedded in or derived from the Media Object itself, on the Media Object's timeline")
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
    
    @field_serializer('created')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
