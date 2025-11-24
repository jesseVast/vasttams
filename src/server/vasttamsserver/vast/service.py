"""
VAST Vector Service

This service handles vector embedding operations for any entity type (objects, flows, sources, segments)
using vastdbmanager vector functionality.
"""

import logging
from typing import Optional, List, Dict, Any, Literal

from fastapi import HTTPException
from ..common.storage.timestamp_utils import get_tams_timestamp, prepare_data_for_pyarrow
from ..objects.service import ObjectStorageService
from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Entity types supported by the vectors table
EntityType = Literal["object", "flow", "source", "segment"]


class VastObjectVectorService:
    """Handles vector embedding operations for entities using vastdbmanager vector client
    
    Note: Vector operations are optional and will not prevent server startup if unavailable.
    The service uses the 'vectors' table which supports any entity type (object, flow, source, segment).
    """
    
    # Table name
    VECTORS_TABLE = "vectors"
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.object_service = ObjectStorageService(vast_db, s3_client)
        self.settings = get_settings()
        
        # Get model dimension from config (default: 1536, legacy: 768)
        self.model_dimension = self.settings.embedding_model_dimension
        
        # Get vector client from vastdbmanager (available in version 1.1.9+)
        self.vector_client = getattr(vast_db, 'vector_client', None)
        if self.vector_client is None:
            logger.warning("Vector client not available in VastDBManager. Vector search may not work properly.")
    
    async def update_vector(
        self,
        entity_id: str,
        entity_type: EntityType,
        vector: List[float],
        summary: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Update or insert vector data for any entity type.
        
        Args:
            entity_id: Entity ID (object, flow, source, or segment ID)
            entity_type: Type of entity ("object", "flow", "source", "segment")
            vector: Vector embedding (dimension from config, default: 1536)
            summary: Optional text summary
            embedding_model: Optional embedding model name (defaults to configured model)
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # Validate entity type
            if entity_type not in ["object", "flow", "source", "segment"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid entity_type: {entity_type}. Must be one of: object, flow, source, segment"
                )
            
            # Validate vector length
            if len(vector) != self.model_dimension:
                raise HTTPException(
                    status_code=400,
                    detail=f"Vector must be exactly {self.model_dimension} dimensions, got {len(vector)}"
                )
            
            # Set defaults
            embedding_date = get_tams_timestamp()
            model_name = embedding_model or self.settings.embedding_model_name
            
            # Prepare vector data for insertion/update
            vector_data = {
                "entity_id": entity_id,
                "entity_type": entity_type,
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
                # insert_record handles upserts (inserts new or replaces existing records)
                self.vast_db.insert_record(self.VECTORS_TABLE, vector_data)
                
                logger.debug(f"Successfully inserted/updated vector for {entity_type} {entity_id} using insert_record (ADBC routing)")
                
                # If entity is an object, also sync the summary to the object's summary field
                # This keeps the object summary in sync with the vector summary
                if entity_type == "object":
                    try:
                        # Update object's summary field to match vector summary (can be None to clear)
                        await self.object_service.update_object_summary(entity_id, summary)
                        logger.debug(f"Synced object summary for {entity_id} from vector summary")
                    except Exception as summary_error:
                        # Non-blocking: log but don't fail vector update
                        logger.warning(f"Failed to sync object summary for {entity_id}: {summary_error}")
                
                return True
                
            except Exception as upsert_error:
                logger.error(f"Upsert failed for {entity_type} {entity_id}: {upsert_error}")
                raise HTTPException(status_code=500, detail="Failed to update vector")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update vector for {entity_type} {entity_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def search_vectors(
        self,
        query_vector: List[float],
        num_matches: Optional[int] = None,
        distance_metric: Optional[str] = None,
        distance_numerical_value: Optional[float] = None,
        entity_types: Optional[List[EntityType]] = None
    ) -> Dict[str, Any]:
        """
        Perform vector similarity search using vastdbmanager vector client.
        
        Args:
            query_vector: Query vector (dimension from config, default: 1536)
            num_matches: Number of matches to return (defaults to config)
            distance_metric: Distance metric - "euclidean" or "cosine" (defaults to config)
            distance_numerical_value: Distance threshold (defaults to config)
            entity_types: Optional list of entity types to filter by (e.g., ["object", "flow"])
            
        Returns:
            Dictionary with matches containing entity_id, entity_type, and related IDs (segment_ids, flow_ids, source_ids), and distances
        """
        try:
            # Validate vector length
            if len(query_vector) != self.model_dimension:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query vector must be exactly {self.model_dimension} dimensions, got {len(query_vector)}"
                )
            
            # Use defaults from config if not provided
            num_matches = num_matches or self.settings.vector_search_default_num_matches
            distance_metric = distance_metric or self.settings.embedding_distance_algorithm or self.settings.vector_search_default_distance_metric
            distance_numerical_value = distance_numerical_value or self.settings.embedding_default_distance_threshold or self.settings.vector_search_default_distance_numerical_value
            
            # Normalize distance metric (vastdbmanager uses "euclidean" or "cosine")
            if distance_metric and distance_metric.lower() not in ["euclidean", "cosine", "dot_product"]:
                logger.warning(f"Invalid distance_metric '{distance_metric}', defaulting to 'cosine'")
                distance_metric = "cosine"
            else:
                distance_metric = (distance_metric or "cosine").lower()
            
            # Get table names - use new vectors table
            vectors_table = self.vast_db.get_qualified_table_name(self.VECTORS_TABLE)
            objects_table = self.vast_db.get_qualified_table_name("objects")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            # Use vastdbmanager query builder search() method (vector-only operations)
            vector_result = None
            builder_error: Optional[Exception] = None
            try:
                query_builder = self.vast_db.query(self.VECTORS_TABLE)
            except AttributeError:
                query_builder = None
            
            if query_builder and hasattr(query_builder, "select") and hasattr(query_builder, "search"):
                try:
                    # Select entity_id and entity_type from vectors table (as strings, not list)
                    select_fields = "entity_id, entity_type"
                    if entity_types:
                        # Add entity_type filter if specified
                        # Note: filter syntax may need adjustment based on vastdbmanager API
                        vector_query = query_builder.select(select_fields).search(
                            query_vector=query_vector,
                            vector_column="vector",
                            distance_metric=distance_metric
                        )
                        # Apply entity_type filter after search if supported
                        # For now, we'll filter in post-processing
                    else:
                        vector_query = query_builder.select(select_fields).search(
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
                    # We'll need to map it to 'entity_id' in post-processing
                    vector_result = self.vector_client.query_vectors_with_distance(
                        table_name=vectors_table,
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
            
            # Extract entity IDs, types, and distances from vector search results
            entities_with_distances = []
            if isinstance(vector_result, dict) and 'data' in vector_result:
                data = vector_result['data']
                if isinstance(data, dict):
                    # Columnar format - handle both 'entity_id' and legacy 'id'/'object_id' columns
                    entity_id_col = data.get('entity_id') or data.get('id') or data.get('object_id') or []
                    entity_type_col = data.get('entity_type', [])
                    distance_col = data.get('distance', [])
                    
                    for i in range(len(entity_id_col)):
                        if entity_id_col[i]:
                            entity_id = str(entity_id_col[i])
                            entity_type = str(entity_type_col[i]) if i < len(entity_type_col) and entity_type_col[i] else "object"
                            distance = float(distance_col[i]) if i < len(distance_col) else None
                            
                            # Apply entity_type filter if specified
                            if entity_types and entity_type not in entity_types:
                                continue
                            
                            # Apply distance threshold if provided
                            if distance_numerical_value is not None:
                                # For cosine distance, lower is better (more similar)
                                # For euclidean, lower is also better
                                if distance is not None and distance > distance_numerical_value:
                                    continue  # Skip if distance exceeds threshold
                            
                            entities_with_distances.append({
                                'entity_id': entity_id,
                                'entity_type': entity_type,
                                'distance': distance
                            })
            
            if not entities_with_distances:
                return {'matches': []}
            
            # Group entities by type for efficient JOIN queries
            entities_by_type = {}
            for item in entities_with_distances:
                entity_type = item['entity_type']
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(item)
            
            # Build JOIN queries for each entity type and combine results
            matches = []
            distance_map = {f"{item['entity_type']}:{item['entity_id']}": item['distance'] for item in entities_with_distances}
            
            # Process each entity type
            for entity_type, entities in entities_by_type.items():
                entity_ids = [item['entity_id'] for item in entities]
                # Escape single quotes in entity IDs and build safe IN clause
                escaped_ids = []
                for entity_id in entity_ids:
                    escaped_id = entity_id.replace("'", "''")
                    escaped_ids.append(f"'{escaped_id}'")
                entity_ids_str = ", ".join(escaped_ids)
                
                # Build JOIN query based on entity type
                if entity_type == "object":
                    join_query = f"""
                        SELECT DISTINCT
                            o.id as entity_id,
                            'object' as entity_type,
                            s.id as segment_id,
                            s.flow_id as flow_id,
                            f.source_id as source_id
                        FROM {objects_table} o
                        LEFT JOIN {segments_table} s ON o.id = s.object_id
                        LEFT JOIN {flows_table} f ON s.flow_id = f.id
                        WHERE o.id IN ({entity_ids_str})
                    """
                elif entity_type == "segment":
                    join_query = f"""
                        SELECT DISTINCT
                            s.id as entity_id,
                            'segment' as entity_type,
                            s.id as segment_id,
                            s.flow_id as flow_id,
                            f.source_id as source_id,
                            s.object_id as object_id
                        FROM {segments_table} s
                        LEFT JOIN {flows_table} f ON s.flow_id = f.id
                        WHERE s.id IN ({entity_ids_str})
                    """
                elif entity_type == "flow":
                    join_query = f"""
                        SELECT DISTINCT
                            f.id as entity_id,
                            'flow' as entity_type,
                            NULL as segment_id,
                            f.id as flow_id,
                            f.source_id as source_id,
                            NULL as object_id
                        FROM {flows_table} f
                        WHERE f.id IN ({entity_ids_str})
                    """
                elif entity_type == "source":
                    join_query = f"""
                        SELECT DISTINCT
                            src.id as entity_id,
                            'source' as entity_type,
                            NULL as segment_id,
                            NULL as flow_id,
                            src.id as source_id,
                            NULL as object_id
                        FROM {sources_table} src
                        WHERE src.id IN ({entity_ids_str})
                    """
                else:
                    # Unknown entity type - skip
                    continue
                
                join_result = self.vast_db.execute_sql(join_query)
                
                # Process JOIN results and combine with distances
                if isinstance(join_result, dict) and 'data' in join_result:
                    data = join_result['data']
                    if isinstance(data, dict):
                        # Columnar format
                        entity_id_col = data.get('entity_id', [])
                        entity_type_col = data.get('entity_type', [])
                        segment_id_col = data.get('segment_id', [])
                        flow_id_col = data.get('flow_id', [])
                        source_id_col = data.get('source_id', [])
                        object_id_col = data.get('object_id', [])
                        
                        for i in range(len(entity_id_col)):
                            if entity_id_col[i]:
                                entity_id = str(entity_id_col[i])
                                entity_type = str(entity_type_col[i]) if i < len(entity_type_col) and entity_type_col[i] else entity_type
                                key = f"{entity_type}:{entity_id}"
                                
                                match = {
                                    'entity_id': entity_id,
                                    'entity_type': entity_type,
                                    'object_id': str(object_id_col[i]) if i < len(object_id_col) and object_id_col[i] else None,
                                    'segment_id': str(segment_id_col[i]) if i < len(segment_id_col) and segment_id_col[i] else None,
                                    'flow_id': str(flow_id_col[i]) if i < len(flow_id_col) and flow_id_col[i] else None,
                                    'source_id': str(source_id_col[i]) if i < len(source_id_col) and source_id_col[i] else None,
                                    'distance': distance_map.get(key)
                                }
                                matches.append(match)
                
                elif isinstance(join_result, list):
                    # Row format
                    for row in join_result:
                        if isinstance(row, dict) and row.get('entity_id'):
                            entity_id = str(row['entity_id'])
                            entity_type = str(row.get('entity_type', entity_type))
                            key = f"{entity_type}:{entity_id}"
                            
                            match = {
                                'entity_id': entity_id,
                                'entity_type': entity_type,
                                'object_id': str(row['object_id']) if row.get('object_id') else None,
                                'segment_id': str(row['segment_id']) if row.get('segment_id') else None,
                                'flow_id': str(row['flow_id']) if row.get('flow_id') else None,
                                'source_id': str(row['source_id']) if row.get('source_id') else None,
                                'distance': distance_map.get(key)
                            }
                            matches.append(match)
            
            return {'matches': matches}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to perform vector search: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def ingest_text(
        self,
        text: str,
        entity_id: str,
        entity_type: EntityType,
        embedding_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest text, convert to embedding vector, and store in VAST database.
        
        Args:
            text: Text to embed
            entity_id: Entity ID to associate with the vector
            entity_type: Type of entity ("object", "flow", "source", "segment")
            embedding_model: Optional embedding model name (defaults to configured model)
            
        Returns:
            Dictionary with ingestion results including entity_id, entity_type, embedding_model, embedding_date, dimension
            
        Raises:
            HTTPException: If ingestion fails
        """
        try:
            # Validate entity type
            if entity_type not in ["object", "flow", "source", "segment"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid entity_type: {entity_type}. Must be one of: object, flow, source, segment"
                )
            
            # Import embedding service
            from .embedding_service import EmbeddingService
            
            # Create embedding service
            embedding_service = EmbeddingService()
            
            # Check if embedding service is available (check if embedder is initialized)
            if not hasattr(embedding_service, '_embedder') or embedding_service._embedder is None:
                raise HTTPException(
                    status_code=503,
                    detail="Embedding service is not available. Please configure embedding provider in settings."
                )
            
            # Use text as summary (stored in database for reference, but not returned in response)
            # The actual text is already stored in the text column
            summary = text[:500]  # Limit summary length for database storage
            
            # Get embedding model name
            model_name = embedding_model or self.settings.embedding_model_name
            
            # Create embedding from text
            logger.debug(f"Creating embedding for entity {entity_type}:{entity_id}")
            vector = await embedding_service.create_embedding(text, model_name=model_name)
            
            # Validate vector dimension
            if len(vector) != self.model_dimension:
                raise HTTPException(
                    status_code=500,
                    detail=f"Embedding dimension mismatch: expected {self.model_dimension}, got {len(vector)}"
                )
            
            # Store vector in database
            logger.debug(f"Storing vector for entity {entity_type}:{entity_id}")
            success = await self.update_vector(
                entity_id=entity_id,
                entity_type=entity_type,
                vector=vector,
                summary=summary,
                embedding_model=model_name
            )
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to store vector in database"
                )
            
            # Get embedding date
            embedding_date = get_tams_timestamp()
            
            # Return response (without summary - it will come from the entity if needed)
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'embedding_model': model_name,
                'embedding_date': embedding_date,
                'dimension': len(vector)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to ingest text for entity {entity_type}:{entity_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def search_by_text(
        self,
        text: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: Optional[int] = None,
        distance_threshold: Optional[float] = None,
        distance_metric: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search vectors by text query.
        
        Converts text to embedding vector, then performs vector similarity search.
        
        Args:
            text: Search query text
            entity_types: Optional list of entity types to filter by
            limit: Number of results to return (defaults to config)
            distance_threshold: Distance threshold (defaults to config)
            distance_metric: Distance metric (defaults to config)
            
        Returns:
            Dictionary with search results including query_text, embedding_model, distance_algorithm, 
            distance_threshold, results, and total count
            
        Raises:
            HTTPException: If search fails
        """
        try:
            # Import embedding service
            from .embedding_service import EmbeddingService
            
            # Create embedding service
            embedding_service = EmbeddingService()
            
            # Check if embedding service is available
            if not hasattr(embedding_service, '_embedder') or embedding_service._embedder is None:
                raise HTTPException(
                    status_code=503,
                    detail="Embedding service is not available. Please configure embedding provider in settings."
                )
            
            # Get embedding model name
            model_name = self.settings.embedding_model_name
            
            # Create embedding from text
            logger.debug(f"Creating embedding for text search: {text[:50]}...")
            query_vector = await embedding_service.create_embedding(text, model_name=model_name)
            
            # Validate vector dimension
            if len(query_vector) != self.model_dimension:
                raise HTTPException(
                    status_code=500,
                    detail=f"Embedding dimension mismatch: expected {self.model_dimension}, got {len(query_vector)}"
                )
            
            # Get defaults from config
            num_matches = limit or self.settings.vector_search_default_num_matches
            distance_metric_used = distance_metric or self.settings.embedding_distance_algorithm or self.settings.vector_search_default_distance_metric
            distance_threshold_used = distance_threshold or self.settings.embedding_default_distance_threshold or self.settings.vector_search_default_distance_numerical_value
            
            # Perform vector search
            logger.debug(f"Performing vector search with {num_matches} matches, threshold={distance_threshold_used}")
            search_results = await self.search_vectors(
                query_vector=query_vector,
                num_matches=num_matches,
                distance_metric=distance_metric_used,
                distance_numerical_value=distance_threshold_used,
                entity_types=entity_types
            )
            
            # Get matches and total count
            matches = search_results.get('matches', [])
            total = len(matches)
            
            # Return formatted response
            return {
                'query_text': text,
                'embedding_model': model_name,
                'distance_algorithm': distance_metric_used,
                'distance_threshold': distance_threshold_used,
                'results': matches,
                'total': total
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to search by text: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

