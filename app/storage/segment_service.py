"""
Segment Storage Service

This module handles all flow segment-related storage operations including
CRUD operations, filtering, and segment management.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import FlowSegment, FlowStorage, FlowStoragePost, MediaObject, HttpRequest

logger = logging.getLogger(__name__)


class SegmentStorageService:
    """Handles flow segment-related storage operations"""
    
    def __init__(self, vast_db, s3_client, settings):
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """Get flow segments with optional timerange filtering"""
        try:
            # Query segments using vaststore
            query = self.vast_db.query("segments").select("*").where(f"flow_id = '{flow_id}'")
            
            if timerange:
                # Add timerange filtering if provided
                query = query.where(f"timerange = '{timerange}'")
            
            result = query.execute()
            
            # Convert to FlowSegment objects
            segments = []
            for row in result:
                segment_data = dict(row)
                segments.append(FlowSegment(**segment_data))
            
            return segments
        except Exception as e:
            logger.error("Failed to get flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_flow_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        """Create a new flow segment"""
        try:
            segment_data = segment.model_dump()
            segment_data['flow_id'] = flow_id
            self.vast_db.insert_record("segments", segment_data)
            return True
        except Exception as e:
            logger.error("Failed to create flow segment: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """Delete flow segments"""
        try:
            # Delete segments using vaststore
            query = self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'")
            if timerange:
                query = query.where(f"timerange = '{timerange}'")
            
            query.execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
        """Create storage allocation for a flow"""
        try:
            import uuid
            
            # Generate object IDs if not provided
            if storage_request.object_ids:
                object_ids = storage_request.object_ids
            else:
                limit = storage_request.limit or self.settings.flow_storage_default_limit
                object_ids = [str(uuid.uuid4()) for _ in range(limit)]
            
            # Validate that object IDs don't already exist
            for object_id in object_ids:
                existing_object = await self._get_object(object_id)
                if existing_object:
                    raise HTTPException(status_code=400, detail=f"Object ID {object_id} already exists")
            
            # Generate storage locations with presigned URLs
            media_objects = []
            for object_id in object_ids:
                # Generate TAMS-compliant storage path
                now = datetime.now()
                year = str(now.year)
                month = f"{now.month:02d}"
                date = f"{now.day:02d}"
                
                # Use TAMS path format: {tams_storage_path}/{year}/{month}/{date}/{object_id}
                storage_path = f"{self.settings.tams_storage_path}/{year}/{month}/{date}/{object_id}"
                
                # Generate presigned URL for upload
                presigned_url = await self._generate_presigned_url(
                    key=storage_path,
                    operation="put_object",
                    expiration=self.settings.s3_presigned_url_upload_timeout
                )
                
                if not presigned_url:
                    raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL for object {object_id}")
                
                # Create MediaObject with the hierarchical path
                media_object = MediaObject(
                    object_id=object_id,
                    put_url=HttpRequest(
                        url=presigned_url,
                        headers={}
                    ),
                    metadata={"storage_path": storage_path}
                )
                
                media_objects.append(media_object)
                
                # Create Object record in database for TAMS compliance
                from ..models import Object
                obj = Object(
                    id=object_id,
                    referenced_by_flows=[flow_id],
                    first_referenced_by_flow=flow_id,
                    created=now
                )
                await self._create_object(obj)
            
            # Create FlowStorage response
            flow_storage = FlowStorage(
                flow_id=flow_id,
                media_objects=media_objects
            )
            
            return flow_storage
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to create flow storage for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _get_object(self, object_id: str):
        """Get an object by ID"""
        try:
            result = self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            if not result or len(result) == 0:
                return None
            return dict(result[0])
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e)
            return None
    
    async def _create_object(self, obj):
        """Create an object"""
        try:
            now = datetime.now(timezone.utc)
            obj.created = now
            
            object_data = obj.model_dump()
            self.vast_db.insert_record("objects", object_data)
            return True
        except Exception as e:
            logger.error("Failed to create object: %s", e)
            return False
    
    async def _generate_presigned_url(self, key: str, operation: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 operations"""
        try:
            return self.s3_client.generate_presigned_url(
                key=key,
                operation=operation,
                expiration=expiration
            )
        except Exception as e:
            logger.error("Failed to generate presigned URL: %s", e)
            return None
