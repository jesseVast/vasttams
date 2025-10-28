"""
HLS Data Models

Models for HLS playlist generation and streaming.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HLSSegment(BaseModel):
    """HLS segment information"""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    url: str = Field(..., description="Segment URL")
    duration: float = Field(..., description="Segment duration in seconds")
    sequence: int = Field(..., description="Segment sequence number")
    discontinuity: bool = Field(False, description="Whether to mark discontinuity")


class HLSPlaylist(BaseModel):
    """HLS playlist data model"""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    version: int = Field(3, description="HLS version")
    target_duration: float = Field(1.0, description="Target segment duration in seconds")
    media_sequence: int = Field(0, description="First segment sequence number")
    segments: List[HLSSegment] = Field(default_factory=list, description="Playlist segments")
    endlist: bool = Field(False, description="Whether playlist has ended")


class HLSStream(BaseModel):
    """HLS stream variant for master playlist"""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    bandwidth: int = Field(..., description="Bitrate in bits per second")
    resolution: Optional[str] = Field(None, description="Resolution (e.g., 1920x1080)")
    codec: Optional[str] = Field(None, description="Codec string")
    playlist_url: str = Field(..., description="Playlist URL")


class HLSMasterManifest(BaseModel):
    """HLS master manifest (for multi-bitrate)"""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    streams: List[HLSStream] = Field(default_factory=list, description="Stream variants")

