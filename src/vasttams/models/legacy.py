"""
TAMS Legacy Models

This module contains legacy models that are kept for backward compatibility.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
import re


class PathTemplateType(str, Enum):
    """Path template types for hierarchical organization"""
    TIME_BASED = "time_based"
    SOURCE_BASED = "source_based"
    HYBRID = "hybrid"
    CUSTOM = "custom"
    FLAT = "flat"


class HierarchicalPath(BaseModel):
    """Hierarchical path configuration for media storage"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
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
    @classmethod
    def validate_custom_template(cls, v):
        if v is not None:
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
    @classmethod
    def validate_time_granularity(cls, v):
        valid_granularities = ['hour', 'day', 'month', 'year']
        if v not in valid_granularities:
            raise ValueError(f'Invalid time granularity. Must be one of: {valid_granularities}')
        return v


class PathSegment(BaseModel):
    """Individual path segment with metadata"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str
    value: str
    type: str  # 'source', 'flow', 'time', 'segment', 'custom'
    metadata: Optional[Dict[str, Any]] = None


class HierarchicalPathResult(BaseModel):
    """Result of hierarchical path generation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    full_path: str
    segments: List[PathSegment]
    template_used: str
    normalized: bool = False
    validation_errors: Optional[List[str]] = None
