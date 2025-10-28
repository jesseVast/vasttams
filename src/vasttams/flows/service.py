"""
Flow Storage Service

This module handles all flow-related storage operations including
CRUD operations, filtering, and flow management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    get_tams_timestamp, 
    get_timeline_synchronizer,
    prepare_data_for_pyarrow,
    prepare_data_for_sql
)
from .models import Flow, VideoFlow, AudioFlow, ImageFlow, DataFlow, MultiFlow
from .bitrate_calculator import BitRateCalculator
from ..common.filters import FlowFilters, FlowDetailFilters
from ..sources.models import Source

logger = logging.getLogger(__name__)


def _get_flow_class(format_str: str):
    """Get the appropriate flow class based on format"""
    if format_str == "urn:x-nmos:format:video":
        return VideoFlow
    elif format_str == "urn:x-nmos:format:audio":
        return AudioFlow
    elif format_str == "urn:x-nmos:format:image":
        return ImageFlow
    elif format_str == "urn:x-nmos:format:data":
        return DataFlow
    elif format_str == "urn:x-nmos:format:multi":
        return MultiFlow
    else:
        # Default to VideoFlow for unknown formats
        return VideoFlow


class FlowStorageService:
    """Handles flow-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_flows(self, filters: FlowFilters) -> List[Flow]:
        """Get flows with filtering (TAMS 8.0 with tag filtering)"""
        try:
            # Build query using vaststore
            query = self.vast_db.query("flows").select("*")
            
            # Add standard filters
            if filters.source_id:
                query = query.where(f"source_id = '{filters.source_id}'")
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
            
            # Convert to Flow objects
            flows = []
            # VAST returns a dict with 'data' field containing column arrays
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        flow_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                # Parse JSON fields
                                if column in ['essence_parameters', 'tags'] and isinstance(value, str):
                                    try:
                                        import json
                                        flow_data[column] = json.loads(value)
                                    except (json.JSONDecodeError, TypeError):
                                        flow_data[column] = value
                                else:
                                    flow_data[column] = value
                        # Get the appropriate flow class based on format
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        flows.append(flow_class(**flow_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        flow_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        # Parse JSON fields
                        for field in ['essence_parameters', 'tags']:
                            if field in flow_data and isinstance(flow_data[field], str):
                                try:
                                    import json
                                    flow_data[field] = json.loads(flow_data[field])
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        # Get the appropriate flow class based on format
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        flows.append(flow_class(**flow_data))
            else:
                # Fallback for direct list results
                for row in result:
                    flow_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    # Parse JSON fields
                    for field in ['essence_parameters', 'tags']:
                        if field in flow_data and isinstance(flow_data[field], str):
                            try:
                                import json
                                flow_data[field] = json.loads(flow_data[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    # Get the appropriate flow class based on format
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    flows.append(flow_class(**flow_data))
            
            return flows
        except Exception as e:
            logger.error("Failed to get flows: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a specific flow by ID"""
        try:
            result = self.vast_db.query("flows").select("*").where(f"id = '{flow_id}'").execute()
            
            # Handle VAST query result format
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    # Get the first row
                    flow_data = {}
                    for column, values in data.items():
                        if column != '$row_id':  # Skip internal row IDs
                            value = values[0] if len(values) > 0 else None
                            # Parse JSON fields
                            if column in ['essence_parameters', 'tags'] and isinstance(value, str):
                                try:
                                    import json
                                    flow_data[column] = json.loads(value)
                                except (json.JSONDecodeError, TypeError):
                                    flow_data[column] = value
                            else:
                                flow_data[column] = value
                    # Get the appropriate flow class based on format
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    return flow_class(**flow_data)
                elif isinstance(data, list):
                    if not data:
                        return None
                    flow_data = dict(data[0]) if hasattr(data[0], '__iter__') and not isinstance(data[0], str) else data[0]
                    # Parse JSON fields
                    for field in ['essence_parameters', 'tags']:
                        if field in flow_data and isinstance(flow_data[field], str):
                            try:
                                import json
                                flow_data[field] = json.loads(flow_data[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    # Get the appropriate flow class based on format
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    return flow_class(**flow_data)
            else:
                if not result or len(result) == 0:
                    return None
                flow_data = dict(result[0]) if hasattr(result[0], '__iter__') and not isinstance(result[0], str) else result[0]
                # Parse JSON fields
                if 'essence_parameters' in flow_data and isinstance(flow_data['essence_parameters'], str):
                    try:
                        import json
                        flow_data['essence_parameters'] = json.loads(flow_data['essence_parameters'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                # Get the appropriate flow class based on format
                flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                return flow_class(**flow_data)
        except Exception as e:
            logger.error("Failed to get flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _calculate_and_update_bit_rates(self, flow_id: str) -> None:
        """
        Calculate and update bit rates for a flow from its segments
        
        Args:
            flow_id: Flow identifier
        """
        try:
            # Get flow to check if bit rates need calculation
            flow = await self.get_flow(flow_id)
            if not flow:
                return
            
            # Check if bit rates are already set
            if flow.avg_bit_rate and flow.max_bit_rate:
                logger.debug(f"Bit rates already set for flow {flow_id}")
                return
            
            # Get flow segments
            from ..segments.service import SegmentStorageService
            from ..core.config import get_settings
            segment_service = SegmentStorageService(self.vast_db, self.s3_client, get_settings())
            
            segments = await segment_service.get_flow_segments(flow_id)
            
            if not segments:
                logger.debug(f"No segments found for flow {flow_id}, skipping bit rate calculation")
                return
            
            # Calculate bit rates
            calculator = BitRateCalculator()
            
            # Get target segment duration from flow
            target_duration = 1.0  # Default 1 second
            if flow.segment_duration:
                target_duration = flow.segment_duration.numerator / flow.segment_duration.denominator
            
            # Calculate bit rates
            avg_bit_rate = await calculator.calculate_avg_bit_rate(segments)
            max_bit_rate = await calculator.calculate_max_bit_rate(segments, target_duration)
            
            # Update flow with calculated bit rates
            if avg_bit_rate or max_bit_rate:
                from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                update_data = {}
                
                if avg_bit_rate:
                    update_data['avg_bit_rate'] = avg_bit_rate
                if max_bit_rate:
                    update_data['max_bit_rate'] = max_bit_rate
                
                if update_data:
                    # Prepare and update
                    prepared_data = prepare_data_for_pyarrow(update_data)
                    self.vast_db.insert_record("flows", prepared_data)  # Will use UPSERT logic
                    logger.info(f"Updated bit rates for flow {flow_id}: avg={avg_bit_rate}, max={max_bit_rate}")
        
        except Exception as e:
            logger.warning(f"Failed to calculate bit rates for flow {flow_id}: {e}")
    
    async def create_flow(self, flow: Flow) -> bool:
        """Create a new flow (TAMS 8.0 with VFR validation)"""
        try:
            # TAMS 8.0: Validate VFR/frame_rate mutex for video flows
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                vfr = flow.essence_parameters.vfr or False
                frame_rate = flow.essence_parameters.frame_rate
                
                # Validate per ADR-0041
                if vfr and frame_rate is not None:
                    raise ValueError("If vfr=True, frame_rate MUST NOT be set")
                if not vfr and frame_rate is None:
                    raise ValueError("If vfr=False or omitted, frame_rate MUST be set")
            
            now = get_tams_timestamp()
            flow.created = now
            flow.metadata_updated = now
            flow.segments_updated = now
            
            # Check if source exists, create it automatically if it doesn't
            await self._ensure_source_exists(flow)
            
            flow_data = flow.model_dump()
            
            # TAMS 8.0: Extract and store VFR field separately
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                flow_data['vfr'] = flow.essence_parameters.vfr
            
            # Convert timestamp fields to PyArrow format using centralized function
            flow_data = prepare_data_for_pyarrow(flow_data)
            
            logger.debug("Creating flow with data: %s", flow_data)
            result = self.vast_db.insert_record("flows", flow_data)
            logger.debug("Flow creation result: %s", result)
            logger.debug("Flow created successfully with ID: %s", flow.id)
            
            # Auto-calculate bit rates if not provided
            if not flow.avg_bit_rate or not flow.max_bit_rate:
                try:
                    await self._calculate_and_update_bit_rates(flow.id)
                except Exception as e:
                    logger.warning("Failed to auto-calculate bit rates: %s", e)
            
            return True
        except ValueError as ve:
            logger.error("VFR validation error creating flow: %s", ve)
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error("Failed to create flow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update an existing flow using update-before-upsert approach (TAMS 8.0 with VFR validation)"""
        try:
            # TAMS 8.0: Validate VFR/frame_rate mutex for video flows
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                vfr = flow.essence_parameters.vfr or False
                frame_rate = flow.essence_parameters.frame_rate
                
                # Validate per ADR-0041
                if vfr and frame_rate is not None:
                    raise ValueError("If vfr=True, frame_rate MUST NOT be set")
                if not vfr and frame_rate is None:
                    raise ValueError("If vfr=False or omitted, frame_rate MUST be set")
            
            flow.metadata_updated = get_tams_timestamp()
            
            # Extract tags separately for handling in tags table
            tags_data = None
            if hasattr(flow, 'tags') and flow.tags is not None:
                tags_data = flow.tags
            
            # Only update mutable fields, exclude read-only fields and tags
            flow_data = flow.model_dump(exclude={'id', 'created', 'created_by', 'collected_by', 'tags'})
            
            # TAMS 8.0: Extract and store VFR field separately
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                flow_data['vfr'] = flow.essence_parameters.vfr
            
            # Convert timestamp fields to SQL format using centralized function
            flow_data = prepare_data_for_sql(flow_data)

            # Convert essence_parameters to JSON string for database compatibility
            if 'essence_parameters' in flow_data and flow_data['essence_parameters'] is not None:
                import json
                if hasattr(flow_data['essence_parameters'], 'model_dump'):
                    flow_data['essence_parameters'] = json.dumps(flow_data['essence_parameters'].model_dump())
                elif isinstance(flow_data['essence_parameters'], dict):
                    flow_data['essence_parameters'] = json.dumps(flow_data['essence_parameters'])

            # Convert flow_collection to JSON string for database compatibility
            if 'flow_collection' in flow_data and flow_data['flow_collection'] is not None:
                import json
                if hasattr(flow_data['flow_collection'], 'root'):
                    flow_data['flow_collection'] = json.dumps(flow_data['flow_collection'].root)
                elif isinstance(flow_data['flow_collection'], list):
                    flow_data['flow_collection'] = json.dumps(flow_data['flow_collection'])

            # Filter out None values to avoid "unknown" type errors
            flow_data = {k: v for k, v in flow_data.items() if v is not None}
            
            # Try UPDATE first
            try:
                if flow_data:
                    # Build SQL update statement directly
                    set_clauses = []
                    for column, value in flow_data.items():
                        if column in ['metadata_updated', 'segments_updated'] and isinstance(value, str) and value.startswith('CAST('):
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
                        flows_table = self.vast_db.get_qualified_table_name("flows")
                        sql = f"UPDATE {flows_table} SET {', '.join(set_clauses)} WHERE id = '{flow_id}'"
                        logger.debug("Updating flow %s with SQL: %s", flow_id, sql)
                        self.vast_db.execute_sql(sql)
                        logger.info("Successfully updated flow %s", flow_id)
                else:
                    logger.warning("No fields to update for flow %s", flow_id)
                
                # Handle tags separately using tag service
                if tags_data is not None:
                    await self.tag_service.update_flow_tags(flow_id, tags_data)
                
                return True
                
            except Exception as update_error:
                logger.warning("UPDATE failed for flow %s, trying upsert approach: %s", flow_id, update_error)
                
                # If UPDATE fails, try DELETE + INSERT (upsert)
                try:
                    # Delete existing flow
                    flows_table = self.vast_db.get_qualified_table_name("flows")
                    delete_sql = f"DELETE FROM {flows_table} WHERE id = '{flow_id}'"
                    self.vast_db.execute_sql(delete_sql)
                    logger.info("Deleted existing flow %s for upsert", flow_id)
                    
                    # Insert new flow data
                    flow_data['id'] = flow_id
                    flow_data['created'] = get_tams_timestamp()
                    
                    # Convert timestamp fields to PyArrow format for insertion
                    flow_data = prepare_data_for_pyarrow(flow_data)
                    
                    logger.debug("Inserting flow %s with data: %s", flow_id, flow_data)
                    self.vast_db.insert_record("flows", flow_data)
                    logger.info("Successfully inserted flow %s via upsert", flow_id)
                    
                    # Handle tags separately using tag service
                    if tags_data is not None:
                        await self.tag_service.update_flow_tags(flow_id, tags_data)
                    
                    return True
                    
                except Exception as upsert_error:
                    logger.error("Both UPDATE and upsert failed for flow %s: %s", flow_id, upsert_error)
                    raise upsert_error
                    
        except ValueError as ve:
            logger.error("VFR validation error updating flow: %s", ve)
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error("Failed to update flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_description(self, flow_id: str, description: str) -> bool:
        """Update flow description only"""
        try:
            escaped_description = description.replace("'", "''")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET description = '{escaped_description}' WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to update flow description %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_description(self, flow_id: str) -> bool:
        """Delete flow description only"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET description = NULL WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to delete flow description %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_label(self, flow_id: str, label: str) -> bool:
        """Update flow label only"""
        try:
            escaped_label = label.replace("'", "''")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET label = '{escaped_label}' WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to update flow label %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_label(self, flow_id: str) -> bool:
        """Delete flow label only"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET label = NULL WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to delete flow label %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_read_only(self, flow_id: str, read_only: bool) -> bool:
        """Update flow read_only status only"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET read_only = {str(read_only).lower()} WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to update flow read_only %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        """Delete a flow"""
        try:
            # Delete flow segments first if cascade is True
            if cascade:
                await self._delete_flow_segments(flow_id)
            
            # Delete flow
            self.vast_db.query("flows").delete().where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        try:
            result = self.vast_db.query("flows").select("read_only").where(f"id = '{flow_id}'").execute()
            if not result or len(result) == 0:
                return False
            
            return result[0].get('read_only', False)
        except Exception as e:
            logger.error("Failed to check flow read-only status for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _delete_flow_segments(self, flow_id: str) -> bool:
        """Delete flow segments for a flow"""
        try:
            self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_flow_with_source_details(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get flow details with source information using join query"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            sql = f"""
                SELECT 
                    f.id,
                    f.source_id,
                    f.format,
                    f.label,
                    f.description,
                    f.read_only,
                    f.created,
                    f.updated,
                    f.tags,
                    s.label as source_label,
                    s.format as source_format,
                    s.description as source_description
                FROM {flows_table} f
                JOIN {sources_table} s ON f.source_id = s.id
                WHERE f.id = '{flow_id}'
            """
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result and len(result['data']) > 0:
                row = result['data'][0]
                return {
                    "id": row[0],
                    "source_id": row[1],
                    "format": row[2],
                    "label": row[3],
                    "description": row[4],
                    "read_only": row[5],
                    "created": row[6],
                    "updated": row[7],
                    "tags": row[8],
                    "source": {
                        "id": row[1],
                        "label": row[9],
                        "format": row[10],
                        "description": row[11]
                    }
                }
            return None
        except Exception as e:
            logger.error("Failed to get flow with source details for %s: %s", flow_id, e)
            return None
    
    async def get_flows_with_source_details(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get flows with source information using join query"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            sql = f"""
                SELECT 
                    f.id,
                    f.source_id,
                    f.format,
                    f.label,
                    f.description,
                    f.read_only,
                    f.created,
                    f.updated,
                    f.tags,
                    s.label as source_label,
                    s.format as source_format,
                    s.description as source_description
                FROM {flows_table} f
                JOIN {sources_table} s ON f.source_id = s.id
            """
            
            # Add filters if provided
            where_conditions = []
            if filters:
                if filters.get("source_id"):
                    where_conditions.append(f"f.source_id = '{filters['source_id']}'")
                if filters.get("label"):
                    where_conditions.append(f"f.label = '{filters['label']}'")
                if filters.get("format"):
                    where_conditions.append(f"f.format = '{filters['format']}'")
                if filters.get("source_format"):
                    where_conditions.append(f"s.format = '{filters['source_format']}'")
            
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
            
            sql += " ORDER BY f.created DESC"
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result:
                flows = []
                for row in result['data']:
                    flows.append({
                        "id": row[0],
                        "source_id": row[1],
                        "format": row[2],
                        "label": row[3],
                        "description": row[4],
                        "read_only": row[5],
                        "created": row[6],
                        "updated": row[7],
                        "tags": row[8],
                        "source": {
                            "id": row[1],
                            "label": row[9],
                            "format": row[10],
                            "description": row[11]
                        }
                    })
                return flows
            return []
        except Exception as e:
            logger.error("Failed to get flows with source details: %s", e)
            return []
    
    async def _ensure_source_exists(self, flow: Flow) -> None:
        """Ensure source exists, create it automatically if it doesn't"""
        try:
            # Check if source exists
            source_query = self.vast_db.query("sources").select("*").where(f"id = '{flow.source_id}'")
            result = source_query.execute()
            
            if not result or not result.get('data') or len(result['data']) == 0:
                # Source doesn't exist, create it automatically
                logger.info("Source %s doesn't exist, creating it automatically", flow.source_id)
                
                # Create source with metadata from flow
                source = Source(
                    id=flow.source_id,
                    format=flow.format,
                    label=flow.label,
                    description=flow.description,
                    created_by=flow.created_by,
                    updated_by=flow.updated_by,
                    tags=flow.tags  # Replicate tags from flow to source
                )
                
                # Insert source into database
                source_data = source.model_dump(exclude={'source_collection', 'collected_by'})
                source_data['created'] = get_tams_timestamp()
                source_data['updated'] = get_tams_timestamp()
                
                self.vast_db.insert_record("sources", source_data)
                logger.info("Successfully created source %s with metadata from flow", flow.source_id)
            else:
                logger.debug("Source %s already exists", flow.source_id)
                
        except Exception as e:
            logger.error("Failed to ensure source exists for flow %s: %s", flow.id, e)
            raise HTTPException(status_code=500, detail="Failed to create source automatically")
