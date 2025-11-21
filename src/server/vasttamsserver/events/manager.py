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

# Global webhook cache shared across all EventManager instances
_global_webhook_cache: Optional[List[Dict[str, Any]]] = None
_global_cache_timestamp: Optional[datetime] = None
_global_cache_ttl = 60  # Cache webhooks for 60 seconds


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
    
    async def _get_webhooks(self) -> List[Dict[str, Any]]:
        """Get webhooks from database with global caching (shared across all EventManager instances)"""
        global _global_webhook_cache, _global_cache_timestamp, _global_cache_ttl
        
        now = datetime.now(timezone.utc)
        
        # Return cached webhooks if still valid (using global cache)
        if (_global_webhook_cache is not None and 
            _global_cache_timestamp and 
            (now - _global_cache_timestamp).total_seconds() < _global_cache_ttl):
            return _global_webhook_cache
        
        try:
            from ..webhooks.service import WebhookService
            # Extract vast_db if self.vast_db is a TAMSStorageService
            vast_db = self.vast_db
            if hasattr(self.vast_db, 'vast_db'):
                # It's a TAMSStorageService, extract the actual vast_db
                vast_db = self.vast_db.vast_db
            
            webhook_service = WebhookService(vast_db)
            webhooks = await webhook_service.get_webhooks()
            
            # Convert Webhook models to dicts for filtering
            webhook_dicts = []
            for webhook in webhooks:
                webhook_dict = webhook.model_dump() if hasattr(webhook, 'model_dump') else webhook.dict()
                webhook_dicts.append(webhook_dict)
            
            # Update global cache (shared across all instances)
            _global_webhook_cache = webhook_dicts
            _global_cache_timestamp = now
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
    
    def _format_event_for_spec(self, event_type: str, event_data: EventData) -> Dict[str, Any]:
        """
        Format event data according to TAMS 8.0 webhook spec.
        
        The spec requires:
        - flows/created, flows/updated: event.flow (full Flow object)
        - flows/deleted: event.flow_id
        - flows/segments_added: event.flow_id, event.segments (array)
        - flows/segments_deleted: event.flow_id, event.timerange
        - sources/created, sources/updated: event.source (full Source object)
        - sources/deleted: event.source_id
        """
        # Convert EventData to dict first
        event_data_dict = event_data.model_dump() if hasattr(event_data, 'model_dump') else event_data.dict()
        
        if event_type in ['flows/created', 'flows/updated']:
            # For created/updated, use full Flow object if available
            flow_obj = getattr(event_data, '_flow_object', None)
            if flow_obj:
                # Convert Flow object to dict
                if hasattr(flow_obj, 'model_dump'):
                    flow_dict = flow_obj.model_dump()
                elif hasattr(flow_obj, 'dict'):
                    flow_dict = flow_obj.dict()
                elif isinstance(flow_obj, dict):
                    flow_dict = flow_obj
                else:
                    # Fallback: try to convert to dict
                    flow_dict = dict(flow_obj) if hasattr(flow_obj, '__dict__') else event_data_dict
                return {"flow": flow_dict}
            else:
                # Fallback to event_data if flow object not available
                return {"flow": event_data_dict}
        elif event_type == 'flows/deleted':
            return {
                "flow_id": event_data_dict.get('flow_id') or event_data_dict.get('entity_id')
            }
        elif event_type == 'flows/segments_added':
            return {
                "flow_id": event_data_dict.get('flow_id'),
                "segments": event_data_dict.get('segments', [])  # Should be array of flow-segment objects
            }
        elif event_type == 'flows/segments_deleted':
            return {
                "flow_id": event_data_dict.get('flow_id'),
                "timerange": event_data_dict.get('timerange')
            }
        elif event_type in ['sources/created', 'sources/updated']:
            # For created/updated, use full Source object if available
            source_obj = getattr(event_data, '_source_object', None)
            if source_obj:
                # Convert Source object to dict
                if hasattr(source_obj, 'model_dump'):
                    source_dict = source_obj.model_dump()
                elif hasattr(source_obj, 'dict'):
                    source_dict = source_obj.dict()
                elif isinstance(source_obj, dict):
                    source_dict = source_obj
                else:
                    # Fallback: try to convert to dict
                    source_dict = dict(source_obj) if hasattr(source_obj, '__dict__') else event_data_dict
                return {"source": source_dict}
            else:
                # Fallback to event_data if source object not available
                return {"source": event_data_dict}
        elif event_type == 'sources/deleted':
            return {
                "source_id": event_data_dict.get('source_id') or event_data_dict.get('entity_id')
            }
        else:
            # Fallback to original structure for unknown event types
            return event_data_dict
    
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
                logger.debug("No webhooks registered for event %s", event_type)
                return
            
            logger.debug("Found %d webhook(s) for event %s", len(webhooks), event_type)
            
            # Filter webhooks based on event type and filtering rules
            relevant_webhooks = [
                webhook for webhook in webhooks
                if self._should_send_to_webhook(webhook, event_type, event_data)
            ]
            
            if not relevant_webhooks:
                logger.debug("No relevant webhooks for event %s (checked %d webhooks)", event_type, len(webhooks))
                return
            
            logger.debug("Delivering event %s to %d webhook(s)", event_type, len(relevant_webhooks))
            
            # Send to webhooks using WebhookDelivery
            for webhook_dict in relevant_webhooks:
                try:
                    from ..webhooks.models import Webhook
                    webhook = Webhook(**webhook_dict)
                    delivery = WebhookDelivery(webhook)
                    
                    # Convert event data to spec-compliant format
                    # TAMS spec requires: event.flow, event.source, etc.
                    spec_compliant_event = self._format_event_for_spec(event_type, event_data)
                    
                    success = await delivery.deliver(event_type, spec_compliant_event)
                    if success:
                        logger.debug("Event %s sent to webhook %s", event_type, webhook.url)
                    else:
                        logger.warning("Failed to send event %s to webhook %s", event_type, webhook.url)
                except Exception as e:
                    logger.error("Error sending event %s to webhook: %s", event_type, e)
            
        except Exception as e:
            logger.error("Error delivering to webhooks: %s", e)
    
    async def emit_source_event(self, event_type: str, source: Any, user_id: Optional[str] = None) -> None:
        """Emit a source-related event"""
        try:
            # Store the full source object for spec-compliant webhook payload
            event_data = SourceEventData(
                event_type=event_type,
                entity_id=str(source.id),
                source_id=str(source.id),
                user_id=user_id,
                label=getattr(source, 'label', None),
                format=getattr(source, 'format', None),
                tags=getattr(source, 'tags', {}).root if hasattr(source, 'tags') and source.tags else None,
            )
            # Store full source object for webhook delivery
            event_data._source_object = source
            
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
            # Store full flow object for webhook delivery
            event_data._flow_object = flow
            
            event = Event(event_type=event_type, data=event_data)
            await self.emit_event(event)
            
        except Exception as e:
            logger.error("Error creating flow event %s: %s", event_type, e)
    
    async def emit_segment_event(self, event_type: str, segment: Any, user_id: Optional[str] = None, flow_id: Optional[str] = None) -> None:
        """Emit a flow segment-related event"""
        try:
            # Normalize flow_id and timerange to match event model expectations
            normalized_flow_id: Optional[str] = None
            if flow_id:
                normalized_flow_id = str(flow_id)
            elif hasattr(segment, 'flow_id') and getattr(segment, 'flow_id') is not None:
                normalized_flow_id = str(getattr(segment, 'flow_id'))
            
            # Convert timerange model to dict payload if needed
            timerange_payload: Optional[Dict[str, Any]] = None
            seg_timerange = getattr(segment, 'timerange', None)
            if seg_timerange is not None:
                try:
                    # Pydantic model with model_dump
                    if hasattr(seg_timerange, 'model_dump'):
                        timerange_payload = seg_timerange.model_dump()
                    # Has 'value' attribute
                    elif hasattr(seg_timerange, 'value'):
                        timerange_payload = {"value": getattr(seg_timerange, 'value')}
                    # Already a dict-like
                    elif isinstance(seg_timerange, dict):
                        timerange_payload = seg_timerange
                    else:
                        timerange_payload = {"value": str(seg_timerange)}
                except Exception:
                    timerange_payload = None

            event_data = FlowSegmentEventData(
                event_type=event_type,
                entity_id=str(segment.object_id),
                segment_id=str(segment.object_id),
                flow_id=normalized_flow_id,
                object_id=str(segment.object_id),
                timerange=timerange_payload,
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
            from ..core.dependencies import get_s3_client
            from ..core.config import get_settings
            
            # Extract vast_db if self.vast_db is a TAMSStorageService
            vast_db = self.vast_db
            if hasattr(self.vast_db, 'vast_db'):
                # It's a TAMSStorageService, extract the actual vast_db
                vast_db = self.vast_db.vast_db
            
            # Get s3_client and settings for LoopRecorderManager
            try:
                s3_client = get_s3_client()
            except Exception as e:
                logger.debug(f"Could not get s3_client for loop recorder: {e}")
                s3_client = None
            
            settings = get_settings()
            
            logger.debug(f"Loop recorder: Triggered for flow {flow_id}")
            loop_recorder = LoopRecorderManager(vast_db, s3_client=s3_client, settings=settings)
            result = await loop_recorder.process_flow(flow_id)
            if result:
                logger.info(f"Loop recorder: Successfully processed flow {flow_id}")
            else:
                logger.debug(f"Loop recorder: No action needed for flow {flow_id}")
        except Exception as e:
            logger.warning("Loop recorder check failed for flow %s: %s", flow_id, e, exc_info=True)
    
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

