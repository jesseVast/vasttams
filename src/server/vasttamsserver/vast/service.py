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
            
            # Use insert_record for vector operations - vastdbmanager 1.1.10+ automatically routes
            # vector operations to ADBC/vector_client, avoiding Trino errors
            # insert_record handles upserts (inserts new or replaces existing records)
            # Prepare vector data for insertion/update
            # insert_record will upsert if object_id exists
            vector_data = {
                "object_id": object_id,
                "vector": vector,
                "embedding_date": embedding_date,
                "embedding_model": model_name
            }
            if summary is not None:
                vector_data["summary"] = summary
            
            # Convert timestamps for PyArrow
            vector_data = prepare_data_for_pyarrow(vector_data)
            
            try:
                # Use insert_record which automatically routes to ADBC for vector columns
                # With vastdbmanager 1.1.10+, this avoids Trino errors
                self.vast_db.insert_record("object_vector", vector_data)
                
                logger.debug(f"Successfully inserted/updated vector for object {object_id} using insert_record (ADBC routing)")
                return True
                
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
            object_vector_table = self.vast_db.get_qualified_table_name("object_vector")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            
            # Use vastdbmanager query builder search() method (vector-only operations)
            vector_result = None
            builder_error: Optional[Exception] = None
            try:
                query_builder = self.vast_db.query("object_vector")
            except AttributeError:
                query_builder = None
            
            if query_builder and hasattr(query_builder, "select") and hasattr(query_builder, "search"):
                try:
                    vector_query = query_builder.select("object_id").search(
                        query_vector=query_vector,
                        vector_column="vector",
                        distance_metric=distance_metric
                    )
                    if num_matches:
                        vector_query = vector_query.limit(num_matches)
                    vector_result = vector_query.execute()
                except Exception as exc:
                    builder_error = exc
                    logger.error("Query builder vector search failed: %s", exc, exc_info=True)
            
            # Fallback to vector_client if query builder search is unavailable or failed
            if vector_result is None and self.vector_client:
                try:
                    # Note: vector_client.query_vectors_with_distance returns results with 'id' column
                    # We'll need to map it to 'object_id' in post-processing
                    vector_result = self.vector_client.query_vectors_with_distance(
                        table_name=object_vector_table,
                        query_vector=query_vector,
                        vector_column="vector",
                        limit=num_matches,
                        distance_metric=distance_metric
                    )
                except Exception as client_error:
                    logger.error("Vector client search failed: %s", client_error, exc_info=True)
                    raise HTTPException(status_code=503, detail="Vector search unavailable") from client_error
            
            if vector_result is None:
                error_detail = "Vector search unavailable"
                if builder_error:
                    error_detail += f": {builder_error}"
                raise HTTPException(status_code=503, detail=error_detail)
            
            # Extract object IDs and distances from vector search results
            object_ids_with_distances = []
            if isinstance(vector_result, dict) and 'data' in vector_result:
                data = vector_result['data']
                if isinstance(data, dict):
                    # Columnar format - handle both 'object_id' and legacy 'id' columns
                    object_id_col = data.get('object_id') or data.get('id') or []
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
            
            # JOIN query using execute_sql - does NOT include object_vector table
            # This avoids Trino reading vector columns - only regular tables in JOIN
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
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to perform vector search: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

