"""
Event Manager for TAMS API

Handles event emission and delivery to multiple mechanisms (webhooks, Kafka, etc.)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio

from .models import Event, EventData, SourceEventData, FlowEventData, FlowSegmentEventData, ObjectEventData, CollectionEventData
from .delivery import EventDeliveryInterface, WebhookDelivery, MultipleDelivery

logger = logging.getLogger(__name__)


class EventManager:
    """Manages event emission and delivery to multiple mechanisms"""
    
    def __init__(self, vast_db, delivery_mechanisms: Optional[List[EventDeliveryInterface]] = None):
        """
        Initialize EventManager
        
        Args:
            vast_db: VAST database connection
            delivery_mechanisms: List of pre-configured delivery mechanisms
        """
        self.vast_db = vast_db
        
        # Initialize delivery mechanisms
        self.delivery_mechanisms = delivery_mechanisms or []
        
        # Webhook cache
        self._webhook_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 60  # Cache webhooks for 60 seconds
    
    async def _get_webhooks(self) -> List[Dict[str, Any]]:
        """Get webhooks from database with caching"""
        now = datetime.now(timezone.utc)
        
        # Return cached webhooks if still valid
        if (self._webhook_cache is not None and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl):
            return self._webhook_cache
        
        try:
            from ..webhooks.service import WebhookService
            webhook_service = WebhookService(self.vast_db)
            webhooks = await webhook_service.get_webhooks()
            
            # Convert Webhook models to dicts for filtering
            webhook_dicts = []
            for webhook in webhooks:
                webhook_dict = webhook.model_dump() if hasattr(webhook, 'model_dump') else webhook.dict()
                webhook_dicts.append(webhook_dict)
            
            self._webhook_cache = webhook_dicts
            self._cache_timestamp = now
            return webhook_dicts
        except Exception as e:
            logger.error("Failed to fetch webhooks: %s", e)
            return []
    
    def _should_send_to_webhook(self, webhook: Dict[str, Any], event_type: str, event_data: EventData) -> bool:
        """Check if webhook should receive this event based on filtering rules"""
        
        # Check if webhook is enabled
        if not webhook.get('enabled', True):
            return False
        
        # Check if webhook is subscribed to this event type
        events = webhook.get('events', [])
        if isinstance(events, str):
            import json
            try:
                events = json.loads(events)
            except json.JSONDecodeError:
                return False
        
        if event_type not in events:
            return False
        
        # Check flow ID filtering
        flow_ids = webhook.get('flow_ids', [])
        if flow_ids:
            if isinstance(flow_ids, str):
                import json
                try:
                    flow_ids = json.loads(flow_ids)
                except json.JSONDecodeError:
                    flow_ids = []
            if hasattr(event_data, 'flow_id') and event_data.flow_id not in flow_ids:
                return False
        
        # Check source ID filtering
        source_ids = webhook.get('source_ids', [])
        if source_ids:
            if isinstance(source_ids, str):
                import json
                try:
                    source_ids = json.loads(source_ids)
                except json.JSONDecodeError:
                    source_ids = []
            if hasattr(event_data, 'source_id') and event_data.source_id not in source_ids:
                return False
        
        return True
    
    async def emit_event(self, event: Event) -> None:
        """
        Emit an event to all configured delivery mechanisms
        
        Args:
            event: Event to emit
        """
        try:
            # Convert event data to dict
            event_data_dict = event.data.model_dump() if hasattr(event.data, 'model_dump') else event.data.dict()
            
            # Deliver to configured mechanisms (Kafka, etc.)
            for mechanism in self.delivery_mechanisms:
                try:
                    await mechanism.deliver(event.event_type, event_data_dict)
                except Exception as e:
                    logger.error(f"Failed to deliver event via mechanism: {e}")
            
            # Also deliver to webhooks if configured
            await self._deliver_to_webhooks(event.event_type, event.data)
            
        except Exception as e:
            logger.error("Error emitting event %s: %s", event.event_type, e)
    
    async def _deliver_to_webhooks(self, event_type: str, event_data: EventData) -> None:
        """Deliver event to webhooks"""
        try:
            webhooks = await self._get_webhooks()
            
            if not webhooks:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("No webhooks registered for event %s", event_type)
                return
            
            # Filter webhooks based on event type and filtering rules
            relevant_webhooks = [
                webhook for webhook in webhooks
                if self._should_send_to_webhook(webhook, event_type, event_data)
            ]
            
            if not relevant_webhooks:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("No relevant webhooks for event %s", event_type)
                return
            
            # Send to webhooks using WebhookDelivery
            for webhook_dict in relevant_webhooks:
                try:
                    from ..webhooks.models import Webhook
                    webhook = Webhook(**webhook_dict)
                    delivery = WebhookDelivery(webhook)
                    event_data_dict = event_data.model_dump() if hasattr(event_data, 'model_dump') else event_data.dict()
                    
                    success = await delivery.deliver(event_type, event_data_dict)
                    if success:
                        logger.info("Event %s sent to webhook %s", event_type, webhook.url)
                    else:
                        logger.warning("Failed to send event %s to webhook %s", event_type, webhook.url)
                except Exception as e:
                    logger.error("Error sending event %s to webhook: %s", event_type, e)
            
        except Exception as e:
            logger.error("Error delivering to webhooks: %s", e)
    
    async def emit_source_event(self, event_type: str, source: Any, user_id: Optional[str] = None) -> None:
        """Emit a source-related event"""
        try:
            event_data = SourceEventData(
                event_type=event_type,
                entity_id=str(source.id),
                source_id=str(source.id),
                user_id=user_id,
                label=getattr(source, 'label', None),
                format=getattr(source, 'format', None),
                tags=getattr(source, 'tags', {}).root if hasattr(source, 'tags') and source.tags else None,
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating source event %s: %s", event_type, e)
    
    async def emit_flow_event(self, event_type: str, flow: Any, user_id: Optional[str] = None) -> None:
        """Emit a flow-related event"""
        try:
            event_data = FlowEventData(
                event_type=event_type,
                entity_id=str(flow.id),
                flow_id=str(flow.id),
                source_id=str(flow.source_id),
                user_id=user_id,
                label=getattr(flow, 'label', None),
                format=getattr(flow, 'format', None),
                codec=getattr(flow, 'codec', None),
                tags=getattr(flow, 'tags', {}).root if hasattr(flow, 'tags') and flow.tags else None,
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating flow event %s: %s", event_type, e)
    
    async def emit_segment_event(self, event_type: str, segment: Any, user_id: Optional[str] = None, flow_id: Optional[str] = None) -> None:
        """Emit a flow segment-related event"""
        try:
            event_data = FlowSegmentEventData(
                event_type=event_type,
                entity_id=str(segment.object_id),
                segment_id=str(segment.object_id),
                flow_id=flow_id or str(segment.flow_id) if hasattr(segment, 'flow_id') else None,
                object_id=str(segment.object_id),
                timerange=getattr(segment, 'timerange', None),
                tags=getattr(segment, 'tags', {}).root if hasattr(segment, 'tags') and segment.tags else None,
                user_id=user_id
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
            # Handle loop recorder (async - don't block event emission)
            if event_type == 'flow-segments/created' and event_data.flow_id:
                asyncio.create_task(self._handle_loop_recorder(event_data.flow_id))
            
        except Exception as e:
            logger.error("Error creating segment event %s: %s", event_type, e)
    
    async def _handle_loop_recorder(self, flow_id: str):
        """Handle loop recorder check (called as background task)"""
        try:
            from ..looprecorder import LoopRecorderManager
            loop_recorder = LoopRecorderManager(self.vast_db)
            await loop_recorder.process_flow(flow_id)
        except Exception as e:
            logger.debug("Loop recorder check skipped for flow %s: %s", flow_id, e)
    
    async def emit_object_event(self, event_type: str, obj: Any, user_id: Optional[str] = None) -> None:
        """Emit an object-related event"""
        try:
            event_data = ObjectEventData(
                event_type=event_type,
                entity_id=str(obj.id),
                object_id=str(obj.id),
                user_id=user_id,
                size=getattr(obj, 'size', None),
                referenced_by_flows=getattr(obj, 'referenced_by_flows', []),
                tags=getattr(obj, 'tags', {}).root if hasattr(obj, 'tags') and obj.tags else None,
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
                event_type=event_type,
                entity_id=str(collection.collection_id),
                collection_id=str(collection.collection_id),
                collection_type=collection_type,
                user_id=user_id,
                label=getattr(collection, 'label', None),
                member_count=None,  # TODO: Calculate member count
                tags=None,  # TODO: Add collection tags if implemented
            )
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating collection event %s: %s", event_type, e)
    
    def clear_cache(self) -> None:
        """Clear the webhook cache"""
        self._webhook_cache = None
        self._cache_timestamp = None
    
    async def close(self) -> None:
        """Close event manager and cleanup resources"""
        for mechanism in self.delivery_mechanisms:
            if hasattr(mechanism, 'close'):
                await mechanism.close()

