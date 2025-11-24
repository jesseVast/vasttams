"""
VAST Objects Router

This router handles VAST-specific object extensions that are outside the TAMS specification.
Routes are under /api/vast/objects to clearly distinguish from TAMS-compliant endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, cast, List
import logging

from .models import (
    ObjectVectorPut, VectorSearchRequest, VectorSearchResult,
    TextIngestionRequest, TextIngestionResponse,
    TextSearchRequest, TextSearchResult
)
from .service import VastObjectVectorService
from ..core.dependencies import get_vast_db, get_s3_client
from ..objects.service import ObjectStorageService
from ..auth.rbac import require_viewer, require_editor
from ..auth.middleware import UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vast/objects", tags=["vast"])


def get_vast_object_vector_service() -> VastObjectVectorService:
    """Get VAST object vector service instance"""
    return VastObjectVectorService(
        vast_db=get_vast_db(),
        s3_client=get_s3_client()
    )


def get_object_storage_service() -> ObjectStorageService:
    """Get object storage service instance"""
    return ObjectStorageService(
        vast_db=get_vast_db(),
        s3_client=get_s3_client()
    )


@router.put("/{object_id}/vector")
async def update_object_vector(
    object_id: str,
    vector_data: ObjectVectorPut = Body(...),
    service: VastObjectVectorService = Depends(get_vast_object_vector_service),
    user_session: UserSession = Depends(require_editor)
):
    """
    Update or insert vector data for an object.
    
    This endpoint allows storing vector embeddings along with
    optional summary and embedding model information.
    Vector dimension is determined by configured embedding model.
    """
    try:
        # Vector dimension is validated in ObjectVectorPut model
        # Update vector
        success = await service.update_vector(
            entity_id=object_id,
            entity_type="object",
            vector=vector_data.vector,
            summary=vector_data.summary,
            embedding_model=vector_data.embedding_model
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update object vector")
        
        return {"message": "Vector updated successfully", "object_id": object_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update vector for object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vector/search", response_model=VectorSearchResult)
async def search_vectors(
    search_request: VectorSearchRequest = Body(...),
    service: VastObjectVectorService = Depends(get_vast_object_vector_service),
    user_session: UserSession = Depends(require_viewer)
):
    """
    Perform vector similarity search.
    
    This endpoint searches for objects with similar vectors and returns
    related object_ids, segment_ids, flow_ids, and source_ids.
    """
    try:
        from ..core.config import get_settings
        settings = get_settings()
        expected_dim = settings.embedding_model_dimension
        
        # Validate vector length (already validated in model, but double-check)
        if len(search_request.vector) != expected_dim:
            raise HTTPException(
                status_code=400,
                detail=f"Query vector must be exactly {expected_dim} dimensions, got {len(search_request.vector)}"
            )
        
        # Perform search
        # Cast entity_types to EntityType list if provided
        from .service import EntityType
        entity_types: Optional[List[EntityType]] = None
        if search_request.entity_types:
            entity_types = cast(List[EntityType], search_request.entity_types)
        
        results = await service.search_vectors(
            query_vector=search_request.vector,
            num_matches=search_request.num_matches,
            distance_metric=search_request.distance_metric,
            distance_numerical_value=search_request.distance_numerical_value,
            entity_types=entity_types
        )
        
        return VectorSearchResult(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform vector search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ingest", response_model=TextIngestionResponse)
async def ingest_text(
    ingestion_request: TextIngestionRequest = Body(...),
    service: VastObjectVectorService = Depends(get_vast_object_vector_service),
    user_session: UserSession = Depends(require_editor)
):
    """
    Ingest text, convert to embedding vector, and store in VAST database.
    
    This endpoint accepts text input, converts it to an embedding vector using
    the configured embedding service, and stores it in the vectors table
    associated with the specified entity.
    """
    try:
        # Ingest text and create vector
        # Cast entity_type to EntityType
        from .service import EntityType
        entity_type = cast(EntityType, ingestion_request.entity_type)
        
        result = await service.ingest_text(
            text=ingestion_request.text,
            entity_id=ingestion_request.entity_id,
            entity_type=entity_type,
            embedding_model=ingestion_request.embedding_model
        )
        
        return TextIngestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest text: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search/text", response_model=TextSearchResult)
async def search_by_text(
    search_request: TextSearchRequest = Body(...),
    service: VastObjectVectorService = Depends(get_vast_object_vector_service),
    user_session: UserSession = Depends(require_viewer)
):
    """
    Search vectors by text query.
    
    This endpoint accepts text input, converts it to an embedding vector,
    performs vector similarity search, and returns matching entities with
    similarity scores.
    """
    try:
        # Perform text-based vector search
        # Cast entity_types to EntityType list if provided
        from .service import EntityType
        entity_types: Optional[List[EntityType]] = None
        if search_request.entity_types:
            entity_types = cast(List[EntityType], search_request.entity_types)
        
        result = await service.search_by_text(
            text=search_request.text,
            entity_types=entity_types,
            limit=search_request.limit,
            distance_threshold=search_request.distance_threshold,
            distance_metric=search_request.distance_metric
        )
        
        return TextSearchResult(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search by text: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{object_id}/summary")
async def get_object_summary(
    object_id: str,
    service: ObjectStorageService = Depends(get_object_storage_service),
    user_session: UserSession = Depends(require_viewer)
):
    """
    Get summary for an object (VAST extension, not part of TAMS spec).
    
    This endpoint retrieves the summary field which is managed separately
    from TAMS-compliant object endpoints.
    """
    try:
        summary = await service.get_object_summary(object_id)
        return {"object_id": object_id, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary for object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{object_id}/summary")
async def update_object_summary(
    object_id: str,
    request_body: dict = Body(...),
    service: ObjectStorageService = Depends(get_object_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """
    Update summary for an object (VAST extension, not part of TAMS spec).
    
    This endpoint allows setting or clearing the summary field which is
    managed separately from TAMS-compliant object endpoints.
    
    Body:
        {
            "summary": "optional string"  // If provided, sets the summary. If null or omitted, clears it.
        }
    """
    try:
        summary = request_body.get("summary") if isinstance(request_body, dict) else None
        success = await service.update_object_summary(object_id, summary)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update object summary")
        return {"message": "Summary updated successfully", "object_id": object_id, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update summary for object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

