"""
Unified TAMS Ingest Client

Main client for uploading all media types to TAMS service with automatic source/flow creation,
media analysis, and S3 integration. Supports video, audio, image, and data files.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import tempfile
import subprocess

from .config import TAMSIngestConfig
from .models import (
    VideoIngestRequest, VideoIngestResult, VideoAnalysisResult, TAMSSegment,
    Source, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow, FlowSegment, 
    Tags, ContentFormat, MimeType, TimeRange
)
from .tams_client import TAMSClient, TAMSError
from .video_analyzer import VideoAnalyzer
from .media_analyzer import UnifiedMediaAnalyzer, MediaAnalysisResult
from .constants import TAMS_FORMATS, DEFAULT_SOURCE_LABEL, DEFAULT_FLOW_LABEL

# Import S3 client from existing store module
try:
    from external.vaststore.vasts3.client import S3Client
    from external.vaststore.vasts3.config import S3Config as StoreS3Config
except ImportError:
    S3Client = None
    StoreS3Config = None

logger = logging.getLogger(__name__)


class UnifiedTAMSIngestClient:
    """
    Unified TAMS Ingest Client.
    
    Provides a high-level interface for uploading all media types to TAMS with:
    - Automatic source and flow creation
    - Media analysis and parameter detection for video, audio, image, and data files
    - S3 integration for media storage
    - Segment creation and upload
    - Support for all TAMS media formats
    """
    
    def __init__(self, config: Optional[TAMSIngestConfig] = None):
        """
        Initialize TAMS ingest client.
        
        Args:
            config: TAMS ingest configuration
        """
        self.config = config or TAMSIngestConfig()
        self.logger = logger
        
        # Initialize TAMS client
        tams_config = self.config.get_tams_api_config()
        self.tams_client = TAMSClient(**tams_config)
        
        # Initialize media analyzers
        self.video_analyzer = VideoAnalyzer()
        self.media_analyzer = UnifiedMediaAnalyzer()
        
        # Initialize S3 client if available
        self.s3_client = None
        if self.config.upload_to_s3 and S3Client is not None:
            try:
                s3_config = StoreS3Config(**self.config.get_s3_config())
                self.s3_client = S3Client(s3_config)
                self.logger.info("S3 client initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
        
        self.logger.info("TAMS Ingest Client initialized")
    
    async def ingest_media(self, media_path: str, **kwargs) -> VideoIngestResult:
        """
        Ingest any supported media type to TAMS.
        
        Args:
            media_path: Path to media file (video, audio, image, or data)
            **kwargs: Additional options for ingestion
            
        Returns:
            VideoIngestResult: Ingestion results
        """
        try:
            self.logger.info(f"Starting media ingestion: {media_path}")
            
            # Analyze the media file
            analysis = await self.media_analyzer.analyze_media(media_path)
            
            # Create appropriate source and flow based on media type
            source_id = await self._create_media_source(analysis, **kwargs)
            flow_id = await self._create_media_flow(analysis, source_id, **kwargs)
            
            # Create segments for the media
            segments = await self._create_media_segments(analysis, flow_id, **kwargs)
            
            # Calculate processing time
            processing_time = (datetime.now() - analysis.analyzed_at).total_seconds()
            
            return VideoIngestResult(
                success=True,
                source_id=source_id,
                flow_id=flow_id,
                segments=segments,
                total_duration=analysis.duration,
                segment_count=len(segments),
                total_file_size=analysis.file_size,
                processing_time=processing_time,
                started_at=analysis.analyzed_at,
                completed_at=datetime.now(),
                video_analysis=VideoAnalysisResult(
                    duration=analysis.duration,
                    width=analysis.width,
                    height=analysis.height,
                    fps=analysis.fps,
                    bitrate=analysis.bitrate,
                    audio_bitrate=analysis.audio_bitrate,
                    video_codec=analysis.video_codec,
                    audio_codec=analysis.audio_codec,
                    file_size=analysis.file_size,
                    format=analysis.format,
                    has_audio=analysis.has_audio,
                    has_video=analysis.has_video,
                    color_space=analysis.color_space,
                    pixel_format=analysis.pixel_format,
                    analyzed_at=analysis.analyzed_at
                ) if analysis.media_type == TAMS_FORMATS["VIDEO"] else None
            )
            
        except Exception as e:
            self.logger.error(f"Media ingestion failed: {e}")
            return VideoIngestResult(
                success=False,
                error_message=str(e),
                total_duration=0,
                processing_time=0,
                started_at=datetime.now(),
                completed_at=datetime.now()
            )
    
    async def _create_media_source(self, analysis: MediaAnalysisResult, **kwargs) -> str:
        """Create TAMS source for any media type."""
        try:
            # Determine source label based on media type
            media_type_labels = {
                TAMS_FORMATS["VIDEO"]: "Video Source",
                TAMS_FORMATS["AUDIO"]: "Audio Source", 
                TAMS_FORMATS["IMAGE"]: "Image Source",
                TAMS_FORMATS["DATA"]: "Data Source",
                TAMS_FORMATS["MULTI"]: "Multi Source"
            }
            
            label = kwargs.get('source_label', media_type_labels.get(analysis.media_type, "Media Source"))
            description = kwargs.get('source_description', f"{analysis.media_type} source created by TAMS Ingest Client")
            
            source_data = {
                "format": analysis.media_type,
                "label": label,
                "description": description,
                "tags": kwargs.get('tags', {})
            }
            
            source_id = await self.tams_client.create_source(source_data)
            self.logger.info(f"Created {analysis.media_type} source: {source_id}")
            return source_id
            
        except Exception as e:
            self.logger.error(f"Failed to create media source: {e}")
            raise
    
    async def _create_media_flow(self, analysis: MediaAnalysisResult, source_id: str, **kwargs) -> str:
        """Create TAMS flow for any media type."""
        try:
            # Determine flow label based on media type
            media_type_labels = {
                TAMS_FORMATS["VIDEO"]: "Video Flow",
                TAMS_FORMATS["AUDIO"]: "Audio Flow",
                TAMS_FORMATS["IMAGE"]: "Image Flow", 
                TAMS_FORMATS["DATA"]: "Data Flow",
                TAMS_FORMATS["MULTI"]: "Multi Flow"
            }
            
            label = kwargs.get('flow_label', media_type_labels.get(analysis.media_type, "Media Flow"))
            description = kwargs.get('flow_description', f"{analysis.media_type} flow created by TAMS Ingest Client")
            
            # Build flow data based on media type
            flow_data = {
                "source_id": source_id,
                "format": analysis.media_type,
                "codec": analysis.video_codec or analysis.audio_codec or "unknown",
                "label": label,
                "description": description,
                "tags": kwargs.get('tags', {})
            }
            
            # Add media-specific properties
            if analysis.media_type == TAMS_FORMATS["VIDEO"]:
                flow_data.update({
                    "frame_width": analysis.width,
                    "frame_height": analysis.height,
                    "frame_rate": str(analysis.fps),
                    "max_bit_rate": analysis.bitrate,
                    "avg_bit_rate": analysis.bitrate
                })
            elif analysis.media_type == TAMS_FORMATS["AUDIO"]:
                flow_data.update({
                    "sample_rate": analysis.sample_rate,
                    "bits_per_sample": analysis.bits_per_sample,
                    "channels": analysis.channels,
                    "max_bit_rate": analysis.audio_bitrate,
                    "avg_bit_rate": analysis.audio_bitrate
                })
            elif analysis.media_type == TAMS_FORMATS["IMAGE"]:
                flow_data.update({
                    "frame_width": analysis.width,
                    "frame_height": analysis.height
                })
            
            flow_id = await self.tams_client.create_flow(flow_data)
            self.logger.info(f"Created {analysis.media_type} flow: {flow_id}")
            return flow_id
            
        except Exception as e:
            self.logger.error(f"Failed to create media flow: {e}")
            raise
    
    async def _create_media_segments(self, analysis: MediaAnalysisResult, flow_id: str, **kwargs) -> List[TAMSSegment]:
        """Create segments for any media type."""
        try:
            segments = []
            
            # For images and data files, create a single segment
            if analysis.media_type in [TAMS_FORMATS["IMAGE"], TAMS_FORMATS["DATA"]]:
                file_stem = Path(analysis.file_path).stem
                segment = TAMSSegment(
                    object_id=f"segment_{file_stem}",
                    timerange="0:00:00_0:00:00" if analysis.duration == 0 else f"0:00:00_{analysis.duration}",
                    file_path=analysis.file_path,
                    file_size=analysis.file_size,
                    duration=analysis.duration,
                    created_at=datetime.now()
                )
                segments.append(segment)
            
            # For audio and video files, create time-based segments
            elif analysis.media_type in [TAMS_FORMATS["AUDIO"], TAMS_FORMATS["VIDEO"]]:
                chunk_duration = kwargs.get('chunk_duration', 30)
                segment_overlap = kwargs.get('segment_overlap', 0)
                
                current_time = 0
                segment_index = 0
                
                file_stem = Path(analysis.file_path).stem
                while current_time < analysis.duration:
                    end_time = min(current_time + chunk_duration, analysis.duration)
                    
                    segment = TAMSSegment(
                        object_id=f"segment_{file_stem}_{segment_index:03d}",
                        timerange=f"{self._format_time(current_time)}_{self._format_time(end_time)}",
                        file_path=analysis.file_path,
                        file_size=analysis.file_size,
                        duration=end_time - current_time,
                        created_at=datetime.now()
                    )
                    segments.append(segment)
                    
                    current_time = end_time - segment_overlap
                    segment_index += 1
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Failed to create media segments: {e}")
            raise
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to TAMS time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    async def ingest_video(self, request: VideoIngestRequest) -> VideoIngestResult:
        """
        Ingest a video into TAMS.
        
        Args:
            request: Video ingestion request
            
        Returns:
            VideoIngestResult: Ingestion result
        """
        start_time = datetime.now()
        self.logger.info(f"Starting video ingestion: {request.video_path}")
        
        try:
            # Step 1: Analyze video
            self.logger.info("Analyzing video...")
            analysis = await self.video_analyzer.analyze_video(request.video_path)
            
            # Step 2: Create or get source
            source_id = await self._ensure_source_exists(request, analysis)
            
            # Step 3: Create or get flow
            flow_id = await self._ensure_flow_exists(request, analysis, source_id)
            
            # Step 4: Create flow segments (time ranges)
            segments = await self._create_flow_segments(request, analysis, flow_id)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate statistics
            total_file_size = sum(seg.file_size or 0 for seg in segments)
            
            result = VideoIngestResult(
                success=True,
                source_id=source_id,
                flow_id=flow_id,
                segments=segments,
                total_duration=analysis.duration,
                segment_count=len(segments),
                total_file_size=total_file_size,
                processing_time=processing_time,
                started_at=start_time,
                completed_at=datetime.now(),
                video_analysis=analysis,
                source_config=request.source_config,
                flow_config=request.flow_config
            )
            
            self.logger.info(f"Video ingestion completed: {len(segments)} segments, {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Video ingestion failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return VideoIngestResult(
                success=False,
                error_message=str(e),
                total_duration=0,
                processing_time=processing_time,
                started_at=start_time,
                completed_at=datetime.now()
            )
    
    async def create_source(self, source_config: Dict[str, Any]) -> str:
        """
        Create a TAMS source.
        
        Args:
            source_config: Source configuration dictionary
            
        Returns:
            str: Created source ID
        """
        try:
            # Check if source already exists
            existing_sources = await self.tams_client.list_sources({
                'label': source_config.get('label'),
                'format': source_config.get('format', 'urn:x-nmos:format:video')
            })
            
            if existing_sources:
                self.logger.info(f"Source already exists: {existing_sources[0].id}")
                return existing_sources[0].id
            
            # Create source data using official API model
            import uuid
            source_data = Source(
                id=uuid.uuid4(),
                format=source_config.get('format', 'urn:x-nmos:format:video'),
                label=source_config.get('label'),
                description=source_config.get('description'),
                tags=Tags(source_config.get('tags', {})) if source_config.get('tags') else None
            )
            
            source_id = await self.tams_client.create_source(source_data.model_dump())
            self.logger.info(f"Created TAMS source: {source_id}")
            return source_id
            
        except Exception as e:
            self.logger.error(f"Failed to create source: {e}")
            raise TAMSError(f"Source creation failed: {e}")
    
    async def create_flow(self, flow_config: Dict[str, Any]) -> str:
        """
        Create a TAMS flow.
        
        Args:
            flow_config: Flow configuration dictionary
            
        Returns:
            str: Created flow ID
        """
        try:
            # Check if flow already exists
            existing_flows = await self.tams_client.list_flows({
                'source_id': flow_config.get('source_id'),
                'label': flow_config.get('label')
            })
            
            if existing_flows:
                self.logger.info(f"Flow already exists: {existing_flows[0].id}")
                return existing_flows[0].id
            
            # Create flow data using official API model
            import uuid
            flow_data = VideoFlow(
                id=uuid.uuid4(),
                source_id=uuid.UUID(flow_config.get('source_id')),
                format=flow_config.get('format', 'urn:x-nmos:format:video'),
                codec=flow_config.get('codec', 'video/mp4'),
                label=flow_config.get('label'),
                description=flow_config.get('description'),
                tags=Tags(flow_config.get('tags', {})) if flow_config.get('tags') else None,
                frame_width=flow_config.get('frame_width', 1920),
                frame_height=flow_config.get('frame_height', 1080),
                frame_rate=flow_config.get('frame_rate', '25/1')
            )
            
            flow_id = await self.tams_client.create_flow(flow_data.model_dump())
            self.logger.info(f"Created TAMS flow: {flow_id}")
            return flow_id
            
        except Exception as e:
            self.logger.error(f"Failed to create flow: {e}")
            raise TAMSError(f"Flow creation failed: {e}")
    
    async def _ensure_source_exists(self, request: VideoIngestRequest, 
                                  analysis: VideoAnalysisResult) -> str:
        """Ensure source exists, create if needed."""
        if request.source_config:
            return await self.create_source(request.source_config)
        
        # Auto-create source based on video analysis
        source_config = {
            'label': request.metadata.get('title', DEFAULT_SOURCE_LABEL),
            'description': request.metadata.get('description', f"Video source for {Path(request.video_path).name}"),
            'format': 'urn:x-nmos:format:video',
            'tags': request.tags
        }
        
        return await self.create_source(source_config)
    
    async def _ensure_flow_exists(self, request: VideoIngestRequest, 
                                analysis: VideoAnalysisResult, source_id: str) -> str:
        """Ensure flow exists, create if needed."""
        if request.flow_config:
            request.flow_config['source_id'] = source_id
            return await self.create_flow(request.flow_config)
        
        # Auto-create flow based on video analysis
        flow_config = {
            'source_id': source_id,
            'label': request.metadata.get('title', DEFAULT_FLOW_LABEL),
            'description': request.metadata.get('description', f"Video flow for {Path(request.video_path).name}"),
            'format': 'urn:x-nmos:format:video',
            'codec': f'video/{analysis.video_codec}',
            'frame_width': analysis.width,
            'frame_height': analysis.height,
            'frame_rate': f'{int(analysis.fps)}/1',
            'tags': request.tags
        }
        
        return await self.create_flow(flow_config)
    
    async def _create_flow_segments(self, request: VideoIngestRequest, 
                                   analysis: VideoAnalysisResult, 
                                   flow_id: str) -> List[TAMSSegment]:
        """Create flow segments (time ranges) in TAMS."""
        segments = []
        chunk_duration = request.chunk_duration
        overlap = request.segment_overlap
        
        # Calculate number of segments
        num_segments = self.video_analyzer.estimate_segment_count(
            analysis.duration, chunk_duration, overlap
        )
        
        self.logger.info(f"Creating {num_segments} flow segments of {chunk_duration}s each")
        
        # Create flow segments (time ranges)
        for i in range(num_segments):
            start_time = i * (chunk_duration - overlap)
            end_time = min(start_time + chunk_duration, analysis.duration)
            
            if start_time >= analysis.duration:
                break
            
            # Create flow segment (time range metadata)
            segment = await self._create_flow_segment(
                request, analysis, flow_id, i, start_time, end_time
            )
            segments.append(segment)
        
        return segments
    
    async def _create_flow_segment(self, request: VideoIngestRequest, 
                                 analysis: VideoAnalysisResult, flow_id: str,
                                 segment_index: int, start_time: float, 
                                 end_time: float, chunk_path: Optional[str] = None) -> TAMSSegment:
        """Create a single flow segment (time range) in TAMS with optional chunk."""
        try:
            # Generate segment object ID
            object_id = f"segment-{Path(request.video_path).stem}-{segment_index:03d}"
            
            # Create time range string using video start time as base
            base_time = datetime(2025, 1, 1, 0, 0, 0)  # Fixed base time for consistency
            start_iso = (base_time + timedelta(seconds=start_time)).isoformat() + "Z"
            end_iso = (base_time + timedelta(seconds=end_time)).isoformat() + "Z"
            timerange = f"{start_iso}/{end_iso}"
            
            # Calculate segment metadata
            duration = end_time - start_time
            sample_rate = int(analysis.fps) if analysis.fps else 25
            sample_offset = int(start_time * sample_rate)
            sample_count = int(duration * sample_rate)
            key_frame_count = int(duration * sample_rate / 30)  # Estimate key frames
            
            # Create flow segment data (FlowSegment schema)
            segment_data = {
                'object_id': object_id,
                'timerange': timerange,
                'ts_offset': f"{start_time:.3f}",
                'last_duration': f"{duration:.3f}",
                'sample_offset': sample_offset,
                'sample_count': sample_count,
                'key_frame_count': key_frame_count,
                'get_urls': []  # Will be populated by TAMS
            }
            
            # Create flow segment in TAMS with optional chunk
            if chunk_path:
                uploaded_object_id = await self.create_flow_segment_with_chunk(
                    flow_id, segment_data, chunk_path
                )
            else:
                uploaded_object_id = await self.tams_client.create_flow_segment(
                    flow_id, segment_data
                )
            
            # Create TAMS segment object
            segment = TAMSSegment(
                object_id=uploaded_object_id or object_id,
                timerange=timerange,
                ts_offset=f"{start_time:.3f}",
                last_duration=f"{duration:.3f}",
                sample_offset=sample_offset,
                sample_count=sample_count,
                key_frame_count=key_frame_count,
                duration=duration,
                get_urls=[]
            )
            
            self.logger.info(f"Created flow segment {segment_index}: {object_id} ({timerange})")
            return segment
            
        except Exception as e:
            self.logger.error(f"Failed to create flow segment {segment_index}: {e}")
            raise TAMSError(f"Flow segment creation failed: {e}")
    
    async def create_flow_segment_with_chunk(self, flow_id: str, segment_data: Dict[str, Any], 
                                           chunk: str) -> str:
        """
        Create a flow segment with a chunk (file path or S3 URL).
        
        Args:
            flow_id: Flow ID to create segment for
            segment_data: FlowSegment data including object_id, timerange, etc.
            chunk: Chunk path (local file) or S3 URL
            
        Returns:
            str: Created segment object_id
        """
        # Determine if chunk is a local file or S3 URL
        if chunk.startswith(('http://', 'https://', 's3://')):
            # S3 URL - create segment without file upload
            return await self.tams_client.create_flow_segment(flow_id, segment_data)
        else:
            # Local file path - create segment with file upload
            return await self.tams_client.create_flow_segment(flow_id, segment_data, chunk)
    
    async def ingest_chunks(self, flow_id: str, chunks: List[Dict[str, Any]]) -> List[TAMSSegment]:
        """
        Ingest multiple chunks into TAMS flow segments.
        
        Args:
            flow_id: Flow ID to create segments for
            chunks: List of chunk dictionaries with:
                - object_id: Segment object ID
                - timerange: Time range string
                - chunk_path: Local file path or S3 URL
                - Optional: ts_offset, last_duration, sample_offset, sample_count, key_frame_count
                
        Returns:
            List of created TAMSSegment objects
        """
        segments = []
        
        for i, chunk_data in enumerate(chunks):
            try:
                # Extract chunk information
                object_id = chunk_data.get('object_id', f'chunk-{i:03d}')
                timerange = chunk_data.get('timerange', '')
                chunk_path = chunk_data.get('chunk_path')
                
                # Create segment data
                segment_data = {
                    'object_id': object_id,
                    'timerange': timerange,
                    'ts_offset': chunk_data.get('ts_offset'),
                    'last_duration': chunk_data.get('last_duration'),
                    'sample_offset': chunk_data.get('sample_offset'),
                    'sample_count': chunk_data.get('sample_count'),
                    'key_frame_count': chunk_data.get('key_frame_count'),
                    'get_urls': []
                }
                
                # Create flow segment with chunk
                if chunk_path:
                    uploaded_object_id = await self.create_flow_segment_with_chunk(
                        flow_id, segment_data, chunk_path
                    )
                else:
                    uploaded_object_id = await self.tams_client.create_flow_segment(
                        flow_id, segment_data
                    )
                
                # Create TAMS segment object
                segment = TAMSSegment(
                    object_id=uploaded_object_id or object_id,
                    timerange=timerange,
                    ts_offset=chunk_data.get('ts_offset'),
                    last_duration=chunk_data.get('last_duration'),
                    sample_offset=chunk_data.get('sample_offset'),
                    sample_count=chunk_data.get('sample_count'),
                    key_frame_count=chunk_data.get('key_frame_count'),
                    duration=chunk_data.get('duration'),
                    get_urls=[]
                )
                
                segments.append(segment)
                self.logger.info(f"Created flow segment {i}: {object_id} ({timerange})")
                
            except Exception as e:
                self.logger.error(f"Failed to create flow segment {i}: {e}")
                raise TAMSError(f"Chunk ingestion failed: {e}")
        
        return segments
    
    async def health_check(self) -> bool:
        """Check if TAMS API is healthy."""
        return await self.tams_client.health_check()


# Convenience functions
async def ingest_video_unified(video_path: str, config: Optional[TAMSIngestConfig] = None, 
                             **kwargs) -> VideoIngestResult:
    """
    Convenience function to ingest a video.
    
    Args:
        video_path: Path to video file
        config: Optional configuration
        **kwargs: Additional parameters for VideoIngestRequest
        
    Returns:
        VideoIngestResult: Ingestion result
    """
    client = UnifiedTAMSIngestClient(config)
    request = VideoIngestRequest(video_path=video_path, **kwargs)
    return await client.ingest_video(request)


async def create_source_unified(source_config: Dict[str, Any], 
                              config: Optional[TAMSIngestConfig] = None) -> str:
    """
    Convenience function to create a source.
    
    Args:
        source_config: Source configuration
        config: Optional configuration
        
    Returns:
        str: Created source ID
    """
    client = UnifiedTAMSIngestClient(config)
    return await client.create_source(source_config)


async def create_flow_unified(flow_config: Dict[str, Any], 
                            config: Optional[TAMSIngestConfig] = None) -> str:
    """
    Convenience function to create a flow.
    
    Args:
        flow_config: Flow configuration
        config: Optional configuration
        
    Returns:
        str: Created flow ID
    """
    client = UnifiedTAMSIngestClient(config)
    return await client.create_flow(flow_config)
