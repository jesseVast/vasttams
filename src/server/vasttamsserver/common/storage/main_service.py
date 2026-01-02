"""
Main TAMS Storage Service

This module provides the main TAMS storage service that composes all
the focused storage services into a unified interface.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from .interfaces import StorageInterface
from .timestamp_utils import get_tams_timestamp, prepare_data_for_pyarrow
# Import models from their resource modules
from ...flows.models import Flow
from ..filters import FlowFilters, FlowDetailFilters
from ...sources.models import Source
from ...segments.models import FlowSegment
from ...objects.models import Object, ObjectInstance

# Import service classes from their resource modules
from ...flows.service import FlowStorageService
from ...sources.service import SourceStorageService  
from ...segments.service import SegmentStorageService
from ...objects.service import ObjectStorageService
from ..tags.service import TagStorageService

# Import shared models from common
from ..filters import SourceFilters
from ..models import Tags, CollectionItem, TimeRange, HttpRequest
from ...service.models import Service
from ...service.storage_models import StorageBackend, MediaObject, FlowStorage, FlowStoragePost

# Import config from core (unchanged location)
from ...core.config import get_settings

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
    
    async def get_flow(self, flow_id: str, filters: Optional[FlowDetailFilters] = None) -> Optional[Flow]:
        return await self.flow_service.get_flow(flow_id, filters)
    
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
        """Delete a flow and cleanup unreferenced objects per TAMS 8.0 spec"""
        return await self.flow_service.delete_flow(flow_id, cascade, self.object_service)
    
    # Flow segment operations - delegate to segment service
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None, skip_get_urls_generation: bool = False) -> List[FlowSegment]:
        return await self.segment_service.get_flow_segments(flow_id, timerange, skip_get_urls_generation=skip_get_urls_generation)
    
    async def create_flow_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        return await self.segment_service.create_flow_segment(flow_id, segment)
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """Delete flow segments and cleanup unreferenced objects per TAMS 8.0 spec"""
        result = await self.segment_service.delete_flow_segments(flow_id, timerange)
        
        # After deleting segments, cleanup unreferenced objects (TAMS 8.0 spec requirement)
        if result:
            try:
                unreferenced = await self.object_service.get_unreferenced_objects()
                if unreferenced:
                    deleted_count = await self.object_service.delete_unreferenced_objects(unreferenced)
                    logger.info("Cleaned up %d unreferenced objects after segment deletion", deleted_count)
            except Exception as e:
                logger.warning("Failed to cleanup unreferenced objects after segment deletion: %s", e)
                # Don't fail the deletion if cleanup fails
        
        return result
    
    # Object operations - delegate to object service
    async def get_objects(self) -> List[Object]:
        return await self.object_service.get_objects()
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        return await self.object_service.get_object(object_id)
    
    async def create_object(self, obj: Object) -> bool:
        return await self.object_service.create_object(obj)
    
    async def delete_object(self, object_id: str) -> bool:
        return await self.object_service.delete_object(object_id)
    
    # Object instance operations (TAMS 8.0) - delegate to object service
    async def create_object_instance(self, object_id: str, instance: ObjectInstance) -> bool:
        return await self.object_service.create_object_instance(object_id, instance)
    
    async def list_object_instances(self, object_id: str) -> List[ObjectInstance]:
        return await self.object_service.list_object_instances(object_id)
    
    async def delete_object_instance(self, object_id: str, label: Optional[str] = None, storage_id: Optional[str] = None) -> bool:
        return await self.object_service.delete_object_instance(object_id, label, storage_id)
    
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
            from ...storagebackends.service import StorageBackendService
            
            # Use the dedicated storage backend service
            backend_service = StorageBackendService(self.vast_db, self.s3_client)
            backends = await backend_service.get_storage_backends()
            
            # If no backends in database, return a default one
            if not backends:
                logger.warning("No storage backends found in database, returning default")
                return [
                    StorageBackend(
                        id="60af2ab4-e8a5-4c65-a09b-d35983680315",
                        label="default-s3-storage",
                        store_type="http_object_store",
                        provider="minio",
                        store_product="minio",
                        region="us-east-1",
                        availability_zone="a",
                        default_storage=True
                    )
                ]
            
            return backends
        except Exception as e:
            logger.error("Failed to get storage backends: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Utility operations
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        return await self.flow_service.check_flow_read_only(flow_id)
    
    async def generate_presigned_url(self, key: str, operation: str, expiration: int = 3600, storage_backend: Optional[Dict[str, Any]] = None, content_type: Optional[str] = None) -> Optional[str]:
        """Generate presigned URL for S3 operations, preferring provided storage backend credentials.
        
        Args:
            key: S3 object key
            operation: S3 operation (get_object, put_object)
            expiration: URL expiration in seconds
            storage_backend: Optional backend-specific config
            content_type: MIME type for PUT requests (TAMS 8.0 requirement)
        """
        try:
            import inspect
            # Map operation to HTTP method commonly used by S3
            http_method = 'GET' if operation.lower() in ('get', 'get_object') else 'PUT'
            # Use provided content_type or fallback (TAMS 8.0 requires content-type for PUT)
            final_content_type = content_type or 'application/octet-stream'
            
            # Check if storage_backend has valid credentials or should fallback to settings
            backend_access_key = storage_backend.get('access_key') if storage_backend else None
            backend_secret_key = storage_backend.get('secret_key') if storage_backend else None
            # Use backend credentials if they exist and are non-empty, otherwise use settings
            final_access_key = (backend_access_key if backend_access_key and backend_access_key.strip() else None) or self.settings.s3_access_key_id
            final_secret_key = (backend_secret_key if backend_secret_key and backend_secret_key.strip() else None) or self.settings.s3_secret_access_key
            
            # Only use backend-specific client if backend has endpoint_url or valid credentials
            if storage_backend and (storage_backend.get('endpoint_url') or (final_access_key and final_secret_key and final_access_key.strip() and final_secret_key.strip())):
                # Build a temporary S3 client using backend-specific config
                from vasts3 import S3Client, S3Config
                settings = self.settings
                
                # Use backend-specific values when available, fallback to settings
                backend_root_path = storage_backend.get('root_path') or getattr(settings, 's3_root_path', None)
                key_prefix = backend_root_path.strip('/') if backend_root_path else ""
                
                cfg = S3Config(
                    endpoint_url=storage_backend.get('endpoint_url') or settings.s3_endpoint_url,
                    bucket_name=storage_backend.get('bucket_name') or settings.s3_bucket_name,
                    access_key=final_access_key,
                    secret_key=final_secret_key,
                    region=storage_backend.get('region') or settings.s3_region,
                    use_ssl=storage_backend.get('use_ssl') if storage_backend.get('use_ssl') is not None else settings.s3_use_ssl,
                    chunk_size=settings.vaststore_s3_chunk_size,
                    max_concurrent_parts=settings.vaststore_s3_max_concurrent_parts,
                    key_prefix=key_prefix,
                )
                tmp_client = S3Client(cfg)
                # Build kwargs compatible with the installed vasts3 version
                sig = inspect.signature(tmp_client.generate_presigned_url)
                supported = set(sig.parameters.keys())
                candidate_kwargs = {
                    'key': key,
                    'operation': operation,
                    'expires_in': expiration,
                    'expiration': expiration,
                    'method': http_method,
                    'http_method': http_method,
                    'content_type': final_content_type if http_method == 'PUT' else None,
                    # Note: response_content_type and response_content_disposition are not included
                    # because VAST S3 backend does not support these parameters in presigned URLs
                }
                # Remove None values
                candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
                kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
                return tmp_client.generate_presigned_url(**kwargs)
            # Fallback to default client
            sig = inspect.signature(self.s3_client.generate_presigned_url)
            supported = set(sig.parameters.keys())
            candidate_kwargs = {
                'key': key,
                'operation': operation,
                'expires_in': expiration,
                'expiration': expiration,
                'method': http_method,
                'http_method': http_method,
                'content_type': final_content_type if http_method == 'PUT' else None,
                # Note: response_content_type and response_content_disposition are not included
                # because VAST S3 backend does not support these parameters in presigned URLs
            }
            # Remove None values
            candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
            kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
            return self.s3_client.generate_presigned_url(**kwargs)
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
                        "timestamp": get_tams_timestamp().isoformat()
                    }
                else:
                    return {
                        "total_sources": 0, "total_flows": 0, "total_segments": 0,
                        "total_objects": 0, "total_storage_bytes": 0,
                        "video_flows": 0, "audio_flows": 0, "data_flows": 0,
                        "timestamp": get_tams_timestamp().isoformat()
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
                        "timestamp": get_tams_timestamp().isoformat()
                    }
                else:
                    return {
                        "sources": [],
                        "total_sources": 0,
                        "timestamp": get_tams_timestamp().isoformat()
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
                        "timestamp": get_tams_timestamp().isoformat()
                    }
                else:
                    return {
                        "total_flows": 0,
                        "estimated_storage_bytes": 0,
                        "timestamp": get_tams_timestamp().isoformat()
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
                        "timestamp": get_tams_timestamp().isoformat()
                    }
                else:
                    return {
                        "total_objects": 0,
                        "total_size_bytes": 0,
                        "timestamp": get_tams_timestamp().isoformat()
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
                        "timestamp": get_tams_timestamp().isoformat()
                    }
                else:
                    return {
                        "total_segments": 0,
                        "timestamp": get_tams_timestamp().isoformat()
                    }
            
            else:
                return {
                    "error": f"Unknown analytics query type: {query_type}",
                    "timestamp": get_tams_timestamp().isoformat()
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
            from ..service.deletion_service import DeletionRequestService
            from ..core.dependencies import get_vast_db
            
            vast_db = get_vast_db()
            deletion_service = DeletionRequestService(vast_db)
            requests = await deletion_service.get_deletion_requests()
            
            # Convert to dict format
            return [req.model_dump() for req in requests]
        except Exception as e:
            logger.error("Failed to get deletion requests: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_deletion_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific deletion request by ID"""
        try:
            from ..service.deletion_service import DeletionRequestService
            from ..core.dependencies import get_vast_db
            
            vast_db = get_vast_db()
            deletion_service = DeletionRequestService(vast_db)
            request = await deletion_service.get_deletion_request(request_id)
            
            if not request:
                return None
            
            return request.model_dump()
        except Exception as e:
            logger.error("Failed to get deletion request %s: %s", request_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Flow storage operations
    async def allocate_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> FlowStorage:
        """Allocate storage for a flow with real S3 presigned URLs"""
        try:
            from ...service.storage_models import MediaObject, HttpRequest
            from ...common.storage.timestamp_utils import get_tams_timestamp
            import uuid
            
            # Get Flow to derive content-type (TAMS 8.0 AppNote 0018 requirement)
            flow = await self.get_flow(flow_id)
            if not flow:
                raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")
            
            # Derive content-type from Flow per TAMS 8.0 spec
            # First check flow.container (authoritative source per TAMS spec)
            flow_container = getattr(flow, 'container', None)
            if flow_container and isinstance(flow_container, str) and '/' in flow_container:
                content_type = flow_container
            else:
                # Fallback to heuristics based on format/codec
                flow_format = getattr(flow, 'format', None)
                flow_codec = getattr(flow, 'codec', None)
                if flow_format == "urn:x-nmos:format:video":
                    content_type = "video/mp2t"
                elif flow_format == "urn:x-nmos:format:audio":
                    content_type = "video/mp2t"
                elif flow_format == "urn:x-nmos:format:image":
                    content_type = flow_codec if flow_codec and '/' in flow_codec else "image/jpeg"
                elif flow_format == "urn:x-nmos:format:data":
                    content_type = "application/octet-stream"
                else:
                    content_type = flow_codec if flow_codec and '/' in flow_codec else "video/mp2t"
            
            logger.debug(f"Derived content-type '{content_type}' from flow {flow_id}")
            
            backend_info = None
            resolved_storage_id = None
            
            # If a storage_id was specified, fetch that backend to use its endpoint/credentials
            if getattr(storage_request, 'storage_id', None):
                resolved_storage_id = storage_request.storage_id
                try:
                    from ...storagebackends.service import StorageBackendService
                    backend_service = StorageBackendService(self.vast_db, self.s3_client)
                    backend = await backend_service.get_storage_backend(storage_request.storage_id)
                    if backend:
                        backend_info = backend.model_dump()
                except Exception as e:
                    logger.warning(f"Failed to load storage backend {storage_request.storage_id}: {e}")
            else:
                # No storage_id provided - resolve default backend at creation time
                # This ensures all objects have storage_id in metadata (required for get_urls)
                try:
                    from ...storagebackends.service import StorageBackendService
                    backend_service = StorageBackendService(self.vast_db, self.s3_client)
                    backends = await backend_service.get_storage_backends()
                    default_backend = next((b for b in backends if b.default_storage), None)
                    if default_backend:
                        resolved_storage_id = default_backend.id
                        backend_info = default_backend.model_dump()
                        logger.debug(f"Using default storage backend {resolved_storage_id} for object allocation")
                    else:
                        logger.warning("No default storage backend found - object will not have storage_id in metadata")
                except Exception as e:
                    logger.warning(f"Failed to resolve default storage backend: {e}")
            
            # Generate object IDs
            limit = storage_request.limit or 1
            object_ids = [str(uuid.uuid4()) for _ in range(limit)]
            
            # Generate storage locations with presigned URLs
            media_objects = []
            for object_id in object_ids:
                # Generate TAMS-compliant storage path
                now = get_tams_timestamp()
                year = str(now.year)
                month = f"{now.month:02d}"
                date = f"{now.day:02d}"
                
                # Use TAMS path format: {tams_storage_path}/{year}/{month}/{date}/{object_id}
                # Normalize paths to avoid double slashes
                # Remove leading/trailing slashes from tams_storage_path
                tams_path = self.settings.tams_storage_path.strip('/')
                relative_storage_path = f"{tams_path}/{year}/{month}/{date}/{object_id}"
                
                # Include root_path in storage_path if backend has one
                # This ensures storage_path in metadata matches the actual S3 key
                backend_root_path = None
                if backend_info:
                    backend_root_path = backend_info.get('root_path')
                    if backend_root_path:
                        backend_root_path = backend_root_path.strip('/')
                
                # If backend has root_path, include it in storage_path for metadata
                if backend_root_path:
                    storage_path = f"{backend_root_path}/{relative_storage_path}"
                else:
                    storage_path = relative_storage_path
                
                # Generate presigned URL for upload with content-type (TAMS 8.0 requirement)
                # Pass relative_storage_path (without root_path) since generate_presigned_url
                # will use key_prefix from storage_backend
                presigned_url = await self.generate_presigned_url(
                    key=relative_storage_path,
                    operation="put_object",
                    expiration=self.settings.s3_presigned_url_upload_timeout,
                    storage_backend=backend_info,
                    content_type=content_type
                )
                
                if not presigned_url:
                    raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL for object {object_id}")
                
                # Create MediaObject with content-type in put_url (TAMS 8.0 requirement)
                # Use model_validate with alias key for proper serialization
                put_url_data = {
                    "url": presigned_url,
                    "content-type": content_type,  # Required by TAMS 8.0 spec (using alias)
                    "headers": {}
                }
                media_object = MediaObject(
                    object_id=object_id,
                    put_url=HttpRequest.model_validate(put_url_data),
                    metadata={"storage_path": storage_path}
                )
                
                media_objects.append(media_object)

                # Persist object row so segments can reference and URLs can be generated dynamically
                try:
                    metadata = {
                        "storage_path": storage_path,  # Full path including root_path
                        "content_type": content_type  # Store for GET URL generation
                    }
                    # Always store storage_id if we resolved one (required for get_urls generation)
                    if resolved_storage_id:
                        metadata["storage_id"] = resolved_storage_id
                    elif backend_info and backend_info.get('id'):
                        # Fallback to backend_info.id if resolved_storage_id wasn't set
                        metadata["storage_id"] = backend_info['id']
                    else:
                        logger.warning(f"Object {object_id} created without storage_id - get_urls generation may fail")
                    # Build raw row dict (avoid Pydantic Object model to bypass timerange requirement)
                    # Note: referenced_by_flows is computed dynamically from segments table, not stored
                    obj_row = {
                        "id": object_id,
                        "first_referenced_by_flow": None,  # Computed dynamically from segments when first segment is created
                        "timerange": None,
                        "size": None,
                        "metadata": json.dumps(metadata),
                        "created": get_tams_timestamp(),
                    }
                    # Convert timestamps to PyArrow format
                    obj_row = prepare_data_for_pyarrow(obj_row)
                    self.vast_db.insert_record("objects", obj_row)
                except Exception as e:
                    logger.warning(f"Failed to persist object {object_id}: {e}")
            
            # Create FlowStorage response
            from ...service.storage_models import FlowStorage
            flow_storage = FlowStorage(
                flow_id=flow_id,
                media_objects=media_objects
            )
            
            return flow_storage
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to allocate storage for flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
