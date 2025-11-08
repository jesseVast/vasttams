# Event vs Webhook Architecture

## Conceptual Relationship

**Events** = "What happened" (domain events)
**Webhooks** = "How to deliver notifications" (infrastructure)

These are **related but distinct concerns**:

### Events
- Define what actions trigger events
- Define event payload structures
- Are emitted by domain logic (sources, flows, objects, segments)
- Models live in `src/vasttams/common/models.py`

### Webhooks
- Define how to receive event notifications
- Store webhook configurations (URLs, filters, API keys)
- Handle delivery (HTTP POST to webhook URLs)
- API lives in `src/vasttams/webhooks/`
- EventManager lives in `src/vasttams/core/event_manager.py`

## Current Architecture

```
┌─────────────────────────────────────────────────┐
│          Domain Logic (Routers)                 │
│  sources, flows, objects, segments, etc.        │
└───────────────────┬───────────────────────────┘
                    │ emits
                    ▼
┌─────────────────────────────────────────────────┐
│          EventManager (core/)                   │
│  - Fetches webhooks from WebhookService         │
│  - Filters webhooks based on event type         │
│  - Sends notifications via HTTP POST            │
└───────────────────┬───────────────────────────┘
                    │ uses
                    ▼
┌─────────────────────────────────────────────────┐
│          WebhookService (webhooks/)             │
│  - CRUD for webhook configurations              │
│  - Stores webhooks in database                  │
└─────────────────────────────────────────────────┘
```

## File Organization

### Current Structure (Recommended)

```
src/vasttams/
├── common/
│   └── models.py              # Event models (Event, EventData, etc.)
├── core/
│   └── event_manager.py       # EventManager class
├── webhooks/
│   ├── models.py             # Webhook, WebhookPost, WebhookUpdate
│   ├── service.py            # WebhookService (CRUD)
│   ├── router.py             # Webhook API endpoints
│   └── schemas.py            # Webhook database schemas
```

### Why NOT Merge?

1. **Separation of Concerns**
   - Events = domain events (what happened)
   - Webhooks = infrastructure (how to receive notifications)
   - EventManager = orchestrator that connects them

2. **Future Extensibility**
   - Other delivery mechanisms could be added:
     - Server-Sent Events (SSE)
     - WebSocket streams
     - Message queues (RabbitMQ, Kafka)
   - These would be separate from webhooks but use the same events

3. **TAMS Specification Alignment**
   - TAMS spec defines events separately from webhooks
   - ADR-0014: "Specify the content of notification messages, plus some example implementations"
   - Webhooks are ONE delivery mechanism, not THE mechanism

4. **Dependency Direction**
   - EventManager depends on WebhookService
   - EventManager does NOT own webhook logic
   - Webhooks are independent infrastructure

## Recommendations

### Keep Current Structure

✅ **DO**: Keep events in `common/models.py`
   - Events are shared across the entire application
   - Multiple delivery mechanisms may use them

✅ **DO**: Keep EventManager in `core/event_manager.py`
   - It's core infrastructure that orchestrates delivery
   - It may use multiple notification mechanisms in the future

✅ **DO**: Keep webhooks in `webhooks/` module
   - They are a specific delivery mechanism
   - They have their own CRUD APIs
   - They can evolve independently

❌ **DON'T**: Move events under webhooks/
   - Events are not owned by webhooks
   - Events are domain concepts, webhooks are infrastructure

❌ **DON'T**: Move webhooks under events/
   - Webhooks are delivery mechanism, not events
   - Multiple delivery mechanisms may exist

### Alternative: Create `events/` Module (If Needed)

If events become complex enough, consider:

```
src/vasttams/
├── events/
│   ├── models.py             # Event models
│   ├── manager.py             # EventManager
│   ├── handlers.py            # Event handlers
│   └── __init__.py
├── webhooks/
│   ├── models.py             # Webhook models
│   ├── service.py            # WebhookService
│   ├── router.py             # Webhook API
│   └── schemas.py            # Webhook schemas
```

But only if:
1. Event management becomes complex enough
2. You plan to add multiple delivery mechanisms
3. Event handling logic grows beyond EventManager

## Current Issues to Fix

1. **EventManager import**: Update to use WebhookService instead of VASTStore
2. **Dependency injection**: EventManager should take `vast_db` not `store: "VASTStore"`
3. **Module organization**: Events and webhooks are correctly separated

## Summary

**Keep events separate from webhooks**. They are related but distinct:
- Events = domain events (what happened)
- Webhooks = delivery mechanism (how to notify)
- EventManager = orchestrator (connects events to webhooks)

Current file organization is correct - no changes needed to structure.

