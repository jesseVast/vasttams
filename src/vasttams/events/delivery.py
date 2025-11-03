"""
Event Delivery Mechanisms

This module provides pluggable event delivery implementations
supporting webhooks, Kafka, SSE, and other mechanisms.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from ..webhooks.models import Webhook

logger = logging.getLogger(__name__)


def _serialize_datetime(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    else:
        return obj


class EventDeliveryInterface(ABC):
    """Abstract interface for event delivery mechanisms"""
    
    @abstractmethod
    async def deliver(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Deliver an event
        
        Args:
            event_type: Type of event (e.g., 'flows/created')
            event_data: Event data payload
            
        Returns:
            bool: True if delivery was successful
        """
        pass


class WebhookDelivery(EventDeliveryInterface):
    """Webhook-based event delivery"""
    
    def __init__(self, webhook: Webhook):
        self.webhook = webhook
    
    async def deliver(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Deliver event via HTTP POST to webhook URL"""
        try:
            # Serialize datetime objects to ISO format strings
            serialized_event_data = _serialize_datetime(event_data)
            
            payload = {
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "event": serialized_event_data
            }
            
            headers = {
                "Content-Type": "application/json",
                self.webhook.api_key_name: self.webhook.api_key_value or ""
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.webhook.url, json=payload, headers=headers)
                return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False


class MultipleDelivery(EventDeliveryInterface):
    """Deliver events to multiple mechanisms"""
    
    def __init__(self, mechanisms: List[EventDeliveryInterface]):
        self.mechanisms = mechanisms
    
    async def deliver(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Deliver event to all configured mechanisms"""
        results = []
        for mechanism in self.mechanisms:
            try:
                result = await mechanism.deliver(event_type, event_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Delivery mechanism failed: {e}")
                results.append(False)
        
        # Return True if at least one delivery succeeded
        return any(results)

