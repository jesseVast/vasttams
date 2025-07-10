"""
Segments submodule for TAMS API.
Handles segment-related operations and business logic.
"""
from typing import List, Optional
from fastapi import HTTPException
import json
import uuid
from datetime import datetime, timezone
from .models import FlowSegment, FlowStorage, FlowStoragePost, StorageLocation
from .vast_store import VASTStore
import logging

logger = logging.getLogger(__name__)

class SegmentManager:
    """Manager for segment operations (create, retrieve, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def head_segments(self, flow_id: str):
        """
        Return headers for the segments endpoint for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.

        Returns:
            dict: Empty dictionary (placeholder for headers).
        """
        return {}

    async def get_segments(self, flow_id: str, timerange: Optional[str] = None, store: Optional[VASTStore] = None) -> List[FlowSegment]:
        """
        Retrieve all segments for a given flow, optionally filtered by timerange.

        Args:
            flow_id (str): The unique identifier of the flow.
            timerange (Optional[str]): Optional timerange filter for segments.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            List[FlowSegment]: List of flow segments matching the criteria.

        Raises:
            HTTPException: 500 if the VAST store is not initialized or an internal error occurs.
        """
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            segments = await store.get_flow_segments(flow_id, timerange=timerange)
            return segments
        except Exception as e:
            logger.error(f"Failed to get flow segments for flow {flow_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_segment(self, flow_id: str, request, file, segment: Optional[str] = None, store: Optional[VASTStore] = None) -> FlowSegment:
        """
        Create a new segment for a given flow, storing media data and metadata.

        Args:
            flow_id (str): The unique identifier of the flow.
            request: The FastAPI request object containing the segment data.
            file: The uploaded media file for the segment.
            segment (Optional[str]): Optional JSON string representing the segment metadata.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            FlowSegment: The created flow segment object.

        Raises:
            HTTPException: 500 if the VAST store is not initialized or creation fails.
        """
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            if segment is not None:
                segment_obj = FlowSegment(**json.loads(segment))
            else:
                data = await request.json()
                segment_obj = FlowSegment(**data["segment"]) if "segment" in data else FlowSegment(**data)
            file_data = await file.read()
            content_type = file.content_type or 'application/octet-stream'
            success = await store.create_flow_segment(segment_obj, flow_id, file_data, content_type)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create flow segment")
            return segment_obj
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create flow segment: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_segments(self, flow_id: str, timerange: Optional[str] = None, store: Optional[VASTStore] = None):
        """
        Delete segments for a given flow, optionally filtered by timerange.

        Args:
            flow_id (str): The unique identifier of the flow.
            timerange (Optional[str]): Optional timerange filter for deletion.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: Message indicating successful deletion.

        Raises:
            HTTPException: 500 if the VAST store is not initialized or deletion fails.
        """
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            success = await store.delete_flow_segments(flow_id, timerange=timerange)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete flow segments")
            return {"message": "Flow segments deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete flow segments: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def allocate_storage(self, flow_id: str, storage_request: FlowStoragePost, store: Optional[VASTStore] = None) -> FlowStorage:
        """
        Allocate storage locations for uploading flow segments.

        Args:
            flow_id (str): The unique identifier of the flow.
            storage_request (FlowStoragePost): The storage allocation request.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            FlowStorage: Storage locations with presigned URLs for uploading segments.

        Raises:
            HTTPException: 404 if the flow is not found, 500 for internal errors or if the store is not initialized.
        """
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            flow = await store.get_flow(flow_id)
            if not flow:
                raise HTTPException(status_code=404, detail="Flow not found")
            storage_locations = []
            object_ids = storage_request.object_ids or [str(uuid.uuid4()) for _ in range(storage_request.limit or 1)]
            for object_id in object_ids:
                put_url = await store.s3_store.generate_presigned_url(
                    flow_id, object_id, "[0:0)", 'put_object'
                )
                storage_locations.append(StorageLocation(
                    object_id=object_id,
                    put_url=put_url or "",
                    bucket_put_url=None
                ))
            return FlowStorage(storage_locations=storage_locations)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to allocate storage for flow {flow_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error") 