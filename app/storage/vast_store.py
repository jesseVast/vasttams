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
import uuid
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
from .endpoints.tags.tags_storage import TagsStorage
from .schemas import tables_config, get_desired_table_projections

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
        self.tags_storage = TagsStorage(self.vast_db_manager)  # NEW: Tags storage module
        
        # Create TAMS tables if they don't exist
        self._setup_tams_tables()
        
        logger.info("VASTStore orchestrator initialized - Endpoint: %s, Bucket: %s, Schema: %s", 
                   self.endpoint, self.bucket, self.schema)
    
    def _setup_tams_tables(self):
        """Setup TAMS tables with their schemas"""
        try:
            settings = get_settings()
            
            # Define desired projections per table. Only columns present in the schema will be used.
            desired_table_projections = get_desired_table_projections()
            
            def _projection_name(table: str, cols: tuple) -> str:
                return f"{table}_{'_'.join(cols)}_proj"
            
            for table_name, schema in tables_config.items():
                try:
                    projections_arg = None
                    
                    if settings.enable_table_projections:
                        # Filter projection columns to only those present in the schema
                        schema_columns = {field.name for field in schema}
                        desired_specs = desired_table_projections.get(table_name, [])
                        projections_map = {}
                        for cols in desired_specs:
                            filtered_cols = [c for c in cols if c in schema_columns]
                            if not filtered_cols:
                                continue
                            proj_name = _projection_name(table_name, tuple(filtered_cols))
                            projections_map[proj_name] = filtered_cols
                        if projections_map:
                            projections_arg = projections_map
                    
                    # Create table with projections (if any)
                    self.vast_db_manager.create_table(table_name, schema, projections=projections_arg)
                    if projections_arg:
                        logger.info("Table '%s' setup complete with projections: %s", table_name, list(projections_arg.keys()))
                    else:
                        logger.info("Table '%s' setup complete", table_name)
                except Exception as e:
                    logger.error("Failed to setup table '%s': %s", table_name, e)
                    raise
                    
            logger.info("TAMS tables setup completed successfully")
        except Exception as e:
            logger.error("Failed to setup TAMS tables: %s", e)
            raise
    
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
        Get a TAMS source - delegated to SourcesStorage
        
        Args:
            source_id: Source identifier
            
        Returns:
            Source model instance or None if not found
        """
        return await self.sources_storage.get_source(source_id)
    
    async def update_source(self, source_id: str, source: Source) -> bool:
        """
        Update a TAMS source - delegated to SourcesStorage
        
        Args:
            source_id: Source identifier
            source: Updated source model instance
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return await self.sources_storage.update_source(source_id, source)
    
    async def delete_source(self, source_id: str, cascade: bool = False) -> bool:
        """
        Delete a TAMS source - delegated to SourcesStorage
        
        Args:
            source_id: Source identifier
            cascade: Whether to cascade delete dependent flows
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.sources_storage.delete_source(source_id, cascade)
    
    async def list_sources(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Source]:
        """
        List TAMS sources - delegated to SourcesStorage
        
        Args:
            filters: Optional filters to apply
            limit: Optional limit on number of results
            
        Returns:
            List of Source model instances
        """
        return await self.sources_storage.list_sources(filters, limit)
    
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
        Get a TAMS flow - delegated to FlowsStorage
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            Flow model instance or None if not found
        """
        return await self.flows_storage.get_flow(flow_id)
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """
        Update a TAMS flow - delegated to FlowsStorage
        
        Args:
            flow_id: Flow identifier
            flow: Updated flow model instance
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return await self.flows_storage.update_flow(flow_id, flow)
    
    async def delete_flow(self, flow_id: str, cascade: bool = False) -> bool:
        """
        Delete a TAMS flow - delegated to FlowsStorage
        
        Args:
            flow_id: Flow identifier
            cascade: Whether to cascade delete dependent segments
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.flows_storage.delete_flow(flow_id, cascade)
    
    async def list_flows(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Flow]:
        """
        List TAMS flows - delegated to FlowsStorage
        
        Args:
            filters: Optional filters to apply
            limit: Optional limit on number of results
            
        Returns:
            List of Flow model instances
        """
        return await self.flows_storage.list_flows(filters, limit)
    
    # ============================================================================
    # SEGMENT OPERATIONS - Delegated to SegmentsStorage
    # ============================================================================
    
    async def create_flow_segment(self, segment: FlowSegment, flow_id: str, 
                                 media_data: Union[bytes, str, Any]) -> bool:
        """
        Create a TAMS flow segment - delegated to SegmentsStorage
        
        Args:
            segment: FlowSegment model instance
            flow_id: Flow identifier
            media_data: Media data to store
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.segments_storage.create_flow_segment(segment, flow_id, media_data)
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """
        Get TAMS flow segments - delegated to SegmentsStorage
        
        Args:
            flow_id: Flow identifier
            timerange: Optional time range filter
            
        Returns:
            List of FlowSegment model instances
        """
        return await self.segments_storage.get_flow_segments(flow_id, timerange)
    
    async def delete_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """
        Delete TAMS flow segments - delegated to SegmentsStorage
        
        Args:
            flow_id: Flow identifier
            timerange: Optional time range filter
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.segments_storage.delete_segments(flow_id, timerange)
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """
        Delete TAMS flow segments - delegated to SegmentsStorage (alias for delete_segments)
        
        Args:
            flow_id: ID of the flow to delete segments for
            timerange: Optional timerange filter
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.segments_storage.delete_segments(flow_id, timerange)
    
    # ============================================================================
    # FLOW-OBJECT REFERENCE MANAGEMENT
    # ============================================================================
    
    async def add_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Add a flow-object reference for TAMS compliance
        
        Args:
            object_id: Object identifier
            flow_id: Flow identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        return await self.objects_storage._add_flow_object_reference(object_id, flow_id)
    
    async def remove_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Remove a flow-object reference for TAMS compliance
        
        Args:
            object_id: Object identifier
            flow_id: Flow identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        return await self.segments_storage.remove_flow_object_reference(object_id, flow_id)
    
    async def get_object_flow_references(self, object_id: str) -> List[str]:
        """
        Get flow references for an object
        
        Args:
            object_id: Object identifier
            
        Returns:
            List of flow IDs that reference this object
        """
        return await self.objects_storage._get_object_flow_references(object_id)
    
    async def create_object(self, obj: Object) -> bool:
        """
        Create a TAMS object - delegated to ObjectsStorage
        
        Args:
            obj: Object model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        return await self.objects_storage.create_object(obj)
    
    async def delete_object(self, object_id: str) -> bool:
        """
        Delete a TAMS object following TAMS API compliance rules
        
        Args:
            object_id: Object identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If object has flow references (TAMS API compliance - objects are immutable)
        """
        return await self.objects_storage.delete_object(object_id)
    
    # ============================================================================
    # WEBHOOK OPERATIONS - For event notifications
    # ============================================================================
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all webhooks
        
        Returns:
            List of webhook dictionaries
        """
        try:
            logger.info("Listing webhooks from VAST database")
            
            # Query webhooks table
            webhooks_data = self.vast_db_manager.query_records('webhooks')
            
            # Fix data format: parse JSON strings to proper types
            for webhook in webhooks_data:
                # Parse events from JSON string to list
                if 'events' in webhook and isinstance(webhook['events'], str):
                    try:
                        import json
                        webhook['events'] = json.loads(webhook['events'])
                    except json.JSONDecodeError:
                        webhook['events'] = []
                
                # Parse other JSON string fields
                json_fields = ['flow_ids', 'source_ids', 'flow_collected_by_ids', 'source_collected_by_ids', 
                             'accept_get_urls', 'accept_storage_ids']
                for field in json_fields:
                    if field in webhook and isinstance(webhook[field], str):
                        try:
                            webhook[field] = json.loads(webhook[field])
                        except json.JSONDecodeError:
                            webhook[field] = []
            
            logger.info("Retrieved %d webhooks from VAST", len(webhooks_data))
            return webhooks_data
            
        except Exception as e:
            logger.error("Failed to list webhooks: %s", e)
            return []
    
    async def create_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Create a new webhook
        
        Args:
            webhook_data: Webhook data dictionary
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating webhook in VAST database")
            
            # Add timestamps and ID
            webhook_data['id'] = str(uuid.uuid4())
            webhook_data['created'] = datetime.now(timezone.utc)
            webhook_data['updated'] = datetime.now(timezone.utc)
            
            # Convert to columnar format for VAST
            webhook_columnar = {k: [v] for k, v in webhook_data.items()}
            
            success = self.vast_db_manager.insert('webhooks', webhook_columnar)
            
            if success:
                logger.info("Successfully created webhook: %s", webhook_data['id'])
            else:
                logger.error("Failed to create webhook")
                
            return bool(success)
            
        except Exception as e:
            logger.error("Failed to create webhook: %s", e)
            return False
    
    # ============================================================================
    # DELETION REQUEST OPERATIONS - For async flow deletion
    # ============================================================================
    
    async def list_deletion_requests(self) -> List[Dict[str, Any]]:
        """
        List all deletion requests
        
        Returns:
            List of deletion request dictionaries
        """
        try:
            logger.info("Listing deletion requests from VAST database")
            
            # Query deletion_requests table
            requests_data = self.vast_db_manager.query_records('deletion_requests')
            
            logger.info("Retrieved %d deletion requests from VAST", len(requests_data))
            return requests_data
            
        except Exception as e:
            logger.error("Failed to list deletion requests: %s", e)
            return []
    
    async def get_deletion_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific deletion request by ID
        
        Args:
            request_id: Deletion request identifier
            
        Returns:
            Deletion request dictionary or None if not found
        """
        try:
            logger.info("Getting deletion request: %s", request_id)
            
            # Query deletion_requests table with predicate
            requests_data = self.vast_db_manager.query_records(
                'deletion_requests', 
                predicate={'id': request_id}
            )
            
            if requests_data:
                logger.info("Found deletion request: %s", request_id)
                return requests_data[0]
            else:
                logger.info("Deletion request not found: %s", request_id)
                return None
                
        except Exception as e:
            logger.error("Failed to get deletion request %s: %s", request_id, e)
            return None
    
    async def create_deletion_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Create a new deletion request
        
        Args:
            request_data: Deletion request data dictionary
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating deletion request in VAST database")
            
            # Add ID if not present
            if 'id' not in request_data:
                request_data['id'] = str(uuid.uuid4())
            
            # Convert to columnar format for VAST
            request_columnar = {k: [v] for k, v in request_data.items()}
            
            success = self.vast_db_manager.insert('deletion_requests', request_columnar)
            
            if success:
                logger.info("Successfully created deletion request: %s", request_data['id'])
            else:
                logger.error("Failed to create deletion request")
                
            return bool(success)
            
        except Exception as e:
            logger.error("Failed to create deletion request: %s", e)
            return False
    
    # ============================================================================
    # OBJECT OPERATIONS - Delegated to ObjectsStorage
    # ============================================================================
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """
        Get a TAMS object - delegated to ObjectsStorage
        
        Args:
            object_id: Object identifier
            
        Returns:
            Object model instance or None if not found
        """
        return await self.objects_storage.get_object(object_id)
    
    async def list_objects(self, filters: Optional[Dict[str, Any]] = None) -> List[Object]:
        """
        List TAMS objects - delegated to ObjectsStorage
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of Object model instances
        """
        return await self.objects_storage.list_objects(filters)
    
    # ============================================================================
    # ANALYTICS OPERATIONS - Delegated to AnalyticsEngine
    # ============================================================================
    
    async def get_analytics(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get analytics data - delegated to AnalyticsEngine
        
        Args:
            query_params: Analytics query parameters
            
        Returns:
            Analytics results
        """
        return await self.analytics_engine.get_analytics(query_params)
    
    # ============================================================================
    # TAGS OPERATIONS - NEW: Delegated to TagsStorage
    # ============================================================================
    
    async def get_source_tags(self, source_id: str) -> Optional[Tags]:
        """
        Get tags for a source - delegated to TagsStorage
        
        Args:
            source_id: Source identifier
            
        Returns:
            Tags object or None if no tags found
        """
        return await self.tags_storage.get_tags('source', source_id)
    
    async def get_source_tag(self, source_id: str, tag_name: str) -> Optional[str]:
        """
        Get a specific tag for a source - delegated to TagsStorage
        
        Args:
            source_id: Source identifier
            tag_name: Tag name
            
        Returns:
            Tag value or None if not found
        """
        return await self.tags_storage.get_tag('source', source_id, tag_name)
    
    async def update_source_tag(self, source_id: str, tag_name: str, tag_value: str, 
                              updated_by: Optional[str] = None) -> bool:
        """
        Update a specific tag for a source - delegated to TagsStorage
        
        Args:
            source_id: Source identifier
            tag_name: Tag name
            tag_value: Tag value
            updated_by: User who updated the tag
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return await self.tags_storage.update_tag('source', source_id, tag_name, tag_value, updated_by)
    
    async def update_source_tags(self, source_id: str, tags: Tags, 
                               updated_by: Optional[str] = None) -> bool:
        """
        Update all tags for a source - delegated to TagsStorage
        
        Args:
            source_id: Source identifier
            tags: Tags object containing all tags to set
            updated_by: User who updated the tags
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return await self.tags_storage.update_tags('source', source_id, tags, updated_by)
    
    async def delete_source_tag(self, source_id: str, tag_name: str) -> bool:
        """
        Delete a specific tag for a source - delegated to TagsStorage
        
        Args:
            source_id: Source identifier
            tag_name: Tag name
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.tags_storage.delete_tag('source', source_id, tag_name)
    
    async def delete_source_tags(self, source_id: str) -> bool:
        """
        Delete all tags for a source - delegated to TagsStorage
        
        Args:
            source_id: Source identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.tags_storage.delete_all_tags('source', source_id)
    
    async def get_flow_tags(self, flow_id: str) -> Optional[Tags]:
        """
        Get tags for a flow - delegated to TagsStorage
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            Tags object or None if no tags found
        """
        return await self.tags_storage.get_tags('flow', flow_id)
    
    async def get_flow_tag(self, flow_id: str, tag_name: str) -> Optional[str]:
        """
        Get a specific tag for a flow - delegated to TagsStorage
        
        Args:
            flow_id: Flow identifier
            tag_name: Tag name
            
        Returns:
            Tag value or None if not found
        """
        return await self.tags_storage.get_tag('flow', flow_id, tag_name)
    
    async def update_flow_tag(self, flow_id: str, tag_name: str, tag_value: str, 
                             updated_by: Optional[str] = None) -> bool:
        """
        Update a specific tag for a flow - delegated to TagsStorage
        
        Args:
            flow_id: Flow identifier
            tag_name: Tag name
            tag_value: Tag value
            updated_by: User who updated the tag
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return await self.tags_storage.update_tag('flow', flow_id, tag_name, tag_value, updated_by)
    
    async def update_flow_tags(self, flow_id: str, tags: Tags, 
                              updated_by: Optional[str] = None) -> bool:
        """
        Update all tags for a flow - delegated to TagsStorage
        
        Args:
            flow_id: Flow identifier
            tags: Tags object containing all tags to set
            updated_by: User who updated the tags
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return await self.tags_storage.update_tags('flow', flow_id, tags, updated_by)
    
    async def delete_flow_tag(self, flow_id: str, tag_name: str) -> bool:
        """
        Delete a specific tag for a flow - delegated to TagsStorage
        
        Args:
            flow_id: Flow identifier
            tag_name: Tag name
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.tags_storage.delete_tag('flow', flow_id, tag_name)
    
    async def delete_flow_tags(self, flow_id: str) -> bool:
        """
        Delete all tags for a flow - delegated to TagsStorage
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return await self.tags_storage.delete_all_tags('flow', flow_id)
    
    # ============================================================================
    # FLOW COLLECTION OPERATIONS
    # ============================================================================
    
    async def get_flow_collections(self, flow_id: str) -> List[FlowCollection]:
        """
        Get flow collections for a specific flow
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            List of FlowCollection instances
        """
        try:
            # Query the flow_collections table for this flow
            predicate = {'flow_id': flow_id}
            collections_data = self.vast_db_manager.select('flow_collections', predicate=predicate, output_by_row=True)
            
            if not collections_data:
                return []
            
            # Convert to FlowCollection models
            collections = []
            for data in collections_data:
                try:
                    collection = FlowCollection(**data)
                    collections.append(collection)
                except Exception as e:
                    logger.warning("Failed to parse flow collection data: %s", e)
                    continue
            
            return collections
            
        except Exception as e:
            logger.error("Failed to get flow collections for flow %s: %s", flow_id, e)
            return []
    
    async def add_flow_to_collection(self, collection_id: str, flow_id: str, 
                                   label: str = "Default Label", 
                                   description: str = "Auto-generated collection") -> bool:
        """
        Add a flow to a collection
        
        Args:
            collection_id: Collection identifier
            flow_id: Flow identifier
            label: Collection label
            description: Collection description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create collection record
            collection_data = {
                'id': str(uuid.uuid4()),
                'collection_id': collection_id,
                'flow_id': flow_id,
                'label': label,
                'description': description,
                'created': datetime.now(timezone.utc),
                'updated': datetime.now(timezone.utc)
            }
            
            # Insert into flow_collections table
            success = self.vast_db_manager.insert_record('flow_collections', collection_data)
            if success:
                logger.info("Successfully added flow %s to collection %s", flow_id, collection_id)
                return True
            else:
                logger.error("Failed to add flow %s to collection %s", flow_id, collection_id)
                return False
                
        except Exception as e:
            logger.error("Failed to add flow %s to collection %s: %s", flow_id, collection_id, e)
            return False
    
    async def remove_flow_from_collection(self, flow_id: str) -> bool:
        """
        Remove a flow from its collection
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete from flow_collections table
            predicate = {'flow_id': flow_id}
            success = self.vast_db_manager.delete('flow_collections', predicate)
            
            if success >= 0:  # 0 or positive means success
                logger.info("Successfully removed flow %s from collection", flow_id)
                return True
            else:
                logger.error("Failed to remove flow %s from collection", flow_id)
                return False
                
        except Exception as e:
            logger.error("Failed to remove flow %s from collection: %s", flow_id, e)
            return False
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    async def close(self):
        """Close the VAST store and cleanup resources"""
        try:
            # Close any open connections or resources
            if hasattr(self.vast_db_manager, 'close'):
                await self.vast_db_manager.close()
            logger.info("VASTStore closed successfully")
        except Exception as e:
            logger.error("Error closing VASTStore: %s", e)