"""
Event Manager for TAMS API

Handles event emission and webhook execution for various TAMS operations.
"""

import asyncio
import logging
import json
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.vast_store import VASTStore
from app.models import Webhook

logger = logging.getLogger(__name__)


class EventManager:
    """Manages event emission and webhook execution for TAMS operations"""
    
    def __init__(self, store: VASTStore):
        self.store = store
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session for webhook calls"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'TAMS-API/6.0'}
            )
        return self.session
    
    async def emit_segment_event(self, event_type: str, segment: Any, **kwargs) -> None:
        """Emit a segment-related event and trigger webhooks"""
        try:
            logger.info(f"Emitting segment event: {event_type}")
            
            # Get all webhooks that listen for this event type
            webhooks = await self.store.list_webhooks()
            relevant_webhooks = [
                webhook for webhook in webhooks 
                if event_type in webhook.events
            ]
            
            if not relevant_webhooks:
                logger.info(f"No webhooks registered for event: {event_type}")
                return
            
            logger.info(f"Found {len(relevant_webhooks)} webhooks for event: {event_type}")
            
            # Prepare event payload
            event_payload = {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "segment": {
                    "object_id": getattr(segment, 'object_id', None),
                    "timerange": getattr(segment, 'timerange', None),
                    "flow_id": kwargs.get('flow_id'),
                    "sample_offset": getattr(segment, 'sample_offset', None),
                    "sample_count": getattr(segment, 'sample_count', None),
                    "key_frame_count": getattr(segment, 'key_frame_count', None)
                },
                "metadata": kwargs
            }
            
            # Execute webhooks asynchronously
            tasks = []
            for webhook in relevant_webhooks:
                task = self._execute_webhook(webhook, event_payload)
                tasks.append(task)
            
            if tasks:
                # Execute all webhooks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Webhook {relevant_webhooks[i].url} failed: {result}")
                    else:
                        logger.info(f"Webhook {relevant_webhooks[i].url} executed successfully")
                        
        except Exception as e:
            logger.error(f"Failed to emit segment event {event_type}: {e}")
    
    async def _execute_webhook(self, webhook: Webhook, payload: Dict[str, Any]) -> bool:
        """Execute a single webhook"""
        try:
            session = await self._get_session()
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-TAMS-Event': payload['event_type'],
                'X-TAMS-Timestamp': payload['timestamp']
            }
            
            # Add API key if configured
            if webhook.api_key_name and webhook.api_key_value:
                headers[webhook.api_key_name] = webhook.api_key_value
            
            # Send webhook
            async with session.post(
                webhook.url,
                json=payload,
                headers=headers
            ) as response:
                if response.status in (200, 201, 202):
                    logger.info(f"Webhook {webhook.url} executed successfully (status: {response.status})")
                    return True
                else:
                    logger.warning(f"Webhook {webhook.url} returned status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to execute webhook {webhook.url}: {e}")
            return False
    
    async def emit_flow_event(self, event_type: str, flow: Any, **kwargs) -> None:
        """Emit a flow-related event and trigger webhooks"""
        try:
            logger.info(f"Emitting flow event: {event_type}")
            
            # Get all webhooks that listen for this event type
            webhooks = await self.store.list_webhooks()
            relevant_webhooks = [
                webhook for webhook in webhooks 
                if event_type in webhook.events
            ]
            
            if not relevant_webhooks:
                logger.info(f"No webhooks registered for event: {event_type}")
                return
            
            # Prepare event payload
            event_payload = {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "flow": {
                    "id": getattr(flow, 'id', None),
                    "source_id": getattr(flow, 'source_id', None),
                    "format": getattr(flow, 'format', None),
                    "label": getattr(flow, 'label', None)
                },
                "metadata": kwargs
            }
            
            # Execute webhooks
            tasks = [self._execute_webhook(webhook, event_payload) for webhook in relevant_webhooks]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Failed to emit flow event {event_type}: {e}")
    
    async def emit_source_event(self, event_type: str, source: Any, **kwargs) -> None:
        """Emit a source-related event and trigger webhooks"""
        try:
            logger.info(f"Emitting source event: {event_type}")
            
            # Get all webhooks that listen for this event type
            webhooks = await self.store.list_webhooks()
            relevant_webhooks = [
                webhook for webhook in webhooks 
                if event_type in webhook.events
            ]
            
            if not relevant_webhooks:
                logger.info(f"No webhooks registered for event: {event_type}")
                return
            
            # Prepare event payload
            event_payload = {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": {
                    "id": getattr(source, 'id', None),
                    "format": getattr(source, 'format', None),
                    "label": getattr(source, 'label', None)
                },
                "metadata": kwargs
            }
            
            # Execute webhooks
            tasks = [self._execute_webhook(webhook, event_payload) for webhook in relevant_webhooks]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Failed to emit source event {event_type}: {e}")
    
    async def close(self):
        """Close the event manager and cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Event manager session closed")
