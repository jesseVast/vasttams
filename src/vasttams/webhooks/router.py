"""
Webhook Router

This module defines FastAPI routes for webhook management.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response

from ..core.dependencies import get_vast_db
from .models import Webhook, WebhookPost, WebhookUpdate
from .service import WebhookService
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession

logger = logging.getLogger(__name__)

router = APIRouter()


def get_webhook_service(vast_db=Depends(get_vast_db)) -> WebhookService:
    """Get webhook service instance"""
    return WebhookService(vast_db)


@router.get("/service/webhooks", response_model=List[Webhook])
async def list_webhooks(service: WebhookService = Depends(get_webhook_service)):
    """List all webhooks"""
    return await service.get_webhooks()


@router.head("/service/webhooks")
async def head_webhooks():
    """Return webhooks path headers"""
    return Response()


@router.post("/service/webhooks", response_model=Webhook, status_code=201)
async def create_webhook(
    webhook: WebhookPost = Body(...),
    service: WebhookService = Depends(get_webhook_service)
):
    """Create a new webhook"""
    try:
        return await service.create_webhook(webhook)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create webhook: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/service/webhooks/{webhook_id}", response_model=Webhook)
async def get_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service),
    user_session: UserSession = Depends(require_viewer)
):
    """Get a specific webhook by ID"""
    webhook = await service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.put("/service/webhooks/{webhook_id}", response_model=Webhook)
async def update_webhook(
    webhook_id: str,
    webhook_update: WebhookUpdate = Body(...),
    service: WebhookService = Depends(get_webhook_service)
):
    """Update a webhook"""
    try:
        return await service.update_webhook(webhook_id, webhook_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update webhook: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/service/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service),
    user_session: UserSession = Depends(require_admin)
):
    """Delete a webhook"""
    try:
        await service.delete_webhook(webhook_id)
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete webhook: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

