"""
Flow management for folder ingestor.

Handles finding existing sources/flows, creating flows, and setting up multi-essence flows.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src" / "client"))

from vasttamsclient import TAMSClient
from vasttamsclient.utils.ffmpeg_probe import probe_and_extract_essence_parameters

logger = logging.getLogger(__name__)


class FlowManager:
    """Manages TAMS flows for folder ingestion."""
    
    def __init__(
        self,
        client: Optional[TAMSClient],
        dry_run: bool = False
    ):
        """
        Initialize flow manager.
        
        Args:
            client: TAMS client instance
            dry_run: If True, don't create anything in TAMS
        """
        self.client = client
        self.dry_run = dry_run
    
    async def find_existing_source(
        self,
        folder_path: str
    ) -> Optional[Tuple[str, Dict[str, str], Optional[str]]]:
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
            if self.client is None:
                logger.warning("⚠️  Client not initialized, cannot search for existing source")
                return None
            sources = await self.client.list_sources_by_tag_async("folder_path", folder_path)
            
            if sources:
                source = sources[0]  # Use first matching source
                logger.info(f"✅ Found existing source: {source.id} for folder: {folder_path}")
                
                # Verify the tag value matches exactly
                source_tags = await source.get_tags()
                stored_folder_path = source_tags.get("folder_path")
                if stored_folder_path != folder_path:
                    logger.warning(f"⚠️  Source {source.id} has folder_path tag mismatch: stored='{stored_folder_path}', looking for='{folder_path}'")
                    # Still use it, but log the mismatch
                
                # Get all flows for this source
                flows = await source.list_flows()
                if flows:
                    flows_dict: Dict[str, str] = {}
                    multi_flow_id: Optional[str] = None
                    
                    # Categorize flows by format and chunking mode
                    for flow in flows:
                        flow_format = flow._data.get("format", "")
                        # Check if this is a chunked or unchunked flow by looking at tags
                        flow_tags = await flow.get_tags()
                        is_chunked_flow = flow_tags.get("chunking_enabled", "true").lower() == "true"
                        chunking_suffix = "" if is_chunked_flow else "_unchunked"
                        
                        if flow_format == "urn:x-nmos:format:multi":
                            multi_flow_id = flow.id
                            logger.info(f"✅ Found existing multi-flow: {flow.id}")
                        elif flow_format == "urn:x-nmos:format:video":
                            # Check if this is an original flow
                            is_original_flow = flow_tags.get("flow_type", "").lower() == "original"
                            if is_original_flow:
                                flow_key = "video_original"
                            else:
                                flow_key = f"video{chunking_suffix}"
                            flows_dict[flow_key] = flow.id
                            flow_type_desc = "original" if is_original_flow else ('chunked' if is_chunked_flow else 'unchunked')
                            logger.info(f"✅ Found existing video flow ({flow_type_desc}): {flow.id}")
                        elif flow_format == "urn:x-nmos:format:audio":
                            # Check if this is an original flow
                            is_original_flow = flow_tags.get("flow_type", "").lower() == "original"
                            if is_original_flow:
                                flow_key = "audio_original"
                            else:
                                flow_key = f"audio{chunking_suffix}"
                            flows_dict[flow_key] = flow.id
                            flow_type_desc = "original" if is_original_flow else ('chunked' if is_chunked_flow else 'unchunked')
                            logger.info(f"✅ Found existing audio flow ({flow_type_desc}): {flow.id}")
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
    
    async def build_processed_files_map(
        self,
        flows_dict: Dict[str, str]
    ) -> Dict[str, Set[int]]:
        """
        Build a map of already-processed files and their chunks.
        
        Note: File mapping is no longer stored on flows. Resume functionality
        based on file mapping has been removed. This function returns an empty
        map to maintain API compatibility.
        
        Args:
            flows_dict: Dict mapping media_type -> flow_id (unused, kept for compatibility)
            
        Returns:
            Dict mapping file_path to set of chunk indices already processed (empty)
        """
        processed_map: Dict[str, Set[int]] = {}
        
        # File mapping removed from flows - resume functionality disabled
        # Future implementation could use object metadata (filename field) to track processed files
        logger.debug("Resume functionality based on file mapping is no longer available")
        
        return processed_map
    
    async def determine_codecs_and_essence_params(
        self,
        media_types_detected: Set[str],
        file_media_types: Dict,
        files: List,
        chunk_format: str = "original"
    ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, Dict[str, Any]]]:
        """
        Determine codec, container, and essence parameters for each media type.
        
        Args:
            media_types_detected: Set of detected media types
            file_media_types: Map file -> media_type
            files: List of file paths
            
        Returns:
            Tuple of (type_codecs, type_containers, type_essence_params)
        """
        type_codecs: Dict[str, str] = {}
        type_containers: Dict[str, str] = {}
        type_essence_params: Dict[str, Dict[str, Any]] = {}
        
        for media_type in media_types_detected:
            if media_type == "data":
                # Always use valid MIME type for data flows
                type_codecs["data"] = "application/octet-stream"
                type_containers["data"] = "application/octet-stream"
                type_essence_params["data"] = {"data_type": "urn:x-tams:data:file"}
                logger.debug(f"Set codec for data flow: {type_codecs['data']}")
                continue
            
            # Get base media type (remove _unchunked suffix)
            base_media_type = media_type.replace("_unchunked", "")
            
            # Find first file of this type to determine codec and container
            for file_path in files:
                if file_media_types.get(file_path) == media_type:
                    try:
                        format_urn = f"urn:x-nmos:format:{base_media_type}"
                        essence_params = probe_and_extract_essence_parameters(
                            str(file_path),
                            format_urn
                        )
                        # Store essence params for base media type (shared between chunked/unchunked)
                        type_essence_params[base_media_type] = essence_params
                        
                        # Determine codec and container from probe
                        import subprocess
                        import json
                        from pathlib import Path
                        
                        # First, check file extension for container hint
                        file_ext = Path(file_path).suffix.lower()
                        container_from_ext = None
                        if file_ext == ".ts":
                            container_from_ext = "video/mp2t"
                        elif file_ext in [".mp4", ".m4v"]:
                            container_from_ext = "video/mp4"
                        elif file_ext == ".mkv":
                            container_from_ext = "video/x-matroska"
                        elif file_ext == ".webm":
                            container_from_ext = "video/webm"
                        elif file_ext == ".avi":
                            container_from_ext = "video/x-msvideo"
                        elif file_ext == ".mov":
                            container_from_ext = "video/quicktime"
                        elif file_ext in [".mp3", ".m4a"]:
                            container_from_ext = "audio/mpeg" if file_ext == ".mp3" else "audio/mp4"
                        elif file_ext == ".aac":
                            container_from_ext = "audio/aac"
                        elif file_ext == ".wav":
                            container_from_ext = "audio/wav"
                        elif file_ext == ".ogg":
                            container_from_ext = "audio/ogg"
                        
                        # Probe for format information
                        probe_cmd = [
                            "ffprobe", "-v", "error", "-show_format", "-show_streams",
                            "-of", "json", str(file_path)
                        ]
                        probe_result = subprocess.run(
                            probe_cmd, capture_output=True, text=True, check=True
                        )
                        probe_data = json.loads(probe_result.stdout)
                        
                        # Get container from format_name if available
                        format_info = probe_data.get("format", {})
                        format_name = format_info.get("format_name", "").lower()
                        container_from_probe = None
                        
                        if "mpegts" in format_name or "ts" in format_name:
                            container_from_probe = "video/mp2t"
                        elif "mp4" in format_name or "mov" in format_name or "isom" in format_name:
                            container_from_probe = "video/mp4"
                        elif "matroska" in format_name or "mkv" in format_name:
                            container_from_probe = "video/x-matroska"
                        elif "webm" in format_name:
                            container_from_probe = "video/webm"
                        elif "avi" in format_name:
                            container_from_probe = "video/x-msvideo"
                        elif "wav" in format_name:
                            container_from_probe = "audio/wav"
                        elif "ogg" in format_name:
                            container_from_probe = "audio/ogg"
                        
                        # Determine codec from streams
                        for stream in probe_data.get("streams", []):
                            if stream.get("codec_type") == base_media_type:
                                codec_name = stream.get("codec_name", "")
                                if base_media_type == "video":
                                    codec_map = {
                                        "h264": "video/h264",
                                        "hevc": "video/hevc",
                                        "vp8": "video/vp8",
                                        "vp9": "video/vp9"
                                    }
                                    # Store codec for base media type (shared between chunked/unchunked)
                                    type_codecs[base_media_type] = codec_map.get(codec_name, "video/h264")
                                elif base_media_type == "audio":
                                    codec_map = {
                                        "aac": "audio/aac",
                                        "mp3": "audio/mpeg",
                                        "opus": "audio/opus"
                                    }
                                    # Store codec for base media type (shared between chunked/unchunked)
                                    type_codecs[base_media_type] = codec_map.get(codec_name, "audio/mpeg")
                                break
                        
                        # Determine container: prefer probe result, then extension, then default
                        # Override for HLS chunk format (chunks are .ts files, so container must be video/mp2t)
                        if chunk_format == "hls" and base_media_type == "video":
                            type_containers[base_media_type] = "video/mp2t"
                            logger.debug(f"Overriding container to video/mp2t for HLS chunk format")
                        elif container_from_probe:
                            type_containers[base_media_type] = container_from_probe
                            logger.debug(f"Detected container from probe: {container_from_probe} for {file_path}")
                        elif container_from_ext:
                            type_containers[base_media_type] = container_from_ext
                            logger.debug(f"Detected container from extension: {container_from_ext} for {file_path}")
                        else:
                            # Default based on media type
                            if base_media_type == "video":
                                type_containers[base_media_type] = "video/mp4"  # Default to MP4 for video
                            elif base_media_type == "audio":
                                type_containers[base_media_type] = "audio/mpeg"  # Default to MPEG for audio
                            logger.debug(f"Using default container for {base_media_type}: {type_containers[base_media_type]}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to probe {base_media_type} file {file_path}: {e}")
                        # Set defaults for base media type
                        if base_media_type == "video":
                            type_codecs[base_media_type] = "video/h264"
                            type_containers[base_media_type] = "video/mp4"
                        elif base_media_type == "audio":
                            type_codecs[base_media_type] = "audio/mpeg"
                            type_containers[base_media_type] = "audio/mpeg"
                    break
        
        return type_codecs, type_containers, type_essence_params
    
    async def create_or_get_flows(
        self,
        source: Any,
        media_types_detected: Set[str],
        flows_dict: Dict[str, str],
        type_codecs: Dict[str, str],
        type_containers: Dict[str, str],
        type_essence_params: Dict[str, Dict[str, Any]],
        source_label: Optional[str],
        folder_path_str: str,
        folder_name: str,
        existing_multi_flow_id: Optional[str] = None,
        tags: Optional[dict] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Create or get flows for each media type.
        
        Args:
            source: TAMS source object
            media_types_detected: Set of detected media types
            flows_dict: Dict mapping media_type -> flow_id (will be updated)
            type_codecs: Dict mapping media_type -> codec
            type_essence_params: Dict mapping media_type -> essence_params
            source_label: Optional source label
            folder_path_str: Absolute folder path string
            folder_name: Folder name
            existing_multi_flow_id: Optional existing multi-flow ID to reuse
            
        Returns:
            Tuple of (flows, multi_flow_id)
            flows maps media_type -> TAMSFlow object
        """
        flows: Dict[str, Any] = {}  # Map media_type -> TAMSFlow object
        
        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would create flows for types: {sorted(media_types_detected)}")
            for media_type in media_types_detected:
                flows_dict[media_type] = f"dry-run-flow-{media_type}-{uuid.uuid4()}"
            multi_flow_id = f"dry-run-multi-flow-{uuid.uuid4()}" if len(media_types_detected) > 1 else None
            return flows, multi_flow_id
        
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
                # Determine base media type (video/audio/data) and chunking mode
                if media_type.endswith("_original"):
                    base_media_type = media_type.replace("_original", "")
                    is_chunked = False
                    is_original = True
                    format_urn = f"urn:x-nmos:format:{base_media_type}"
                    codec = type_codecs.get(base_media_type, "video/mp2t")
                    container = type_containers.get(base_media_type)
                    label_suffix = f"{base_media_type} (original)"
                elif media_type.endswith("_unchunked"):
                    base_media_type = media_type.replace("_unchunked", "")
                    is_chunked = False
                    is_original = False
                    format_urn = f"urn:x-nmos:format:{base_media_type}"
                    codec = type_codecs.get(base_media_type, "video/mp2t")
                    container = type_containers.get(base_media_type)
                    label_suffix = f"{base_media_type} (unchunked)"
                else:
                    base_media_type = media_type
                    is_chunked = True
                    is_original = False
                    format_urn = f"urn:x-nmos:format:{base_media_type}"
                    # For data flows, use base_media_type to get codec (which is "data")
                    # For other flows, try media_type first, then base_media_type
                    if base_media_type == "data":
                        # Ensure data flows always have a valid MIME type codec
                        # Force to application/octet-stream regardless of what's in type_codecs
                        codec = "application/octet-stream"
                        container = type_containers.get(base_media_type, "application/octet-stream")
                        logger.debug(f"Data flow: forcing codec to 'application/octet-stream' (type_codecs had: {type_codecs.get('data')})")
                    else:
                        codec = type_codecs.get(media_type) or type_codecs.get(base_media_type, "video/mp2t")
                        container = type_containers.get(base_media_type)
                    label_suffix = f"{media_type}"
                
                logger.info(f"➕ Creating new {label_suffix} flow...")
                
                # Final validation: ensure codec is always a valid MIME type
                if not codec or not isinstance(codec, str) or "/" not in codec:
                    logger.warning(f"Invalid codec '{codec}' for {label_suffix} flow, using default")
                    if base_media_type == "data":
                        codec = "application/octet-stream"
                    elif base_media_type == "video":
                        codec = "video/mp2t"
                    elif base_media_type == "audio":
                        codec = "audio/mpeg"
                    else:
                        codec = "application/octet-stream"
                
                logger.debug(f"Creating flow with format={format_urn}, codec={codec} (type: {type(codec)})")
                
                # Double-check codec is valid before creating flow
                if base_media_type == "data" and codec != "application/octet-stream":
                    logger.warning(f"Data flow codec is '{codec}', forcing to 'application/octet-stream'")
                    codec = "application/octet-stream"
                
                flow = source.TAMSFlow(
                    format=format_urn,
                    codec=codec,
                    label=f"{source_label or folder_name} ({label_suffix})"
                )
                
                # Set container if detected
                if container:
                    flow._data["container"] = container
                    logger.debug(f"Setting container for {label_suffix} flow: {container}")
                
                # Verify codec in flow data before creation
                if flow._data.get("codec") != codec:
                    logger.warning(f"Codec mismatch: expected '{codec}', got '{flow._data.get('codec')}'")
                    flow._data["codec"] = codec
                
                # Add essence parameters if available (use base media type)
                if base_media_type in type_essence_params:
                    flow._data["essence_parameters"] = type_essence_params[base_media_type]
                
                # Final check: ensure codec is still valid before creation
                final_codec = flow._data.get("codec")
                logger.debug(f"Codec before final validation: {final_codec} (type: {type(final_codec)})")
                
                # For data flows, ALWAYS force to application/octet-stream
                if base_media_type == "data":
                    if final_codec != "application/octet-stream":
                        logger.warning(f"Data flow codec is '{final_codec}' (type: {type(final_codec)}), forcing to 'application/octet-stream'")
                    flow._data["codec"] = "application/octet-stream"
                    final_codec = "application/octet-stream"
                elif not final_codec or not isinstance(final_codec, str) or "/" not in final_codec:
                    logger.error(f"Invalid codec '{final_codec}' (type: {type(final_codec)}) in flow._data before creation! Fixing...")
                    flow._data["codec"] = "video/mp2t"
                    final_codec = "video/mp2t"
                
                # One more absolute check - ensure it's a string and valid MIME type
                if not isinstance(flow._data.get("codec"), str):
                    logger.error(f"Codec is not a string! Type: {type(flow._data.get('codec'))}, Value: {flow._data.get('codec')}")
                    flow._data["codec"] = "application/octet-stream" if base_media_type == "data" else "video/mp2t"
                elif "/" not in flow._data.get("codec", ""):
                    logger.error(f"Codec does not contain '/': {flow._data.get('codec')}")
                    flow._data["codec"] = "application/octet-stream" if base_media_type == "data" else "video/mp2t"
                
                logger.info(f"Final flow data before creation: format={flow._data.get('format')}, codec={flow._data.get('codec')}, codec_type={type(flow._data.get('codec'))}")
                
                # Log the entire flow data dict for debugging
                import json
                try:
                    flow_data_str = json.dumps(flow._data, indent=2, default=str)
                    logger.debug(f"Complete flow._data being sent:\n{flow_data_str}")
                except Exception as e:
                    logger.debug(f"Could not serialize flow._data: {e}")
                    logger.debug(f"flow._data keys: {list(flow._data.keys())}")
                    logger.debug(f"flow._data['codec']: {repr(flow._data.get('codec'))}")
                
                await flow._ensure_created()
                flows_dict[media_type] = flow.id
                flows[media_type] = flow
                logger.info(f"✅ Created {label_suffix} flow: {flow.id}")
                
                # Set flow tags
                logger.debug(f"🏷️  Setting {label_suffix} flow tags...")
                await flow.set_tag("ingest_folder", folder_path_str)
                await flow.set_tag("media_type", base_media_type)
                await flow.set_tag("chunking_enabled", "true" if is_chunked else "false")
                if is_original:
                    await flow.set_tag("flow_type", "original")
                
                # Set user-provided tags
                if tags:
                    for key, value in tags.items():
                        await flow.set_tag(key, str(value))
        
        # Create multi-flow if multiple types detected
        multi_flow_id: Optional[str] = existing_multi_flow_id
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
                    label=source_label or folder_name
                )
                await multi_flow._ensure_created()
                multi_flow_id = multi_flow.id
                logger.info(f"✅ Created multi-flow: {multi_flow_id}")
            
            # Set flow tags
            logger.debug("🏷️  Setting multi-flow tags...")
            await multi_flow.set_tag("ingest_folder", folder_path_str)
            
            # Set user-provided tags
            if tags:
                for key, value in tags.items():
                    await multi_flow.set_tag(key, str(value))
            
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
            if self.client._session is None:
                raise RuntimeError("Client session not initialized")
            url = f"{self.client.server_url}{self.client.api_prefix}/flows/{multi_flow_id}/flow_collection"
            headers = await self.client._get_headers()
            async with self.client._session.put(url, json=collection_items, headers=headers) as response:
                if response.status not in (200, 201):
                    error_text = await response.text()
                    logger.warning(f"Failed to set flow_collection: {error_text}")
                else:
                    logger.info(f"✅ Set flow_collection on multi-flow with {len(collection_items)} items")
        
        return flows, multi_flow_id

