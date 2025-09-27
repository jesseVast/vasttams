"""
Service API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models import Service, StorageBackend, Webhook, WebhookPost
from ..storage import get_storage_service
from ..storage.interfaces import StorageInterface
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service", tags=["service"])

@router.head("")
async def head_service():
    """Return service path headers"""
    return {}

@router.get("")
async def get_service(
    storage: StorageInterface = Depends(get_storage_service)
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

@router.head("/storage-backends")
async def head_storage_backends():
    """Return storage backends path headers"""
    return {}

@router.get("/storage-backends")
async def get_storage_backends(
    storage: StorageInterface = Depends(get_storage_service)
):
    """Provide information about the storage backends available on this service instance"""
    try:
        storage_backends = await storage.get_storage_backends()
        return storage_backends
    except Exception as e:
        logger.error("Failed to get storage backends: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/webhooks")
async def head_webhooks():
    """Return webhooks path headers"""
    return {}

@router.get("/webhooks")
async def get_webhooks(
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get the list of registered webhook URLs"""
    try:
        webhooks = await storage.get_webhooks()
        return webhooks
    except Exception as e:
        logger.error("Failed to get webhooks: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhooks")
async def create_webhook(
    webhook: WebhookPost,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Register a webhook URL"""
    try:
        created_webhook = await storage.create_webhook(webhook)
        return created_webhook
    except Exception as e:
        logger.error("Failed to create webhook: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete a webhook"""
    try:
        success = await storage.delete_webhook(webhook_id)
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return {"message": "Webhook deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete webhook: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
