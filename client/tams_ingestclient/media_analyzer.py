"""
Unified Media Analysis Module

Provides comprehensive media analysis capabilities for all TAMS-supported media types:
- Video files (using FFmpeg)
- Audio files (using FFmpeg)
- Image files (using FFmpeg/ImageIO)
- Data files (basic file analysis)
"""

import asyncio
import logging
import subprocess
import json
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime

from .models import VideoAnalysisResult, VideoIngestRequestUpdated as VideoIngestRequest
from .constants import (
    SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS, SUPPORTED_IMAGE_FORMATS, SUPPORTED_DATA_FORMATS,
    VIDEO_CODEC_MAPPINGS, AUDIO_CODEC_MAPPINGS, IMAGE_CODEC_MAPPINGS, DATA_CODEC_MAPPINGS,
    get_media_type_from_extension, get_mime_type_from_extension, get_supported_extensions,
    TAMS_FORMATS
)

logger = logging.getLogger(__name__)


class MediaAnalysisResult:
    """Unified media analysis result for all media types."""
    
    def __init__(self, media_type: str, **kwargs):
        self.media_type = media_type
        self.file_path = kwargs.get('file_path', '')
        self.file_size = kwargs.get('file_size', 0)
        self.mime_type = kwargs.get('mime_type', '')
        self.format = kwargs.get('format', '')
        self.duration = kwargs.get('duration', 0.0)
        self.analyzed_at = kwargs.get('analyzed_at', datetime.now())
        
        # Video-specific properties
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.fps = kwargs.get('fps', 0.0)
        self.bitrate = kwargs.get('bitrate', 0)
        self.video_codec = kwargs.get('video_codec', '')
        self.audio_codec = kwargs.get('audio_codec', '')
        self.audio_bitrate = kwargs.get('audio_bitrate', 0)
        self.has_audio = kwargs.get('has_audio', False)
        self.has_video = kwargs.get('has_video', False)
        
        # Audio-specific properties
        self.sample_rate = kwargs.get('sample_rate', 0)
        self.channels = kwargs.get('channels', 0)
        self.bits_per_sample = kwargs.get('bits_per_sample', 0)
        
        # Image-specific properties
        self.color_space = kwargs.get('color_space', '')
        self.pixel_format = kwargs.get('pixel_format', '')
        
        # Data-specific properties
        self.encoding = kwargs.get('encoding', '')
        self.line_count = kwargs.get('line_count', 0)
        
        # Common properties
        self.tags = kwargs.get('tags', {})
        self.warnings = kwargs.get('warnings', [])
        self.errors = kwargs.get('errors', [])


class UnifiedMediaAnalyzer:
    """Unified media analyzer for all TAMS-supported media types."""
    
    def __init__(self):
        """Initialize unified media analyzer."""
        self.logger = logger
    
    async def analyze_media(self, media_path: str) -> MediaAnalysisResult:
        """
        Analyze media file and extract metadata for all supported types.
        
        Args:
            media_path: Path to media file
            
        Returns:
            MediaAnalysisResult: Analysis results
            
        Raises:
            ValueError: If media file is invalid or analysis fails
        """
        try:
            self.logger.info(f"Analyzing media: {media_path}")
            
            # Check if file exists
            path = Path(media_path)
            if not path.exists():
                raise ValueError(f"Media file does not exist: {media_path}")
            
            # Get file extension and determine media type
            extension = path.suffix.lower()
            media_type = get_media_type_from_extension(extension)
            mime_type = get_mime_type_from_extension(extension)
            
            # Basic file information
            file_size = path.stat().st_size
            
            # Route to appropriate analyzer based on media type
            if media_type == TAMS_FORMATS["VIDEO"]:
                return await self._analyze_video(media_path, media_type, mime_type, file_size)
            elif media_type == TAMS_FORMATS["AUDIO"]:
                return await self._analyze_audio(media_path, media_type, mime_type, file_size)
            elif media_type == TAMS_FORMATS["IMAGE"]:
                return await self._analyze_image(media_path, media_type, mime_type, file_size)
            elif media_type == TAMS_FORMATS["DATA"]:
                return await self._analyze_data(media_path, media_type, mime_type, file_size)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to analyze media {media_path}: {e}")
            raise ValueError(f"Media analysis failed: {e}")
    
    async def _analyze_video(self, video_path: str, media_type: str, mime_type: str, file_size: int) -> MediaAnalysisResult:
        """Analyze video file using FFmpeg."""
        try:
            # Run FFprobe to get video metadata
            probe_data = await self._run_ffprobe(video_path)
            
            # Parse video-specific data
            video_stream = None
            audio_stream = None
            
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video' and video_stream is None:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            # Extract video properties
            width = video_stream.get('width', 0) if video_stream else 0
            height = video_stream.get('height', 0) if video_stream else 0
            fps = self._parse_fps(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0.0
            video_codec = video_stream.get('codec_name', '') if video_stream else ''
            bitrate = int(probe_data.get('format', {}).get('bit_rate', 0))
            
            # Extract audio properties
            audio_codec = audio_stream.get('codec_name', '') if audio_stream else ''
            sample_rate = audio_stream.get('sample_rate', 0) if audio_stream else 0
            channels = audio_stream.get('channels', 0) if audio_stream else 0
            audio_bitrate = int(audio_stream.get('bit_rate', 0)) if audio_stream else 0
            
            # Calculate duration
            duration = float(probe_data.get('format', {}).get('duration', 0))
            
            return MediaAnalysisResult(
                media_type=media_type,
                file_path=video_path,
                file_size=file_size,
                mime_type=mime_type,
                format=probe_data.get('format', {}).get('format_name', ''),
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                bitrate=bitrate,
                video_codec=video_codec,
                audio_codec=audio_codec,
                audio_bitrate=audio_bitrate,
                has_audio=audio_stream is not None,
                has_video=video_stream is not None,
                analyzed_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Video analysis failed for {video_path}: {e}")
            raise ValueError(f"Video analysis failed: {e}")
    
    async def _analyze_audio(self, audio_path: str, media_type: str, mime_type: str, file_size: int) -> MediaAnalysisResult:
        """Analyze audio file using FFmpeg."""
        try:
            # Run FFprobe to get audio metadata
            probe_data = await self._run_ffprobe(audio_path)
            
            # Find audio stream
            audio_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise ValueError("No audio stream found in file")
            
            # Extract audio properties
            codec = audio_stream.get('codec_name', '')
            sample_rate = int(audio_stream.get('sample_rate', 0))
            channels = int(audio_stream.get('channels', 0))
            bits_per_sample = int(audio_stream.get('bits_per_sample', 0))
            bitrate = int(audio_stream.get('bit_rate', 0))
            
            # Calculate duration
            duration = float(probe_data.get('format', {}).get('duration', 0))
            
            return MediaAnalysisResult(
                media_type=media_type,
                file_path=audio_path,
                file_size=file_size,
                mime_type=mime_type,
                format=probe_data.get('format', {}).get('format_name', ''),
                duration=duration,
                audio_codec=codec,
                sample_rate=sample_rate,
                channels=channels,
                bits_per_sample=bits_per_sample,
                audio_bitrate=bitrate,
                has_audio=True,
                has_video=False,
                analyzed_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Audio analysis failed for {audio_path}: {e}")
            raise ValueError(f"Audio analysis failed: {e}")
    
    async def _analyze_image(self, image_path: str, media_type: str, mime_type: str, file_size: int) -> MediaAnalysisResult:
        """Analyze image file using FFmpeg."""
        try:
            # Run FFprobe to get image metadata
            probe_data = await self._run_ffprobe(image_path)
            
            # Find video stream (images are treated as single-frame videos by FFmpeg)
            video_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ValueError("No image stream found in file")
            
            # Extract image properties
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            codec = video_stream.get('codec_name', '')
            pixel_format = video_stream.get('pix_fmt', '')
            color_space = video_stream.get('color_space', '')
            
            # Images have duration of 0
            duration = 0.0
            
            return MediaAnalysisResult(
                media_type=media_type,
                file_path=image_path,
                file_size=file_size,
                mime_type=mime_type,
                format=probe_data.get('format', {}).get('format_name', ''),
                duration=duration,
                width=width,
                height=height,
                video_codec=codec,
                pixel_format=pixel_format,
                color_space=color_space,
                has_video=True,
                has_audio=False,
                analyzed_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Image analysis failed for {image_path}: {e}")
            raise ValueError(f"Image analysis failed: {e}")
    
    async def _analyze_data(self, data_path: str, media_type: str, mime_type: str, file_size: int) -> MediaAnalysisResult:
        """Analyze data file (basic file analysis)."""
        try:
            # For data files, we do basic file analysis
            path = Path(data_path)
            
            # Try to determine encoding for text files
            encoding = 'utf-8'
            line_count = 0
            
            if mime_type.startswith('text/'):
                try:
                    with open(data_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        line_count = content.count('\n') + 1
                except UnicodeDecodeError:
                    encoding = 'binary'
                    line_count = 0
            
            return MediaAnalysisResult(
                media_type=media_type,
                file_path=data_path,
                file_size=file_size,
                mime_type=mime_type,
                format=path.suffix[1:] if path.suffix else 'unknown',
                duration=0.0,
                encoding=encoding,
                line_count=line_count,
                has_video=False,
                has_audio=False,
                analyzed_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Data analysis failed for {data_path}: {e}")
            raise ValueError(f"Data analysis failed: {e}")
    
    async def _run_ffprobe(self, media_path: str) -> Dict[str, Any]:
        """Run FFprobe to get media metadata."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                media_path
            ]
            
            self.logger.debug(f"Running FFprobe: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                raise RuntimeError(f"FFprobe failed: {error_msg}")
            
            return json.loads(stdout.decode('utf-8'))
            
        except FileNotFoundError:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")
    
    def _parse_fps(self, fps_str: str) -> float:
        """Parse FPS string from FFprobe output."""
        try:
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den)
            else:
                return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def get_supported_formats(self) -> Dict[str, list]:
        """Get all supported file formats by media type."""
        return {
            "video": list(SUPPORTED_VIDEO_FORMATS.keys()),
            "audio": list(SUPPORTED_AUDIO_FORMATS.keys()),
            "image": list(SUPPORTED_IMAGE_FORMATS.keys()),
            "data": list(SUPPORTED_DATA_FORMATS.keys())
        }
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        extension = Path(file_path).suffix.lower()
        return extension in get_supported_extensions()
