"""
Main folder ingestor class.

Orchestrates the ingestion process using flow management and file processing modules.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src" / "client"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from vasttamsclient import TAMSClient

from metadata_matcher import find_metadata_files, detect_metadata_format
from embedded_markers import detect_embedded_chapters, has_embedded_chapters
from .flow_manager import FlowManager
from .file_processor import FileProcessor

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
        dry_run: bool = False,
        max_parallel_uploads: int = 4,
        no_chunking: bool = False,
        use_metadata: bool = False,
        include_originals: bool = False
    ):
        """
        Initialize folder ingestor.
        
        Args:
            server_url: TAMS server URL
            username: TAMS username
            password: TAMS password
            chunk_duration: Duration of each chunk in seconds (default: 30, ignored if no_chunking=True)
            recursive: Whether to process subdirectories recursively
            dry_run: If True, don't create anything in TAMS (default: False)
            max_parallel_uploads: Maximum number of parallel uploads (default: 4)
            no_chunking: If True, upload files as-is without chunking (default: False). Overrides use_metadata.
            use_metadata: If True, use metadata files for marker-based chunking when available (default: False)
            include_originals: If True, also upload original files to separate flow when chunking (default: False)
        """
        self.server_url = server_url
        self.username = username
        self.password = password
        self.chunk_duration = chunk_duration
        self.recursive = recursive
        self.dry_run = dry_run
        self.max_parallel_uploads = max_parallel_uploads
        self.no_chunking = no_chunking
        self.use_metadata = use_metadata
        self.include_originals = include_originals
        self.client: Optional[TAMSClient] = None
        self.flow_manager: Optional[FlowManager] = None
        self.file_processor: Optional[FileProcessor] = None
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE: No changes will be made to TAMS")
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.dry_run:
            logger.info(f"🔌 Connecting to TAMS server: {self.server_url}")
            # Configure connection pooling for parallel uploads
            # Set limit_per_host to at least max_parallel_uploads + some overhead
            limit_per_host = max(self.max_parallel_uploads * 2, 30)
            self.client = TAMSClient(
                server_url=self.server_url,
                username=self.username,
                password=self.password,
                timeout=300,
                limit=100,  # Total connection pool size
                limit_per_host=limit_per_host,  # Max connections per host (scaled for parallel uploads)
                keepalive_timeout=60  # Keep connections alive for reuse
            )
            await self.client.__aenter__()
            logger.info(f"✅ Connected to TAMS server (connection pool: {limit_per_host} per host)")
        else:
            logger.info("🔍 DRY RUN: Skipping TAMS connection")
        
        # Initialize managers
        self.flow_manager = FlowManager(self.client, self.dry_run)
        self.file_processor = FileProcessor(
            self.client,
            self.chunk_duration,
            self.dry_run,
            self.max_parallel_uploads,
            self.no_chunking,
            self.use_metadata,
            self.include_originals
        )
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _auto_detect_source_format(self, media_types_detected: Set[str]) -> str:
        """
        Auto-detect source format based on detected media types.
        
        Args:
            media_types_detected: Set of detected media types (e.g., {"video", "data"})
            
        Returns:
            Source format URN
        """
        # Get base media types (remove _unchunked suffix)
        base_types = {mt.replace("_unchunked", "") for mt in media_types_detected}
        
        # Remove "data" from consideration for format detection (data is always secondary)
        content_types = base_types - {"data"}
        
        if len(content_types) > 1:
            # Multiple content types - use multi format
            return "urn:x-nmos:format:multi"
        elif len(content_types) == 1:
            # Single content type
            content_type = list(content_types)[0]
            return f"urn:x-nmos:format:{content_type}"
        elif "data" in base_types:
            # Only data files
            return "urn:x-nmos:format:data"
        else:
            # Fallback to video if nothing detected
            logger.warning("⚠️  No media types detected, defaulting to video format")
            return "urn:x-nmos:format:video"
    
    async def ingest_folder(
        self,
        folder_path: str,
        source_format: Optional[str] = None,
        source_label: Optional[str] = None,
        source_description: Optional[str] = None
    ) -> Tuple[str, Dict[str, str], Optional[str]]:
        """
        Ingest all files from a folder into TAMS.
        
        Args:
            folder_path: Path to folder to ingest
            source_format: Optional source format URN (e.g., "urn:x-nmos:format:video").
                          If not provided, will be auto-detected from folder contents.
            source_label: Optional source label
            source_description: Optional source description
            
        Returns:
            Tuple of (source_id, flows_dict, multi_flow_id)
            flows_dict maps media_type -> flow_id
        """
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Folder does not exist or is not a directory: {folder_path}")
        
        folder_path_str = str(folder)
        logger.info(f"📁 Processing folder: {folder_path_str}")
        
        # Check for existing source/flows
        if self.flow_manager is None:
            raise RuntimeError("Flow manager not initialized")
        
        existing = await self.flow_manager.find_existing_source(folder_path_str)
        if existing:
            source_id, flows_dict, multi_flow_id = existing
            if flows_dict:
                # Build processed files map from all flows
                logger.info("📊 Building processed files map...")
                processed_map = await self.flow_manager.build_processed_files_map(flows_dict)
                logger.info(f"✅ Resuming ingestion - found {len(processed_map)} already processed files")
            else:
                flows_dict = {}
                processed_map = {}
                logger.info("ℹ️  Found existing source but no flows - will create flows")
        else:
            source_id = None
            flows_dict = {}
            multi_flow_id = None
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
        
        # Detect all media types in folder
        if self.file_processor is None:
            raise RuntimeError("File processor not initialized")
        
        media_types_detected, file_media_types, file_chunking_mode = self.file_processor.detect_media_types(
            files, metadata_map
        )
        
        logger.info(f"📊 Detected media types: {sorted(media_types_detected)}")
        if len(media_types_detected) > 1:
            logger.info("🔗 Will create multi-essence flow to collect all types")
        elif len(media_types_detected) == 1:
            media_type = list(media_types_detected)[0]
            logger.info(f"📝 Single media type detected: {media_type}")
        
        # Auto-detect source format if not provided
        if source_format is None:
            source_format = self._auto_detect_source_format(media_types_detected)
            logger.info(f"🔍 Auto-detected source format: {source_format}")
        
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
            if self.client is None:
                raise RuntimeError("Client not initialized")
            if source_id:
                logger.info(f"📝 Using existing source: {source_id}")
                source = self.client.TAMSSource(id=source_id, format=source_format)
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
        
        # Determine codec and essence params for each media type
        type_codecs, type_essence_params = await self.flow_manager.determine_codecs_and_essence_params(
            media_types_detected,
            file_media_types,
            files
        )
        
        # Create or get flows for each media type
        flows, multi_flow_id = await self.flow_manager.create_or_get_flows(
            source,
            media_types_detected,
            flows_dict,
            type_codecs,
            type_essence_params,
            source_label,
            folder_path_str,
            folder.name,
            existing_multi_flow_id=multi_flow_id
        )
        
        # Process files
        files_processed = 0
        files_skipped = 0
        files_failed = 0
        
        logger.info(f"🚀 Starting file processing ({len(files)} files)...")
        
        metadata_files = set(metadata_map.values())
        
        for idx, file_path in enumerate(files, 1):
            file_path_str = str(file_path)
            relative_path = file_path.relative_to(folder)
            
            logger.info(f"[{idx}/{len(files)}] Processing: {relative_path}")
            
            # Check if this is a metadata file (will be processed as data file AND used for chunking)
            is_metadata_file = file_path in metadata_files
            if is_metadata_file:
                logger.info(f"📎 Metadata file detected - will be uploaded to data flow and used for chunking associated media")
            
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
            else:
                processed_chunks = set()
            
            try:
                # Get media type from pre-detected map
                media_type = file_media_types.get(file_path, "data")
                
                # Get the appropriate flow for this media type
                if media_type not in flows_dict:
                    logger.warning(f"⚠️  No flow found for media type {media_type}, skipping {relative_path}")
                    files_failed += 1
                    continue
                
                target_flow_id = flows_dict[media_type]
                target_flow = flows.get(media_type)
                
                if not target_flow and not self.dry_run:
                    # Load flow if not already loaded
                    if self.client is None:
                        raise RuntimeError("Client not initialized")
                    from vasttamsclient.api import flows as flow_api
                    flow_data = await flow_api.get_flow(self.client, target_flow_id)
                    if flow_data:
                        target_flow = self.client.TAMSFlow(
                            id=target_flow_id,
                            **{k: v for k, v in flow_data.items() if k != "id"}
                        )
                        flows[media_type] = target_flow
                
                # Determine if this is a video/audio file (chunked or unchunked)
                base_media_type = media_type.replace("_unchunked", "").replace("_original", "")
                should_chunk = file_chunking_mode.get(file_path, False) and not media_type.endswith("_unchunked") and not media_type.endswith("_original")
                
                if base_media_type in ("video", "audio"):
                    if should_chunk:
                        # Chunk and upload media file
                        logger.info(f"🎬 Media file detected: {base_media_type} (will be chunked)")
                        
                        # Check for markers: embedded chapters first, then external metadata files
                        metadata_file = None
                        chunk_mode = "duration"
                        
                        if self.use_metadata:
                            # First check for embedded chapter markers in the video file
                            if has_embedded_chapters(file_path_str):
                                chunk_mode = "mp4_markers"
                                logger.info(f"📎 Using embedded chapter markers from {relative_path.name}")
                            else:
                                # Fall back to external metadata file if available
                                metadata_file = metadata_map.get(file_path)
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
                                        metadata_file = None  # Don't use invalid metadata file
                                else:
                                    logger.debug(f"📎 No embedded chapters or metadata file found for {relative_path.name}, using duration-based chunking")
                        elif metadata_map.get(file_path):
                            logger.debug(f"📎 Metadata file found for {relative_path.name} but --use-metadata not set, using duration-based chunking")
                        
                        # Process chunked file
                        processed, skipped = await self.file_processor.process_media_file_chunked(
                            file_path,
                            relative_path,
                            file_path_str,
                            target_flow,
                            media_type,
                            metadata_file,
                            processed_chunks,
                            chunk_mode
                        )
                        files_processed += processed
                        files_skipped += skipped
                        
                        # If include_originals is set, also upload original file to separate flow
                        if self.include_originals:
                            original_flow_key = f"{base_media_type}_original"
                            if original_flow_key in flows_dict:
                                original_flow_id = flows_dict[original_flow_key]
                                original_flow = flows.get(original_flow_key)
                                
                                if not original_flow and not self.dry_run:
                                    # Load original flow if not already loaded
                                    if self.client is None:
                                        raise RuntimeError("Client not initialized")
                                    from vasttamsclient.api import flows as flow_api
                                    flow_data = await flow_api.get_flow(self.client, original_flow_id)
                                    if flow_data:
                                        original_flow = self.client.TAMSFlow(
                                            id=original_flow_id,
                                            **{k: v for k, v in flow_data.items() if k != "id"}
                                        )
                                        flows[original_flow_key] = original_flow
                                
                                logger.info(f"📤 Also uploading original file to {original_flow_key} flow...")
                                orig_processed, orig_skipped = await self.file_processor.process_media_file_unchunked(
                                    file_path,
                                    relative_path,
                                    file_path_str,
                                    original_flow,
                                    base_media_type,
                                    original_flow_key
                                )
                                files_processed += orig_processed
                                files_skipped += orig_skipped
                    else:
                        # Upload as-is without chunking
                        logger.info(f"📄 Media file detected: {base_media_type} (will be uploaded as-is)")
                        
                        # Process unchunked file
                        processed, skipped = await self.file_processor.process_media_file_unchunked(
                            file_path,
                            relative_path,
                            file_path_str,
                            target_flow,
                            base_media_type,
                            media_type
                        )
                        files_processed += processed
                        files_skipped += skipped
                else:
                    # Non-media file - upload as data file
                    logger.info(f"📄 Data file detected")
                    
                    # Check if already processed
                    if -1 in processed_chunks:
                        logger.info(f"⏭️  Skipping already processed data file: {relative_path}")
                        files_skipped += 1
                        continue
                    
                    # Process data file
                    processed, skipped = await self.file_processor.process_data_file(
                        file_path,
                        relative_path,
                        file_path_str,
                        target_flow,
                        media_type
                    )
                    files_processed += processed
                    files_skipped += skipped
                
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
        logger.info(f"   🔗 Flows created: {len(flows_dict)}")
        for media_type, flow_id in flows_dict.items():
            logger.info(f"      - {media_type}: {flow_id}")
        if multi_flow_id:
            logger.info(f"   🔗 Multi-flow: {multi_flow_id}")
        if self.dry_run:
            logger.info(f"   🔍 DRY RUN: No changes were made to TAMS")
        logger.info("=" * 60)
        
        return (source_id, flows_dict, multi_flow_id)

