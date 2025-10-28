"""
Events Module for TAMS API

This module provides event emission, management, and delivery for TAMS compliance.
Supports multiple delivery mechanisms (webhooks, Kafka, SSE, etc.).
"""

from .models import Event, EventData, SourceEventData, FlowEventData, FlowSegmentEventData, ObjectEventData, CollectionEventData, EventStreamMechanism
from .manager import EventManager
from .delivery import EventDeliveryInterface, WebhookDelivery

__all__ = [
    # Models
    "Event",
    "EventData",
    "SourceEventData",
    "FlowEventData",
    "FlowSegmentEventData",
    "ObjectEventData",
    "CollectionEventData",
    "EventStreamMechanism",
    # Manager
    "EventManager",
    # Delivery
    "EventDeliveryInterface",
    "WebhookDelivery",
]

