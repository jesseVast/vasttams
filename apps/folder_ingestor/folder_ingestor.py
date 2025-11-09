#!/usr/bin/env python3
"""
Folder Ingestor Application

Ingests all files from a folder into TAMS.
Each folder becomes one source and one flow.
Media files are chunked into time-based segments.
Non-media files are stored as data files.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "client"))
# Add current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSClientError
from vasttamsclient.utils.ffmpeg_probe import probe_and_extract_essence_parameters

from file_detector import detect_media_type
from media_processor import chunk_media_file
from metadata_matcher import find_metadata_files, detect_metadata_format

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FolderIngestor:
    """Main folder ingestor class."""
    
    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        chunk_duration: int = 30,
        recursive: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize folder ingestor.
        
        Args:
            server_url: TAMS server URL
            username: TAMS username
            password: TAMS password
            chunk_duration: Duration of each chunk in seconds (default: 30)
            recursive: Whether to process subdirectories recursively
            dry_run: If True, don't create anything in TAMS (default: False)
        """
        self.server_url = server_url
        self.username = username
        self.password = password
        self.chunk_duration = chunk_duration
        self.recursive = recursive
        self.dry_run = dry_run
        self.client: Optional[TAMSClient] = None
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE: No changes will be made to TAMS")
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.dry_run:
            logger.info(f"🔌 Connecting to TAMS server: {self.server_url}")
            self.client = TAMSClient(
                server_url=self.server_url,
                username=self.username,
                password=self.password,
                timeout=300
            )
            await self.client.__aenter__()
            logger.info("✅ Connected to TAMS server")
        else:
            logger.info("🔍 DRY RUN: Skipping TAMS connection")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def find_existing_source(self, folder_path: str) -> Optional[Tuple[str, str]]:
        """
        Find existing source for the folder path.
        
        Args:
            folder_path: Absolute folder path
            
        Returns:
            Tuple of (source_id, flow_id) if found, None otherwise
        """
        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would check for existing source with folder_path={folder_path}")
            return None
            
        try:
            logger.debug(f"🔍 Searching for existing source with folder_path tag: {folder_path}")
            # Query sources by folder_path tag
            sources = await self.client.list_sources_by_tag("folder_path", folder_path)
            
            if sources:
                source = sources[0]  # Use first matching source
                logger.info(f"✅ Found existing source: {source.id} for folder: {folder_path}")
                
                # Get flows for this source
                flows = await source.list_flows()
                if flows:
                    flow = flows[0]  # Use first flow
                    logger.info(f"✅ Found existing flow: {flow.id}")
                    return (source.id, flow.id)
                else:
                    logger.warning(f"⚠️  Source {source.id} exists but has no flows")
                    return (source.id, None)
            
            logger.debug("No existing source found")
            return None
        except Exception as e:
            logger.warning(f"⚠️  Error finding existing source: {e}")
            return None
    
    async def build_processed_files_map(self, flow_id: str) -> Dict[str, Set[int]]:
        """
        Build a map of already-processed files and their chunks.
        
        Args:
            flow_id: Flow ID to check
            
        Returns:
            Dict mapping file_path to set of chunk indices already processed
        """
        processed_map: Dict[str, Set[int]] = {}
        
        try:
            from vasttamsclient.api import flows as flow_api
            flow_data = await flow_api.get_flow(self.client, flow_id)
            if not flow_data:
                return processed_map
            
            flow_obj = self.client.TAMSFlow(id=flow_id, **{k: v for k, v in flow_data.items() if k != "id"})
            flow_tags = await flow_obj.get_tags()
            for tag_name, tag_value in flow_tags.items():
                if tag_name.startswith("file_mapping_"):
                    # Parse mapping: filename|file_path|chunk_index|total_chunks
                    try:
                        parts = str(tag_value).split("|")
                        if len(parts) >= 2:
                            file_path = parts[1]
                            if file_path not in processed_map:
                                processed_map[file_path] = set()
                            
                            if len(parts) >= 3:
                                chunk_index_str = parts[2]
                                if chunk_index_str and chunk_index_str != "-1":
                                    try:
                                        chunk_index = int(chunk_index_str)
                                        processed_map[file_path].add(chunk_index)
                                    except (ValueError, TypeError):
                                        pass
                                elif chunk_index_str == "-1":
                                    # Data file - mark as fully processed
                                    processed_map[file_path].add(-1)
                    except Exception as e:
                        logger.debug(f"Failed to parse file mapping tag {tag_name}: {e}")
                        continue
            
            logger.info(f"Found {len(processed_map)} processed files with {sum(len(chunks) for chunks in processed_map.values())} chunks")
            return processed_map
            
        except Exception as e:
            logger.warning(f"Error building processed files map: {e}")
            return processed_map
    
    async def ingest_folder(
        self,
        folder_path: str,
        source_format: str,
        source_label: Optional[str] = None,
        source_description: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Ingest all files from a folder into TAMS.
        
        Args:
            folder_path: Path to folder to ingest
            source_format: Source format URN (e.g., "urn:x-nmos:format:video")
            source_label: Optional source label
            source_description: Optional source description
            
        Returns:
            Tuple of (source_id, flow_id)
        """
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Folder does not exist or is not a directory: {folder_path}")
        
        folder_path_str = str(folder)
        logger.info(f"📁 Processing folder: {folder_path_str}")
        
        # Check for existing source/flow
        existing = await self.find_existing_source(folder_path_str)
        if existing:
            source_id, flow_id = existing
            if flow_id:
                # Build processed files map
                logger.info("📊 Building processed files map...")
                processed_map = await self.build_processed_files_map(flow_id)
                logger.info(f"✅ Resuming ingestion - found {len(processed_map)} already processed files")
            else:
                processed_map = {}
                logger.info("ℹ️  Found existing source but no flow - will create flow")
        else:
            source_id = None
            flow_id = None
            processed_map = {}
            logger.info("🆕 Starting new ingestion")
        
        # Get all files in folder
        if self.recursive:
            files = list(folder.rglob("*"))
        else:
            files = list(folder.glob("*"))
        
        # Filter to only files (not directories)
        files = [f for f in files if f.is_file()]
        files.sort()  # Process in consistent order
        
        logger.info(f"📋 Found {len(files)} files to process")
        if self.dry_run:
            logger.info("🔍 DRY RUN: Will simulate processing without creating TAMS resources")
        
        # Find metadata files and match them to media files
        logger.info("🔍 Scanning for metadata files...")
        metadata_map = find_metadata_files(folder, files)
        if metadata_map:
            logger.info(f"📎 Found {len(metadata_map)} metadata file(s) for marker-based chunking")
        else:
            logger.info("📎 No metadata files found - will use duration-based chunking")
        
        # Create or get source
        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would {'use existing' if source_id else 'create new'} source")
            logger.info(f"   Format: {source_format}")
            logger.info(f"   Label: {source_label or folder.name}")
            if source_id:
                source_id = f"dry-run-source-{uuid.uuid4()}"
            else:
                source_id = f"dry-run-source-{uuid.uuid4()}"
            source = None
        else:
            if source_id:
                logger.info(f"📝 Using existing source: {source_id}")
                source = self.client.TAMSSource(id=source_id)
                await source.refresh()
            else:
                logger.info(f"➕ Creating new source...")
                source = self.client.TAMSSource(
                    format=source_format,
                    label=source_label or folder.name,
                    description=source_description or f"Folder ingest: {folder_path_str}"
                )
                await source._ensure_created()
                source_id = source.id
                logger.info(f"✅ Created source: {source_id}")
                
                # Set folder_path tag
                logger.debug("🏷️  Setting source tags...")
                await source.set_tag("folder_path", folder_path_str)
                await source.set_tag("ingest_state", "in_progress")
                await source.set_tag("ingest_started", datetime.now().isoformat())
                await source.set_tag("files_total", str(len(files)))
        
        # Update ingest state
        if not self.dry_run and source:
            await source.set_tag("ingest_last_updated", datetime.now().isoformat())
        
        # Determine flow format and codec from first media file
        flow_format = source_format
        flow_codec = "video/mp2t"  # Default
        essence_params = None
        first_media_file = None
        
        # Find first media file to determine flow parameters
        for file_path in files:
            media_type = detect_media_type(str(file_path))
            if media_type in ("video", "audio"):
                first_media_file = file_path
                try:
                    essence_params = probe_and_extract_essence_parameters(
                        str(file_path),
                        source_format
                    )
                    # Determine codec from probe
                    import subprocess
                    import json
                    probe_cmd = [
                        "ffprobe", "-v", "error", "-show_streams",
                        "-of", "json", str(file_path)
                    ]
                    probe_result = subprocess.run(
                        probe_cmd, capture_output=True, text=True, check=True
                    )
                    probe_data = json.loads(probe_result.stdout)
                    for stream in probe_data.get("streams", []):
                        if stream.get("codec_type") == media_type:
                            codec_name = stream.get("codec_name", "")
                            if media_type == "video":
                                codec_map = {
                                    "h264": "video/h264",
                                    "hevc": "video/hevc",
                                    "vp8": "video/vp8",
                                    "vp9": "video/vp9"
                                }
                                flow_codec = codec_map.get(codec_name, "video/mp2t")
                            elif media_type == "audio":
                                codec_map = {
                                    "aac": "audio/aac",
                                    "mp3": "audio/mpeg",
                                    "opus": "audio/opus"
                                }
                                flow_codec = codec_map.get(codec_name, "audio/mpeg")
                            break
                except Exception as e:
                    logger.warning(f"Failed to probe first media file {file_path}: {e}")
                break
        
        # Create or get flow
        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would {'use existing' if flow_id else 'create new'} flow")
            logger.info(f"   Format: {flow_format}")
            logger.info(f"   Codec: {flow_codec}")
            if flow_id:
                flow_id = f"dry-run-flow-{uuid.uuid4()}"
            else:
                flow_id = f"dry-run-flow-{uuid.uuid4()}"
            flow = None
        else:
            if flow_id:
                logger.info(f"📝 Using existing flow: {flow_id}")
                from vasttamsclient.api import flows as flow_api
                flow_data = await flow_api.get_flow(self.client, flow_id)
                if flow_data:
                    flow = self.client.TAMSFlow(id=flow_id, **{k: v for k, v in flow_data.items() if k != "id"})
                else:
                    raise ValueError(f"Flow {flow_id} not found")
            else:
                logger.info(f"➕ Creating new flow...")
                flow = source.TAMSFlow(
                    format=flow_format,
                    codec=flow_codec,
                    label=source_label or folder.name
                )
                if essence_params:
                    flow._data["essence_parameters"] = essence_params
                await flow._ensure_created()
                flow_id = flow.id
                logger.info(f"✅ Created flow: {flow_id}")
                
                # Set flow tags
                logger.debug("🏷️  Setting flow tags...")
                await flow.set_tag("ingest_folder", folder_path_str)
        
        # Process files
        files_processed = 0
        files_skipped = 0
        files_failed = 0
        
        logger.info(f"🚀 Starting file processing ({len(files)} files)...")
        
        for idx, file_path in enumerate(files, 1):
            file_path_str = str(file_path)
            relative_path = file_path.relative_to(folder)
            logger.info(f"[{idx}/{len(files)}] Processing: {relative_path}")
            
            # Check if file already processed
            if file_path_str in processed_map:
                processed_chunks = processed_map[file_path_str]
                if -1 in processed_chunks:
                    # Non-media file fully processed
                    logger.info(f"⏭️  Skipping already processed file: {relative_path}")
                    files_skipped += 1
                    continue
                else:
                    logger.debug(f"   Found {len(processed_chunks)} already processed chunks")
                # Media file - will check chunks later
            else:
                processed_chunks = set()
            
            try:
                # Detect media type
                media_type = detect_media_type(file_path_str)
                
                if media_type in ("video", "audio"):
                    # Chunk and upload media file
                    logger.info(f"🎬 Media file detected: {media_type}")
                    
                    # Check if there's a metadata file for this media file
                    metadata_file = metadata_map.get(file_path)
                    chunk_mode = "duration"
                    if metadata_file:
                        format_type = detect_metadata_format(metadata_file)
                        if format_type == "ffmetadata":
                            chunk_mode = "metadata_file"
                            logger.info(f"📎 Using FFMETADATA1 marker file: {metadata_file.name}")
                        elif format_type == "json":
                            chunk_mode = "metadata_file"
                            logger.info(f"📎 Using JSON marker file: {metadata_file.name}")
                        else:
                            logger.warning(f"⚠️  Metadata file {metadata_file.name} format not recognized, using duration-based chunking")
                    
                    if self.dry_run:
                        if chunk_mode == "metadata_file":
                            logger.info(f"🔍 DRY RUN: Would chunk {relative_path} using markers from {metadata_file.name}")
                            # Try to count segments in metadata file
                            try:
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
                                import subprocess
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
                        files_processed += 1
                    else:
                        # Chunk the file
                        if chunk_mode == "metadata_file":
                            logger.info(f"✂️  Chunking file using markers from {metadata_file.name}...")
                        else:
                            logger.info(f"✂️  Chunking file into {self.chunk_duration}s segments...")
                        
                        chunk_files = await chunk_media_file(
                            file_path_str,
                            chunk_duration=self.chunk_duration,
                            metadata_file=str(metadata_file) if metadata_file else None,
                            chunk_mode=chunk_mode
                        )
                        
                        # Calculate total chunks expected
                        total_chunks = len(chunk_files)
                        logger.info(f"✅ Created {total_chunks} chunks")
                        
                        # Upload each chunk as a segment
                        chunks_to_upload = [c for i, c in enumerate(chunk_files) if i not in processed_chunks]
                        if chunks_to_upload:
                            logger.info(f"📤 Uploading {len(chunks_to_upload)} chunks...")
                        else:
                            logger.info(f"⏭️  All chunks already processed")
                        
                        for chunk_idx, chunk_file in enumerate(chunk_files):
                            # Check if chunk already processed
                            if chunk_idx in processed_chunks:
                                logger.debug(f"   ⏭️  Skipping already processed chunk {chunk_idx + 1}/{total_chunks}")
                                continue
                            
                            # Calculate timerange for chunk
                            start_seconds = chunk_idx * self.chunk_duration
                            end_seconds = min(start_seconds + self.chunk_duration, start_seconds + self.chunk_duration)
                            
                            timerange = {
                                "value": f"[{start_seconds}:0_{end_seconds}:0)"
                            }
                            
                            # Upload chunk
                            logger.debug(f"   📤 Uploading chunk {chunk_idx + 1}/{total_chunks}...")
                            segment = await flow.add_segment(
                                file_path=str(chunk_file),
                                timerange=timerange,
                                auto_probe=False  # Don't probe chunks
                            )
                            
                            # Store filename mapping in flow tags (segments don't have tags in TAMS)
                            # Use pattern: file_mapping_{object_id} = {filename}|{file_path}|{chunk_index}|{total_chunks}
                            object_id = segment.object_id
                            mapping_value = f"{relative_path.name}|{file_path_str}|{chunk_idx}|{total_chunks}"
                            await flow.set_tag(f"file_mapping_{object_id}", mapping_value)
                            
                            logger.debug(f"   ✅ Uploaded chunk {chunk_idx + 1}/{total_chunks}")
                        
                        # Cleanup chunk files
                        logger.debug("🧹 Cleaning up temporary chunk files...")
                        for chunk_file in chunk_files:
                            try:
                                chunk_file.unlink()
                            except Exception as e:
                                logger.warning(f"⚠️  Failed to cleanup chunk file {chunk_file}: {e}")
                        
                        files_processed += 1
                        logger.info(f"✅ Completed: {relative_path}")
                    
                else:
                    # Non-media file - upload as data file
                    logger.info(f"📄 Data file detected")
                    
                    # Check if already processed
                    if -1 in processed_chunks:
                        logger.info(f"⏭️  Skipping already processed data file: {relative_path}")
                        files_skipped += 1
                        continue
                    
                    if self.dry_run:
                        file_size = file_path.stat().st_size
                        logger.info(f"🔍 DRY RUN: Would upload data file ({file_size} bytes) to TAMS")
                        files_processed += 1
                    else:
                        # For data files, we need to create a data flow
                        # Since we're using a single flow per folder, we'll upload data files
                        # as segments with a special timerange
                        # Note: This is a simplified approach - in practice, you might want
                        # separate data flows or objects
                        
                        # Read file content
                        file_size = file_path.stat().st_size
                        logger.info(f"📤 Uploading data file ({file_size} bytes)...")
                        file_data = file_path.read_bytes()
                        
                        # Create a temporary file for upload
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_path.suffix) as tmp_file:
                            tmp_file.write(file_data)
                            tmp_path = tmp_file.name
                        
                        try:
                            # Upload as segment with timerange [0:0_0:0) for data files
                            timerange = {"value": "[0:0_0:0)"}
                            segment = await flow.add_segment(
                                file_path=tmp_path,
                                timerange=timerange,
                                auto_probe=False
                            )
                            
                            # Store filename mapping in flow tags (segments don't have tags in TAMS)
                            object_id = segment.object_id
                            mapping_value = f"{relative_path.name}|{file_path_str}|-1|-1"  # -1 indicates data file
                            await flow.set_tag(f"file_mapping_{object_id}", mapping_value)
                            
                            files_processed += 1
                            logger.info(f"✅ Completed: {relative_path}")
                        finally:
                            # Cleanup temp file
                            try:
                                Path(tmp_path).unlink()
                            except Exception:
                                pass
                
            except Exception as e:
                logger.error(f"❌ Failed to process file {relative_path}: {e}", exc_info=True)
                files_failed += 1
                continue
            
            # Update progress
            if not self.dry_run and source:
                await source.set_tag("files_processed", str(files_processed))
                await source.set_tag("ingest_last_updated", datetime.now().isoformat())
        
        # Mark ingestion as completed
        if not self.dry_run and source:
            logger.info("🏁 Marking ingestion as completed...")
            await source.set_tag("ingest_state", "completed")
            await source.set_tag("ingest_completed", datetime.now().isoformat())
        
        logger.info("=" * 60)
        logger.info(f"✅ Ingestion completed!")
        logger.info(f"   📊 Files processed: {files_processed}")
        logger.info(f"   ⏭️  Files skipped: {files_skipped}")
        if files_failed > 0:
            logger.info(f"   ❌ Files failed: {files_failed}")
        if self.dry_run:
            logger.info(f"   🔍 DRY RUN: No changes were made to TAMS")
        logger.info("=" * 60)
        
        return (source_id, flow_id)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest files from a folder into TAMS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--folder",
        required=True,
        help="Path to folder to ingest"
    )
    parser.add_argument(
        "--format",
        required=True,
        help="Source format URN (e.g., urn:x-nmos:format:video)"
    )
    parser.add_argument(
        "--label",
        help="Source label"
    )
    parser.add_argument(
        "--description",
        help="Source description"
    )
    parser.add_argument(
        "--config",
        help="Path to JSON config file"
    )
    parser.add_argument(
        "--server-url",
        help="TAMS server URL"
    )
    parser.add_argument(
        "--username",
        help="TAMS username"
    )
    parser.add_argument(
        "--password",
        help="TAMS password"
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=30,
        help="Chunk duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run through the process without creating anything in TAMS"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config file if provided
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Get settings from args or config
    server_url = args.server_url or config.get("server_url") or "http://localhost:8000"
    username = args.username or config.get("username") or "admin"
    password = args.password or config.get("password") or "admin"
    chunk_duration = args.chunk_duration or config.get("chunk_duration", 30)
    recursive = args.recursive or config.get("recursive", False)
    dry_run = args.dry_run or config.get("dry_run", False)
    
    try:
        async with FolderIngestor(
            server_url=server_url,
            username=username,
            password=password,
            chunk_duration=chunk_duration,
            recursive=recursive,
            dry_run=dry_run
        ) as ingestor:
            source_id, flow_id = await ingestor.ingest_folder(
                folder_path=args.folder,
                source_format=args.format,
                source_label=args.label,
                source_description=args.description
            )
            print(f"✅ Ingestion completed successfully!")
            print(f"   Source ID: {source_id}")
            print(f"   Flow ID: {flow_id}")
            
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

