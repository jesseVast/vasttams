"""
File processing for folder ingestor.

Handles file detection, chunking, uploading, and data file processing.
"""

import asyncio
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src" / "client"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from vasttamsclient import TAMSClient

from file_detector import detect_media_type
from media_processor import chunk_media_file
from metadata_matcher import find_metadata_files, detect_metadata_format

logger = logging.getLogger(__name__)


class FileProcessor:
    """Processes files for folder ingestion."""
    
    def __init__(
        self,
        client: Optional[TAMSClient],
        chunk_duration: int,
        dry_run: bool,
        max_parallel_uploads: int,
        no_chunking: bool,
        use_metadata: bool = False,
        include_originals: bool = False
    ):
        """
        Initialize file processor.
        
        Args:
            client: TAMS client instance
            chunk_duration: Duration of each chunk in seconds
            dry_run: If True, don't create anything in TAMS
            max_parallel_uploads: Maximum number of parallel uploads
            no_chunking: If True, upload files as-is without chunking (overrides use_metadata)
            use_metadata: If True, use metadata files for marker-based chunking when available
            include_originals: If True, also upload original files to separate flow when chunking
        """
        self.client = client
        self.chunk_duration = chunk_duration
        self.dry_run = dry_run
        self.max_parallel_uploads = max_parallel_uploads
        self.no_chunking = no_chunking
        self.use_metadata = use_metadata
        self.include_originals = include_originals
        self._upload_semaphore = asyncio.Semaphore(max_parallel_uploads)
    
    def detect_media_types(
        self,
        files: List[Path],
        metadata_map: Dict[Path, Path]
    ) -> Tuple[Set[str], Dict[Path, str], Dict[Path, bool]]:
        """
        Detect media types for all files.
        
        Args:
            files: List of file paths
            metadata_map: Map of media_file -> metadata_file
            
        Returns:
            Tuple of (media_types_detected, file_media_types, file_chunking_mode)
        """
        media_types_detected: Set[str] = set()
        file_media_types: Dict[Path, str] = {}
        file_chunking_mode: Dict[Path, bool] = {}
        metadata_files = set(metadata_map.values())
        
        for file_path in files:
            media_type = detect_media_type(str(file_path))
            if media_type in ("video", "audio"):
                # Determine if this file should be chunked
                # no_chunking always prevents chunking (even if metadata exists)
                # If no_chunking is False, chunking is enabled
                # use_metadata determines if we use metadata-based chunking when available
                has_metadata = file_path in metadata_map
                should_chunk = not self.no_chunking
                
                # Create flow key based on chunking mode
                if should_chunk:
                    flow_key = media_type  # chunked
                    media_types_detected.add(flow_key)
                    file_media_types[file_path] = flow_key
                    file_chunking_mode[file_path] = True
                    
                    # If include_originals is set, also create an original flow
                    if self.include_originals:
                        original_flow_key = f"{media_type}_original"
                        media_types_detected.add(original_flow_key)
                        # Note: We'll handle the original upload separately in processing
                    
                    if has_metadata and self.use_metadata:
                        logger.debug(f"📎 {file_path.name} will be chunked using metadata file")
                    else:
                        logger.debug(f"✂️  {file_path.name} will be chunked by duration")
                else:
                    flow_key = f"{media_type}_unchunked"  # unchunked
                    media_types_detected.add(flow_key)
                    file_media_types[file_path] = flow_key
                    file_chunking_mode[file_path] = False
                    logger.debug(f"📄 {file_path.name} will be uploaded as-is (no chunking)")
            elif media_type is None:
                # Non-media file - treat as data file
                media_types_detected.add("data")
                file_media_types[file_path] = "data"
                file_chunking_mode[file_path] = False  # Data files are never chunked
                if file_path in metadata_files:
                    logger.debug(f"📎 Metadata file {file_path.name} will be uploaded to data flow and used for chunking")
        
        return media_types_detected, file_media_types, file_chunking_mode
    
    async def process_media_file_chunked(
        self,
        file_path: Path,
        relative_path: Path,
        file_path_str: str,
        target_flow: Any,
        media_type: str,
        metadata_file: Optional[Path],
        processed_chunks: Set[int],
        chunk_mode: str
    ) -> Tuple[int, int]:
        """
        Process a media file with chunking.
        
        Args:
            file_path: Path to media file
            relative_path: Relative path from folder root
            file_path_str: String representation of file path
            target_flow: Target TAMS flow
            media_type: Media type (video/audio)
            metadata_file: Optional metadata file for marker-based chunking
            processed_chunks: Set of already processed chunk indices
            chunk_mode: Chunking mode ("duration" or "metadata_file")
            
        Returns:
            Tuple of (files_processed, files_skipped)
        """
        if self.dry_run:
            if chunk_mode == "mp4_markers":
                logger.info(f"🔍 DRY RUN: Would chunk {relative_path} using embedded chapter markers")
                # Try to count embedded chapters
                try:
                    from embedded_markers import detect_embedded_chapters
                    chapters = detect_embedded_chapters(file_path_str)
                    estimated_chunks = len(chapters) if chapters else 1
                    logger.info(f"   Estimated chunks from embedded markers: {estimated_chunks}")
                except Exception as e:
                    logger.debug(f"   Could not count embedded markers: {e}")
                    estimated_chunks = 1
            elif chunk_mode == "metadata_file" and metadata_file is not None:
                logger.info(f"🔍 DRY RUN: Would chunk {relative_path} using markers from {metadata_file.name}")
                # Try to count segments in metadata file
                try:
                    format_type = detect_metadata_format(metadata_file)
                    if format_type == "ffmetadata":
                        # Count [CHAPTER] sections
                        with open(metadata_file, 'r') as f:
                            content = f.read()
                            estimated_chunks = content.count('[CHAPTER]')
                    elif format_type == "json":
                        # Count segments in JSON
                        with open(metadata_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                estimated_chunks = len(data)
                            elif isinstance(data, dict) and 'chapters' in data:
                                estimated_chunks = len(data['chapters'])
                            else:
                                estimated_chunks = 1
                    else:
                        estimated_chunks = 1
                    logger.info(f"   Estimated chunks from markers: {estimated_chunks}")
                except Exception as e:
                    logger.debug(f"   Could not count markers: {e}")
                    estimated_chunks = 1
            else:
                logger.info(f"🔍 DRY RUN: Would chunk {relative_path} into {self.chunk_duration}s segments")
                # Simulate chunking by checking file duration
                try:
                    probe_cmd = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", str(file_path)
                    ]
                    probe_result = subprocess.run(
                        probe_cmd, capture_output=True, text=True, check=True
                    )
                    probe_data = json.loads(probe_result.stdout)
                    duration = float(probe_data.get("format", {}).get("duration", 0))
                    estimated_chunks = int(duration / self.chunk_duration) + (1 if duration % self.chunk_duration > 0 else 0)
                    logger.info(f"   Estimated chunks: {estimated_chunks} (duration: {duration:.1f}s)")
                except Exception as e:
                    logger.debug(f"   Could not estimate chunks: {e}")
                    estimated_chunks = 1
            
            logger.info(f"🔍 DRY RUN: Would upload {estimated_chunks} chunks to TAMS")
            return 1, 0
        
        # Chunk the file
        if chunk_mode == "mp4_markers":
            logger.info(f"✂️  Chunking file using embedded chapter markers...")
        elif chunk_mode == "metadata_file" and metadata_file is not None:
            logger.info(f"✂️  Chunking file using markers from {metadata_file.name}...")
        else:
            logger.info(f"✂️  Chunking file into {self.chunk_duration}s segments...")
        
        chunk_files = await chunk_media_file(
            file_path_str,
            chunk_duration=self.chunk_duration,
            metadata_file=str(metadata_file) if metadata_file and chunk_mode == "metadata_file" else None,
            chunk_mode=chunk_mode
        )
        
        # Calculate total chunks expected
        total_chunks = len(chunk_files)
        logger.info(f"✅ Created {total_chunks} chunks")
        
        # Check which chunks actually exist in TAMS (verify against segments, not just tags)
        if target_flow and not self.dry_run:
            logger.debug(f"🔍 Verifying chunk presence in TAMS for {len(chunk_files)} chunks...")
            existing_segments = await target_flow.list_segments()
            # Build a set of existing timeranges
            existing_timeranges = set()
            for seg in existing_segments:
                timerange = seg.timerange
                if isinstance(timerange, dict) and "value" in timerange:
                    existing_timeranges.add(timerange["value"])
            
            # Track initial processed count before verification
            initial_processed_count = len(processed_chunks)
            
            # Filter out chunks that already exist in TAMS
            verified_chunks_to_upload = []
            for chunk_idx, chunk_file in enumerate(chunk_files):
                if chunk_idx in processed_chunks:
                    continue  # Already marked as processed
                
                # Calculate expected timerange
                start_seconds = chunk_idx * self.chunk_duration
                end_seconds = min(start_seconds + self.chunk_duration, start_seconds + self.chunk_duration)
                expected_timerange = f"[{start_seconds}:0_{end_seconds}:0)"
                
                if expected_timerange in existing_timeranges:
                    logger.debug(f"   ✓ Chunk {chunk_idx + 1}/{total_chunks} already exists in TAMS (timerange: {expected_timerange})")
                    processed_chunks.add(chunk_idx)  # Mark as processed
                else:
                    verified_chunks_to_upload.append((chunk_idx, chunk_file))
            
            chunks_to_upload = verified_chunks_to_upload
            # Calculate how many chunks were newly found to already exist
            newly_found_count = len(processed_chunks) - initial_processed_count
            if newly_found_count > 0:
                logger.info(f"✅ Verified: {newly_found_count} chunks already exist in TAMS, {len(verified_chunks_to_upload)} need upload")
        else:
            # Fallback to tag-based check if flow not available or dry-run
            chunks_to_upload = [(i, c) for i, c in enumerate(chunk_files) if i not in processed_chunks]
        
        if chunks_to_upload:
            logger.info(f"📤 Uploading {len(chunks_to_upload)} chunks to {media_type} flow (max {self.max_parallel_uploads} parallel)...")
        else:
            logger.info(f"⏭️  All chunks already processed and verified in TAMS")
            # Cleanup chunk files
            for chunk_file in chunk_files:
                try:
                    chunk_file.unlink()
                except Exception as e:
                    logger.warning(f"⚠️  Failed to cleanup chunk file {chunk_file}: {e}")
            return 0, 1
        
        async def upload_chunk(chunk_idx: int, chunk_file: Path) -> None:
            """Upload a single chunk with semaphore limiting."""
            async with self._upload_semaphore:
                # Calculate timerange for chunk
                start_seconds = chunk_idx * self.chunk_duration
                end_seconds = min(start_seconds + self.chunk_duration, start_seconds + self.chunk_duration)
                
                timerange = {
                    "value": f"[{start_seconds}:0_{end_seconds}:0)"
                }
                
                # Upload chunk to the appropriate flow
                if target_flow is None:
                    raise RuntimeError(f"Target flow for {media_type} not initialized")
                logger.debug(f"   📤 Uploading chunk {chunk_idx + 1}/{total_chunks} to {media_type} flow...")
                segment = await target_flow.add_segment(
                    file_path=str(chunk_file),
                    timerange=timerange,
                    auto_probe=False  # Don't probe chunks
                )
                
                # Store filename mapping in flow tags (segments don't have tags in TAMS)
                # Use pattern: file_mapping_{object_id} = {filename}|{file_path}|{chunk_index}|{total_chunks}
                object_id = segment.object_id
                mapping_value = f"{relative_path.name}|{file_path_str}|{chunk_idx}|{total_chunks}"
                await target_flow.set_tag(f"file_mapping_{object_id}", mapping_value)
                
                logger.debug(f"   ✅ Uploaded chunk {chunk_idx + 1}/{total_chunks}")
        
        # Upload chunks in parallel
        upload_tasks = [
            upload_chunk(chunk_idx, chunk_file)
            for chunk_idx, chunk_file in chunks_to_upload
        ]
        if upload_tasks:
            await asyncio.gather(*upload_tasks)
            logger.info(f"✅ Uploaded {len(chunks_to_upload)} chunks in parallel")
        
        # Cleanup chunk files
        logger.debug("🧹 Cleaning up temporary chunk files...")
        for chunk_file in chunk_files:
            try:
                chunk_file.unlink()
            except Exception as e:
                logger.warning(f"⚠️  Failed to cleanup chunk file {chunk_file}: {e}")
        
        logger.info(f"✅ Completed: {relative_path}")
        return 1, 0
    
    async def process_media_file_unchunked(
        self,
        file_path: Path,
        relative_path: Path,
        file_path_str: str,
        target_flow: Any,
        base_media_type: str,
        media_type: str
    ) -> Tuple[int, int]:
        """
        Process a media file without chunking (upload as-is).
        
        Args:
            file_path: Path to media file
            relative_path: Relative path from folder root
            file_path_str: String representation of file path
            target_flow: Target TAMS flow
            base_media_type: Base media type (video/audio)
            media_type: Media type with suffix (video_unchunked/audio_unchunked)
            
        Returns:
            Tuple of (files_processed, files_skipped)
        """
        if self.dry_run:
            file_size = file_path.stat().st_size
            logger.info(f"🔍 DRY RUN: Would upload {base_media_type} file as-is ({file_size} bytes) to TAMS")
            return 1, 0
        
        # Upload entire file as single segment
        logger.info(f"📤 Uploading {base_media_type} file as-is to {media_type} flow...")
        
        if target_flow is None:
            raise RuntimeError(f"Target flow for {media_type} not initialized")
        
        # Get file duration for timerange
        try:
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(file_path)
            ]
            probe_result = subprocess.run(
                probe_cmd, capture_output=True, text=True, check=True, timeout=30
            )
            probe_data = json.loads(probe_result.stdout)
            duration = float(probe_data.get("format", {}).get("duration", 0))
            timerange = {"value": f"[0:0_{int(duration)}:0)"}
        except Exception as e:
            logger.warning(f"⚠️  Could not determine duration for {relative_path}: {e}, using [0:0_0:0)")
            timerange = {"value": "[0:0_0:0)"}
        
        # Upload as single segment
        segment = await target_flow.add_segment(
            file_path=str(file_path),
            timerange=timerange,
            auto_probe=True  # Probe the full file
        )
        
        # Store filename mapping in flow tags
        object_id = segment.object_id
        mapping_value = f"{relative_path.name}|{file_path_str}|-1|-1"  # -1 indicates full file (not chunked)
        await target_flow.set_tag(f"file_mapping_{object_id}", mapping_value)
        
        logger.info(f"✅ Completed: {relative_path}")
        return 1, 0
    
    async def process_data_file(
        self,
        file_path: Path,
        relative_path: Path,
        file_path_str: str,
        target_flow: Any,
        media_type: str
    ) -> Tuple[int, int]:
        """
        Process a data file (non-media file).
        
        Args:
            file_path: Path to data file
            relative_path: Relative path from folder root
            file_path_str: String representation of file path
            target_flow: Target TAMS flow
            media_type: Media type (should be "data")
            
        Returns:
            Tuple of (files_processed, files_skipped)
        """
        if self.dry_run:
            file_size = file_path.stat().st_size
            logger.info(f"🔍 DRY RUN: Would upload data file ({file_size} bytes) to TAMS")
            return 1, 0
        
        # Upload data file to data flow
        file_size = file_path.stat().st_size
        logger.info(f"📤 Uploading data file ({file_size} bytes) to data flow...")
        file_data = file_path.read_bytes()
        
        # Create a temporary file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_path.suffix) as tmp_file:
            tmp_file.write(file_data)
            tmp_path = tmp_file.name
        
        try:
            # Upload as segment with timerange [0:0_0:0) for data files
            if target_flow is None:
                raise RuntimeError(f"Target flow for {media_type} not initialized")
            timerange = {"value": "[0:0_0:0)"}
            segment = await target_flow.add_segment(
                file_path=tmp_path,
                timerange=timerange,
                auto_probe=False
            )
            
            # Store filename mapping in flow tags (segments don't have tags in TAMS)
            object_id = segment.object_id
            mapping_value = f"{relative_path.name}|{file_path_str}|-1|-1"  # -1 indicates data file
            await target_flow.set_tag(f"file_mapping_{object_id}", mapping_value)
            
            logger.info(f"✅ Completed: {relative_path}")
            return 1, 0
        finally:
            # Cleanup temp file
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

