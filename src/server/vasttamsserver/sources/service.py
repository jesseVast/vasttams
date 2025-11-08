"""
Source Storage Service

This module handles all source-related storage operations including
CRUD operations, filtering, and collection management.
"""

import logging
import time
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    get_tams_timestamp,
    prepare_data_for_pyarrow,
    prepare_data_for_sql,
    is_timestamp_field
)
from .models import Source
from ..common.filters import SourceFilters
from ..common.models import Tags, CollectionItem
from ..core.telemetry import telemetry_manager

logger = logging.getLogger(__name__)


class SourceStorageService:
    """Handles source-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_sources(self, filters: SourceFilters) -> List[Source]:
        """Get sources with filtering (TAMS 8.0 with tag filtering)"""
        total_start = time.time()
        query_start = time.time()
        json_parse_start = 0
        json_parse_duration = 0
        
        try:
            # Check if filters are being used
            has_filters = bool(filters.label or filters.format)
            
            # Check if we need tag filtering - if so, use SQL JOIN query
            has_tag_filters = (filters.tag_filters and len(filters.tag_filters) > 0) or \
                            (filters.tag_exists_filters and len(filters.tag_exists_filters) > 0)
            
            if has_tag_filters:
                has_filters = True
            
            if has_tag_filters:
                # Use SQL JOIN query for tag filtering
                sources_table = self.vast_db.get_qualified_table_name("sources")
                tags_table = self.vast_db.get_qualified_table_name("tags")
                
                # Build WHERE conditions for standard filters
                where_conditions = []
                if filters.label:
                    escaped_label = filters.label.replace("'", "''")
                    where_conditions.append(f"s.label = '{escaped_label}'")
                if filters.format:
                    escaped_format = filters.format.replace("'", "''")
                    where_conditions.append(f"s.format = '{escaped_format}'")
                
                # Separate positive (tag exists/value matches) and negative (tag doesn't exist) filters
                positive_tag_conditions = []
                negative_tag_names = []
                
                # Tag value filters (always positive - tag must exist with matching value)
                if filters.tag_filters:
                    for tag_name, tag_values in filters.tag_filters.items():
                        escaped_name = tag_name.replace("'", "''")
                        if isinstance(tag_values, list):
                            # OR query: tag value matches at least one in the list
                            value_conditions = []
                            for val in tag_values:
                                escaped_val = str(val).replace("'", "''")
                                # Handle JSON array values - Trino doesn't have JSON_CONTAINS, use simpler check
                                value_conditions.append(f"t.tag_value = '{escaped_val}'")
                            positive_tag_conditions.append(f"(t.tag_name = '{escaped_name}' AND ({' OR '.join(value_conditions)}))")
                        else:
                            # Single string value
                            escaped_val = str(tag_values).replace("'", "''")
                            positive_tag_conditions.append(f"(t.tag_name = '{escaped_name}' AND t.tag_value = '{escaped_val}')")
                
                # Tag existence filters
                if filters.tag_exists_filters:
                    for tag_name, exists in filters.tag_exists_filters.items():
                        escaped_name = tag_name.replace("'", "''")
                        if exists:
                            positive_tag_conditions.append(f"t.tag_name = '{escaped_name}'")
                        else:
                            negative_tag_names.append(escaped_name)
                
                # Build the query
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                limit_clause = f"LIMIT {filters.limit}" if filters.limit else ""
                
                # Explicitly list columns to avoid selecting non-existent 'tags' column
                source_columns = "s.id, s.format, s.label, s.description, s.created_by, s.updated_by, s.created, s.updated"
                
                if positive_tag_conditions:
                    # We have positive tag filters - use INNER JOIN
                    positive_tag_clause = " AND ".join(positive_tag_conditions)
                    
                    sql = f"""
                        SELECT DISTINCT {source_columns}
                        FROM {sources_table} s
                        INNER JOIN {tags_table} t ON s.id = t.entity_id AND t.entity_type = 'source'
                        WHERE {where_clause} AND {positive_tag_clause}
                    """
                    
                    # Add negative tag filters as NOT EXISTS subqueries
                    for tag_name in negative_tag_names:
                        sql += f" AND NOT EXISTS (SELECT 1 FROM {tags_table} t2 WHERE t2.entity_type = 'source' AND t2.entity_id = s.id AND t2.tag_name = '{tag_name}')"
                    
                    sql += f" {limit_clause}"
                else:
                    # Only negative tag filters - no JOIN needed
                    sql = f"""
                        SELECT {source_columns}
                        FROM {sources_table} s
                        WHERE {where_clause}
                    """
                    
                    for tag_name in negative_tag_names:
                        sql += f" AND NOT EXISTS (SELECT 1 FROM {tags_table} t2 WHERE t2.entity_type = 'source' AND t2.entity_id = s.id AND t2.tag_name = '{tag_name}')"
                    
                    sql += f" {limit_clause}"
                
                result = self.vast_db.execute_sql(sql)
                query_duration = time.time() - query_start
                json_parse_start = time.time()
            else:
                # No tag filters - use standard query builder
                query = self.vast_db.query("sources").select("*")
                
                # Add standard filters
                if filters.label:
                    query = query.where(f"label = '{filters.label}'")
                if filters.format:
                    query = query.where(f"format = '{filters.format}'")
                
                # Add limit
                if filters.limit:
                    query = query.limit(filters.limit)
                
                result = query.execute()
            
            query_duration = time.time() - query_start
            json_parse_start = time.time()
            
            # Convert to Source objects
            sources_data = []
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
                        
                        sources_data.append(source_data)
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        source_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        sources_data.append(source_data)
            else:
                # Fallback for direct list results
                for row in result:
                    source_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    sources_data.append(source_data)
            
            # source_collection is computed on-demand in get_source() only
            # For list operations, set it to empty list to avoid expensive JOIN queries
            sources = []
            for source_data in sources_data:
                # Set source_collection to empty list for list operations
                # It will be computed on-demand when retrieving a single source via get_source()
                source_data['source_collection'] = []
                sources.append(Source(**source_data))
            
            json_parse_duration = time.time() - json_parse_start
            total_duration = time.time() - total_start
            
            # Record telemetry metrics
            telemetry_manager.record_list_performance(
                entity_type="sources",
                query_duration=query_duration,
                json_parse_duration=json_parse_duration,
                total_duration=total_duration,
                record_count=len(sources),
                has_filters=has_filters
            )
            
            return sources
        except Exception as e:
            total_duration = time.time() - total_start if 'total_start' in locals() else 0
            logger.error("Failed to get sources (duration=%.3fs): %s", total_duration, e)
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
            # Keep updated_by if provided, but don't overwrite created_by
            source_data = source.model_dump(exclude={'id', 'created', 'created_by', 'source_collection', 'collected_by', 'tags'}, exclude_none=False)
            
            # Convert timestamp fields to SQL format using centralized function
            from ..common.storage.timestamp_utils import prepare_data_for_sql
            source_data = prepare_data_for_sql(source_data)
            
            # Filter out None values to avoid "unknown" type errors
            # But keep empty strings as they are valid values
            # Use exclude_none=False to ensure all fields including empty strings are included
            # IMPORTANT: Keep empty strings (v == '') as they are valid values for fields like label
            # Empty strings are not None, so they will be included by the v is not None check
            source_data = {k: v for k, v in source_data.items() if v is not None}
            
            # Log what we're updating for debugging
            logger.debug("Updating source %s with fields: %s", source_id, list(source_data.keys()))
            
            # Try UPDATE first
            try:
                if source_data:
                    # Build SQL update statement directly
                    set_clauses = []
                    for column, value in source_data.items():
                        # Check if this is a timestamp field that should be CAST
                        if is_timestamp_field(column) and isinstance(value, str) and value.startswith('CAST('):
                            # Handle timestamp fields that are already CAST expressions - don't quote them
                            set_clauses.append(f"{column} = {value}")
                        elif is_timestamp_field(column) and isinstance(value, datetime):
                            # Convert datetime to SQL timestamp format
                            from ..common.storage.timestamp_utils import prepare_data_for_sql
                            timestamp_data = prepare_data_for_sql({column: value})
                            if column in timestamp_data:
                                set_clauses.append(f"{column} = {timestamp_data[column]}")
                        else:
                            # Handle regular fields
                            if isinstance(value, str):
                                # Escape single quotes and handle empty strings
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
                        logger.debug("Successfully updated source %s", source_id)
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
                    logger.debug("Deleted existing source %s for upsert", source_id)
                    
                    # Insert new source data
                    source_data['id'] = source_id
                    source_data['created'] = get_tams_timestamp()
                    
                    # Convert timestamp fields to PyArrow format for insertion
                    from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                    source_data = prepare_data_for_pyarrow(source_data)
                    
                    logger.debug("Inserting source %s with data: %s", source_id, source_data)
                    self.vast_db.insert_record("sources", source_data)
                    logger.debug("Successfully inserted source %s via upsert", source_id)
                    
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
            logger.debug("delete_source called with cascade=%s", cascade)
            
            # Check for dependencies if cascade is False
            if not cascade:
                # Check if source has flows
                flows_result = self.vast_db.query("flows").select("id").where(f"source_id = '{source_id}'").execute()
                if flows_result and len(flows_result) > 0:
                    raise ValueError("Cannot delete source with existing flows. Use cascade=True to delete flows first.")
            
            # Cascade delete: Delete dependent flows first (and their segments)
            if cascade:
                logger.debug("Calling _cascade_delete_flows for source %s", source_id)
                await self._cascade_delete_flows(source_id)
                logger.debug("_cascade_delete_flows completed for source %s", source_id)
            
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
        """Delete all flows and their segments for a source (cascade delete)
        
        Per TAMS 8.0 spec: After deleting segments, unreferenced objects should be cleaned up.
        """
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
            
            # Clean up unreferenced objects after deleting segments (TAMS 8.0 spec requirement)
            try:
                from ..objects.service import ObjectStorageService
                object_service = ObjectStorageService(self.vast_db, self.s3_client)
                unreferenced = await object_service.get_unreferenced_objects()
                if unreferenced:
                    deleted_count = await object_service.delete_unreferenced_objects(unreferenced)
                    logger.info("Cleaned up %d unreferenced objects after cascade deleting source %s", deleted_count, source_id)
            except Exception as e:
                logger.warning("Failed to cleanup unreferenced objects after cascade delete for source %s: %s", source_id, e)
                # Don't fail the deletion if cleanup fails
            
            # Delete all flows for this source
            if flow_ids:
                self.vast_db.query("flows").delete().where(f"source_id = '{source_id}'").execute()
                logger.debug("Deleted %d flows for source %s", len(flow_ids), source_id)
            
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
    
