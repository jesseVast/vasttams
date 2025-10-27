"""
TAMS Flow Models

This module contains models related to Flows in the TAMS API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Annotated, Literal
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict

from ..common.models import (
    Tags, 
    FlowCollection, 
    ContainerMapping, 
    SegmentDuration, 
    TimeRange,
    validate_tams_uuid, 
    validate_mime_type
)


# ============================================================================
# Flow Essence Parameters
# ============================================================================

class VideoEssenceParameters(BaseModel):
    """
    Video flow essence parameters with TAMS 8.0 VFR support.
    
    Supports both fixed frame rate (frame_rate set, vfr=False) and 
    variable frame rate (vfr=True, frame_rate must be None).
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    frame_width: int = Field(..., gt=0, description="Width of the picture in pixels")
    frame_height: int = Field(..., gt=0, description="Height of the picture in pixels")
    frame_rate: Optional[SegmentDuration] = Field(None, description="Frames per second. MUST be set if vfr=false or omitted. MUST NOT be set if vfr=true")
    vfr: Optional[bool] = Field(default=False, description="If true, frame rate is variable and frame_rate must be omitted. If false or omitted, frame rate is fixed and frame_rate must be set")
    bit_depth: Optional[int] = Field(None, gt=0, description="Number of significant bits per sample")
    interlace_mode: Optional[str] = Field(None, description="Interlaced video mode")
    colorspace: Optional[str] = Field(None, description="Colorspace used for the video")
    transfer_characteristic: Optional[str] = Field(None, description="Transfer characteristic")
    aspect_ratio: Optional[SegmentDuration] = Field(None, description="Display aspect ratio")
    pixel_aspect_ratio: Optional[SegmentDuration] = Field(None, description="Pixel aspect ratio")
    component_type: Optional[str] = Field(None, description="Picture component representation")
    horiz_chroma_subs: Optional[int] = Field(None, gt=0, description="Horizontal chroma sub-sampling")
    vert_chroma_subs: Optional[int] = Field(None, gt=0, description="Vertical chroma sub-sampling")
    
    # Uncompressed video parameters
    unc_parameters: Optional[Dict[str, Any]] = Field(None, description="Uncompressed video parameters")
    
    # AVC parameters
    avc_parameters: Optional[Dict[str, Any]] = Field(None, description="AVC codec parameters")
    
    @field_validator('frame_rate', 'vfr')
    @classmethod
    def validate_vfr_frame_rate(cls, v, info):
        """
        Validate VFR/frame_rate mutual exclusivity per ADR-0041.
        If vfr=True, frame_rate must be None.
        If vfr=False or omitted, frame_rate must be set.
        """
        data = info.data if hasattr(info, 'data') else {}
        vfr_value = data.get('vfr', False)
        frame_rate_value = data.get('frame_rate')
        
        # Only validate when both values are being set
        if 'vfr' in data and 'frame_rate' in data:
            if vfr_value and frame_rate_value is not None:
                raise ValueError("If vfr=True, frame_rate MUST NOT be set")
            if not vfr_value and frame_rate_value is None:
                raise ValueError("If vfr=False or omitted, frame_rate MUST be set")
        
        return v


class AudioEssenceParameters(BaseModel):
    """Audio flow essence parameters"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sample_rate: int = Field(..., gt=0, description="Samples per second")
    channels: int = Field(..., gt=0, description="Channel count")
    bit_depth: Optional[int] = Field(None, gt=0, description="Number of significant bits per sample")
    
    # Codec parameters
    codec_parameters: Optional[Dict[str, Any]] = Field(None, description="Audio codec parameters")
    
    # Uncompressed audio parameters
    unc_parameters: Optional[Dict[str, Any]] = Field(None, description="Uncompressed audio parameters")


class ImageEssenceParameters(BaseModel):
    """Image flow essence parameters"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    frame_width: int = Field(..., gt=0, description="Width of the picture in pixels")
    frame_height: int = Field(..., gt=0, description="Height of the picture in pixels")
    aspect_ratio: Optional[SegmentDuration] = Field(None, description="Display aspect ratio")


class DataEssenceParameters(BaseModel):
    """Data flow essence parameters"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    data_type: Optional[str] = Field(None, description="Type of information encoded in the flow")


# ============================================================================
# Flow Models
# ============================================================================

class FlowCore(BaseModel):
    """Common properties for all flow types"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Flow identifier")
    source_id: str = Field(..., description="Source identifier")
    label: Optional[str] = Field(None, description="Freeform string label for the flow")
    description: Optional[str] = Field(None, description="Freeform text describing the flow")
    created_by: Optional[str] = Field(None, description="Entity that created the flow")
    updated_by: Optional[str] = Field(None, description="Entity that updated the flow metadata most recently")
    tags: Optional[Tags] = Field(None, description="Flow tags")
    metadata_version: Optional[str] = Field(None, description="Flow metadata version for change tracking")
    generation: Optional[int] = Field(None, ge=0, description="Number of lossy encodings the flow content has been through")
    created: Optional[datetime] = Field(None, description="Date-time the flow was created")
    metadata_updated: Optional[datetime] = Field(None, description="Date-time the flow metadata was updated")
    segments_updated: Optional[datetime] = Field(None, description="Date-time the flow segments were updated")
    read_only: Optional[bool] = Field(False, description="Whether flow is read-only")
    codec: Optional[str] = Field(None, description="MIME type identification of the coding used")
    container: Optional[str] = Field(None, description="Container MIME type for flow segments")
    avg_bit_rate: Optional[int] = Field(None, ge=0, description="Average bit rate in 1000 bits/second")
    max_bit_rate: Optional[int] = Field(None, ge=0, description="Maximum bit rate in 1000 bits/second")
    segment_duration: Optional[SegmentDuration] = Field(None, description="Target flow segment duration")
    timerange: Optional[TimeRange] = Field(None, description="Timerange of samples available in the flow")
    flow_collection: Optional[FlowCollection] = Field(None, description="Flows collected by this flow")
    collected_by: Optional[List[str]] = Field(None, description="Flows that reference this flow")
    container_mapping: Optional[ContainerMapping] = Field(None, description="Container mapping for this flow")
    
    @field_validator('id', 'source_id')
    @classmethod
    def validate_uuids(cls, v: str) -> str:
        return validate_tams_uuid(v)
    
    @field_validator('codec', 'container')
    @classmethod
    def validate_mime_types(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_mime_type(v)
        return v
    
    @field_serializer('created', 'metadata_updated', 'segments_updated')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class VideoFlow(FlowCore):
    """Video flow model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    format: Literal["urn:x-nmos:format:video"] = Field(default="urn:x-nmos:format:video", description="Content format URN")
    essence_parameters: VideoEssenceParameters = Field(..., description="Video essence parameters")
    codec: str = Field(..., description="MIME type identification of the coding used")


class AudioFlow(FlowCore):
    """Audio flow model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    format: Literal["urn:x-nmos:format:audio"] = Field(default="urn:x-nmos:format:audio", description="Content format URN")
    essence_parameters: AudioEssenceParameters = Field(..., description="Audio essence parameters")
    codec: str = Field(..., description="MIME type identification of the coding used")


class ImageFlow(FlowCore):
    """Image flow model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    format: Literal["urn:x-tam:format:image"] = Field(default="urn:x-tam:format:image", description="Content format URN")
    essence_parameters: ImageEssenceParameters = Field(..., description="Image essence parameters")
    codec: str = Field(..., description="MIME type identification of the coding used")


class DataFlow(FlowCore):
    """Data flow model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    format: Literal["urn:x-nmos:format:data"] = Field(default="urn:x-nmos:format:data", description="Content format URN")
    essence_parameters: DataEssenceParameters = Field(..., description="Data essence parameters")
    codec: str = Field(..., description="MIME type identification of the coding used")


class MultiFlow(FlowCore):
    """Multi flow model - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    format: Literal["urn:x-nmos:format:multi"] = Field(default="urn:x-nmos:format:multi", description="Content format URN")


# Union type for all flow types
Flow = Annotated[Union[VideoFlow, AudioFlow, ImageFlow, DataFlow, MultiFlow], Field(discriminator='format')]
