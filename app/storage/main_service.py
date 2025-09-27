"""
Main TAMS Storage Service

This module provides the main TAMS storage service that composes all
the focused storage services into a unified interface.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import (
    Source, Flow, FlowSegment, Object, Service, StorageBackend,
    SourceFilters, FlowFilters, FlowDetailFilters,
    FlowStorage, FlowStoragePost, MediaObject, HttpRequest,
    Tags, CollectionItem, TimeRange
)
from .source_service import SourceStorageService
from .flow_service import FlowStorageService
from .segment_service import SegmentStorageService
from .object_service import ObjectStorageService
from .tag_service import TagStorageService
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class TAMSStorageService(StorageInterface):
    """Main TAMS storage service that composes all focused services"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = get_settings()
        
        # Initialize focused services
        self.source_service = SourceStorageService(vast_db, s3_client)
        self.flow_service = FlowStorageService(vast_db, s3_client)
        self.segment_service = SegmentStorageService(vast_db, s3_client, self.settings)
        self.object_service = ObjectStorageService(vast_db, s3_client)
        self.tag_service = TagStorageService(vast_db, s3_client)
    
    # Source operations - delegate to source service
    async def get_sources(self, filters: SourceFilters) -> List[Source]:
        return await self.source_service.get_sources(filters)
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        return await self.source_service.get_source(source_id)
    
    async def create_source(self, source: Source) -> bool:
        return await self.source_service.create_source(source)
    
    async def update_source(self, source_id: str, source: Source) -> bool:
        return await self.source_service.update_source(source_id, source)
    
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        return await self.source_service.delete_source(source_id, cascade)
    
    # Flow operations - delegate to flow service
    async def get_flows(self, filters: FlowFilters) -> List[Flow]:
        return await self.flow_service.get_flows(filters)
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        return await self.flow_service.get_flow(flow_id)
    
    async def create_flow(self, flow: Flow) -> bool:
        return await self.flow_service.create_flow(flow)
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        return await self.flow_service.update_flow(flow_id, flow)
    
    async def delete_flow(self, flow_id: str) -> bool:
        return await self.flow_service.delete_flow(flow_id)
    
    # Flow segment operations - delegate to segment service
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        return await self.segment_service.get_flow_segments(flow_id, timerange)
    
    async def create_flow_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        return await self.segment_service.create_flow_segment(flow_id, segment)
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        return await self.segment_service.delete_flow_segments(flow_id, timerange)
    
    # Object operations - delegate to object service
    async def get_object(self, object_id: str) -> Optional[Object]:
        return await self.object_service.get_object(object_id)
    
    async def create_object(self, obj: Object) -> bool:
        return await self.object_service.create_object(obj)
    
    async def delete_object(self, object_id: str) -> bool:
        return await self.object_service.delete_object(object_id)
    
    # Storage allocation operations - delegate to segment service
    async def create_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
        return await self.segment_service.create_flow_storage(flow_id, storage_request)
    
    # Tag operations - delegate to tag service
    async def get_source_tags(self, source_id: str) -> Optional[Tags]:
        return await self.tag_service.get_source_tags(source_id)
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        return await self.tag_service.update_source_tags(source_id, tags)
    
    async def get_source_tag(self, source_id: str, name: str) -> Optional[str]:
        return await self.tag_service.get_source_tag(source_id, name)
    
    async def update_source_tag(self, source_id: str, name: str, value: str) -> bool:
        return await self.tag_service.update_source_tag(source_id, name, value)
    
    async def delete_source_tag(self, source_id: str, name: str) -> bool:
        return await self.tag_service.delete_source_tag(source_id, name)
    
    # Collection operations - delegate to source service
    async def get_source_collections(self, source_id: str) -> List[CollectionItem]:
        return await self.source_service.get_source_collections(source_id)
    
    async def add_source_to_collection(self, collection_id: str, source_id: str, label: str, description: str) -> bool:
        return await self.source_service.add_source_to_collection(collection_id, source_id, label, description)
    
    async def remove_source_from_collection(self, collection_id: str, source_id: str) -> bool:
        return await self.source_service.remove_source_from_collection(collection_id, source_id)
    
    # Service operations
    async def get_service_info(self) -> Service:
        """Get service information"""
        try:
            return Service(
                name=self.settings.api_title,
                description=self.settings.api_description,
                type="urn:x-tams:service:api",
                api_version=self.settings.api_version,
                service_version="1.0.0"
            )
        except Exception as e:
            logger.error("Failed to get service info: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_storage_backends(self) -> List[StorageBackend]:
        """Get storage backends"""
        try:
            # For now, return a default S3 backend
            # In a real implementation, this would query the database
            return [
                StorageBackend(
                    id=str(uuid.uuid4()),
                    store_type="s3",
                    provider="minio",
                    store_product="minio",
                    region="us-east-1",
                    label="Default S3 Storage",
                    default_storage=True
                )
            ]
        except Exception as e:
            logger.error("Failed to get storage backends: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Utility operations
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        return await self.flow_service.check_flow_read_only(flow_id)
    
    async def generate_presigned_url(self, key: str, operation: str, expiration: int = 3600) -> Optional[str]:
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
    
    async def get_analytics(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """Get analytics data for the specified query type"""
        try:
            if query_type == "flow_usage":
                # Get flow usage analytics
                flows = await self.flow_service.get_flows(FlowFilters())
                total_flows = len(flows)
                
                # Calculate estimated storage bytes (simplified)
                estimated_storage_bytes = total_flows * 1024 * 1024  # 1MB per flow estimate
                
                return {
                    "total_flows": total_flows,
                    "estimated_storage_bytes": estimated_storage_bytes,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "storage_usage":
                # Get storage usage analytics
                objects = await self.object_service.get_objects()
                total_objects = len(objects)
                
                # Calculate total size (simplified)
                total_size_bytes = sum(obj.size or 0 for obj in objects)
                
                return {
                    "total_objects": total_objects,
                    "total_size_bytes": total_size_bytes,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "time_range_analysis":
                # Get time range analytics
                segments = await self.segment_service.get_flow_segments("", None)
                total_segments = len(segments)
                
                return {
                    "total_segments": total_segments,
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                return {
                    "error": f"Unknown analytics query type: {query_type}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("Failed to get analytics for %s: %s", query_type, e)
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
