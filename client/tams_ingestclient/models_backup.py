"""
TAMS Ingest Client Models

Data models for TAMS video ingestion including source/flow configurations,
video analysis results, and ingestion requests/results.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

from .constants import TAMS_FORMATS, SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS


class SourceType(str, Enum):
    """Source type enumeration."""
    FILE = "file"
    STREAM = "stream"
    CAMERA = "camera"


class FlowType(str, Enum):
    """Flow type enumeration."""
    VIDEO = "video"
    AUDIO = "audio"
    MULTIMEDIA = "multimedia"


class TAMSSourceConfig(BaseModel):
    """TAMS source configuration."""
    label: str = Field(..., description="Source label")
    description: Optional[str] = Field(default=None, description="Source description")
    format: str = Field(default=TAMS_FORMATS["VIDEO"], description="Source format")
    tags: Dict[str, str] = Field(default_factory=dict, description="Source tags")
    source_type: SourceType = Field(default=SourceType.FILE, description="Source type")
    
    # File-specific settings
    file_path: Optional[str] = Field(default=None, description="File path for file sources")
    stream_url: Optional[str] = Field(default=None, description="Stream URL for stream sources")
    
    # Auto-detection settings
    auto_detect_format: bool = Field(default=True, description="Auto-detect format from file")
    auto_detect_metadata: bool = Field(default=True, description="Auto-detect metadata from file")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in TAMS_FORMATS.values():
            raise ValueError(f'format must be one of {list(TAMS_FORMATS.values())}')
        return v


class TAMSFlowConfig(BaseModel):
    """TAMS flow configuration."""
    source_id: str = Field(..., description="Source ID this flow belongs to")
    label: str = Field(..., description="Flow label")
    description: Optional[str] = Field(default=None, description="Flow description")
    format: str = Field(default=TAMS_FORMATS["VIDEO"], description="Flow format")
    codec: str = Field(default="h264", description="Video codec")
    audio_codec: Optional[str] = Field(default="aac", description="Audio codec")
    tags: Dict[str, str] = Field(default_factory=dict, description="Flow tags")
    flow_type: FlowType = Field(default=FlowType.VIDEO, description="Flow type")
    
    # Video parameters
    frame_width: Optional[int] = Field(default=None, description="Frame width")
    frame_height: Optional[int] = Field(default=None, description="Frame height")
    frame_rate: Optional[float] = Field(default=None, description="Frame rate")
    bitrate: Optional[str] = Field(default=None, description="Video bitrate")
    audio_bitrate: Optional[str] = Field(default=None, description="Audio bitrate")
    
    # Auto-detection settings
    auto_detect_codec: bool = Field(default=True, description="Auto-detect codec from source")
    auto_detect_resolution: bool = Field(default=True, description="Auto-detect resolution from source")
    auto_detect_framerate: bool = Field(default=True, description="Auto-detect framerate from source")
    auto_detect_bitrate: bool = Field(default=True, description="Auto-detect bitrate from source")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in TAMS_FORMATS.values():
            raise ValueError(f'format must be one of {list(TAMS_FORMATS.values())}')
        return v


class VideoAnalysisResult(BaseModel):
    """Video analysis result from FFmpeg."""
    duration: float = Field(..., description="Video duration in seconds")
    width: int = Field(..., description="Video width")
    height: int = Field(..., description="Video height")
    fps: float = Field(..., description="Frames per second")
    bitrate: int = Field(..., description="Video bitrate in bps")
    audio_bitrate: Optional[int] = Field(default=None, description="Audio bitrate in bps")
    video_codec: str = Field(..., description="Video codec")
    audio_codec: Optional[str] = Field(default=None, description="Audio codec")
    file_size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Container format")
    
    # Additional metadata
    has_audio: bool = Field(default=False, description="Whether video has audio track")
    has_video: bool = Field(default=True, description="Whether file has video track")
    color_space: Optional[str] = Field(default=None, description="Color space")
    pixel_format: Optional[str] = Field(default=None, description="Pixel format")
    
    # Timestamps
    analyzed_at: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")


class VideoIngestRequest(BaseModel):
    """Video ingestion request."""
    video_path: str = Field(..., description="Path to video file")
    source_config: Optional[TAMSSourceConfig] = Field(default=None, description="Source configuration")
    flow_config: Optional[TAMSFlowConfig] = Field(default=None, description="Flow configuration")
    
    # Processing options
    chunk_duration: int = Field(default=30, description="Chunk duration in seconds")
    segment_overlap: int = Field(default=0, description="Segment overlap in seconds")
    auto_create_source: bool = Field(default=True, description="Auto-create source if not exists")
    auto_create_flow: bool = Field(default=True, description="Auto-create flow if not exists")
    
    # S3 integration
    upload_to_s3: bool = Field(default=True, description="Upload segments to S3")
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket for uploads")
    s3_prefix: Optional[str] = Field(default=None, description="S3 prefix for uploads")
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('video_path')
    @classmethod
    def validate_video_path(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f'Video file does not exist: {v}')
        
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_VIDEO_FORMATS:
            raise ValueError(f'Unsupported video format: {suffix}. Supported: {list(SUPPORTED_VIDEO_FORMATS.keys())}')
        
        return str(path.absolute())


class TAMSSegment(BaseModel):
    """TAMS segment model."""
    object_id: str = Field(..., description="Segment object ID")
    timerange: str = Field(..., description="Time range in ISO format")
    ts_offset: Optional[str] = Field(default=None, description="Timestamp offset")
    last_duration: Optional[str] = Field(default=None, description="Last duration")
    sample_offset: Optional[int] = Field(default=None, description="Sample offset")
    sample_count: Optional[int] = Field(default=None, description="Sample count")
    key_frame_count: Optional[int] = Field(default=None, description="Key frame count")
    
    # URLs
    get_urls: List[Dict[str, str]] = Field(default_factory=list, description="GET URLs for segment")
    
    # Metadata
    file_path: Optional[str] = Field(default=None, description="Local file path")
    s3_key: Optional[str] = Field(default=None, description="S3 object key")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    duration: Optional[float] = Field(default=None, description="Segment duration in seconds")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class VideoIngestResult(BaseModel):
    """Video ingestion result."""
    success: bool = Field(..., description="Whether ingestion was successful")
    source_id: Optional[str] = Field(default=None, description="Created source ID")
    flow_id: Optional[str] = Field(default=None, description="Created flow ID")
    segments: List[TAMSSegment] = Field(default_factory=list, description="Created segments")
    
    # Processing statistics
    total_duration: float = Field(..., description="Total video duration in seconds")
    segment_count: int = Field(default=0, description="Number of segments created")
    total_file_size: int = Field(default=0, description="Total file size in bytes")
    processing_time: float = Field(..., description="Processing time in seconds")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    
    # Timestamps
    started_at: datetime = Field(..., description="Processing start time")
    completed_at: datetime = Field(..., description="Processing completion time")
    
    # Metadata
    video_analysis: Optional[VideoAnalysisResult] = Field(default=None, description="Video analysis result")
    source_config: Optional[TAMSSourceConfig] = Field(default=None, description="Source configuration used")
    flow_config: Optional[TAMSFlowConfig] = Field(default=None, description="Flow configuration used")


class TAMSSource(BaseModel):
    """TAMS source model."""
    id: str = Field(..., description="Source ID")
    format: str = Field(..., description="Source format")
    label: str = Field(..., description="Source label")
    description: Optional[str] = Field(default=None, description="Source description")
    created_by: Optional[str] = Field(default=None, description="Created by")
    updated_by: Optional[str] = Field(default=None, description="Updated by")
    created: datetime = Field(..., description="Creation timestamp")
    updated: datetime = Field(..., description="Update timestamp")
    tags: Dict[str, str] = Field(default_factory=dict, description="Source tags")


class TAMSFlow(BaseModel):
    """TAMS flow model."""
    id: str = Field(..., description="Flow ID")
    source_id: str = Field(..., description="Source ID")
    format: str = Field(..., description="Flow format")
    codec: Optional[str] = Field(default=None, description="Video codec")
    label: str = Field(..., description="Flow label")
    description: Optional[str] = Field(default=None, description="Flow description")
    created_by: Optional[str] = Field(default=None, description="Created by")
    updated_by: Optional[str] = Field(default=None, description="Updated by")
    created: datetime = Field(..., description="Creation timestamp")
    updated: datetime = Field(..., description="Update timestamp")
    tags: Dict[str, str] = Field(default_factory=dict, description="Flow tags")
    
    # Video parameters
    frame_width: Optional[int] = Field(default=None, description="Frame width")
    frame_height: Optional[int] = Field(default=None, description="Frame height")
    frame_rate: Optional[float] = Field(default=None, description="Frame rate")
    bitrate: Optional[str] = Field(default=None, description="Video bitrate")
    read_only: bool = Field(default=False, description="Read-only flag")
    
    @field_validator('frame_rate', mode='before')
    @classmethod
    def validate_frame_rate(cls, v):
        if v == '' or v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None