"""
Simplified VAST Store Orchestrator for TAMS Application

This module is now a simplified orchestrator that delegates VAST operations
to specialized endpoint modules. It maintains backward compatibility while using
the new modular architecture.

TAMS API DELETE RULES (CRITICAL COMPLIANCE):
============================================

1. SOURCE DELETION:
   - cascade=false: MUST FAIL (409 Conflict) if dependent flows exist
   - cascade=true: MUST SUCCEED (200 OK) by deleting source + all dependent flows

2. FLOW DELETION:
   - cascade=false: MUST FAIL (409 Conflict) if dependent segments exist  
   - cascade=true: MUST SUCCEED (200 OK) by deleting flow + all dependent segments

3. SEGMENT DELETION:
   - MUST FAIL (409 Conflict) if dependent objects exist
   - Objects are immutable and cannot be deleted via cascade

4. OBJECT DELETION:
   - Objects are immutable by TAMS API design
   - MUST FAIL (409 Conflict) if they have flow references
   - Cannot be deleted via cascade operations

All delete operations now properly implement TAMS API compliance rules.
"""

import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone

from ..models.models import (
    Source, Flow, FlowSegment, Object, DeletionRequest, 
    TimeRange, Tags, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
    CollectionItem, GetUrl, Webhook, WebhookPost, User, ApiToken, AuthLog, 
    SegmentDuration, FlowCollection, SourceCollection
)
from ..core.config import get_settings
from .storage_backend_manager import StorageBackendManager
from .vastdbmanager import VastDBManager
from .core.storage_factory import StorageFactory
from .endpoints.sources.sources_storage import SourcesStorage
from .endpoints.flows.flows_storage import FlowsStorage
from .endpoints.segments.segments_storage import SegmentsStorage
from .endpoints.objects.objects_storage import ObjectsStorage
from .endpoints.analytics.analytics_engine import AnalyticsEngine

logger = logging.getLogger(__name__)


class VASTStore:
    """
    Simplified VAST Store Orchestrator for TAMS Application
    
    This class now acts as an orchestrator that delegates operations to
    specialized endpoint modules. It maintains backward compatibility while using
    the new modular architecture.
    """
    
    def __init__(self, 
                 endpoint: Optional[str] = None, 
                 access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None, 
                 bucket: Optional[str] = None,
                 schema: Optional[str] = None):
        """
        Initialize VAST Store using provided config or config.py
        
        Args:
            endpoint: VAST Database endpoint URL
            access_key: VAST access key for authentication
            secret_key: VAST secret key for authentication
            bucket: VAST bucket name for TAMS data
            schema: VAST schema name for TAMS tables
        """
        # Use provided parameters or load from config
        if endpoint is None or access_key is None or secret_key is None or bucket is None:
            settings = get_settings()
            self.endpoint = endpoint or settings.vast_endpoint
            self.access_key = access_key or settings.vast_access_key
            self.secret_key = secret_key or settings.vast_secret_key
            self.bucket = bucket or settings.vast_bucket
            self.schema = schema or settings.vast_schema
        else:
            self.endpoint = endpoint
            self.access_key = access_key
            self.secret_key = secret_key
            self.bucket = bucket
            self.schema = schema or "tams7"
        
        # Initialize storage backend manager
        self.storage_backend_manager = StorageBackendManager()
        
        # Initialize storage factory
        self.storage_factory = StorageFactory()
        
        # Initialize VastDBManager for endpoint modules
        self.vast_db_manager = VastDBManager(endpoints=self.endpoint)
        
        # Initialize S3 store (for backward compatibility)
        from .s3_store import S3Store
        self.s3_store = S3Store(storage_backend_manager=self.storage_backend_manager)
        
        # Initialize S3 segments handler
        from .endpoints.segments.segments_s3 import SegmentsS3
        self.segments_s3 = SegmentsS3(self.storage_factory.get_s3_core(), self.storage_backend_manager)
        
        # Initialize specialized endpoint modules
        self.sources_storage = SourcesStorage(self.vast_db_manager)
        self.flows_storage = FlowsStorage(self.vast_db_manager)
        self.segments_storage = SegmentsStorage(self.vast_db_manager, self.segments_s3)
        self.objects_storage = ObjectsStorage(self.vast_db_manager)
        self.analytics_engine = AnalyticsEngine(self.vast_db_manager)
        
        # Create TAMS tables if they don't exist
        self._setup_tams_tables()
        
        logger.info("VASTStore orchestrator initialized - Endpoint: %s, Bucket: %s, Schema: %s", 
                   self.endpoint, self.bucket, self.schema)
    
    def _setup_tams_tables(self):
        """Setup TAMS tables with their schemas - delegated to VASTCore"""
        try:
            # This is now handled by VASTCore during initialization
            logger.info("TAMS tables setup delegated to VASTCore")
        except Exception as e:
            logger.error("Failed to setup TAMS tables: %s", e)
    
    # ============================================================================
    # SOURCE OPERATIONS - Delegated to SourcesStorage
    # ============================================================================
    
    async def create_source(self, source: Source) -> bool:
        """
        Create a TAMS source - delegated to SourcesStorage
        
        Args:
            source: Source model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.sources_storage.create_source(source)
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """
        Get a TAMS source by ID - delegated to SourcesStorage
        
        Args:
            source_id: ID of the source to get
            
        Returns:
            Source: Source model instance or None if not found
        """
        return await self.sources_storage.get_source(source_id)
    
    async def list_sources(self, filters: Optional[Dict[str, Any]] = None, 
                          limit: Optional[int] = None) -> List[Source]:
        """
        List TAMS sources with optional filtering - delegated to SourcesStorage
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of sources to return
            
        Returns:
            List[Source]: List of source models
        """
        return await self.sources_storage.list_sources(filters, limit)
    
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        """
        Delete a TAMS source - delegated to SourcesStorage
        
        Args:
            source_id: ID of the source to delete
            cascade: Whether to cascade delete related flows
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If cascade=False and dependent flows exist (TAMS API compliance)
        """
        try:
            return await self.sources_storage.delete_source(source_id, cascade)
        except ValueError as e:
            # Re-raise TAMS compliance errors for proper HTTP handling
            raise e
    
    # ============================================================================
    # FLOW OPERATIONS - Delegated to FlowsStorage
    # ============================================================================
    
    async def create_flow(self, flow: Flow) -> bool:
        """
        Create a TAMS flow - delegated to FlowsStorage
        
        Args:
            flow: Flow model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.flows_storage.create_flow(flow)
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """
        Get a TAMS flow by ID - delegated to FlowsStorage
        
        Args:
            flow_id: ID of the flow to get
            
        Returns:
            Flow: Flow model instance or None if not found
        """
        return await self.flows_storage.get_flow(flow_id)
    
    async def list_flows(self, filters: Optional[Dict[str, Any]] = None, 
                         limit: Optional[int] = None) -> List[Flow]:
        """
        List TAMS flows with optional filtering - delegated to FlowsStorage
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of flows to return
            
        Returns:
            List[Flow]: List of flow models
        """
        return await self.flows_storage.list_flows(filters, limit)
    
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        """
        Delete a TAMS flow - delegated to FlowsStorage
        
        Args:
            flow_id: ID of the flow to delete
            cascade: Whether to cascade delete related segments
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If cascade=False and dependent segments exist (TAMS API compliance)
        """
        try:
            return await self.flows_storage.delete_flow(flow_id, cascade)
        except ValueError as e:
            # Re-raise TAMS compliance errors for proper HTTP handling
            raise e
    
    # ============================================================================
    # SEGMENT OPERATIONS - Delegated to SegmentsStorage
    # ============================================================================
    
    async def create_flow_segment(self, segment: FlowSegment, flow_id: str, 
                                 data: bytes, content_type: str = "application/octet-stream") -> bool:
        """
        Create a TAMS flow segment - delegated to SegmentsStorage
        
        Args:
            segment: FlowSegment model instance
            flow_id: ID of the flow this segment belongs to
            data: Media data bytes
            content_type: MIME type of the media data
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.segments_storage.create_segment(segment, flow_id, data)
    
    async def create_flow_segment_metadata(self, segment: FlowSegment, flow_id: str) -> bool:
        """
        Create a TAMS flow segment with metadata only (no media data)
        Used when media data is uploaded separately via presigned URL
        
        Args:
            segment: FlowSegment model instance
            flow_id: ID of the flow this segment belongs to
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.segments_storage.create_segment_metadata(segment, flow_id)
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """
        Get TAMS flow segments - delegated to SegmentsStorage
        
        Args:
            flow_id: ID of the flow to get segments for
            timerange: Optional timerange filter
            
        Returns:
            List[FlowSegment]: List of flow segment models
        """
        return await self.segments_storage.get_segments(flow_id, timerange)
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """
        Delete TAMS flow segments - delegated to SegmentsStorage
        
        Args:
            flow_id: ID of the flow to delete segments for
            timerange: Optional timerange filter
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.segments_storage.delete_segments(flow_id, timerange)
    
    # ============================================================================
    # OBJECT OPERATIONS - Delegated to ObjectsStorage
    # ============================================================================
    
    async def create_object(self, obj: Object) -> bool:
        """
        Create a TAMS object - delegated to ObjectsStorage
        
        Args:
            obj: Object model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.objects_storage.create_object(obj)
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """
        Get a TAMS object by ID - delegated to ObjectsStorage
        
        Args:
            object_id: ID of the object to get
            
        Returns:
            Object: Object model instance or None if not found
        """
        return await self.objects_storage.get_object(object_id)
    
    async def delete_object(self, object_id: str) -> bool:
        """
        Delete a TAMS object - delegated to ObjectsStorage
        
        Args:
            object_id: ID of the object to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If object has flow references (TAMS API compliance - objects are immutable)
        """
        try:
            return await self.objects_storage.delete_object(object_id)
        except ValueError as e:
            # Re-raise TAMS compliance errors for proper HTTP handling
            raise e
    
    # ============================================================================
    # ANALYTICS OPERATIONS - Delegated to AnalyticsEngine
    # ============================================================================
    
    async def analytics_query(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """
        Execute analytics query - delegated to AnalyticsEngine
        
        Args:
            query_type: Type of analytics query
            **kwargs: Query parameters
            
        Returns:
            Dict: Analytics query results
        """
        try:
            if query_type == "flow_usage":
                return await self.analytics_engine.flow_usage_analytics(**kwargs)
            elif query_type == "storage_usage":
                return await self.analytics_engine.storage_usage_analytics(**kwargs)
            elif query_type == "time_range":
                return await self.analytics_engine.time_range_analysis(**kwargs)
            elif query_type == "performance":
                return await self.analytics_engine.get_performance_metrics()
            else:
                logger.warning("Unknown analytics query type: %s", query_type)
                return {"error": f"Unknown query type: {query_type}"}
        except Exception as e:
            logger.error("Analytics query failed: %s", e)
            return {"error": str(e)}
    
    # ============================================================================
    # COLLECTION OPERATIONS - Delegated to appropriate modules
    # ============================================================================
    
    async def get_flow_collections(self, flow_id: str) -> List[FlowCollection]:
        """Get flow collections - delegated to FlowsStorage"""
        return await self.flows_storage.get_flow_collections(flow_id)
    
    async def add_flow_to_collection(self, collection_id: str, flow_id: str, 
                                   label: str, description: Optional[str] = None, 
                                   created_by: Optional[str] = None) -> bool:
        """Add flow to collection - delegated to FlowsStorage"""
        return await self.flows_storage.add_flow_to_collection(collection_id, flow_id, label, description, created_by)
    
    async def get_source_collections(self, source_id: str) -> List[SourceCollection]:
        """Get source collections - delegated to SourcesStorage"""
        return await self.sources_storage.get_source_collections(source_id)
    
    async def add_source_to_collection(self, collection_id: str, source_id: str, 
                                     label: str, description: Optional[str] = None, 
                                     created_by: Optional[str] = None) -> bool:
        """Add source to collection - delegated to SourcesStorage"""
        return await self.sources_storage.add_source_to_collection(collection_id, source_id, label, description, created_by)
    
    # ============================================================================
    # OBJECT-FLOW REFERENCE OPERATIONS - Delegated to ObjectsStorage
    # ============================================================================
    
    async def add_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """Add flow object reference - delegated to ObjectsStorage"""
        return await self.objects_storage.add_flow_reference(object_id, flow_id)
    
    async def remove_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """Remove flow object reference - delegated to ObjectsStorage"""
        return await self.objects_storage.remove_flow_reference(object_id, flow_id)
    
    async def get_object_flow_references(self, object_id: str) -> List[str]:
        """Get object flow references - delegated to ObjectsStorage"""
        return await self.objects_storage._get_object_flow_references(object_id)
    
    # ============================================================================
    # LEGACY METHODS FOR BACKWARD COMPATIBILITY
    # ============================================================================

    async def update_source(self, source_id: str, source: Source) -> bool:
        """Update source - delegated to SourcesStorage"""
        return await self.sources_storage.update_source(source_id, {})
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update flow - delegated to FlowsStorage"""
        return await self.flows_storage.update_flow(flow_id, {})
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags - delegated to SourcesStorage"""
        return await self.sources_storage.update_source(source_id, {"tags": tags})
    
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        """Update flow tags - delegated to FlowsStorage"""
        return await self.flows_storage.update_flow(flow_id, {"tags": tags})

    async def check_source_dependencies(self, source_id: str) -> Dict[str, Any]:
        """Check source dependencies - delegated to SourcesStorage"""
        return await self.sources_storage._get_dependent_flows(source_id)
    
    async def check_flow_dependencies(self, flow_id: str) -> Dict[str, Any]:
        """Check flow dependencies - delegated to FlowsStorage"""
        return await self.flows_storage._get_dependent_segments(flow_id)
    
    # ============================================================================
    # UTILITY AND HEALTH CHECK METHODS
    # ============================================================================
    
    async def close(self):
        """Close all connections"""
        try:
            self.vast_db_manager.close()
            logger.info("VASTStore connections closed")
        except Exception as e:
            logger.error("Error closing VASTStore: %s", e)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on VAST storage
            
        Returns:
            Dict: Health check results
        """
        try:
            vast_health = self.vast_db_manager.is_connected()
            return {
                'status': 'healthy' if vast_health else 'unhealthy',
                'vast_connected': vast_health,
                'endpoint': self.endpoint,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'endpoint': self.endpoint,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information
            
        Returns:
            Dict: Storage information
        """
        try:
            return {
                'type': 'vast',
                'endpoint': self.endpoint,
                'bucket': self.bucket,
                'schema': self.schema,
                'vast_connected': self.vast_db_manager.is_connected(),
                'storage_backend_manager': self.storage_backend_manager.get_default_backend()
            }
        except Exception as e:
            return {
                'type': 'vast',
                'error': str(e),
                'endpoint': self.endpoint,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    # ============================================================================
    # MISSING METHODS FOR API ENDPOINTS
    # ============================================================================
    
    async def list_deletion_requests(self) -> List[Dict[str, Any]]:
        """List deletion requests - delegated to appropriate storage"""
        try:
            # This would need to be implemented based on the deletion_requests table
            # For now, return empty list
            logger.info("list_deletion_requests called - returning empty list")
            return []
        except Exception as e:
            logger.error(f"Error listing deletion requests: {e}")
            return []
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List webhooks - delegated to appropriate storage"""
        try:
            # This would need to be implemented based on the webhooks table
            # For now, return empty list
            logger.info("list_webhooks called - returning empty list")
            return []
        except Exception as e:
            logger.error(f"Error listing webhooks: {e}")
            return []
    
    async def create_flow_collection(self, collection_id: str, label: str, description: Optional[str] = None, created_by: Optional[str] = None) -> bool:
        """Create a new flow collection - creates empty collection"""
        try:
            # Create collection metadata without any flows initially
            # Use simple string fields to avoid data type conversion issues
            collection_metadata = {
                'collection_id': str(collection_id),
                'label': str(label),
                'description': str(description or ''),
                'created_by': str(created_by or 'system')
            }
            
            # Store in VAST
            success = self.vast_db_manager.insert_record('flow_collections', collection_metadata)
            
            if success:
                logger.info("Successfully created flow collection %s", collection_id)
            else:
                logger.error("Failed to create flow collection %s", collection_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to create flow collection %s: %s", collection_id, e)
            return False
    
    async def create_source_collection(self, collection_id: str, label: str, description: Optional[str] = None, created_by: Optional[str] = None) -> bool:
        """Create a new source collection - creates empty collection"""
        try:
            # Create collection metadata without any sources initially
            # Use simple string fields to avoid data type conversion issues
            collection_metadata = {
                'collection_id': str(collection_id),
                'label': str(label),
                'description': str(description or ''),
                'created_by': str(created_by or 'system')
            }
            
            # Store in VAST
            success = self.vast_db_manager.insert_record('source_collections', collection_metadata)
            
            if success:
                logger.info("Successfully created source collection %s", collection_id)
            else:
                logger.error("Failed to create source collection %s", collection_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to create source collection %s: %s", collection_id, e)
            return False

