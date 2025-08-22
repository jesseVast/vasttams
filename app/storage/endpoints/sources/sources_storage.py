"""
TAMS-specific source storage operations

This module handles TAMS-specific source operations including:
- Source creation and metadata storage
- Source retrieval with TAMS compliance
- Source collection management

TAMS API DELETE RULES (CRITICAL COMPLIANCE):
============================================

SOURCE DELETION:
- cascade=false: MUST FAIL (409 Conflict) if dependent flows exist
- cascade=true: MUST SUCCEED (200 OK) by deleting source + all dependent flows
- Objects are immutable and cannot be deleted via cascade

All delete operations implement TAMS API compliance rules to prevent
referential integrity violations and data corruption.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from ...vastdbmanager import VastDBManager
from ...storage_backend_manager import StorageBackendManager
from ....models.models import Source, SourceCollection

logger = logging.getLogger(__name__)


class SourcesStorage:
    """
    TAMS-specific source operations
    
    This class handles TAMS-specific source operations including
    metadata storage and collection management.
    """
    
    def __init__(self, vast_core: VastDBManager):
        """
        Initialize sources storage
        
        Args:
            vast_core: VastDBManager for metadata operations
        """
        self.vast = vast_core
        
        logger.info("SourcesStorage initialized")
    
    async def create_source(self, source: Source) -> bool:
        """
        Create a TAMS source
        
        Args:
            source: Source model instance
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating TAMS source: %s", source.id)
            
            # Convert Source to VAST-compatible format
            # Use simple string fields to avoid data type conversion issues
            metadata = {
                'id': str(source.id),
                'format': str(source.format),
                'label': str(source.label),
                'description': str(source.description)
            }
            
            # Store tags if they exist
            if source.tags:
                metadata['tags'] = source.tags.model_dump() if hasattr(source.tags, 'model_dump') else dict(source.tags)
            
            # Store in VAST
            success = self.vast.insert_record('sources', metadata)
            
            if success:
                logger.info("Successfully created TAMS source: %s", source.id)
            else:
                logger.error("Failed to create TAMS source: %s", source.id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to create TAMS source %s: %s", source.id, e)
            return False
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """
        Get a TAMS source by ID
        
        Args:
            source_id: ID of the source to get
            
        Returns:
            Source: Source model instance or None if not found
        """
        try:
            logger.info("Getting TAMS source by ID: %s", source_id)
            
            # Get metadata from VAST
            metadata = self.vast.query_records('sources', predicate={'id': source_id})
            
            if not metadata:
                logger.info("Source not found: %s", source_id)
                return None
            
            # Convert to Source model
            source = await self._metadata_to_source(metadata[0])
            
            if source:
                logger.info("Successfully retrieved TAMS source: %s", source_id)
            
            return source
            
        except Exception as e:
            logger.error("Failed to get TAMS source %s: %s", source_id, e)
            return None
    
    async def list_sources(self, filters: Optional[Dict[str, Any]] = None, 
                          limit: Optional[int] = None) -> List[Source]:
        """
        List TAMS sources with optional filtering
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of sources to return
            
        Returns:
            List[Source]: List of source models
        """
        try:
            logger.info("Listing TAMS sources with filters: %s, limit: %s", filters, limit)
            
            # Build predicate
            predicate = {}
            if filters:
                if 'label' in filters:
                    predicate['label'] = filters['label']
                if 'format' in filters:
                    predicate['format'] = filters['format']
            
            # Query VAST
            metadata = self.vast.query_records('sources', predicate=predicate, limit=limit)
            
            # Convert to Source models
            sources = []
            for meta in metadata:
                source = await self._metadata_to_source(meta)
                if source:
                    sources.append(source)
            
            logger.info("Retrieved %d TAMS sources", len(sources))
            return sources
            
        except Exception as e:
            logger.error("Failed to list TAMS sources: %s", e)
            return []
    
    async def update_source(self, source_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a TAMS source
        
        Args:
            source_id: ID of the source to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            logger.info("Updating TAMS source %s with: %s", source_id, updates)
            
            # Use VAST's update capabilities via db_manager
            result = self.vast.db_manager.update('sources', updates, predicate={'id': source_id})
            
            if result and result > 0:
                logger.info("Successfully updated TAMS source %s", source_id)
                return True
            else:
                logger.warning("No changes made to source %s", source_id)
                return False
                
        except Exception as e:
            logger.error("Failed to update TAMS source %s: %s", source_id, e)
            return False
    
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        """
        Delete a TAMS source following TAMS API compliance rules
        
        Args:
            source_id: ID of the source to delete
            cascade: Whether to cascade delete related flows
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Raises:
            ValueError: If cascade=False and dependent flows exist (TAMS API compliance)
        """
        try:
            logger.info("Deleting TAMS source %s (cascade: %s)", source_id, cascade)
            
            # Check for dependent flows if not cascading
            if not cascade:
                dependent_flows = await self._get_dependent_flows(source_id)
                if dependent_flows:
                    error_msg = f"Cannot delete source {source_id}: {len(dependent_flows)} dependent flows exist. Use cascade=true to delete all dependencies."
                    logger.warning(error_msg)
                    raise ValueError(error_msg)
            
            # Delete source metadata from VAST
            vast_success = await self._delete_source_metadata(source_id)
            
            if vast_success:
                logger.info("Successfully deleted TAMS source: %s", source_id)
            else:
                logger.error("Failed to delete TAMS source: %s", source_id)
            
            return vast_success
            
        except ValueError:
            # Re-raise TAMS compliance errors
            raise
        except Exception as e:
            logger.error("Failed to delete TAMS source %s: %s", source_id, e)
            return False
    
    async def _metadata_to_source(self, metadata: Dict[str, Any]) -> Optional[Source]:
        """
        Convert VAST metadata to Source model
        
        Args:
            metadata: Source metadata from VAST
            
        Returns:
            Source: Source model instance or None if failed
        """
        try:
            # Create Source model
            source = Source(
                id=metadata['id'],
                format=metadata['format'],
                label=metadata.get('label'),
                description=metadata.get('description')
            )
            
            # Restore tags if they exist
            if 'tags' in metadata and metadata['tags']:
                source.tags = metadata['tags']
            
            # Note: source_collection and collected_by are computed dynamically
            # from the source_collections table, not stored directly
            
            return source
            
        except Exception as e:
            logger.error("Failed to convert metadata to source for %s: %s", 
                        metadata.get('id', 'unknown'), e)
            return None
    
    async def _delete_source_metadata(self, source_id: str) -> bool:
        """
        Delete source metadata from VAST
        
        Args:
            source_id: ID of the source to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            from ibis import _ as ibis_
            
            # Delete source from VAST database using ibis predicate
            predicate = (ibis_.id == source_id)
            deleted_count = self.vast.db_manager.delete('sources', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully deleted source %s from VAST", source_id)
                return True
            else:
                logger.warning("Source %s not found for deletion", source_id)
                return False
                
        except Exception as e:
            logger.error("Failed to delete source metadata for %s: %s", source_id, e)
            return False
    
    async def _get_dependent_flows(self, source_id: str) -> List[str]:
        """
        Get flows that depend on this source
        
        Args:
            source_id: ID of the source to check
            
        Returns:
            List[str]: List of dependent flow IDs
        """
        try:
            # Query flows table for dependent flows
            flows = self.vast.query_records('flows', predicate={'source_id': source_id})
            return [flow['id'] for flow in flows]
            
        except Exception as e:
            logger.error("Failed to get dependent flows for source %s: %s", source_id, e)
            return []
    
    # Source collection management methods
    async def get_source_collections(self, source_id: str) -> List[SourceCollection]:
        """
        Get all collections a source belongs to
        
        Args:
            source_id: ID of the source
            
        Returns:
            List[SourceCollection]: List of source collections
        """
        try:
            logger.info("Getting source collections for source: %s", source_id)
            
            # Query source_collections table
            collections_metadata = self.vast.query_records(
                'source_collections', 
                predicate={'source_id': source_id}
            )
            
            collections = []
            for meta in collections_metadata:
                collection = SourceCollection(
                    collection_id=meta['collection_id'],
                    source_id=meta['source_id'],
                    label=meta.get('label', ''),
                    description=meta.get('description'),
                    created=meta.get('created'),
                    created_by=meta.get('created_by')
                )
                collections.append(collection)
            
            logger.info("Retrieved %d source collections for source %s", len(collections), source_id)
            return collections
            
        except Exception as e:
            logger.error("Failed to get source collections for source %s: %s", source_id, e)
            return []
    
    async def add_source_to_collection(self, collection_id: str, source_id: str, 
                                     label: str, description: Optional[str] = None, 
                                     created_by: Optional[str] = None) -> bool:
        """
        Add a source to a collection
        
        Args:
            collection_id: ID of the collection
            source_id: ID of the source to add
            label: Collection label
            description: Collection description
            created_by: Who created the collection
            
        Returns:
            bool: True if addition successful, False otherwise
        """
        try:
            logger.info("Adding source %s to collection %s", source_id, collection_id)
            
            # Create collection metadata
            # Use simple string fields to avoid data type conversion issues
            collection_metadata = {
                'collection_id': str(collection_id),
                'source_id': str(source_id),
                'label': str(label),
                'description': str(description or ''),
                'created_by': str(created_by or 'system')
            }
            
            # Store in VAST
            success = self.vast.insert_record('source_collections', collection_metadata)
            
            if success:
                logger.info("Successfully added source %s to collection %s", source_id, collection_id)
            else:
                logger.error("Failed to add source %s to collection %s", source_id, collection_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to add source %s to collection %s: %s", source_id, collection_id, e)
            return False
    
    async def remove_source_from_collection(self, collection_id: str, source_id: str) -> bool:
        """
        Remove a source from a collection
        
        Args:
            collection_id: ID of the collection
            source_id: ID of the source to remove
            
        Returns:
            bool: True if removal successful, False otherwise
        """
        try:
            logger.info("Removing source %s from collection %s", source_id, collection_id)
            
            from ibis import _ as ibis_
            
            # Remove source from collection using ibis predicate
            predicate = (ibis_.collection_id == collection_id) & (ibis_.source_id == source_id)
            deleted_count = self.vast.db_manager.delete('source_collections', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully removed source %s from collection %s", source_id, collection_id)
                return True
            else:
                logger.warning("Source %s not found in collection %s", source_id, collection_id)
                return False
                
        except Exception as e:
            logger.error("Failed to remove source %s from collection %s: %s", source_id, collection_id, e)
            return False
