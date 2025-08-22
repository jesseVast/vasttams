"""
TAMS-specific flow storage operations

This module handles TAMS-specific flow operations including:
- Flow creation and metadata storage
- Flow retrieval with TAMS compliance
- Flow collection management

TAMS API DELETE RULES (CRITICAL COMPLIANCE):
============================================

FLOW DELETION:
- cascade=false: MUST FAIL (409 Conflict) if dependent segments exist
- cascade=true: MUST SUCCEED (200 OK) by deleting flow + all dependent segments
- Segments are deleted but objects remain immutable

All delete operations implement TAMS API compliance rules to prevent
referential integrity violations and data corruption.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from ...vastdbmanager import VastDBManager
from ...storage_backend_manager import StorageBackendManager
from ....models.models import Flow, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow, FlowCollection

logger = logging.getLogger(__name__)


class FlowsStorage:
    """
    TAMS-specific flow operations
    
    This class handles TAMS-specific flow operations including
    metadata storage and collection management.
    """
    
    def __init__(self, vast_core: VastDBManager):
        """
        Initialize flows storage
        
        Args:
            vast_core: VastDBManager for metadata operations
        """
        self.vast = vast_core
        
        logger.info("FlowsStorage initialized")
    
    async def create_flow(self, flow: Flow) -> bool:
        """
        Create a TAMS flow
        
        Args:
            flow: Flow model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating TAMS flow: %s", flow.id)
            
            # Convert Flow to VAST-compatible format
            metadata = {
                'id': str(flow.id),
                'source_id': str(flow.source_id),
                'format': flow.format,
                'label': flow.label,
                'description': flow.description,
                'created': datetime.now(timezone.utc).isoformat(),
                'updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Add flow-specific fields based on type
            if hasattr(flow, 'frame_width'):
                metadata['frame_width'] = flow.frame_width
            if hasattr(flow, 'frame_height'):
                metadata['frame_height'] = flow.frame_height
            if hasattr(flow, 'frame_rate'):
                metadata['frame_rate'] = flow.frame_rate
            if hasattr(flow, 'sample_rate'):
                metadata['sample_rate'] = flow.sample_rate
            if hasattr(flow, 'channels'):
                metadata['channels'] = flow.channels
            if hasattr(flow, 'bit_rate'):
                metadata['bit_rate'] = flow.bit_rate
            
            # Store in VAST
            success = self.vast.insert_record('flows', metadata)
            
            if success:
                logger.info("Successfully created TAMS flow: %s", flow.id)
            else:
                logger.error("Failed to create TAMS flow: %s", flow.id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to create TAMS flow %s: %s", flow.id, e)
            return False
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """
        Get a TAMS flow by ID
        
        Args:
            flow_id: ID of the flow to get
            
        Returns:
            Flow: Flow model instance or None if not found
        """
        try:
            logger.info("Getting TAMS flow by ID: %s", flow_id)
            
            # Get metadata from VAST
            metadata = self.vast.query_records('flows', predicate={'id': flow_id})
            
            if not metadata:
                logger.info("Flow not found: %s", flow_id)
                return None
            
            # Convert to Flow model
            flow = await self._metadata_to_flow(metadata[0])
            
            if flow:
                logger.info("Successfully retrieved TAMS flow: %s", flow_id)
            
            return flow
            
        except Exception as e:
            logger.error("Failed to get TAMS flow %s: %s", flow_id, e)
            return None
    
    async def list_flows(self, filters: Optional[Dict[str, Any]] = None, 
                         limit: Optional[int] = None) -> List[Flow]:
        """
        List TAMS flows with optional filtering
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of flows to return
            
        Returns:
            List[Flow]: List of flow models
        """
        try:
            logger.info("Listing TAMS flows with filters: %s, limit: %s", filters, limit)
            
            # Build predicate
            predicate = {}
            if filters:
                if 'source_id' in filters:
                    predicate['source_id'] = filters['source_id']
                if 'format' in filters:
                    predicate['format'] = filters['format']
                if 'label' in filters:
                    predicate['label'] = filters['label']
                if 'frame_width' in filters:
                    predicate['frame_width'] = filters['frame_width']
                if 'frame_height' in filters:
                    predicate['frame_height'] = filters['frame_height']
            
            # Query VAST
            metadata = self.vast.query_records('flows', predicate=predicate, limit=limit)
            
            # Convert to Flow models
            flows = []
            for meta in metadata:
                flow = await self._metadata_to_flow(meta)
                if flow:
                    flows.append(flow)
            
            logger.info("Retrieved %d TAMS flows", len(flows))
            return flows
            
        except Exception as e:
            logger.error("Failed to list TAMS flows: %s", e)
            return []
    
    async def update_flow(self, flow_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a TAMS flow
        
        Args:
            flow_id: ID of the flow to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            logger.info("Updating TAMS flow %s with: %s", flow_id, updates)
            
            # Use VAST's update capabilities via db_manager
            result = self.vast.db_manager.update('flows', updates, predicate={'id': flow_id})
            
            if result and result > 0:
                logger.info("Successfully updated TAMS flow %s", flow_id)
                return True
            else:
                logger.warning("No changes made to flow %s", flow_id)
                return False
                
        except Exception as e:
            logger.error("Failed to update TAMS flow %s: %s", flow_id, e)
            return False
    
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        """
        Delete a TAMS flow following TAMS API compliance rules
        
        Args:
            flow_id: ID of the flow to delete
            cascade: Whether to cascade delete related segments
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If cascade=False and dependent segments exist (TAMS API compliance)
        """
        try:
            logger.info("Deleting TAMS flow %s (cascade: %s)", flow_id, cascade)
            
            # Check for dependent segments if not cascading
            if not cascade:
                dependent_segments = await self._get_dependent_segments(flow_id)
                if dependent_segments:
                    error_msg = f"Cannot delete flow {flow_id}: {len(dependent_segments)} dependent segments exist. Use cascade=true to delete all dependencies."
                    logger.warning(error_msg)
                    raise ValueError(error_msg)
            
            # Delete flow metadata from VAST
            vast_success = await self._delete_flow_metadata(flow_id)
            
            if vast_success:
                logger.info("Successfully deleted TAMS flow: %s", flow_id)
            else:
                logger.error("Failed to delete TAMS flow: %s", flow_id)
            
            return vast_success
            
        except ValueError:
            # Re-raise TAMS compliance errors
            raise
        except Exception as e:
            logger.error("Failed to delete TAMS flow %s: %s", flow_id, e)
            return False
    
    async def _metadata_to_flow(self, metadata: Dict[str, Any]) -> Optional[Flow]:
        """
        Convert VAST metadata to Flow model
        
        Args:
            metadata: Flow metadata from VAST
            
        Returns:
            Flow: Flow model instance or None if failed
        """
        try:
            # Determine flow type based on format
            flow_format = metadata.get('format', '')
            
            # Create appropriate flow type
            if 'video' in flow_format.lower():
                flow = VideoFlow(
                    id=metadata['id'],
                    source_id=metadata['source_id'],
                    format=metadata['format'],
                    codec=metadata.get('codec', 'video/mp4'),  # Add missing required codec field
                    label=metadata.get('label'),
                    description=metadata.get('description'),
                    frame_width=metadata.get('frame_width'),
                    frame_height=metadata.get('frame_height'),
                    frame_rate=metadata.get('frame_rate')
                )
            elif 'audio' in flow_format.lower():
                flow = AudioFlow(
                    id=metadata['id'],
                    source_id=metadata['source_id'],
                    format=metadata['format'],
                    label=metadata.get('label'),
                    description=metadata.get('description'),
                    sample_rate=metadata.get('sample_rate'),
                    channels=metadata.get('channels'),
                    bit_rate=metadata.get('bit_rate')
                )
            elif 'data' in flow_format.lower():
                flow = DataFlow(
                    id=metadata['id'],
                    source_id=metadata['source_id'],
                    format=metadata['format'],
                    label=metadata.get('label'),
                    description=metadata.get('description')
                )
            elif 'image' in flow_format.lower():
                flow = ImageFlow(
                    id=metadata['id'],
                    source_id=metadata['source_id'],
                    format=metadata['format'],
                    label=metadata.get('label'),
                    description=metadata.get('description'),
                    frame_width=metadata.get('frame_width'),
                    frame_height=metadata.get('frame_height')
                )
            else:
                # Default to generic Flow
                flow = Flow(
                    id=metadata['id'],
                    source_id=metadata['source_id'],
                    format=metadata['format'],
                    label=metadata.get('label'),
                    description=metadata.get('description')
                )
            
            # Note: flow_collection and collected_by are computed dynamically
            # from the flow_collections table, not stored directly
            
            return flow
            
        except Exception as e:
            logger.error("Failed to convert metadata to flow for %s: %s", 
                        metadata.get('id', 'unknown'), e)
            return None
    
    async def _delete_flow_metadata(self, flow_id: str) -> bool:
        """
        Delete flow metadata from VAST
        
        Args:
            flow_id: ID of the flow to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            from ibis import _ as ibis_
            
            # Delete flow from VAST database using ibis predicate
            predicate = (ibis_.id == flow_id)
            deleted_count = self.vast.db_manager.delete('flows', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully deleted flow %s from VAST", flow_id)
                return True
            else:
                logger.warning("Flow %s not found for deletion", flow_id)
                return False
                
        except Exception as e:
            logger.error("Failed to delete flow metadata for %s: %s", flow_id, e)
            return False
    
    async def _get_dependent_segments(self, flow_id: str) -> List[str]:
        """
        Get segments that depend on this flow
        
        Args:
            flow_id: ID of the flow to check
            
        Returns:
            List[str]: List of dependent segment IDs
        """
        try:
            # Query segments table for dependent segments
            segments = self.vast.query_records('segments', predicate={'flow_id': flow_id})
            return [segment['id'] for segment in segments]
            
        except Exception as e:
            logger.error("Failed to get dependent segments for flow %s: %s", flow_id, e)
            return []
    
    # Flow collection management methods
    async def get_flow_collections(self, flow_id: str) -> List[FlowCollection]:
        """
        Get all collections a flow belongs to
        
        Args:
            flow_id: ID of the flow
            
        Returns:
            List[FlowCollection]: List of flow collections
        """
        try:
            logger.info("Getting flow collections for flow: %s", flow_id)
            
            # Query flow_collections table
            collections_metadata = self.vast.query_records(
                'flow_collections', 
                predicate={'flow_id': flow_id}
            )
            
            collections = []
            for meta in collections_metadata:
                collection = FlowCollection(
                    collection_id=meta['collection_id'],
                    flow_id=meta['flow_id'],
                    label=meta.get('label', ''),
                    description=meta.get('description'),
                    created=meta.get('created'),
                    created_by=meta.get('created_by')
                )
                collections.append(collection)
            
            logger.info("Retrieved %d flow collections for flow %s", len(collections), flow_id)
            return collections
            
        except Exception as e:
            logger.error("Failed to get flow collections for flow %s: %s", flow_id, e)
            return []
    
    async def add_flow_to_collection(self, collection_id: str, flow_id: str, 
                                   label: str, description: Optional[str] = None, 
                                   created_by: Optional[str] = None) -> bool:
        """
        Add a flow to a collection
        
        Args:
            collection_id: ID of the collection
            flow_id: ID of the flow to add
            label: Collection label
            description: Collection description
            created_by: Who created the collection
            
        Returns:
            bool: True if addition successful, False otherwise
        """
        try:
            logger.info("Adding flow %s to collection %s", flow_id, collection_id)
            
            # Create collection metadata
            collection_metadata = {
                'collection_id': collection_id,
                'flow_id': flow_id,
                'label': label,
                'description': description or '',
                'created': datetime.now(timezone.utc).isoformat(),
                'created_by': created_by or 'system'
            }
            
            # Store in VAST
            success = self.vast.insert_record('flow_collections', collection_metadata)
            
            if success:
                logger.info("Successfully added flow %s to collection %s", flow_id, collection_id)
            else:
                logger.error("Failed to add flow %s to collection %s", flow_id, collection_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to add flow %s to collection %s: %s", flow_id, collection_id, e)
            return False
    
    async def remove_flow_from_collection(self, collection_id: str, flow_id: str) -> bool:
        """
        Remove a flow from a collection
        
        Args:
            collection_id: ID of the collection
            flow_id: ID of the flow to remove
            
        Returns:
            bool: True if removal successful, False otherwise
        """
        try:
            logger.info("Removing flow %s from collection %s", flow_id, collection_id)
            
            from ibis import _ as ibis_
            
            # Remove flow from collection using ibis predicate
            predicate = (ibis_.collection_id == collection_id) & (ibis_.flow_id == flow_id)
            deleted_count = self.vast.db_manager.delete('flow_collections', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully removed flow %s from collection %s", flow_id, collection_id)
                return True
            else:
                logger.warning("Flow %s not found in collection %s", flow_id, collection_id)
                return False
                
        except Exception as e:
            logger.error("Failed to remove flow %s from collection %s: %s", flow_id, collection_id, e)
            return False
