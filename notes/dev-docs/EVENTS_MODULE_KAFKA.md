# Events Module with Kafka Support

## Overview

The events module has been created to support multiple event delivery mechanisms including webhooks and Kafka. This provides a flexible, pluggable architecture for event delivery.

## Module Structure

```
src/vasttams/events/
├── __init__.py          # Module exports
├── models.py             # Event models (Event, EventData, etc.)
├── manager.py            # EventManager with multi-delivery support
└── delivery.py           # Delivery mechanism interfaces (WebhookDelivery, KafkaDelivery)
```

## Key Features

### 1. **Multiple Delivery Mechanisms**

The `EventManager` now supports multiple delivery mechanisms:

- **Webhooks**: HTTP POST to registered webhook URLs
- **Kafka**: Publish events to Kafka topics
- **MultipleDelivery**: Deliver to multiple mechanisms simultaneously

### 2. **Pluggable Architecture**

```python
from vasttams.events import EventManager, KafkaDelivery

# Initialize with Kafka
kafka_config = {
    'bootstrap_servers': ['localhost:9092'],
    'topic': 'tams-events',
    'client_id': 'tams-producer'
}

event_manager = EventManager(
    vast_db=vast_db,
    kafka_config=kafka_config
)

# Emit events - automatically delivered to Kafka and webhooks
await event_manager.emit_source_event('sources/created', source)
```

### 3. **Event Models Extracted**

Event models have been extracted from `common/models.py` to `events/models.py`:

- `Event`: Base event structure
- `EventData`: Base event data
- `SourceEventData`, `FlowEventData`, `FlowSegmentEventData`, `ObjectEventData`, `CollectionEventData`: Specific event types
- `EventStreamMechanism`: Configuration for event stream mechanisms

## Kafka Configuration

### Configuration Format

```python
kafka_config = {
    'bootstrap_servers': ['kafka-broker-1:9092', 'kafka-broker-2:9092'],
    'topic': 'tams-events',  # Kafka topic name
    'client_id': 'tams-event-producer',
    'security_protocol': 'PLAINTEXT',  # or 'SASL_PLAINTEXT'
    'sasl_mechanism': 'PLAIN',  # or 'SCRAM-SHA-256'
    'sasl_username': 'kafka-user',  # Optional
    'sasl_password': 'kafka-password',  # Optional
}
```

### Enabling Kafka in Config

Add to `config/config.json`:

```json
{
  "kafka": {
    "enabled": true,
    "bootstrap_servers": ["localhost:9092"],
    "topic": "tams-events",
    "client_id": "tams-producer",
    "security_protocol": "PLAINTEXT"
  }
}
```

### Installing Kafka Library

```bash
pip install kafka-python
```

## Migration from Old EventManager

### Before

```python
from vasttams.core.event_manager import EventManager

event_manager = EventManager(storage)
await event_manager.emit_source_event('sources/created', source)
```

### After

```python
from vasttams.events import EventManager
from vasttams.core.dependencies import get_vast_db

vast_db = get_vast_db()
event_manager = EventManager(vast_db, kafka_config=kafka_config)  # Optional
await event_manager.emit_source_event('sources/created', source)
```

### Key Changes

1. **Import Path**: `core.event_manager` → `events`
2. **Initialization**: Takes `vast_db` instead of `storage`
3. **Kafka Support**: Add optional `kafka_config` parameter
4. **Multiple Delivery**: Can deliver to multiple mechanisms at once

## Usage Examples

### 1. Basic Usage (Webhooks Only)

```python
from vasttams.events import EventManager
from vasttams.core.dependencies import get_vast_db

vast_db = get_vast_db()
event_manager = EventManager(vast_db)

# Emit a source event
await event_manager.emit_source_event('sources/created', source)

# Emit a flow event
await event_manager.emit_flow_event('flows/created', flow)
```

### 2. With Kafka

```python
from vasttams.events import EventManager, KafkaDelivery
from vasttams.core.dependencies import get_vast_db

vast_db = get_vast_db()
kafka_config = {
    'bootstrap_servers': ['localhost:9092'],
    'topic': 'tams-events'
}

event_manager = EventManager(vast_db, kafka_config=kafka_config)

# Events now delivered to both webhooks and Kafka
await event_manager.emit_source_event('sources/created', source)
```

### 3. Custom Delivery Mechanisms

```python
from vasttams.events import EventManager, WebhookDelivery, KafkaDelivery
from vasttams.core.dependencies import get_vast_db

# Create custom delivery mechanisms
webhook = Webhook(url="https://example.com/webhook", ...)
webhook_delivery = WebhookDelivery(webhook)

kafka_config = {'bootstrap_servers': ['localhost:9092'], 'topic': 'tams-events'}
kafka_delivery = KafkaDelivery(kafka_config)

# Use multiple mechanisms
vast_db = get_vast_db()
event_manager = EventManager(
    vast_db,
    delivery_mechanisms=[webhook_delivery, kafka_delivery]
)

# Deliver to all configured mechanisms
await event_manager.emit_source_event('sources/created', source)
```

## Testing

### Test Event Delivery

```python
# Test webhook delivery
import asyncio
from vasttams.events import EventManager, WebhookDelivery
from vasttams.webhooks.models import Webhook

webhook = Webhook(
    url="https://httpbin.org/post",
    api_key_name="x-api-key",
    api_key_value="test-key",
    events=["sources/created"]
)

delivery = WebhookDelivery(webhook)
result = await delivery.deliver('sources/created', {'id': 'test-source'})
print(f"Webhook delivery: {result}")

# Test Kafka delivery
kafka_config = {'bootstrap_servers': ['localhost:9092'], 'topic': 'test-events'}
kafka_delivery = KafkaDelivery(kafka_config)
result = await kafka_delivery.deliver('sources/created', {'id': 'test-source'})
print(f"Kafka delivery: {result}")
```

## Future Enhancements

1. **Server-Sent Events (SSE)**: Real-time browser event streaming
2. **WebSocket Delivery**: Bidirectional event communication
3. **RabbitMQ/AMQP**: Message queue delivery
4. **Event Storage**: Persistent event log
5. **Event Replay**: Replay historical events
6. **Event Filtering**: Advanced filtering rules
7. **Event Batching**: Batch multiple events
8. **Event Correlation**: Track related events

## Benefits

1. **Flexibility**: Easy to add new delivery mechanisms
2. **Scalability**: Kafka provides high throughput
3. **Reliability**: Multiple delivery options reduce risk
4. **TAMS Compliance**: All event types supported
5. **Pluggable**: Easy to configure or disable mechanisms

## Configuration Priority

1. **Webhooks**: Always enabled (stored in database)
2. **Kafka**: Optional (configured via config file)
3. **Custom**: Can be added programmatically

## Import Migration

All router files need to be updated:

```python
# Old
from vasttams.core.event_manager import EventManager

# New
from vasttams.events import EventManager
```

This affects:
- `src/vasttams/sources/router.py`
- `src/vasttams/flows/router.py`
- `src/vasttams/objects/router.py`
- `src/vasttams/segments/router.py`

