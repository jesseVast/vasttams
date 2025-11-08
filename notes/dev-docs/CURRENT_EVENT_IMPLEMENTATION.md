# Current Event Implementation

## Overview

The TAMS API has a webhook-based event streaming system that emits events when resources are created, updated, or deleted. This document describes the current implementation.

## Architecture

### Components

1. **EventManager** (`src/vasttams/core/event_manager.py`)
   - Centralized event emission and webhook notifications
   - Manages webhook caching with 60-second TTL
   - Filters webhooks based on event type and resource IDs

2. **Event Models** (`src/vasttams/common/models.py`)
   - `Event`: Base event structure
   - `EventData`: Base event data
   - `SourceEventData`, `FlowEventData`, `FlowSegmentEventData`, `ObjectEventData`, `CollectionEventData`: Specific event types

3. **Webhook Infrastructure** (`src/vasttams/webhooks/`)
   - Dedicated module for webhook management
   - CRUD operations for webhooks
   - Database-backed webhook storage

### Event Types

The system emits the following event types:

- **sources/created**: When a source is created
- **sources/updated**: When a source is updated (tags, description, label)
- **sources/deleted**: When a source is deleted
- **flows/created**: When a flow is created
- **flows/updated**: When a flow is updated
- **flows/deleted**: When a flow is deleted
- **flows/segments_added**: When a segment is added to a flow
- **flows/segments_deleted**: When a segment is removed from a flow
- **objects/created**: When an object is created
- **objects/deleted**: When an object is deleted

## Current Implementation Status

### ✅ What's Working

1. **Event Models**: Fully defined and TAMS-compliant
2. **Event Manager**: Core logic implemented
3. **Webhook Infrastructure**: Database-backed webhooks with CRUD APIs
4. **Event Emission**: Routers emit events on CRUD operations

### ⚠️ Current Issues

1. **VASTStore Dependency**: EventManager still references `VASTStore` which is deprecated
   - Location: `src/vasttams/core/event_manager.py` line 27
   - Issue: `__init__(self, store: "VASTStore")` and `await self.store.get_webhooks()`

2. **Storage Interface**: EventManager should use the new webhooks service instead of the deprecated VASTStore

3. **Dependency Injection**: EventManager is instantiated in router files:
   ```python
   event_manager = EventManager(storage)  # In each router
   ```

## Event Flow

```
1. Router receives request (e.g., POST /sources)
2. Router performs CRUD operation
3. Router instantiates EventManager with storage
4. EventManager emits event via emit_source_event()
5. EventManager fetches webhooks (from old VASTStore)
6. EventManager filters webhooks based on event type and resource IDs
7. EventManager sends HTTP POST requests to webhook URLs
```

## Webhook Configuration

Webhooks are stored in the `webhooks` table with the following fields:

- `id`: Unique identifier
- `url`: Webhook URL
- `api_key_name`: HTTP header name for authentication
- `api_key_value`: HTTP header value for authentication
- `events`: JSON array of event types to subscribe to
- `flow_ids`: JSON array of flow IDs to filter events
- `source_ids`: JSON array of source IDs to filter events
- `flow_collected_by_ids`: JSON array of flow collection IDs
- `source_collected_by_ids`: JSON array of source collection IDs
- `accept_get_urls`: JSON array of URL labels to include
- `accept_storage_ids`: JSON array of storage IDs to include
- `presigned`: Boolean for presigned URL filtering
- `verbose_storage`: Boolean for verbose storage metadata
- `tags`: JSON object for webhook tags
- `enabled`: Boolean for enabling/disabling webhook
- `created`, `updated`: Timestamps

## Recommendations

### Immediate Fixes Needed

1. **Update EventManager to use WebhookService**
   - Instead of `await self.store.get_webhooks()`
   - Use `from ..webhooks.service import WebhookService`
   - Get webhooks from the database via WebhookService

2. **Refactor EventManager initialization**
   - Currently takes `store: "VASTStore"` as parameter
   - Should take `vast_db` and instantiate WebhookService internally
   - Or use dependency injection pattern

3. **Update routers to pass correct dependencies**
   - Currently pass `storage` (StorageInterface)
   - Should pass `vast_db` or a webhook service instance

### Example Fix

```python
# In event_manager.py
from ..webhooks.service import WebhookService

class EventManager:
    def __init__(self, vast_db):
        self.vast_db = vast_db
        self._webhook_service = None  # Lazy initialization
        self._webhook_cache: Optional[List[Webhook]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 60
    
    @property
    def webhook_service(self) -> WebhookService:
        if self._webhook_service is None:
            self._webhook_service = WebhookService(self.vast_db)
        return self._webhook_service
    
    async def _get_webhooks(self) -> List[Webhook]:
        # ... caching logic ...
        webhooks = await self.webhook_service.get_webhooks()
        # ...
```

## Testing

Event system testing would require:

1. Create webhook via `/service/webhooks`
2. Perform CRUD operation (e.g., create source)
3. Verify webhook receives POST request
4. Validate event payload structure

## Future Enhancements

1. **Event Retry Logic**: Add retry mechanism for failed webhook deliveries
2. **Event Batching**: Batch multiple events into a single webhook payload
3. **Event Filtering**: More sophisticated filtering based on collections
4. **Event Subscriptions**: Direct API subscriptions to event streams (SSE/WebSocket)
5. **Event Logging**: Persistent event log for audit trail

