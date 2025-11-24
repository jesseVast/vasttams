"""
Entity Vectorization Service

This service automatically vectorizes entities (flows, sources, objects) when they are
created, updated, or deleted. It converts entity JSON to text and generates embeddings.
"""

import logging
import json
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel

from ..core.config import get_settings
from .embedding_service import EmbeddingService
from .service import VastObjectVectorService

logger = logging.getLogger(__name__)

EntityType = Literal["object", "flow", "source", "segment"]


class EntityVectorizationService:
    """Service for automatically vectorizing entities"""
    
    def __init__(self, vast_db, s3_client):
        """Initialize the entity vectorization service"""
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.vector_service = VastObjectVectorService(vast_db, s3_client)
    
    def _is_vectorization_enabled(self) -> bool:
        """Check if vectorization is enabled and embedding service is available"""
        if not hasattr(self.embedding_service, '_embedder') or self.embedding_service._embedder is None:
            return False
        return True
    
    def _entity_to_text(self, entity: Dict[str, Any], entity_type: EntityType) -> str:
        """
        Convert entity dictionary to text representation suitable for embedding.
        
        Excludes ID fields and internal metadata, includes descriptive fields.
        """
        # Create a copy to avoid modifying the original
        entity_copy = entity.copy()
        
        # Remove ID fields
        id_fields = ['id', 'object_id', 'flow_id', 'source_id', 'segment_id']
        for field in id_fields:
            entity_copy.pop(field, None)
        
        # Remove internal/timestamp fields (optional - can include as metadata if needed)
        internal_fields = ['created', 'created_by', 'updated', 'updated_by', 
                          'metadata_updated', 'segments_updated']
        for field in internal_fields:
            entity_copy.pop(field, None)
        
        # Convert to text representation
        # Format: "label: value, description: value, tags: {...}, ..."
        text_parts = []
        
        # Add label if present
        if 'label' in entity_copy and entity_copy['label']:
            text_parts.append(f"label: {entity_copy['label']}")
        
        # Add description if present
        if 'description' in entity_copy and entity_copy['description']:
            text_parts.append(f"description: {entity_copy['description']}")
        
        # Add tags if present
        if 'tags' in entity_copy and entity_copy['tags']:
            tags = entity_copy['tags']
            if isinstance(tags, dict) and 'root' in tags:
                tags = tags['root']
            if tags:
                tags_text = json.dumps(tags, separators=(',', ':'))
                text_parts.append(f"tags: {tags_text}")
        
        # Add format/codec info for flows
        if entity_type == "flow":
            if 'format' in entity_copy:
                text_parts.append(f"format: {entity_copy['format']}")
            if 'codec' in entity_copy:
                text_parts.append(f"codec: {entity_copy['codec']}")
            if 'essence_parameters' in entity_copy:
                essence = entity_copy['essence_parameters']
                if isinstance(essence, dict):
                    essence_text = json.dumps(essence, separators=(',', ':'))
                    text_parts.append(f"essence_parameters: {essence_text}")
        
        # Add format for sources
        if entity_type == "source":
            if 'format' in entity_copy:
                text_parts.append(f"format: {entity_copy['format']}")
        
        # Add remaining fields as JSON (excluding already processed ones)
        processed_fields = {'label', 'description', 'tags', 'format', 'codec', 'essence_parameters'}
        remaining_fields = {k: v for k, v in entity_copy.items() 
                          if k not in processed_fields and v is not None}
        
        if remaining_fields:
            remaining_text = json.dumps(remaining_fields, separators=(',', ':'))
            text_parts.append(f"metadata: {remaining_text}")
        
        # Join all parts
        text = ", ".join(text_parts)
        
        # Limit text length (embedding models have token limits)
        max_length = 8000  # Conservative limit
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    async def vectorize_entity(
        self,
        entity: Dict[str, Any],
        entity_id: str,
        entity_type: EntityType
    ) -> bool:
        """
        Vectorize an entity and store the vector.
        
        Args:
            entity: Entity dictionary (from model.model_dump() or similar)
            entity_id: Entity ID
            entity_type: Type of entity ("object", "flow", "source", "segment")
            
        Returns:
            True if successful, False otherwise (non-blocking)
        """
        try:
            # Check if vectorization is enabled
            if not self._is_vectorization_enabled():
                logger.debug("Vectorization skipped: embedding service not available")
                return False
            
            # Convert entity to text
            text = self._entity_to_text(entity, entity_type)
            
            if not text or not text.strip():
                logger.warning(f"Empty text generated for entity {entity_type}:{entity_id}, skipping vectorization")
                return False
            
            # Create embedding
            logger.debug(f"Creating embedding for {entity_type}:{entity_id}")
            vector = await self.embedding_service.create_embedding(text)
            
            # Validate dimension
            expected_dim = self.settings.embedding_model_dimension
            if len(vector) != expected_dim:
                logger.error(
                    f"Embedding dimension mismatch for {entity_type}:{entity_id}: "
                    f"expected {expected_dim}, got {len(vector)}"
                )
                return False
            
            # Store vector
            logger.debug(f"Storing vector for {entity_type}:{entity_id}")
            success = await self.vector_service.update_vector(
                entity_id=entity_id,
                entity_type=entity_type,
                vector=vector,
                summary=text[:500],  # Store truncated text as summary
                embedding_model=self.settings.embedding_model_name
            )
            
            if success:
                logger.debug(f"Successfully vectorized {entity_type}:{entity_id}")
            else:
                logger.warning(f"Failed to store vector for {entity_type}:{entity_id}")
            
            return success
            
        except Exception as e:
            # Non-blocking: log error but don't raise
            logger.error(f"Error vectorizing {entity_type}:{entity_id}: {e}", exc_info=True)
            return False
    
    async def delete_entity_vector(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> bool:
        """
        Delete vector associated with an entity.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            
        Returns:
            True if successful or if vector doesn't exist, False on error
        """
        try:
            # Note: We don't have a delete_vector method yet, but vectors can be
            # removed by updating with None or by direct database operation
            # For now, we'll just log the deletion - actual deletion can be handled
            # by the vector service if needed
            logger.debug(f"Vector deletion requested for {entity_type}:{entity_id}")
            # TODO: Implement actual vector deletion if needed
            return True
            
        except Exception as e:
            logger.error(f"Error deleting vector for {entity_type}:{entity_id}: {e}", exc_info=True)
            return False

