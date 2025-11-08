"""
Webhooks Module for TAMS API

This module provides database-backed webhook management following the TAMS 8.0 specification.
"""

from .models import Webhook, WebhookPost, WebhookUpdate
from .router import router
from .service import WebhookService
from .schemas import get_webhooks_schema, get_webhooks_projections

__all__ = [
    "Webhook",
    "WebhookPost", 
    "WebhookUpdate",
    "router",
    "WebhookService",
    "get_webhooks_schema",
    "get_webhooks_projections",
]

