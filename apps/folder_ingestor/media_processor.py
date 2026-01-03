"""
Media file chunking using videotools.

Chunks video and audio files into time-based segments.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import List, Optional
import sys

# Import videotools components
try:
    from videotools import VideoProcessor
    from videotools.models import ChunkingTransformConfig, VideoTransformConfig, AudioTransformConfig
    from videotools.utils.process import process_video_with_chunks_async, wait_for_chunk_completion_async
    from videotools.models.processor import ProcessorStatus
    VIDEOTOOLS_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"videotools not available: {e}")
    logger.error("Please install videotools from ~/Developer/gitlab/videotools")
    VIDEOTOOLS_AVAILABLE = False

logger = logging.getLogger(__name__)


async def chunk_media_file(
    file_path: str,
    chunk_duration: int = 30,
    output_dir: Optional[str] = None,
    metadata_file: Optional[str] = None,
    chunk_mode: str = "duration",
    chunk_format: str = "original"
) -> List[Path]:
    """
    Chunk a media file into time-based segments using videotools.
    
    Args:
        file_path: Path to the media file to chunk
        chunk_duration: Duration of each chunk in seconds (default: 30)
        output_dir: Optional output directory (default: temp directory)
        metadata_file: Optional path to metadata file for marker-based chunking
        chunk_mode: Chunking mode - "duration", "metadata_file", or "mp4_markers" (default: "duration")
        chunk_format: Output format - "original" (copy codecs, MP4), "mp4" (transcode to H.264/AAC MP4), or "hls" (HLS-compatible TS) (default: "original")
        
    Returns:
        List of Path objects for the created chunk files
        
    Raises:
        ImportError: If videotools is not available
        FileNotFoundError: If the input file doesn't exist
        RuntimeError: If chunking fails
    """
    if not VIDEOTOOLS_AVAILABLE:
        raise ImportError("videotools module is not available. Please install it.")
    
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Create output directory if not provided
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tams_chunks_")
    else:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    output_path = Path(output_dir)
    
    # Determine output format and codecs based on chunk_format
    if chunk_format == "hls":
        # HLS format: MPEG-TS container with H.264/AAC
        file_ext = ".ts"
        output_format = "mpegts"
        vcodec = "libx264"  # H.264 for HLS compatibility
        acodec = "aac"  # AAC for HLS compatibility
        logger.info(f"Chunking to HLS format (MPEG-TS with H.264/AAC)")
    elif chunk_format == "mp4":
        # MP4 format: MP4 container with H.264/AAC (transcoded)
        file_ext = ".mp4"
        output_format = "mp4"
        vcodec = "libx264"  # H.264 for MP4 compatibility
        acodec = "aac"  # AAC for MP4 compatibility
        logger.info(f"Chunking to MP4 format (H.264/AAC)")
    else:
        # Original format: copy codecs, MP4 container
        file_ext = ".mp4"
        output_format = "mp4"
        vcodec = "copy"  # Copy codec for speed
        acodec = "copy"  # Copy codec for speed
        logger.info(f"Chunking to original format (copy codecs, MP4)")
    
    # Generate chunk filename template
    file_stem = file_path_obj.stem
    chunk_template = f"{file_stem}_chunk_{{chunk_id}}{file_ext}"
    
    try:
        # Create VideoProcessor
        processor = VideoProcessor()
        await processor.start()
        
        try:
            # Create video and audio transform configs
            video_config = VideoTransformConfig(
                codec=vcodec,
                format=output_format
            )
            audio_config = AudioTransformConfig(
                codec=acodec
            )
            
            # For mp4_markers mode, we need to set video_source
            video_source = None
            if chunk_mode == "mp4_markers":
                from videotools.models import VideoSource
                video_source = VideoSource(path=str(file_path_obj.absolute()))
            
            # Create chunking config
            chunk_config = ChunkingTransformConfig(
                segment_duration=chunk_duration,
                include_timestamps=True,
                chunk_mode=chunk_mode,
                metadata_file=metadata_file if chunk_mode == "metadata_file" else None,
                marker_fallback=True,  # Fallback to markers if chapters not found
                video_source=video_source,
                video_config=video_config,
                audio_config=audio_config
            )
            
            # Process video with chunks using helper function
            result = await process_video_with_chunks_async(
                processor=processor,
                input_path=str(file_path_obj.absolute()),
                chunk_config=chunk_config,
                output_path=str(output_path),
                filename_template=chunk_template,
                duration=chunk_duration,
                wait_for_completion=True,
                timeout=3600  # 1 hour max
            )
            
            if result is None:
                raise RuntimeError("Chunking timed out after 3600 seconds")
            
            # Type check: result should be ProcessingResult when wait_for_completion=True
            from videotools.models import ProcessingResult
            if not isinstance(result, ProcessingResult):
                raise RuntimeError(f"Unexpected result type: {type(result)}")
            
            if result.status != ProcessorStatus.COMPLETED:
                error_msg = getattr(result, 'error_message', 'Unknown error')
                raise RuntimeError(f"Chunking failed: {error_msg}")
            
            # Extract chunk files from result
            chunk_files = []
            if result.outputs:
                for output in result.outputs:
                    if 'chunks' in output and isinstance(output['chunks'], list):
                        # ChunkOutput provides chunks metadata
                        for chunk_info in output['chunks']:
                            chunk_file = Path(chunk_info.get('file', ''))
                            if chunk_file.exists():
                                chunk_files.append(chunk_file)
                    elif 'file' in output:
                        # Single file output (shouldn't happen with ChunkOutput)
                        chunk_file = Path(output['file'])
                        if chunk_file.exists():
                            chunk_files.append(chunk_file)
            
            # If no chunks found in metadata, search for chunk files
            if not chunk_files:
                pattern = chunk_template.replace('{chunk_id}', '*')
                chunk_files = sorted(output_path.glob(pattern))
            
            # Sort chunks by index (extract from filename)
            def get_chunk_index(chunk_path: Path) -> int:
                try:
                    # Extract number from filename like "file_chunk_000.mp4"
                    name = chunk_path.stem
                    if '_chunk_' in name:
                        num_str = name.split('_chunk_')[-1]
                        return int(num_str)
                except (ValueError, IndexError):
                    pass
                return 0
            
            chunk_files = sorted(chunk_files, key=get_chunk_index)
            
            logger.info(f"Created {len(chunk_files)} chunks for {file_path}")
            return chunk_files
                
        finally:
            await processor.stop()
            
    except Exception as e:
        logger.error(f"Failed to chunk media file {file_path}: {e}")
        raise

