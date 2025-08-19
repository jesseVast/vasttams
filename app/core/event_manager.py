"""
Event Manager for TAMS API

Handles event emission, webhook filtering, and notification delivery
for TAMS event streaming compliance.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.models import (
    Event, EventData, SourceEventData, FlowEventData, FlowSegmentEventData,
    ObjectEventData, CollectionEventData, Webhook
)
# Note: VASTStore imported via string to avoid circular import
from .utils import send_webhook_notification

logger = logging.getLogger(__name__)


class EventManager:
    """Manages event emission and webhook notifications for TAMS compliance"""
    
    def __init__(self, store: "VASTStore"):
        self.store = store
        self._webhook_cache: Optional[List[Webhook]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 60  # Cache webhooks for 60 seconds
    
    async def _get_webhooks(self) -> List[Webhook]:
        """Get webhooks with caching for performance"""
        now = datetime.now(timezone.utc)
        
        # Return cached webhooks if still valid
        if (self._webhook_cache is not None and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl):
            return self._webhook_cache
        
        try:
            webhooks = await self.store.list_webhooks()
            self._webhook_cache = webhooks
            self._cache_timestamp = now
            return webhooks
        except Exception as e:
            logger.error("Failed to fetch webhooks: %s", e)
            return []
    
    def _should_send_to_webhook(self, webhook: Webhook, event_type: str, event_data: EventData) -> bool:
        """Check if webhook should receive this event based on filtering rules"""
        
        # Check if webhook is subscribed to this event type
        if event_type not in webhook.events:
            return False
        
        # Check flow ID filtering
        if webhook.flow_ids and hasattr(event_data, 'flow_id'):
            if event_data.flow_id not in webhook.flow_ids:
                return False
        
        # Check source ID filtering
        if webhook.source_ids and hasattr(event_data, 'source_id'):
            if event_data.source_id not in webhook.source_ids:
                return False
        
        # Check flow collection filtering
        if webhook.flow_collected_by_ids and hasattr(event_data, 'flow_id'):
            # TODO: Implement flow collection membership check
            pass
        
        # Check source collection filtering
        if webhook.source_collected_by_ids and hasattr(event_data, 'source_id'):
            # TODO: Implement source collection membership check
            pass
        
        return True
    
    async def emit_event(self, event: Event) -> None:
        """Emit an event to all relevant webhooks"""
        try:
            webhooks = await self._get_webhooks()
            
            if not webhooks:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("No webhooks registered for event %s", event.event_type)
                return
            
            # Filter webhooks based on event type and filtering rules
            relevant_webhooks = [
                webhook for webhook in webhooks
                if self._should_send_to_webhook(webhook, event.event_type, event.data)
            ]
            
            if not relevant_webhooks:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("No relevant webhooks for event %s", event.event_type)
                return
            
            # Send notifications to relevant webhooks
            for webhook in relevant_webhooks:
                try:
                    success = await send_webhook_notification(
                        webhook, 
                        event.event_type, 
                        event.data.model_dump()
                    )
                    if success:
                        logger.info("Event %s sent to webhook %s", event.event_type, webhook.url)
                    else:
                        logger.warning("Failed to send event %s to webhook %s", event.event_type, webhook.url)
                except Exception as e:
                    logger.error("Error sending event %s to webhook %s: %s", 
                               event.event_type, webhook.url, e)
            
        except Exception as e:
            logger.error("Error emitting event %s: %s", event.event_type, e)
    
    async def emit_source_event(self, event_type: str, source: Any, user_id: Optional[str] = None) -> None:
        """Emit a source-related event"""
        try:
            event_data = SourceEventData(
                entity_id=str(source.id),
                source_id=str(source.id),
                label=getattr(source, 'label', None),
                format=getattr(source, 'format', None),
                tags=getattr(source, 'tags', {}).root if hasattr(source, 'tags') and source.tags else None,
                user_id=user_id
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating source event %s: %s", event_type, e)
    
    async def emit_flow_event(self, event_type: str, flow: Any, user_id: Optional[str] = None) -> None:
        """Emit a flow-related event"""
        try:
            event_data = FlowEventData(
                entity_id=str(flow.id),
                flow_id=str(flow.id),
                source_id=str(flow.source_id),
                label=getattr(flow, 'label', None),
                format=getattr(flow, 'format', None),
                codec=getattr(flow, 'codec', None),
                tags=getattr(flow, 'tags', {}).root if hasattr(flow, 'tags') and flow.tags else None,
                user_id=user_id
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating flow event %s: %s", event_type, e)
    
    async def emit_segment_event(self, event_type: str, segment: Any, user_id: Optional[str] = None) -> None:
        """Emit a flow segment-related event"""
        try:
            event_data = FlowSegmentEventData(
                entity_id=str(segment.id),
                segment_id=str(segment.id),
                flow_id=str(segment.flow_id),
                object_id=str(segment.object_id),
                timerange=getattr(segment, 'timerange', None),
                tags=getattr(segment, 'tags', {}).root if hasattr(segment, 'tags') and segment.tags else None,
                user_id=user_id
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating segment event %s: %s", event_type, e)
    
    async def emit_object_event(self, event_type: str, obj: Any, user_id: Optional[str] = None) -> None:
        """Emit an object-related event"""
        try:
            event_data = ObjectEventData(
                entity_id=str(obj.id),
                object_id=str(obj.id),
                size=getattr(obj, 'size', None),
                referenced_by_flows=getattr(obj, 'referenced_by_flows', []),
                tags=getattr(obj, 'tags', {}).root if hasattr(obj, 'tags') and obj.tags else None,
                user_id=user_id
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating object event %s: %s", event_type, e)
    
    async def emit_collection_event(self, event_type: str, collection: Any, collection_type: str, 
                                  user_id: Optional[str] = None) -> None:
        """Emit a collection-related event"""
        try:
            event_data = CollectionEventData(
                entity_id=str(collection.collection_id),
                collection_id=str(collection.collection_id),
                collection_type=collection_type,
                label=getattr(collection, 'label', None),
                member_count=None,  # TODO: Calculate member count
                tags=None,  # TODO: Add collection tags if implemented
                user_id=user_id
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating collection event %s: %s", event_type, e)
    
    def clear_cache(self) -> None:
        """Clear the webhook cache"""
        self._webhook_cache = None
        self._cache_timestamp = None
