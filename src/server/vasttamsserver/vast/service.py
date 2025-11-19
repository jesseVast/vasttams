"""
VAST Object Vector Service

This service handles vector embedding operations for objects using vastdbmanager vector functionality.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import HTTPException
from ..common.storage.timestamp_utils import get_tams_timestamp, prepare_data_for_pyarrow
from ..objects.service import ObjectStorageService
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class VastObjectVectorService:
    """Handles vector embedding operations for objects using vastdbmanager vector client"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.object_service = ObjectStorageService(vast_db, s3_client)
        self.settings = get_settings()
        
        # Get vector client from vastdbmanager (available in version 1.1.9+)
        self.vector_client = getattr(vast_db, 'vector_client', None)
        if self.vector_client is None:
            logger.warning("Vector client not available in VastDBManager. Vector search may not work properly.")
    
    async def update_object_vector(
        self,
        object_id: str,
        vector: List[float],
        summary: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Update or insert vector data for an object.
        
        Args:
            object_id: Object ID
            vector: 768-dimensional vector embedding
            summary: Optional text summary
            embedding_model: Optional embedding model name (defaults to "nomic-embed-1.5")
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If object doesn't exist or validation fails
        """
        try:
            # Validate object exists
            obj = await self.object_service.get_object(object_id)
            if not obj:
                raise HTTPException(status_code=404, detail=f"Object {object_id} not found")
            
            # Validate vector length
            if len(vector) != 768:
                raise HTTPException(
                    status_code=400,
                    detail=f"Vector must be exactly 768 dimensions, got {len(vector)}"
                )
            
            # Set defaults
            embedding_date = get_tams_timestamp()
            model_name = embedding_model or "nomic-embed-1.5"
            
            # Use vastdbmanager's query builder interface for vector updates
            # This uses VAST's native UPDATE capability with fluent query builder
            try:
                # Get existing object data
                existing_obj = await self.object_service.get_object(object_id)
                if not existing_obj:
                    raise HTTPException(status_code=404, detail=f"Object {object_id} not found")
                
                # Escape object_id to prevent SQL injection
                escaped_object_id = object_id.replace("'", "''")
                
                # Build UPDATE query using query builder interface
                # Format: query(table).update().set(column=value, ...).where(condition).execute()
                query_builder = self.vast_db.query("objects").update()
                
                # Set vector field (768-dimensional list)
                # The query builder will handle proper formatting of the vector list
                query_builder = query_builder.set(vector=vector)
                
                # Add optional fields if provided
                if summary is not None:
                    query_builder = query_builder.set(summary=summary)
                if embedding_date:
                    query_builder = query_builder.set(embedding_date=embedding_date)
                if model_name:
                    query_builder = query_builder.set(embedding_model=model_name)
                
                # Add WHERE clause
                query_builder = query_builder.where(f"id == '{escaped_object_id}'")
                
                # Execute the update query
                result = query_builder.execute()
                
                # Check if update was successful
                # The execute() method returns a dict with execution results
                # For UPDATE operations, it typically returns affected row count or success status
                if isinstance(result, dict):
                    # Check for error or zero rows updated
                    if result.get('row_count', 0) == 0:
                        logger.warning(f"No rows updated for object {object_id}, object may not exist")
                        raise HTTPException(status_code=404, detail=f"Object {object_id} not found or could not be updated")
                
                logger.debug(f"Successfully updated vector for object {object_id} using vastdbmanager query builder")
                return True
                
            except HTTPException:
                raise
            except Exception as upsert_error:
                logger.error(f"Upsert failed for object {object_id}: {upsert_error}")
                raise HTTPException(status_code=500, detail="Failed to update object vector")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update object vector for {object_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def search_vectors(
        self,
        query_vector: List[float],
        num_matches: Optional[int] = None,
        distance_metric: Optional[str] = None,
        distance_numerical_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform vector similarity search using vastdbmanager vector client.
        
        Args:
            query_vector: 768-dimensional query vector
            num_matches: Number of matches to return (defaults to config)
            distance_metric: Distance metric - "euclidean" or "cosine" (defaults to config)
            distance_numerical_value: Distance threshold (defaults to config, 0.75 for cosine)
            
        Returns:
            Dictionary with matches containing object_ids, segment_ids, flow_ids, source_ids, and distances
        """
        try:
            # Validate vector length
            if len(query_vector) != 768:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query vector must be exactly 768 dimensions, got {len(query_vector)}"
                )
            
            # Use defaults from config if not provided
            num_matches = num_matches or self.settings.vector_search_default_num_matches
            distance_metric = distance_metric or self.settings.vector_search_default_distance_metric
            distance_numerical_value = distance_numerical_value or self.settings.vector_search_default_distance_numerical_value
            
            # Normalize distance metric (vastdbmanager uses "euclidean" or "cosine")
            if distance_metric and distance_metric.lower() not in ["euclidean", "cosine"]:
                logger.warning(f"Invalid distance_metric '{distance_metric}', defaulting to 'cosine'")
                distance_metric = "cosine"
            else:
                distance_metric = (distance_metric or "cosine").lower()
            
            # Get table names
            objects_table = self.vast_db.get_qualified_table_name("objects")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            
            # Use vastdbmanager vector client if available
            if self.vector_client:
                try:
                    # Use vector client to find matching objects with distances
                    # Note: vector_client works on single table, so we'll get object matches first
                    # then JOIN with segments/flows to get related IDs
                    vector_result = self.vector_client.query_vectors_with_distance(
                        table_name=objects_table,
                        query_vector=query_vector,
                        vector_column="vector",
                        limit=num_matches,
                        distance_metric=distance_metric,
                        where_clause="vector IS NOT NULL",
                        columns=["id"]  # Only need object IDs initially
                    )
                    
                    # Extract object IDs and distances from vector search results
                    object_ids_with_distances = []
                    if isinstance(vector_result, dict) and 'data' in vector_result:
                        data = vector_result['data']
                        if isinstance(data, dict):
                            # Columnar format
                            object_id_col = data.get('id', [])
                            distance_col = data.get('distance', [])
                            
                            for i in range(len(object_id_col)):
                                if object_id_col[i]:
                                    obj_id = str(object_id_col[i])
                                    distance = float(distance_col[i]) if i < len(distance_col) else None
                                    
                                    # Apply distance threshold if provided
                                    if distance_numerical_value is not None:
                                        # For cosine distance, lower is better (more similar)
                                        # For euclidean, lower is also better
                                        if distance is not None and distance > distance_numerical_value:
                                            continue  # Skip if distance exceeds threshold
                                    
                                    object_ids_with_distances.append({
                                        'object_id': obj_id,
                                        'distance': distance
                                    })
                    
                    if not object_ids_with_distances:
                        return {'matches': []}
                    
                    # Build list of object IDs for JOIN query
                    object_ids = [item['object_id'] for item in object_ids_with_distances]
                    # Escape single quotes in object IDs and build safe IN clause
                    escaped_ids = []
                    for obj_id in object_ids:
                        # Escape single quotes by doubling them
                        escaped_id = obj_id.replace("'", "''")
                        escaped_ids.append(f"'{escaped_id}'")
                    object_ids_str = ", ".join(escaped_ids)
                    
                    # JOIN with segments and flows to get related IDs
                    join_query = f"""
                        SELECT DISTINCT
                            o.id as object_id,
                            s.id as segment_id,
                            s.flow_id as flow_id,
                            f.source_id as source_id
                        FROM {objects_table} o
                        LEFT JOIN {segments_table} s ON o.id = s.object_id
                        LEFT JOIN {flows_table} f ON s.flow_id = f.id
                        WHERE o.id IN ({object_ids_str})
                    """
                    
                    join_result = self.vast_db.execute_sql(join_query)
                    
                    # Create a mapping of object_id to distance
                    distance_map = {item['object_id']: item['distance'] for item in object_ids_with_distances}
                    
                    # Process JOIN results and combine with distances
                    matches = []
                    if isinstance(join_result, dict) and 'data' in join_result:
                        data = join_result['data']
                        if isinstance(data, dict):
                            # Columnar format
                            object_id_col = data.get('object_id', [])
                            segment_id_col = data.get('segment_id', [])
                            flow_id_col = data.get('flow_id', [])
                            source_id_col = data.get('source_id', [])
                            
                            for i in range(len(object_id_col)):
                                if object_id_col[i]:
                                    obj_id = str(object_id_col[i])
                                    match = {
                                        'object_id': obj_id,
                                        'segment_id': str(segment_id_col[i]) if i < len(segment_id_col) and segment_id_col[i] else None,
                                        'flow_id': str(flow_id_col[i]) if i < len(flow_id_col) and flow_id_col[i] else None,
                                        'source_id': str(source_id_col[i]) if i < len(source_id_col) and source_id_col[i] else None,
                                        'distance': distance_map.get(obj_id)
                                    }
                                    matches.append(match)
                    
                    elif isinstance(join_result, list):
                        # Row format
                        for row in join_result:
                            if isinstance(row, dict) and row.get('object_id'):
                                obj_id = str(row['object_id'])
                                match = {
                                    'object_id': obj_id,
                                    'segment_id': str(row['segment_id']) if row.get('segment_id') else None,
                                    'flow_id': str(row['flow_id']) if row.get('flow_id') else None,
                                    'source_id': str(row['source_id']) if row.get('source_id') else None,
                                    'distance': distance_map.get(obj_id)
                                }
                                matches.append(match)
                    
                    return {'matches': matches}
                    
                except Exception as vector_error:
                    logger.error(f"Vector client search failed: {vector_error}, falling back to basic search")
                    # Fall through to basic search below
            else:
                logger.warning("Vector client not available, using basic search")
            
            # Fallback: Basic search without vector similarity (for compatibility)
            # This should rarely be used if vector_client is properly initialized
            objects_table = self.vast_db.get_qualified_table_name("objects")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            
            search_query = f"""
                SELECT DISTINCT
                    o.id as object_id,
                    s.id as segment_id,
                    s.flow_id as flow_id,
                    f.source_id as source_id
                FROM {objects_table} o
                LEFT JOIN {segments_table} s ON o.id = s.object_id
                LEFT JOIN {flows_table} f ON s.flow_id = f.id
                WHERE o.vector IS NOT NULL
                LIMIT {num_matches}
            """
            
            result = self.vast_db.execute_sql(search_query)
            matches = []
            
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    object_id_col = data.get('object_id', [])
                    segment_id_col = data.get('segment_id', [])
                    flow_id_col = data.get('flow_id', [])
                    source_id_col = data.get('source_id', [])
                    
                    for i in range(len(object_id_col)):
                        if object_id_col[i]:
                            match = {
                                'object_id': str(object_id_col[i]),
                                'segment_id': str(segment_id_col[i]) if i < len(segment_id_col) and segment_id_col[i] else None,
                                'flow_id': str(flow_id_col[i]) if i < len(flow_id_col) and flow_id_col[i] else None,
                                'source_id': str(source_id_col[i]) if i < len(source_id_col) and source_id_col[i] else None,
                                'distance': None  # No distance available in fallback mode
                            }
                            matches.append(match)
            
            return {'matches': matches}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to perform vector search: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

