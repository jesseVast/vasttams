"""
TAMS Analytics Models

This module contains Pydantic models for analytics data structures.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class StorageStatistics(BaseModel):
    """Storage statistics"""
    total_size_bytes: int = Field(0, description="Total storage size in bytes")
    total_size_mb: float = Field(0.0, description="Total storage size in megabytes")
    total_size_gb: float = Field(0.0, description="Total storage size in gigabytes")
    average_size_bytes: float = Field(0.0, description="Average object size in bytes")
    min_size_bytes: Optional[int] = Field(None, description="Minimum object size in bytes")
    max_size_bytes: Optional[int] = Field(None, description="Maximum object size in bytes")
    object_count_with_size: int = Field(0, description="Number of objects with size information")


class FormatBreakdown(BaseModel):
    """Format breakdown statistics"""
    video_flows: int = Field(0, description="Number of video flows")
    audio_flows: int = Field(0, description="Number of audio flows")
    image_flows: int = Field(0, description="Number of image flows")
    data_flows: int = Field(0, description="Number of data flows")
    multi_flows: int = Field(0, description="Number of multi flows")
    total_flows: int = Field(0, description="Total number of flows")


class TimeStatistics(BaseModel):
    """Time-based statistics"""
    earliest_source_created: Optional[datetime] = Field(None, description="Earliest source creation time")
    latest_source_created: Optional[datetime] = Field(None, description="Latest source creation time")
    earliest_flow_created: Optional[datetime] = Field(None, description="Earliest flow creation time")
    latest_flow_created: Optional[datetime] = Field(None, description="Latest flow creation time")
    earliest_segment_created: Optional[datetime] = Field(None, description="Earliest segment creation time")
    latest_segment_created: Optional[datetime] = Field(None, description="Latest segment creation time")
    earliest_object_created: Optional[datetime] = Field(None, description="Earliest object creation time")
    latest_object_created: Optional[datetime] = Field(None, description="Latest object creation time")


class CountStatistics(BaseModel):
    """Count statistics"""
    total_sources: int = Field(0, description="Total number of sources")
    total_flows: int = Field(0, description="Total number of flows")
    total_segments: int = Field(0, description="Total number of segments")
    total_objects: int = Field(0, description="Total number of objects")
    flows_per_source_avg: float = Field(0.0, description="Average number of flows per source")
    segments_per_flow_avg: float = Field(0.0, description="Average number of segments per flow")


class AnalyticsSummary(BaseModel):
    """Complete analytics summary"""
    counts: CountStatistics = Field(..., description="Count statistics")
    storage: StorageStatistics = Field(..., description="Storage statistics")
    formats: FormatBreakdown = Field(..., description="Format breakdown")
    time: TimeStatistics = Field(..., description="Time-based statistics")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(), description="When the analytics were generated")


class SourceAnalytics(BaseModel):
    """Source-specific analytics"""
    source_id: str = Field(..., description="Source ID")
    source_label: Optional[str] = Field(None, description="Source label")
    flow_count: int = Field(0, description="Number of flows for this source")
    segment_count: int = Field(0, description="Number of segments for this source")
    total_size_bytes: int = Field(0, description="Total storage size for this source in bytes")
    created: Optional[datetime] = Field(None, description="Source creation time")


class FlowAnalytics(BaseModel):
    """Flow-specific analytics"""
    flow_id: str = Field(..., description="Flow ID")
    flow_label: Optional[str] = Field(None, description="Flow label")
    source_id: Optional[str] = Field(None, description="Source ID")
    format: str = Field(..., description="Flow format")
    segment_count: int = Field(0, description="Number of segments in this flow")
    total_duration_seconds: Optional[float] = Field(None, description="Total duration of flow in seconds calculated from segments")
    total_size_bytes: int = Field(0, description="Total storage size for this flow in bytes")
    created: Optional[datetime] = Field(None, description="Flow creation time")


