"""
Service API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .models import Service
from .storage_models import StorageBackend
from .webhooks import Webhook, WebhookPost
from ..common.storage.dependencies import get_storage_service
from ..common.storage.interfaces import StorageInterface
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service", tags=["service"])

@router.head("")
async def head_service():
    """Return service path headers"""
    return {}

@router.get("")
async def get_service(
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_viewer)
):
    """Provide information about the service"""
    try:
        service_info = await storage.get_service_info()
        return service_info
    except Exception as e:
        logger.error("Failed to get service info: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("")
async def update_service(
    service: Service,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update the service info"""
    try:
        # For now, just return the service info as-is
        # In a real implementation, this would update the service configuration
        return service
    except Exception as e:
        logger.error("Failed to update service info: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Storage backends endpoints moved to dedicated storage_backends_router
# They are now at /service/storage-backends via the dedicated module

# Webhooks endpoints moved to dedicated webhooks_router
# They are now at /service/webhooks via the dedicated module

