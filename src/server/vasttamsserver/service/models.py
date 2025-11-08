"""
TAMS Service Models

This module contains models related to the TAMS service information.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import EventStreamMechanism from events module to avoid circular import
try:
    from ..events.models import EventStreamMechanism
except ImportError:
    # Fallback for backward compatibility
    from ..common.models import EventStreamMechanism


class Service(BaseModel):
    """Service information model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: Optional[str] = Field(None, description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    type: str = Field(default="urn:x-tams:service:api", description="Service type URN")
    api_version: str = Field(default="7.0", description="TAMS API version")
    service_version: Optional[str] = Field(None, description="Service implementation version")
    event_stream_mechanisms: Optional[List[EventStreamMechanism]] = Field(None, description="Available event stream mechanisms")
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if not v.startswith('urn:x-tams:service:'):
            raise ValueError('Service type must start with urn:x-tams:service:')
        return v
