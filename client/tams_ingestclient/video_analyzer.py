"""
Video Analysis Module

Provides video analysis capabilities using FFmpeg to extract metadata,
codec information, and other properties needed for TAMS ingestion.
"""

import asyncio
import logging
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .models import VideoAnalysisResult
from .constants import (
    SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS,
    VIDEO_CODEC_MAPPINGS, AUDIO_CODEC_MAPPINGS
)

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """Video analyzer using FFmpeg for metadata extraction."""
    
    def __init__(self):
        """Initialize video analyzer."""
        self.logger = logger
    
    async def analyze_video(self, video_path: str) -> VideoAnalysisResult:
        """
        Analyze video file and extract metadata.
        
        Args:
            video_path: Path to video file
            
        Returns:
            VideoAnalysisResult: Analysis results
            
        Raises:
            ValueError: If video file is invalid or analysis fails
        """
        try:
            self.logger.info(f"Analyzing video: {video_path}")
            
            # Check if file exists
            path = Path(video_path)
            if not path.exists():
                raise ValueError(f"Video file does not exist: {video_path}")
            
            # Run FFprobe to get video metadata
            probe_data = await self._run_ffprobe(video_path)
            
            # Parse the probe data
            analysis = self._parse_probe_data(probe_data, video_path)
            
            self.logger.info(f"Video analysis completed: {analysis.duration}s, {analysis.width}x{analysis.height}, {analysis.fps}fps")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze video {video_path}: {e}")
            raise ValueError(f"Video analysis failed: {e}")
    
    async def _run_ffprobe(self, video_path: str) -> Dict[str, Any]:
        """Run FFprobe to get video metadata."""
        try:
            # FFprobe command to get comprehensive metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-show_chapters',
                video_path
            ]
            
            self.logger.debug(f"Running FFprobe: {' '.join(cmd)}")
            
            # Run FFprobe asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                raise RuntimeError(f"FFprobe failed: {error_msg}")
            
            # Parse JSON output
            probe_data = json.loads(stdout.decode('utf-8'))
            return probe_data
            
        except FileNotFoundError:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")
        except Exception as e:
            raise RuntimeError(f"FFprobe execution failed: {e}")
    
    def _parse_probe_data(self, probe_data: Dict[str, Any], video_path: str) -> VideoAnalysisResult:
        """Parse FFprobe data into VideoAnalysisResult."""
        try:
            format_info = probe_data.get('format', {})
            streams = probe_data.get('streams', [])
            
            # Find video and audio streams
            video_stream = None
            audio_stream = None
            
            for stream in streams:
                if stream.get('codec_type') == 'video' and video_stream is None:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            if not video_stream:
                raise ValueError("No video stream found in file")
            
            # Extract basic information
            duration = float(format_info.get('duration', 0))
            file_size = int(format_info.get('size', 0))
            container_format = format_info.get('format_name', '').split(',')[0]
            
            # Extract video information
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            # Calculate FPS
            fps_str = video_stream.get('r_frame_rate', '0/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) != 0 else 0
            else:
                fps = float(fps_str)
            
            # Extract codecs
            video_codec = video_stream.get('codec_name', 'unknown')
            audio_codec = audio_stream.get('codec_name', 'unknown') if audio_stream else None
            
            # Extract bitrates
            video_bitrate = int(video_stream.get('bit_rate', 0))
            audio_bitrate = int(audio_stream.get('bit_rate', 0)) if audio_stream else None
            
            # Extract additional metadata
            color_space = video_stream.get('color_space')
            pixel_format = video_stream.get('pix_fmt')
            
            # Map codecs to standard names
            video_codec = self._map_codec(video_codec, VIDEO_CODEC_MAPPINGS)
            if audio_codec:
                audio_codec = self._map_codec(audio_codec, AUDIO_CODEC_MAPPINGS)
            
            return VideoAnalysisResult(
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                bitrate=video_bitrate,
                audio_bitrate=audio_bitrate,
                video_codec=video_codec,
                audio_codec=audio_codec,
                file_size=file_size,
                format=container_format,
                has_audio=audio_stream is not None,
                has_video=True,
                color_space=color_space,
                pixel_format=pixel_format,
                analyzed_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse probe data: {e}")
            raise ValueError(f"Failed to parse video metadata: {e}")
    
    def _map_codec(self, codec: str, mappings: Dict[str, str]) -> str:
        """Map FFmpeg codec name to standard name."""
        for standard_name, ffmpeg_name in mappings.items():
            if ffmpeg_name in codec or codec in ffmpeg_name:
                return standard_name
        return codec
    
    def get_video_format(self, video_path: str) -> str:
        """Get video format from file extension."""
        path = Path(video_path)
        suffix = path.suffix.lower()
        return SUPPORTED_VIDEO_FORMATS.get(suffix, 'video/mp4')
    
    def is_video_file(self, video_path: str) -> bool:
        """Check if file is a supported video format."""
        path = Path(video_path)
        suffix = path.suffix.lower()
        return suffix in SUPPORTED_VIDEO_FORMATS
    
    def estimate_segment_count(self, duration: float, chunk_duration: int, overlap: int = 0) -> int:
        """Estimate number of segments for given duration and chunk size."""
        if chunk_duration <= 0:
            return 1
        
        effective_duration = chunk_duration - overlap
        if effective_duration <= 0:
            return 1
        
        return max(1, int(duration / effective_duration))
    
    def get_optimal_chunk_duration(self, duration: float, target_segments: int = 10) -> int:
        """Get optimal chunk duration for target number of segments."""
        if target_segments <= 0:
            return 30
        
        optimal_duration = duration / target_segments
        # Round to nearest 5 seconds
        return max(5, int(optimal_duration / 5) * 5)












