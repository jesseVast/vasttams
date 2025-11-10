"""
TAMS Flow Domain Object

Encapsulates flow operations and provides fluent API.
"""

import uuid
import asyncio
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from .base import TAMSDomainObject
from .segment import TAMSSegment
from ..api import flows as flow_api
from ..api import segments as segment_api
from ..api import tags as tag_api
from ..api import storage_backends as storage_api
from ..exceptions import TAMSClientError
from ..utils.ffmpeg_probe import probe_and_extract_essence_parameters


class TAMSFlow(TAMSDomainObject):
    """TAMS Flow domain object."""
    
    def __init__(self, client, source=None, id: Optional[str] = None, format: str = None, 
                 codec: str = None, label: Optional[str] = None, **flow_data):
        """
        Create or represent a TAMS flow.
        
        Args:
            client: TAMSClient instance
            source: Optional TAMSSource instance or source_id string
            id: Optional flow ID (if None, creates new flow)
            format: Flow format URN (required for new flow)
            codec: Flow codec MIME type (required for new flow)
            label: Optional flow label
            **flow_data: Additional flow data (essence_parameters fields can be passed as top-level)
        """
        if id is None:
            # Create new flow
            if format is None or codec is None:
                raise ValueError("format and codec are required for new flow")
            
            # Handle source parameter
            if source is not None:
                if hasattr(source, 'id'):
                    # TAMSSource instance
                    flow_data["source_id"] = source.id
                else:
                    # source_id string
                    flow_data["source_id"] = source
            elif "source_id" not in flow_data:
                raise ValueError("source or source_id is required for new flow")
            
            if "id" not in flow_data:
                flow_data["id"] = str(uuid.uuid4())
            
            # Extract essence_parameters fields if passed as top-level
            essence_param_fields = ['frame_width', 'frame_height', 'frame_rate', 'vfr', 
                                   'bit_depth', 'interlace_mode', 'colorspace', 
                                   'transfer_characteristic', 'aspect_ratio', 'pixel_aspect_ratio',
                                   'component_type', 'horiz_chroma_subs', 'vert_chroma_subs',
                                   'sample_rate', 'channels', 'codec_parameters', 'unc_parameters',
                                   'avc_parameters']
            
            # If essence_parameters not already structured, build it from top-level params
            if "essence_parameters" not in flow_data or not flow_data.get("essence_parameters"):
                essence_params = {}
                for field in essence_param_fields:
                    if field in flow_data:
                        essence_params[field] = flow_data.pop(field)
                
                # Only add essence_parameters if we have some values
                if essence_params:
                    flow_data["essence_parameters"] = essence_params
            
            flow_data.update({
                "format": format,
                "codec": codec,
                "label": label
            })
        else:
            # Represent existing flow
            # Include format, codec, label if provided as keyword arguments
            if format is not None:
                flow_data["format"] = format
            if codec is not None:
                flow_data["codec"] = codec
            if label is not None:
                flow_data["label"] = label
            flow_data["id"] = id
        
        super().__init__(client, flow_data["id"], flow_data)
        self._created = id is None
        self._segment_count = 0
    
    async def _ensure_created(self):
        """Ensure flow is created on server."""
        if self._created:
            try:
                # Create flow with minimal data
                result = await flow_api.create_flow(self._client, self._data)
                self._data.update(result)
                self._created = False
            except Exception as e:
                raise TAMSClientError(f"Failed to create flow: {e}")
    
    async def add_segment(self, file_path: Optional[str] = None, s3_object: Optional[Dict[str, Any]] = None,
                         timerange: Optional[Dict[str, Any]] = None, auto_probe: bool = True,
                         chunk_size: int = 8 * 1024 * 1024, **segment_data) -> 'TAMSSegment':
        """
        Add a segment to this flow (combined operation: allocate → upload → create).
        
        Args:
            file_path: Path to local file to upload
            s3_object: Dict with 'bucket', 'key', 'region' for S3 object (alternative to file_path)
            timerange: Timerange dict with 'value' key (TAMS format: "[start:0_end:0)")
            auto_probe: If True and first segment, probe file and update flow essence_parameters
            **segment_data: Additional segment data
            
        Returns:
            TAMSSegment: Created segment instance
        """
        await self._ensure_created()
        
        if not file_path and not s3_object:
            raise ValueError("Either file_path or s3_object must be provided")
        
        # Auto-probe on first segment
        if auto_probe and self._segment_count == 0 and file_path:
            try:
                essence_params = probe_and_extract_essence_parameters(file_path, self._data.get("format", ""))
                # Update flow with essence parameters
                update_data = {"essence_parameters": essence_params}
                await flow_api.update_flow(self._client, self._id, {**self._data, **update_data})
                self._data.update(update_data)
            except Exception as e:
                # Log but don't fail - flow can be updated manually later
                import logging
                logging.warning(f"Auto-probe failed: {e}")
        
        # Allocate storage
        storage_result = await segment_api.allocate_storage(
            self._client,
            self._id,
            label=segment_data.get("label"),
            limit=1
        )
        
        # Extract presigned URL and object_id
        media_objects = storage_result.get("media_objects", [])
        if not media_objects:
            raise TAMSClientError("No storage allocation returned")
        
        media_obj = media_objects[0]
        object_id = media_obj["object_id"]
        put_url_obj = media_obj["put_url"]
        presigned_url = put_url_obj["url"]
        content_type = put_url_obj.get("content-type", "application/octet-stream")
        
        # Log storage allocation details
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Storage allocation received:")
        logger.debug(f"  Object ID: {object_id}")
        logger.debug(f"  Presigned URL: {presigned_url}")
        logger.debug(f"  Content-Type: {content_type}")
        logger.debug(f"  Put URL object: {put_url_obj}")
        
        # Upload file or use S3 object
        if file_path:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Use chunked upload for large files (multipart support)
            await segment_api.upload_to_storage(
                self._client, 
                presigned_url, 
                file_path=str(file_path_obj),
                content_type=content_type,
                chunk_size=chunk_size
            )
        elif s3_object:
            # For S3 objects, we assume the object already exists in S3
            # In a real implementation, you might need to copy from S3 to the presigned URL
            # For now, we'll just use the object_id
            pass
        
        # Create segment
        if not timerange:
            # Generate default timerange if not provided
            start_seconds = self._segment_count * 10
            end_seconds = start_seconds + 10
            timerange = {"value": f"[{start_seconds}:0_{end_seconds}:0)"}
        
        segment_data.update({
            "object_id": object_id,
            "timerange": timerange
        })
        
        segment_result = await segment_api.create_segment(self._client, self._id, segment_data)
        self._segment_count += 1
        
        return TAMSSegment(self._client, self._id, segment_result)
    
    async def get_segment(self, segment_id: str) -> Optional['TAMSSegment']:
        """Get a segment by object_id."""
        segments = await segment_api.list_segments(self._client, self._id, {"object_id": segment_id})
        if segments:
            return TAMSSegment(self._client, self._id, segments[0])
        return None
    
    async def list_segments(self, **query_params) -> List['TAMSSegment']:
        """List segments for this flow."""
        segments_data = await segment_api.list_segments(self._client, self._id, query_params)
        return [TAMSSegment(self._client, self._id, s) for s in segments_data]
    
    async def delete_segments(self, **filters):
        """Delete segments matching filters."""
        await segment_api.delete_segments(self._client, self._id, filters)
    
    async def refresh(self):
        """Refresh flow data from server."""
        flow_data = await flow_api.get_flow(self._client, self._id)
        if flow_data:
            self._data.update(flow_data)
            # Clear tags cache since data may have changed
            self._tags_cache = None
        else:
            raise TAMSClientError(f"Flow {self._id} not found")
    
    async def update(self, **updates):
        """Update flow metadata."""
        self._data.update(updates)
        result = await flow_api.update_flow(self._client, self._id, self._data)
        self._data.update(result)
        # Note: Tags cache not cleared here as tags are managed separately
    
    async def delete(self):
        """Delete flow."""
        await flow_api.delete_flow(self._client, self._id)
        # Remove from client cache
        if hasattr(self._client, '_cache') and "flow" in self._client._cache:
            self._client._cache["flow"].pop(self._id, None)
    
    async def get_tags(self, use_cache: bool = True) -> Dict[str, Union[str, List[str]]]:
        """
        Get all tags.
        
        Args:
            use_cache: If True, return cached tags if available
            
        Returns:
            Dict mapping tag names to values (string or list of strings)
        """
        # Return cached tags if available
        if use_cache and self._tags_cache is not None:
            return self._tags_cache
        
        # Fetch from server
        tags = await tag_api.get_tags(self._client, "flow", self._id)
        # Cache the result (empty dict is valid, so we cache it)
        self._tags_cache = tags
        return tags
    
    async def get_tag(self, name: str, use_cache: bool = True) -> Optional[Union[str, List[str]]]:
        """
        Get a specific tag.
        
        Args:
            name: Tag name
            use_cache: If True, check cached tags first
            
        Returns:
            Tag value (string or list of strings) or None if not found
        """
        # Check cache first
        if use_cache and self._tags_cache is not None:
            return self._tags_cache.get(name)
        
        # Fetch from server
        value = await tag_api.get_tag(self._client, "flow", self._id, name)
        # Update cache if we have one
        if self._tags_cache is not None:
            if value is None:
                self._tags_cache.pop(name, None)
            else:
                self._tags_cache[name] = value
        return value
    
    async def set_tag(self, name: str, value: Union[str, List[str]]):
        """
        Set or update a tag.
        
        Args:
            name: Tag name
            value: Tag value (string or list of strings)
        """
        await tag_api.set_tag(self._client, "flow", self._id, name, value)
        # Update cache
        if self._tags_cache is None:
            self._tags_cache = {}
        self._tags_cache[name] = value
    
    async def delete_tag(self, name: str):
        """
        Delete a tag.
        
        Args:
            name: Tag name
        """
        await tag_api.delete_tag(self._client, "flow", self._id, name)
        # Update cache
        if self._tags_cache is not None:
            self._tags_cache.pop(name, None)
    
    def clear_tags_cache(self):
        """Clear the tags cache (force refresh on next get_tags/get_tag call)."""
        self._tags_cache = None
    
    # Properties
    @property
    def source_id(self) -> str:
        return self._data.get("source_id", "")
    
    @property
    def format(self) -> str:
        return self._data.get("format", "")
    
    @property
    def codec(self) -> str:
        return self._data.get("codec", "")
    
    @property
    def label(self) -> Optional[str]:
        return self._data.get("label")
    
    @property
    def description(self) -> Optional[str]:
        return self._data.get("description")
    
    @property
    def essence_parameters(self) -> Dict[str, Any]:
        return self._data.get("essence_parameters", {})

