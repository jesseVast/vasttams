"""
Source Storage Service

This module handles all source-related storage operations including
CRUD operations, filtering, and collection management.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    get_tams_timestamp,
    prepare_data_for_pyarrow,
    prepare_data_for_sql
)
from .models import Source
from ..common.filters import SourceFilters
from ..common.models import Tags, CollectionItem

logger = logging.getLogger(__name__)


class SourceStorageService:
    """Handles source-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_sources(self, filters: SourceFilters) -> List[Source]:
        """Get sources with filtering (TAMS 8.0 with tag filtering)"""
        try:
            # Build query using vaststore
            query = self.vast_db.query("sources").select("*")
            
            # Add standard filters
            if filters.label:
                query = query.where(f"label = '{filters.label}'")
            if filters.format:
                query = query.where(f"format = '{filters.format}'")
            
            # TAMS 8.0: Add tag filters if present
            if filters.tag_filters:
                for tag_name, tag_values in filters.tag_filters.items():
                    # tag_values can be string or list
                    if isinstance(tag_values, list):
                        # "OR" query: tag value matches at least one in the list
                        conditions = []
                        for val in tag_values:
                            conditions.append(f"JSON_CONTAINS(tags, '\"{val}\"', '$.\"{tag_name}\"') OR JSON_CONTAINS(tags, '[\"{val}\"]', '$.\"{tag_name}\"')")
                        tag_filter = " OR ".join(conditions)
                        query = query.where(f"({tag_filter})")
                    else:
                        # Single string value
                        query = query.where(f"(JSON_EXTRACT(tags, '$.\"{tag_name}\"') = '\"{tag_values}\"' OR JSON_CONTAINS(JSON_EXTRACT(tags, '$.\"{tag_name}\"'), '\"{tag_values}\"'))")
            
            # TAMS 8.0: Add tag_exists filters if present
            if filters.tag_exists_filters:
                for tag_name, exists in filters.tag_exists_filters.items():
                    if exists:
                        query = query.where(f"JSON_EXTRACT(tags, '$.\"{tag_name}\"') IS NOT NULL")
                    else:
                        query = query.where(f"JSON_EXTRACT(tags, '$.\"{tag_name}\"') IS NULL")
            
            # Add limit
            if filters.limit:
                query = query.limit(filters.limit)
            
            result = query.execute()
            
            # Convert to Source objects
            sources = []
            # VAST returns a dict with 'data' field containing column arrays
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        source_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                
                                # Handle tags field - parse JSON string if needed
                                if column == 'tags' and value and isinstance(value, str):
                                    try:
                                        import json
                                        value = json.loads(value)
                                    except (json.JSONDecodeError, TypeError):
                                        value = None
                                
                                source_data[column] = value
                        
                        # Compute source_collection from flow collections
                        source_data['source_collection'] = await self._compute_source_collection(source_data.get('id'))
                        sources.append(Source(**source_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        source_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        # Compute source_collection from flow collections
                        source_data['source_collection'] = await self._compute_source_collection(source_data.get('id'))
                        sources.append(Source(**source_data))
            else:
                # Fallback for direct list results
                for row in result:
                    source_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    # Compute source_collection from flow collections
                    source_data['source_collection'] = await self._compute_source_collection(source_data.get('id'))
                    sources.append(Source(**source_data))
            
            return sources
        except Exception as e:
            logger.error("Failed to get sources: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """Get a specific source by ID"""
        try:
            result = self.vast_db.query("sources").select("*").where(f"id = '{source_id}'").execute()
            
            # Handle VAST query result format (same as get_sources)
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    # Get the first (and should be only) row
                    source_data = {}
                    for column, values in data.items():
                        if column != '$row_id':  # Skip internal row IDs
                            value = values[0] if len(values) > 0 else None
                            
                            # Handle tags field - parse JSON string if needed
                            if column == 'tags' and value and isinstance(value, str):
                                try:
                                    import json
                                    value = json.loads(value)
                                except (json.JSONDecodeError, TypeError):
                                    value = None
                            
                            source_data[column] = value
                    
                    # Compute source_collection from flow collections
                    source_data['source_collection'] = await self._compute_source_collection(source_id)
                    return Source(**source_data)
                elif isinstance(data, list):
                    # If data is a list, get first item
                    if not data:
                        return None
                    source_data = dict(data[0]) if hasattr(data[0], '__iter__') and not isinstance(data[0], str) else data[0]
                    # Compute source_collection from flow collections
                    source_data['source_collection'] = await self._compute_source_collection(source_id)
                    return Source(**source_data)
            else:
                # Fallback for direct list results
                if not result or len(result) == 0:
                    return None
                source_data = dict(result[0]) if hasattr(result[0], '__iter__') and not isinstance(result[0], str) else result[0]
                # Compute source_collection from flow collections
                source_data['source_collection'] = await self._compute_source_collection(source_id)
                return Source(**source_data)
            
            return None
        except Exception as e:
            logger.error("Failed to get source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_source(self, source: Source) -> bool:
        """Create a new source"""
        try:
            now = get_tams_timestamp()
            source.created = now
            source.updated = now
            
            source_data = source.model_dump(exclude={'source_collection', 'collected_by'})
            
            # Convert timestamp fields to PyArrow format using centralized function
            from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
            source_data = prepare_data_for_pyarrow(source_data)
            
            self.vast_db.insert_record("sources", source_data)
            return True
        except Exception as e:
            logger.error("Failed to create source: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source(self, source_id: str, source: Source) -> bool:
        """Update an existing source using update-before-upsert approach"""
        try:
            source.updated = get_tams_timestamp()
            
            # Extract tags separately for handling in tags table
            tags_data = None
            if hasattr(source, 'tags') and source.tags is not None:
                tags_data = source.tags
            
            # Only update mutable fields, exclude read-only fields and tags
            source_data = source.model_dump(exclude={'id', 'created', 'created_by', 'source_collection', 'collected_by', 'tags'})
            
            # Convert timestamp fields to SQL format using centralized function
            from ..common.storage.timestamp_utils import prepare_data_for_sql
            source_data = prepare_data_for_sql(source_data)
            
            # Filter out None values to avoid "unknown" type errors
            source_data = {k: v for k, v in source_data.items() if v is not None}
            
            # Try UPDATE first
            try:
                if source_data:
                    # Build SQL update statement directly
                    set_clauses = []
                    for column, value in source_data.items():
                        if column == 'updated' and isinstance(value, str) and value.startswith('CAST('):
                            # Handle timestamp fields that are already CAST expressions
                            set_clauses.append(f"{column} = {value}")
                        else:
                            # Handle regular fields
                            if isinstance(value, str):
                                escaped_value = value.replace("'", "''")
                                set_clauses.append(f"{column} = '{escaped_value}'")
                            elif value is None:
                                set_clauses.append(f"{column} = NULL")
                            else:
                                set_clauses.append(f"{column} = {value}")
                    
                    if set_clauses:
                        sources_table = self.vast_db.get_qualified_table_name("sources")
                        sql = f"UPDATE {sources_table} SET {', '.join(set_clauses)} WHERE id = '{source_id}'"
                        logger.debug("Updating source %s with SQL: %s", source_id, sql)
                        self.vast_db.execute_sql(sql)
                        logger.info("Successfully updated source %s", source_id)
                else:
                    logger.warning("No fields to update for source %s", source_id)
                
                # Handle tags separately using tag service
                if tags_data is not None:
                    await self.tag_service.update_source_tags(source_id, tags_data)
                
                return True
                
            except Exception as update_error:
                logger.warning("UPDATE failed for source %s, trying upsert approach: %s", source_id, update_error)
                
                # If UPDATE fails, try DELETE + INSERT (upsert)
                try:
                    # Delete existing source
                    sources_table = self.vast_db.get_qualified_table_name("sources")
                    delete_sql = f"DELETE FROM {sources_table} WHERE id = '{source_id}'"
                    self.vast_db.execute_sql(delete_sql)
                    logger.info("Deleted existing source %s for upsert", source_id)
                    
                    # Insert new source data
                    source_data['id'] = source_id
                    source_data['created'] = get_tams_timestamp()
                    
                    # Convert timestamp fields to PyArrow format for insertion
                    from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                    source_data = prepare_data_for_pyarrow(source_data)
                    
                    logger.debug("Inserting source %s with data: %s", source_id, source_data)
                    self.vast_db.insert_record("sources", source_data)
                    logger.info("Successfully inserted source %s via upsert", source_id)
                    
                    # Handle tags separately using tag service
                    if tags_data is not None:
                        await self.tag_service.update_source_tags(source_id, tags_data)
                    
                    return True
                    
                except Exception as upsert_error:
                    logger.error("Both UPDATE and upsert failed for source %s: %s", source_id, upsert_error)
                    raise upsert_error
                    
        except Exception as e:
            logger.error("Failed to update source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        """Delete a source with optional cascade to dependent flows"""
        try:
            logger.info("delete_source called with cascade=%s", cascade)
            
            # Check for dependencies if cascade is False
            if not cascade:
                # Check if source has flows
                flows_result = self.vast_db.query("flows").select("id").where(f"source_id = '{source_id}'").execute()
                if flows_result and len(flows_result) > 0:
                    raise ValueError("Cannot delete source with existing flows. Use cascade=True to delete flows first.")
            
            # Cascade delete: Delete dependent flows first (and their segments)
            if cascade:
                logger.info("Calling _cascade_delete_flows for source %s", source_id)
                await self._cascade_delete_flows(source_id)
                logger.info("_cascade_delete_flows completed for source %s", source_id)
            
            # Delete source
            self.vast_db.query("sources").delete().where(f"id = '{source_id}'").execute()
            return True
        except ValueError as e:
            # Re-raise constraint violations
            raise e
        except Exception as e:
            logger.error("Failed to delete source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _cascade_delete_flows(self, source_id: str) -> bool:
        """Delete all flows and their segments for a source (cascade delete)"""
        try:
            # Get all flow IDs for this source
            flows_result = self.vast_db.query("flows").select("id").where(f"source_id = '{source_id}'").execute()
            
            if not flows_result or len(flows_result) == 0:
                return True  # No flows to delete
            
            # Extract flow IDs from result (handle both columnar and row-oriented formats)
            flow_ids = []
            if isinstance(flows_result, dict) and 'data' in flows_result:
                # Trino columnar format: {'data': {'id': [...], ...}}
                data = flows_result['data']
                if isinstance(data, dict) and 'id' in data:
                    flow_ids = data['id'] if isinstance(data['id'], list) else [data['id']]
                elif isinstance(data, list):
                    # Row-oriented format: list of dicts
                    for row in data:
                        if isinstance(row, dict) and 'id' in row:
                            flow_ids.append(row['id'])
            elif isinstance(flows_result, list):
                # Row-oriented format
                for row in flows_result:
                    if isinstance(row, dict) and 'id' in row:
                        flow_ids.append(row['id'])
                    elif isinstance(row, str):
                        flow_ids.append(row)
            
            logger.debug("Found %d flows to delete for source %s", len(flow_ids), source_id)
            
            # Delete segments for each flow
            for flow_id in flow_ids:
                try:
                    self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'").execute()
                    logger.debug("Deleted segments for flow %s", flow_id)
                except Exception as e:
                    logger.warning("Failed to delete segments for flow %s: %s", flow_id, e)
                    # Continue with other flows
            
            # Delete all flows for this source
            if flow_ids:
                self.vast_db.query("flows").delete().where(f"source_id = '{source_id}'").execute()
                logger.info("Deleted %d flows for source %s", len(flow_ids), source_id)
            
            return True
        except Exception as e:
            logger.error("Failed to cascade delete flows for source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _compute_source_collection(self, source_id: str) -> List[CollectionItem]:
        """Compute source_collection from flow collections as per TAMS spec"""
        try:
            if not source_id:
                return []
            
            # Get flows for this source
            flows_result = self.vast_db.query("flows").select("id, flow_collection").where(f"source_id = '{source_id}'").execute()
            
            collection_items = []
            processed_collections = set()
            
            # Handle VAST query result format
            if isinstance(flows_result, dict) and 'data' in flows_result:
                data = flows_result['data']
                if isinstance(data, dict) and 'flow_collection' in data:
                    flow_collections = data['flow_collection']
                    flow_ids = data.get('id', [])
                    
                    for i, flow_collection in enumerate(flow_collections):
                        if flow_collection and isinstance(flow_collection, str):
                            try:
                                import json
                                collection_data = json.loads(flow_collection)
                                if isinstance(collection_data, list):
                                    for item in collection_data:
                                        if isinstance(item, dict) and 'id' in item and 'role' in item:
                                            # Create CollectionItem for each collected flow
                                            collection_item = CollectionItem(
                                                id=item['id'],
                                                role=item['role']
                                            )
                                            # Avoid duplicates
                                            item_key = f"{item['id']}:{item['role']}"
                                            if item_key not in processed_collections:
                                                collection_items.append(collection_item)
                                                processed_collections.add(item_key)
                            except (json.JSONDecodeError, TypeError):
                                continue
                elif isinstance(data, list):
                    for row in data:
                        if hasattr(row, 'get') and row.get('flow_collection'):
                            try:
                                import json
                                collection_data = json.loads(row['flow_collection'])
                                if isinstance(collection_data, list):
                                    for item in collection_data:
                                        if isinstance(item, dict) and 'id' in item and 'role' in item:
                                            collection_item = CollectionItem(
                                                id=item['id'],
                                                role=item['role']
                                            )
                                            item_key = f"{item['id']}:{item['role']}"
                                            if item_key not in processed_collections:
                                                collection_items.append(collection_item)
                                                processed_collections.add(item_key)
                            except (json.JSONDecodeError, TypeError):
                                continue
            else:
                # Fallback for direct list results
                for row in flows_result:
                    if hasattr(row, 'get') and row.get('flow_collection'):
                        try:
                            import json
                            collection_data = json.loads(row['flow_collection'])
                            if isinstance(collection_data, list):
                                for item in collection_data:
                                    if isinstance(item, dict) and 'id' in item and 'role' in item:
                                        collection_item = CollectionItem(
                                            id=item['id'],
                                            role=item['role']
                                        )
                                        item_key = f"{item['id']}:{item['role']}"
                                        if item_key not in processed_collections:
                                            collection_items.append(collection_item)
                                            processed_collections.add(item_key)
                        except (json.JSONDecodeError, TypeError):
                            continue
            
            return collection_items
            
        except Exception as e:
            logger.error("Failed to compute source collection for %s: %s", source_id, e)
            return []
    
