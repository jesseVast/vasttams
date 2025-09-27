"""
TAMS Source Models

This module contains models related to Sources in the TAMS API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict
import re

from .core import Tags, CollectionItem, validate_tams_uuid, validate_content_format


class Source(BaseModel):
    """Source model as defined in TAMS API"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Source identifier")
    format: str = Field(..., description="Content format URN")
    label: Optional[str] = Field(None, description="Freeform string label for the Source")
    description: Optional[str] = Field(None, description="Freeform text describing the Source")
    created_by: Optional[str] = Field(None, description="Entity that created the Source")
    updated_by: Optional[str] = Field(None, description="Entity that updated the Source metadata most recently")
    created: Optional[datetime] = Field(None, description="Date-time the Source was created")
    updated: Optional[datetime] = Field(None, description="Date-time the Source metadata was last updated")
    tags: Optional[Tags] = Field(None, description="Source tags")
    
    # Computed fields (read-only)
    source_collection: Optional[List[CollectionItem]] = Field(None, description="List of Sources collected by this Source")
    collected_by: Optional[List[str]] = Field(None, description="Sources that reference this Source")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_tams_uuid(v)
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        return validate_content_format(v)
    
    @field_validator('collected_by')
    @classmethod
    def validate_collected_by(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            for source_id in v:
                if not isinstance(source_id, str) or not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', source_id):
                    raise ValueError('Invalid UUID format in collected_by')
        return v

    @field_serializer('created', 'updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
