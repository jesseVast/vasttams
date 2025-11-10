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
from typing import Any, Dict, List, Optional, Set, Tuple
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
        dry_run: bool = False,
        max_parallel_uploads: int = 4
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
            max_parallel_uploads: Maximum number of parallel uploads (default: 4)
        """
        self.server_url = server_url
        self.username = username
        self.password = password
        self.chunk_duration = chunk_duration
        self.recursive = recursive
        self.dry_run = dry_run
        self.max_parallel_uploads = max_parallel_uploads
        self._upload_semaphore = asyncio.Semaphore(max_parallel_uploads)
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
    
    async def find_existing_source(self, folder_path: str) -> Optional[Tuple[str, Dict[str, str], Optional[str]]]:
        """
        Find existing source for the folder path and all its flows.
        
        Args:
            folder_path: Absolute folder path
            
        Returns:
            Tuple of (source_id, flows_dict, multi_flow_id) if found, None otherwise
            flows_dict maps media_type -> flow_id
        """
        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would check for existing source with folder_path={folder_path}")
            return None
            
        try:
            logger.debug(f"🔍 Searching for existing source with folder_path tag: {folder_path}")
            # Query sources by folder_path tag
            if self.client is None:
                return None
            sources = await self.client.list_sources_by_tag("folder_path", folder_path)
            
            if sources:
                source = sources[0]  # Use first matching source
                logger.info(f"✅ Found existing source: {source.id} for folder: {folder_path}")
                
                # Get all flows for this source
                flows = await source.list_flows()
                if flows:
                    flows_dict: Dict[str, str] = {}
                    multi_flow_id: Optional[str] = None
                    
                    # Categorize flows by format
                    for flow in flows:
                        flow_format = flow._data.get("format", "")
                        if flow_format == "urn:x-nmos:format:multi":
                            multi_flow_id = flow.id
                            logger.info(f"✅ Found existing multi-flow: {flow.id}")
                        elif flow_format == "urn:x-nmos:format:video":
                            flows_dict["video"] = flow.id
                            logger.info(f"✅ Found existing video flow: {flow.id}")
                        elif flow_format == "urn:x-nmos:format:audio":
                            flows_dict["audio"] = flow.id
                            logger.info(f"✅ Found existing audio flow: {flow.id}")
                        elif flow_format == "urn:x-nmos:format:data":
                            flows_dict["data"] = flow.id
                            logger.info(f"✅ Found existing data flow: {flow.id}")
                    
                    if flows_dict or multi_flow_id:
                        return (source.id, flows_dict, multi_flow_id)
                    else:
                        # Legacy: single flow (not multi-essence)
                        flow = flows[0]
                        logger.info(f"✅ Found existing flow (legacy): {flow.id}")
                        # Determine type from format
                        flow_format = flow._data.get("format", "")
                        if "video" in flow_format:
                            flows_dict["video"] = flow.id
                        elif "audio" in flow_format:
                            flows_dict["audio"] = flow.id
                        elif "data" in flow_format:
                            flows_dict["data"] = flow.id
                        else:
                            flows_dict["video"] = flow.id  # Default
                        return (source.id, flows_dict, None)
                else:
                    logger.warning(f"⚠️  Source {source.id} exists but has no flows")
                    return (source.id, {}, None)
            
            logger.debug("No existing source found")
            return None
        except Exception as e:
            logger.warning(f"⚠️  Error finding existing source: {e}")
            return None
    
    async def build_processed_files_map(self, flows_dict: Dict[str, str]) -> Dict[str, Set[int]]:
        """
        Build a map of already-processed files and their chunks from all flows.
        
        Args:
            flows_dict: Dict mapping media_type -> flow_id
            
        Returns:
            Dict mapping file_path to set of chunk indices already processed
        """
        processed_map: Dict[str, Set[int]] = {}
        
        try:
            from vasttamsclient.api import flows as flow_api
            
            if self.client is None:
                return processed_map
            
            # Check all flows
            for media_type, flow_id in flows_dict.items():
                flow_data = await flow_api.get_flow(self.client, flow_id)
                if not flow_data:
                    continue
                
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
    ) -> Tuple[str, Dict[str, str], Optional[str]]:
        """
        Ingest all files from a folder into TAMS.
        
        Args:
            folder_path: Path to folder to ingest
            source_format: Source format URN (e.g., "urn:x-nmos:format:video")
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
        existing = await self.find_existing_source(folder_path_str)
        if existing:
            source_id, flows_dict, multi_flow_id = existing
            if flows_dict:
                # Build processed files map from all flows
                logger.info("📊 Building processed files map...")
                processed_map = await self.build_processed_files_map(flows_dict)
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
        logger.info("🔍 Analyzing files to detect media types...")
        media_types_detected: Set[str] = set()
        file_media_types: Dict[Path, str] = {}  # Map file -> media_type
        
        for file_path in files:
            media_type = detect_media_type(str(file_path))
            if media_type in ("video", "audio"):
                media_types_detected.add(media_type)
                file_media_types[file_path] = media_type
            elif media_type is None:
                # Non-media file
                media_types_detected.add("data")
                file_media_types[file_path] = "data"
        
        logger.info(f"📊 Detected media types: {sorted(media_types_detected)}")
        if len(media_types_detected) > 1:
            logger.info("🔗 Will create multi-essence flow to collect all types")
        elif len(media_types_detected) == 1:
            media_type = list(media_types_detected)[0]
            logger.info(f"📝 Single media type detected: {media_type}")
        
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
        type_codecs: Dict[str, str] = {}
        type_essence_params: Dict[str, Dict[str, Any]] = {}
        
        for media_type in media_types_detected:
            if media_type == "data":
                type_codecs["data"] = "application/octet-stream"
                type_essence_params["data"] = {"data_type": "urn:x-tams:data:file"}
                continue
            
            # Find first file of this type to determine codec
            for file_path in files:
                if file_media_types.get(file_path) == media_type:
                    try:
                        format_urn = f"urn:x-nmos:format:{media_type}"
                        essence_params = probe_and_extract_essence_parameters(
                            str(file_path),
                            format_urn
                        )
                        type_essence_params[media_type] = essence_params
                        
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
                                    type_codecs[media_type] = codec_map.get(codec_name, "video/mp2t")
                                elif media_type == "audio":
                                    codec_map = {
                                        "aac": "audio/aac",
                                        "mp3": "audio/mpeg",
                                        "opus": "audio/opus"
                                    }
                                    type_codecs[media_type] = codec_map.get(codec_name, "audio/mpeg")
                                break
                    except Exception as e:
                        logger.warning(f"Failed to probe {media_type} file {file_path}: {e}")
                        # Set defaults
                        if media_type == "video":
                            type_codecs[media_type] = "video/mp2t"
                        elif media_type == "audio":
                            type_codecs[media_type] = "audio/mpeg"
                    break
        
        # Create or get flows for each media type
        flows: Dict[str, Any] = {}  # Map media_type -> TAMSFlow object
        
        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would create flows for types: {sorted(media_types_detected)}")
            for media_type in media_types_detected:
                flows_dict[media_type] = f"dry-run-flow-{media_type}-{uuid.uuid4()}"
            if len(media_types_detected) > 1:
                multi_flow_id = f"dry-run-multi-flow-{uuid.uuid4()}"
        else:
            # Create or get flows for each detected type
            for media_type in media_types_detected:
                if self.client is None:
                    raise RuntimeError("Client not initialized")
                if source is None:
                    raise RuntimeError("Source not initialized")
                    
                if media_type in flows_dict:
                    # Use existing flow
                    logger.info(f"📝 Using existing {media_type} flow: {flows_dict[media_type]}")
                    from vasttamsclient.api import flows as flow_api
                    flow_data = await flow_api.get_flow(self.client, flows_dict[media_type])
                    if flow_data:
                        flows[media_type] = self.client.TAMSFlow(
                            id=flows_dict[media_type],
                            **{k: v for k, v in flow_data.items() if k != "id"}
                        )
                    else:
                        raise ValueError(f"Flow {flows_dict[media_type]} not found")
                else:
                    # Create new flow for this type
                    logger.info(f"➕ Creating new {media_type} flow...")
                    format_urn = f"urn:x-nmos:format:{media_type}"
                    codec = type_codecs.get(media_type, "video/mp2t")
                    
                    flow = source.TAMSFlow(
                        format=format_urn,
                        codec=codec,
                        label=f"{source_label or folder.name} ({media_type})"
                    )
                    
                    # Add essence parameters if available
                    if media_type in type_essence_params:
                        flow._data["essence_parameters"] = type_essence_params[media_type]
                    
                    await flow._ensure_created()
                    flows_dict[media_type] = flow.id
                    flows[media_type] = flow
                    logger.info(f"✅ Created {media_type} flow: {flow.id}")
                    
                    # Set flow tags
                    logger.debug(f"🏷️  Setting {media_type} flow tags...")
                    await flow.set_tag("ingest_folder", folder_path_str)
                    await flow.set_tag("media_type", media_type)
            
            # Create multi-flow if multiple types detected
            if len(media_types_detected) > 1:
                if self.client is None:
                    raise RuntimeError("Client not initialized")
                if source is None:
                    raise RuntimeError("Source not initialized")
                    
                if multi_flow_id:
                    logger.info(f"📝 Using existing multi-flow: {multi_flow_id}")
                    from vasttamsclient.api import flows as flow_api
                    flow_data = await flow_api.get_flow(self.client, multi_flow_id)
                    if flow_data:
                        multi_flow = self.client.TAMSFlow(
                            id=multi_flow_id,
                            **{k: v for k, v in flow_data.items() if k != "id"}
                        )
                    else:
                        raise ValueError(f"Multi-flow {multi_flow_id} not found")
                else:
                    logger.info(f"➕ Creating new multi-flow...")
                    multi_flow = source.TAMSFlow(
                        format="urn:x-nmos:format:multi",
                        codec="video/mp2t",  # Container codec for multi-essence
                        label=source_label or folder.name
                    )
                    await multi_flow._ensure_created()
                    multi_flow_id = multi_flow.id
                    logger.info(f"✅ Created multi-flow: {multi_flow_id}")
                    
                    # Set flow tags
                    logger.debug("🏷️  Setting multi-flow tags...")
                    await multi_flow.set_tag("ingest_folder", folder_path_str)
                    
                    # Set flow_collection
                    collection_items = []
                    for media_type in sorted(media_types_detected):
                        if media_type in flows_dict:
                            role = media_type if media_type != "data" else "data"
                            collection_items.append({
                                "id": flows_dict[media_type],
                                "role": role
                            })
                    
                    # Update flow_collection via API
                    if self.client is None:
                        raise RuntimeError("Client not initialized")
                    if self.client._session is None:
                        raise RuntimeError("Client session not initialized")
                    url = f"{self.client.server_url}/flows/{multi_flow_id}/flow_collection"
                    headers = await self.client._get_headers()
                    async with self.client._session.put(url, json=collection_items, headers=headers) as response:
                        if response.status not in (200, 201):
                            error_text = await response.text()
                            logger.warning(f"Failed to set flow_collection: {error_text}")
                        else:
                            logger.info(f"✅ Set flow_collection on multi-flow with {len(collection_items)} items")
            else:
                multi_flow_id = None
        
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
                        if chunk_mode == "metadata_file" and metadata_file is not None:
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
                        if chunk_mode == "metadata_file" and metadata_file is not None:
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
                        
                        # Upload each chunk as a segment to the appropriate flow (in parallel)
                        chunks_to_upload = [(i, c) for i, c in enumerate(chunk_files) if i not in processed_chunks]
                        if chunks_to_upload:
                            logger.info(f"📤 Uploading {len(chunks_to_upload)} chunks to {media_type} flow (max {self.max_parallel_uploads} parallel)...")
                        else:
                            logger.info(f"⏭️  All chunks already processed")
                        
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
                        # Upload data file to data flow
                        file_size = file_path.stat().st_size
                        logger.info(f"📤 Uploading data file ({file_size} bytes) to data flow...")
                        file_data = file_path.read_bytes()
                        
                        # Create a temporary file for upload
                        import tempfile
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
        logger.info(f"   🔗 Flows created: {len(flows_dict)}")
        for media_type, flow_id in flows_dict.items():
            logger.info(f"      - {media_type}: {flow_id}")
        if multi_flow_id:
            logger.info(f"   🔗 Multi-flow: {multi_flow_id}")
        if self.dry_run:
            logger.info(f"   🔍 DRY RUN: No changes were made to TAMS")
        logger.info("=" * 60)
        
        return (source_id, flows_dict, multi_flow_id)


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
    parser.add_argument(
        "--max-parallel-uploads",
        type=int,
        default=4,
        help="Maximum number of parallel uploads (default: 4)"
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
    max_parallel_uploads = args.max_parallel_uploads or config.get("max_parallel_uploads", 4)
    
    try:
        async with FolderIngestor(
            server_url=server_url,
            username=username,
            password=password,
            chunk_duration=chunk_duration,
            recursive=recursive,
            dry_run=dry_run,
            max_parallel_uploads=max_parallel_uploads
        ) as ingestor:
            source_id, flows_dict, multi_flow_id = await ingestor.ingest_folder(
                folder_path=args.folder,
                source_format=args.format,
                source_label=args.label,
                source_description=args.description
            )
            print(f"✅ Ingestion completed successfully!")
            print(f"   Source ID: {source_id}")
            print(f"   Flows: {len(flows_dict)}")
            for media_type, flow_id in flows_dict.items():
                print(f"      - {media_type}: {flow_id}")
            if multi_flow_id:
                print(f"   Multi-flow ID: {multi_flow_id}")
        
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

