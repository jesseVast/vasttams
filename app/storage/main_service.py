"""
Main TAMS Storage Service

This module provides the main TAMS storage service that composes all
the focused storage services into a unified interface.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
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
    
    async def update_flow_description(self, flow_id: str, description: str) -> bool:
        return await self.flow_service.update_flow_description(flow_id, description)
    
    async def delete_flow_description(self, flow_id: str) -> bool:
        return await self.flow_service.delete_flow_description(flow_id)
    
    async def update_flow_label(self, flow_id: str, label: str) -> bool:
        return await self.flow_service.update_flow_label(flow_id, label)
    
    async def delete_flow_label(self, flow_id: str) -> bool:
        return await self.flow_service.delete_flow_label(flow_id)
    
    async def update_flow_read_only(self, flow_id: str, read_only: bool) -> bool:
        return await self.flow_service.update_flow_read_only(flow_id, read_only)
    
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        return await self.flow_service.delete_flow(flow_id, cascade)
    
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
    
    # Flow tag methods
    async def get_flow_tags(self, flow_id: str) -> Optional[Tags]:
        return await self.tag_service.get_flow_tags(flow_id)
    
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        return await self.tag_service.update_flow_tags(flow_id, tags)
    
    async def update_flow_tag(self, flow_id: str, name: str, value: str) -> bool:
        return await self.tag_service.update_flow_tag(flow_id, name, value)
    
    async def delete_flow_tag(self, flow_id: str, name: str) -> bool:
        return await self.tag_service.delete_flow_tag(flow_id, name)
    
    
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
    
    # Join query operations for enhanced data retrieval
    async def get_flow_with_source_details(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get flow details with source information using join query"""
        return await self.flow_service.get_flow_with_source_details(flow_id)
    
    async def get_flows_with_source_details(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get flows with source information using join query"""
        return await self.flow_service.get_flows_with_source_details(filters)
    
    async def get_segments_with_flow_and_object_details(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get segments with flow and object details using join query"""
        return await self.segment_service.get_segments_with_flow_and_object_details(flow_id)
    
    async def get_segment_analytics(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get segment analytics using join queries"""
        return await self.segment_service.get_segment_analytics(flow_id)
    
    async def get_analytics(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """Get analytics data for the specified query type using optimized SQL queries with joins"""
        try:
            if query_type == "comprehensive_overview":
                # Get comprehensive overview using join queries
                sources_table = self.vast_db.get_qualified_table_name("sources")
                flows_table = self.vast_db.get_qualified_table_name("flows")
                segments_table = self.vast_db.get_qualified_table_name("segments")
                objects_table = self.vast_db.get_qualified_table_name("objects")
                
                sql = f"""
                    SELECT 
                        COUNT(DISTINCT s.id) as total_sources,
                        COUNT(DISTINCT f.id) as total_flows,
                        COUNT(DISTINCT seg.id) as total_segments,
                        COUNT(DISTINCT o.id) as total_objects,
                        COALESCE(SUM(o.size), 0) as total_storage_bytes,
                        COUNT(DISTINCT CASE WHEN f.format = 'urn:x-nmos:format:video' THEN f.id END) as video_flows,
                        COUNT(DISTINCT CASE WHEN f.format = 'urn:x-nmos:format:audio' THEN f.id END) as audio_flows,
                        COUNT(DISTINCT CASE WHEN f.format = 'urn:x-nmos:format:data' THEN f.id END) as data_flows
                    FROM {sources_table} s
                    LEFT JOIN {flows_table} f ON s.id = f.source_id
                    LEFT JOIN {segments_table} seg ON f.id = seg.flow_id
                    LEFT JOIN {objects_table} o ON seg.object_id = o.id
                """
                
                result = self.vast_db.execute_sql(sql)
                if result and 'data' in result and len(result['data']) > 0:
                    row = result['data'][0]
                    return {
                        "total_sources": row[0] if row[0] is not None else 0,
                        "total_flows": row[1] if row[1] is not None else 0,
                        "total_segments": row[2] if row[2] is not None else 0,
                        "total_objects": row[3] if row[3] is not None else 0,
                        "total_storage_bytes": row[4] if row[4] is not None else 0,
                        "video_flows": row[5] if row[5] is not None else 0,
                        "audio_flows": row[6] if row[6] is not None else 0,
                        "data_flows": row[7] if row[7] is not None else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "total_sources": 0, "total_flows": 0, "total_segments": 0,
                        "total_objects": 0, "total_storage_bytes": 0,
                        "video_flows": 0, "audio_flows": 0, "data_flows": 0,
                        "timestamp": datetime.now().isoformat()
                    }
            
            elif query_type == "source_analytics":
                # Get source analytics with flow and segment counts using joins
                sources_table = self.vast_db.get_qualified_table_name("sources")
                flows_table = self.vast_db.get_qualified_table_name("flows")
                segments_table = self.vast_db.get_qualified_table_name("segments")
                objects_table = self.vast_db.get_qualified_table_name("objects")
                
                sql = f"""
                    SELECT 
                        s.id,
                        s.label,
                        s.format,
                        COUNT(DISTINCT f.id) as flow_count,
                        COUNT(seg.id) as segment_count,
                        COALESCE(SUM(o.size), 0) as total_size_bytes
                    FROM {sources_table} s
                    LEFT JOIN {flows_table} f ON s.id = f.source_id
                    LEFT JOIN {segments_table} seg ON f.id = seg.flow_id
                    LEFT JOIN {objects_table} o ON seg.object_id = o.id
                    GROUP BY s.id, s.label, s.format
                    ORDER BY flow_count DESC, segment_count DESC
                """
                
                result = self.vast_db.execute_sql(sql)
                if result and 'data' in result:
                    sources_data = []
                    for row in result['data']:
                        sources_data.append({
                            "source_id": row[0],
                            "label": row[1],
                            "format": row[2],
                            "flow_count": row[3] if row[3] is not None else 0,
                            "segment_count": row[4] if row[4] is not None else 0,
                            "total_size_bytes": row[5] if row[5] is not None else 0
                        })
                    return {
                        "sources": sources_data,
                        "total_sources": len(sources_data),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "sources": [],
                        "total_sources": 0,
                        "timestamp": datetime.now().isoformat()
                    }
            
            elif query_type == "flow_usage":
                # Get flow usage analytics using SQL aggregation
                flows_table = self.vast_db.get_qualified_table_name("flows")
                sql = f"""
                    SELECT 
                        COUNT(*) as total_flows,
                        COUNT(*) * 1048576 as estimated_storage_bytes
                    FROM {flows_table}
                """
                
                result = self.vast_db.execute_sql(sql)
                if result and 'data' in result and len(result['data']) > 0:
                    row = result['data'][0]
                    return {
                        "total_flows": row[0] if row[0] is not None else 0,
                        "estimated_storage_bytes": row[1] if row[1] is not None else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "total_flows": 0,
                        "estimated_storage_bytes": 0,
                        "timestamp": datetime.now().isoformat()
                    }
            
            elif query_type == "storage_usage":
                # Get storage usage analytics using SQL aggregation
                objects_table = self.vast_db.get_qualified_table_name("objects")
                sql = f"""
                    SELECT 
                        COUNT(*) as total_objects,
                        COALESCE(SUM(size), 0) as total_size_bytes
                    FROM {objects_table}
                """
                
                result = self.vast_db.execute_sql(sql)
                if result and 'data' in result and len(result['data']) > 0:
                    row = result['data'][0]
                    return {
                        "total_objects": row[0] if row[0] is not None else 0,
                        "total_size_bytes": row[1] if row[1] is not None else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "total_objects": 0,
                        "total_size_bytes": 0,
                        "timestamp": datetime.now().isoformat()
                    }
            
            elif query_type == "time_range_analysis":
                # Get time range analytics using SQL aggregation
                segments_table = self.vast_db.get_qualified_table_name("segments")
                sql = f"""
                    SELECT COUNT(*) as total_segments
                    FROM {segments_table}
                """
                
                result = self.vast_db.execute_sql(sql)
                if result and 'data' in result and len(result['data']) > 0:
                    row = result['data'][0]
                    return {
                        "total_segments": row[0] if row[0] is not None else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "total_segments": 0,
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
    
    # Webhook operations
    async def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhooks"""
        try:
            # For now, return empty list as webhooks are not fully implemented
            return []
        except Exception as e:
            logger.error("Failed to get webhooks: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Deletion request operations
    async def get_deletion_requests(self) -> List[Dict[str, Any]]:
        """Get all deletion requests"""
        try:
            # For now, return empty list as deletion requests are not fully implemented
            return []
        except Exception as e:
            logger.error("Failed to get deletion requests: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Flow storage operations
    async def allocate_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> FlowStorage:
        """Allocate storage for a flow"""
        try:
            # For now, return a mock storage allocation
            # In a real implementation, this would create actual storage allocation
            from ..models import MediaObject, HttpRequest
            
            # Create a mock media object for testing
            mock_media_object = MediaObject(
                object_id=f"mock-object-{flow_id}",
                put_url=HttpRequest(
                    method="PUT",
                    url=f"https://mock-storage.example.com/objects/{flow_id}",
                    headers={"Content-Type": "application/octet-stream"}
                ),
                metadata={"storage_path": f"/flows/{flow_id}/media"}
            )
            
            return FlowStorage(
                media_objects=[mock_media_object]
            )
        except Exception as e:
            logger.error("Failed to allocate storage for flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
