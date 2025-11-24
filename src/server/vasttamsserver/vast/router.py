"""
VAST Objects Router

This router handles VAST-specific object extensions that are outside the TAMS specification.
Routes are under /api/vast/objects to clearly distinguish from TAMS-compliant endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional
import logging

from .models import ObjectVectorPut, VectorSearchRequest, VectorSearchResult
from .service import VastObjectVectorService
from ..core.dependencies import get_vast_db, get_s3_client
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
        results = await service.search_vectors(
            query_vector=search_request.vector,
            num_matches=search_request.num_matches,
            distance_metric=search_request.distance_metric,
            distance_numerical_value=search_request.distance_numerical_value,
            entity_types=search_request.entity_types
        )
        
        return VectorSearchResult(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform vector search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

