"""
TAMS Query Filter Models

This module contains models for query parameters and filters in the TAMS API.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SourceFilters(BaseModel):
    """Source query filters - TAMS 8.0 with tag filtering support"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    label: Optional[str] = None
    format: Optional[str] = None
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    
    # TAMS 8.0: Tag filtering (dynamic parameters will be extracted from request)
    tag_filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tag filters from query parameters")
    tag_exists_filters: Optional[Dict[str, bool]] = Field(default_factory=dict, description="Tag existence filters")


class FlowFilters(BaseModel):
    """Flow query filters - TAMS 8.0 with tag filtering support"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    source_id: Optional[str] = None
    timerange: Optional[str] = None
    format: Optional[str] = None
    codec: Optional[str] = None
    label: Optional[str] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    page: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    
    # TAMS 8.0: Tag filtering (dynamic parameters will be extracted from request)
    tag_filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tag filters from query parameters")
    tag_exists_filters: Optional[Dict[str, bool]] = Field(default_factory=dict, description="Tag existence filters")


class FlowDetailFilters(BaseModel):
    """Flow detail query filters"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    include_timerange: bool = False
    timerange: Optional[str] = None
