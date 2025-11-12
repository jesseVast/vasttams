"""
Storage Backend Router

This module provides API endpoints for managing storage backends.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List
from .models import StorageBackend, StorageBackendPost, StorageBackendPatch, StorageBackendsList
from .service import StorageBackendService
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tams/v8.0/service/storage-backends", tags=["storage-backends"])


def get_storage_backend_service() -> StorageBackendService:
    """Dependency to get storage backend service"""
    # This will be injected - we need to get from storage service
    from ..common.storage.dependencies import get_storage_service
    storage_service = get_storage_service()
    return StorageBackendService(storage_service.vast_db, storage_service.s3_client)


@router.head("")
async def head_storage_backends():
    """Return storage backends path headers"""
    return {}


@router.get("", response_model=List[StorageBackend])
async def list_storage_backends(
    service: StorageBackendService = Depends(get_storage_backend_service)
):
    """Get all storage backends"""
    return await service.get_storage_backends()


@router.post("", response_model=StorageBackend, status_code=201)
async def create_storage_backend(
    backend: StorageBackendPost,
    service: StorageBackendService = Depends(get_storage_backend_service),
    user_session: UserSession = Depends(require_admin)
):
    """Create a new storage backend"""
    return await service.create_storage_backend(backend)


@router.head("/{backend_id}")
async def head_storage_backend(backend_id: str):
    """Return storage backend path headers"""
    return {}


@router.get("/{backend_id}", response_model=StorageBackend)
async def get_storage_backend(
    backend_id: str,
    service: StorageBackendService = Depends(get_storage_backend_service),
    user_session: UserSession = Depends(require_viewer)
):
    """Get a specific storage backend by ID"""
    backend = await service.get_storage_backend(backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="Storage backend not found")
    return backend


@router.put("/{backend_id}", response_model=StorageBackend)
async def update_storage_backend(
    backend_id: str,
    backend: StorageBackendPatch,
    service: StorageBackendService = Depends(get_storage_backend_service),
    user_session: UserSession = Depends(require_admin)
):
    """Update a storage backend"""
    return await service.update_storage_backend(backend_id, backend)


@router.delete("/{backend_id}")
async def delete_storage_backend(
    backend_id: str,
    service: StorageBackendService = Depends(get_storage_backend_service),
    user_session: UserSession = Depends(require_admin)
):
    """Delete a storage backend (only if no objects reference it)"""
    success = await service.delete_storage_backend(backend_id)
    if not success:
        logger.debug("Storage backend %s deletion returned False, raising 404", backend_id)
        raise HTTPException(status_code=404, detail="Storage backend not found")
    return Response(status_code=204)

