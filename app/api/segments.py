"""
Segments submodule for TAMS API.
Handles flow segment-related operations and business logic.
"""
from typing import List, Optional, Dict
from fastapi import HTTPException
import json
import uuid
from datetime import datetime, timezone
from ..models.models import FlowSegment, FlowStorage, FlowStoragePost, MediaObject, HttpRequest
from ..storage.vast_store import VASTStore
from ..core.timerange_utils import get_storage_timerange
import logging

logger = logging.getLogger(__name__)

# Standalone functions for router use
async def get_flow_segments(store: VASTStore, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
    """Get flow segments with optional timerange filtering"""
    try:
        segments = await store.get_flow_segments(flow_id, timerange=timerange)
        return segments
    except Exception as e:
        logger.error(f"Failed to get flow segments for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_flow_segment(store: VASTStore, flow_id: str, segment: FlowSegment) -> bool:
    """Create a new flow segment"""
    try:
        # For now, we'll create the segment without media data
        # In a real implementation, you'd handle the media data upload
        success = await store.create_flow_segment(segment, flow_id, b"", "application/octet-stream")
        return success
    except Exception as e:
        logger.error(f"Failed to create flow segment for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def delete_flow_segments(store: VASTStore, flow_id: str, timerange: Optional[str] = None, soft_delete: bool = True, deleted_by: str = "system") -> bool:
    """Delete flow segments"""
    try:
        success = await store.delete_flow_segments(flow_id, timerange=timerange, soft_delete=soft_delete, deleted_by=deleted_by)
        return success
    except Exception as e:
        logger.error(f"Failed to delete flow segments for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_flow_storage(store: VASTStore, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
    """Create storage allocation for a flow"""
    try:
        from ..models.models import MediaObject, HttpRequest
        
        # Generate object IDs if not provided
        if storage_request.object_ids:
            object_ids = storage_request.object_ids
        else:
            # Generate the requested number of object IDs
            import uuid
            limit = storage_request.limit or 10
            object_ids = [str(uuid.uuid4()) for _ in range(limit)]
        
        # Validate that object IDs don't already exist
        for object_id in object_ids:
            existing_object = await store.get_object(object_id)
            if existing_object:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=f"Object ID {object_id} already exists")
        
        # Generate storage locations with presigned URLs using S3Store
        media_objects = []
        for object_id in object_ids:
            # Generate hierarchical path for storage allocation
            # This ensures consistency between storage and retrieval URLs
            object_key = store.s3_store.generate_segment_key(flow_id, object_id, get_storage_timerange())
            
            logger.info(f"Generated hierarchical path: {object_key} for object {object_id}")
            
            # Generate S3 presigned PUT URL using S3Store
            put_url = store.s3_store.generate_object_presigned_url(
                object_id=object_id,
                operation='put_object',
                custom_key=object_key  # Use the hierarchical path
            )
            
            if not put_url:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL for object {object_id}")
            
            # Create MediaObject with the hierarchical path
            media_object = MediaObject(
                object_id=object_id,
                put_url=HttpRequest(
                    url=put_url,
                    headers={}  # No custom headers for S3 compatibility
                ),
                # Store the hierarchical path for later use
                metadata={"storage_path": object_key}
            )
            
            media_objects.append(media_object)
        
        return FlowStorage(media_objects=media_objects)
        
    except Exception as e:
        logger.error(f"Failed to create flow storage for {flow_id}: {e}")
        raise

class SegmentManager:
    """Manager for segment operations (create, retrieve, update, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def get_segments(self, flow_id: str, timerange: Optional[str], store: Optional[VASTStore] = None) -> List[FlowSegment]:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            segments = await store.get_flow_segments(flow_id, timerange=timerange)
            return segments
        except Exception as e:
            logger.error(f"Failed to get segments for flow {flow_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_segment(self, flow_id: str, request, file, segment: str, store: Optional[VASTStore] = None) -> FlowSegment:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            # Parse segment data
            import json
            segment_data = json.loads(segment) if segment else {}
            segment_obj = FlowSegment(**segment_data)
            
            # Read file data
            file_content = await file.read()
            
            # Create segment in store
            success = await store.create_flow_segment(segment_obj, flow_id, file_content, file.content_type)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create segment")
            
            return segment_obj
        except Exception as e:
            logger.error(f"Failed to create segment for flow {flow_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_segments(self, flow_id: str, timerange: Optional[str], store: Optional[VASTStore] = None, soft_delete: bool = True, deleted_by: str = "system"):
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            success = await store.delete_flow_segments(flow_id, timerange=timerange, soft_delete=soft_delete, deleted_by=deleted_by)
            if not success:
                raise HTTPException(status_code=404, detail="Flow not found")
            
            delete_type = "soft deleted" if soft_delete else "hard deleted"
            timerange_msg = f" in timerange {timerange}" if timerange else ""
            return {"message": f"Segments {delete_type}{timerange_msg}"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete segments for flow {flow_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def allocate_storage(self, flow_id: str, storage_request: FlowStoragePost, store: Optional[VASTStore] = None) -> FlowStorage:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            # This would typically involve creating storage locations
            # For now, return a mock response
            storage_locations = []
            if storage_request.object_ids:
                for object_id in storage_request.object_ids:
                    storage_locations.append({
                        "object_id": object_id,
                        "put_url": f"http://example.com/upload/{object_id}",
                        "bucket_put_url": f"http://example.com/bucket/{object_id}"
                    })
            
            return FlowStorage(storage_locations=storage_locations)
        except Exception as e:
            logger.error(f"Failed to allocate storage for flow {flow_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def head_segments(self, flow_id: str) -> dict:
        """Return headers for the segments endpoint for a given flow."""
        return {} 