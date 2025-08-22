"""
TAMS-specific object storage operations

This module handles TAMS-specific object operations including:
- Object creation and metadata storage
- Object retrieval with TAMS compliance
- Object flow reference management

TAMS API DELETE RULES (CRITICAL COMPLIANCE):
============================================

OBJECT DELETION:
- Objects are IMMUTABLE by TAMS API design
- MUST FAIL (409 Conflict) if they have flow references
- Cannot be deleted via cascade operations
- Flow references must be removed before deletion

All delete operations implement TAMS API compliance rules to prevent
referential integrity violations and data corruption.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from ...vastdbmanager import VastDBManager
from ...storage_backend_manager import StorageBackendManager
from ....models.models import Object

logger = logging.getLogger(__name__)


class ObjectsStorage:
    """
    TAMS-specific object operations
    
    This class handles TAMS-specific object operations including
    metadata storage and flow reference management.
    """
    
    def __init__(self, vast_core: VastDBManager):
        """
        Initialize objects storage
        
        Args:
            vast_core: VastDBManager for metadata operations
        """
        self.vast = vast_core
        
        logger.info("ObjectsStorage initialized")
    
    async def create_object(self, obj: Object) -> bool:
        """
        Create a TAMS object
        
        Args:
            obj: Object model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating TAMS object: %s", obj.id)
            
            # Convert Object to VAST-compatible format
            metadata = {
                'id': str(obj.id),
                'size': obj.size,
                'created': datetime.now(timezone.utc).isoformat()
            }
            
            # Store object metadata in VAST
            success = self.vast.insert_record('objects', metadata)
            
            if not success:
                logger.error("Failed to store object metadata in VAST for object %s", obj.id)
                return False
            
            # Store flow references if provided
            if obj.referenced_by_flows:
                for flow_id in obj.referenced_by_flows:
                    reference_success = await self._add_flow_object_reference(obj.id, flow_id)
                    if not reference_success:
                        logger.warning("Failed to add flow reference for object %s, flow %s", 
                                     obj.id, flow_id)
            
            logger.info("Successfully created TAMS object: %s", obj.id)
            return True
            
        except Exception as e:
            logger.error("Failed to create TAMS object %s: %s", obj.id, e)
            return False
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """
        Get a TAMS object by ID
        
        Args:
            object_id: ID of the object to get
            
        Returns:
            Object: Object model instance or None if not found
        """
        try:
            logger.info("Getting TAMS object by ID: %s", object_id)
            
            # Get object metadata from VAST
            metadata = self.vast.query_records('objects', predicate={'id': object_id})
            
            if not metadata:
                logger.info("Object not found: %s", object_id)
                return None
            
            # Get flow references
            referenced_by_flows = await self._get_object_flow_references(object_id)
            
            # Convert to Object model
            obj = Object(
                id=metadata[0]['id'],
                size=metadata[0].get('size'),
                referenced_by_flows=referenced_by_flows,
                created=metadata[0].get('created')
            )
            
            logger.info("Successfully retrieved TAMS object: %s", object_id)
            return obj
            
        except Exception as e:
            logger.error("Failed to get TAMS object %s: %s", object_id, e)
            return None
    
    async def list_objects(self, filters: Optional[Dict[str, Any]] = None, 
                          limit: Optional[int] = None) -> List[Object]:
        """
        List TAMS objects with optional filtering
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of objects to return
            
        Returns:
            List[Object]: List of object models
        """
        try:
            logger.info("Listing TAMS objects with filters: %s, limit: %s", filters, limit)
            
            # Build predicate
            predicate = {}
            if filters:
                if 'size' in filters:
                    predicate['size'] = filters['size']
            
            # Query VAST
            metadata = self.vast.query_records('objects', predicate=predicate, limit=limit)
            
            # Convert to Object models
            objects = []
            for meta in metadata:
                obj = await self.get_object(meta['id'])
                if obj:
                    objects.append(obj)
            
            logger.info("Retrieved %d TAMS objects", len(objects))
            return objects
            
        except Exception as e:
            logger.error("Failed to list TAMS objects: %s", e)
            return []
    
    async def update_object(self, object_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a TAMS object
        
        Args:
            object_id: ID of the object to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            logger.info("Updating TAMS object %s with: %s", object_id, updates)
            
            # Use VAST's update capabilities via db_manager
            result = self.vast.db_manager.update('objects', updates, predicate={'id': object_id})
            
            if result and result > 0:
                logger.info("Successfully updated TAMS object %s", object_id)
                return True
            else:
                logger.warning("No changes made to object %s", object_id)
                return False
                
        except Exception as e:
            logger.error("Failed to update TAMS object %s: %s", object_id, e)
            return False
    
    async def delete_object(self, object_id: str) -> bool:
        """
        Delete a TAMS object following TAMS API compliance rules
        
        Args:
            object_id: ID of the object to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If object has flow references (TAMS API compliance - objects are immutable)
        """
        try:
            logger.info("Deleting TAMS object: %s", object_id)
            
            # Check for flow references - TAMS API rules: objects are immutable
            referenced_by_flows = await self._get_object_flow_references(object_id)
            if referenced_by_flows:
                error_msg = f"Cannot delete object {object_id}: {len(referenced_by_flows)} flow references exist. Objects are immutable by TAMS API design."
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # Delete object metadata from VAST
            vast_success = await self._delete_object_metadata(object_id)
            
            if vast_success:
                logger.info("Successfully deleted TAMS object: %s", object_id)
            else:
                logger.error("Failed to delete TAMS object: %s", object_id)
            
            return vast_success
            
        except ValueError:
            # Re-raise TAMS compliance errors
            raise
        except Exception as e:
            logger.error("Failed to delete TAMS object %s: %s", object_id, e)
            return False
    
    async def _add_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Add a flow reference to an object
        
        Args:
            object_id: ID of the object
            flow_id: ID of the flow that references this object
            
        Returns:
            bool: True if addition successful, False otherwise
        """
        try:
            # Create flow object reference metadata
            reference_metadata = {
                'object_id': object_id,
                'flow_id': flow_id,
                'created': datetime.now(timezone.utc).isoformat()
            }
            
            # Store in VAST
            success = self.vast.insert_record('flow_object_references', reference_metadata)
            
            if success:
                logger.debug("Added flow reference for object %s, flow %s", object_id, flow_id)
            else:
                logger.error("Failed to add flow reference for object %s, flow %s", object_id, flow_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to add flow reference for object %s, flow %s: %s", 
                        object_id, flow_id, e)
            return False
    
    async def _get_object_flow_references(self, object_id: str) -> List[str]:
        """
        Get flow references for an object
        
        Args:
            object_id: ID of the object
            
        Returns:
            List[str]: List of flow IDs that reference this object
        """
        try:
            # Query flow_object_references table
            references = self.vast.query_records(
                'flow_object_references', 
                predicate={'object_id': object_id}
            )
            
            flow_ids = [ref['flow_id'] for ref in references]
            logger.debug("Retrieved %d flow references for object %s", len(flow_ids), object_id)
            return flow_ids
            
        except Exception as e:
            logger.error("Failed to get flow references for object %s: %s", object_id, e)
            return []
    
    async def _delete_object_metadata(self, object_id: str) -> bool:
        """
        Delete object metadata from VAST
        
        Args:
            object_id: ID of the object to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            from ibis import _ as ibis_
            
            # Delete object from VAST database using ibis predicate
            predicate = (ibis_.id == object_id)
            deleted_count = self.vast.db_manager.delete('objects', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully deleted object %s from VAST", object_id)
                return True
            else:
                logger.warning("Object %s not found for deletion", object_id)
                return False
                
        except Exception as e:
            logger.error("Failed to delete object metadata for %s: %s", object_id, e)
            return False
    
    async def add_flow_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Add a flow reference to an object
        
        Args:
            object_id: ID of the object
            flow_id: ID of the flow that references this object
            
        Returns:
            bool: True if addition successful, False otherwise
        """
        return await self._add_flow_object_reference(object_id, flow_id)
    
    async def remove_flow_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Remove a flow reference from an object
        
        Args:
            object_id: ID of the object
            flow_id: ID of the flow reference to remove
            
        Returns:
            bool: True if removal successful, False otherwise
        """
        try:
            logger.info("Removing flow reference for object %s, flow %s", object_id, flow_id)
            
            from ibis import _ as ibis_
            
            # Remove flow reference using ibis predicate
            predicate = (ibis_.object_id == object_id) & (ibis_.flow_id == flow_id)
            deleted_count = self.vast.db_manager.delete('flow_object_references', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully removed flow reference for object %s, flow %s", object_id, flow_id)
                return True
            else:
                logger.warning("Flow reference not found for object %s, flow %s", object_id, flow_id)
                return False
                
        except Exception as e:
            logger.error("Failed to remove flow reference for object %s, flow %s: %s", 
                        object_id, flow_id, e)
            return False
    
    async def get_objects_by_flow(self, flow_id: str) -> List[Object]:
        """
        Get all objects referenced by a specific flow
        
        Args:
            flow_id: ID of the flow
            
        Returns:
            List[Object]: List of objects referenced by the flow
        """
        try:
            logger.info("Getting objects referenced by flow: %s", flow_id)
            
            # Query flow_object_references table
            references = self.vast.query_records(
                'flow_object_references', 
                predicate={'flow_id': flow_id}
            )
            
            # Get objects
            objects = []
            for ref in references:
                obj = await self.get_object(ref['object_id'])
                if obj:
                    objects.append(obj)
            
            logger.info("Retrieved %d objects referenced by flow %s", len(objects), flow_id)
            return objects
            
        except Exception as e:
            logger.error("Failed to get objects referenced by flow %s: %s", flow_id, e)
            return []
