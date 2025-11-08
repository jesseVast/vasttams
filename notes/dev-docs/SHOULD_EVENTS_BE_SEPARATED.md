# Should Events Be Separated?

## Current State

### Event-Related Code in `common/models.py`
- **7 event classes**: `EventData`, `SourceEventData`, `FlowEventData`, `FlowSegmentEventData`, `ObjectEventData`, `CollectionEventData`, `Event`
- **2 related classes**: `EventStreamMechanism`, (possibly `HttpRequest` for webhooks)
- **Total**: ~9 classes out of 17 in `common/models.py` (53%)

### File Sizes
- `src/vasttams/common/models.py`: 292 lines
- `src/vasttams/core/event_manager.py`: 222 lines
- **Event-related code**: ~40% of `common/models.py`

## Analysis

### Arguments FOR Separating Events

1. **Size & Complexity**
   - Event models are a significant portion (53%) of `common/models.py`
   - As event handling grows, this file will become unwieldy
   - Clear logical grouping (all event models together)

2. **Future Extensibility**
   - Event handling may grow (handlers, processors, transformers)
   - Different delivery mechanisms (SSE, WebSocket, Kafka)
   - Event persistence, replay, or event sourcing
   - Event filtering, routing, or transformations

3. **Dependency Management**
   - Event models and EventManager are tightly coupled
   - Currently EventManager imports from `common/models.py`
   - Separating them creates clearer boundaries

4. **Architectural Clarity**
   - Events are a cross-cutting concern
   - They're used across all domain modules (sources, flows, objects, segments)
   - Having a dedicated `events/` module makes their role explicit

### Arguments AGAINST Separating Events

1. **Current Simplicity**
   - Events are simple data classes (Pydantic models)
   - EventManager is already separate in `core/event_manager.py`
   - No immediate need for complex event handling

2. **Import Overhead**
   - All routers import from `common/models.py` already
   - Separating events requires updating many import statements
   - Minimal benefit if event handling stays simple

3. **Module Proliferation**
   - Already have: `core/`, `common/`, `webhooks/`, `flows/`, `sources/`, etc.
   - Adding `events/` increases complexity
   - Only worth it if the module has significant content

4. **TAMS Specification**
   - Events are tightly tied to domain models (sources, flows, objects)
   - The specification treats them as part of resource definitions
   - Not a standalone subdomain

## Recommendation

### **KEEP Events in `common/models.py` FOR NOW**

#### Why?

1. **Current Complexity is Manageable**
   - 9 event-related classes is reasonable
   - Event logic is simple (data classes only)
   - No complex event handling logic yet

2. **Premature Optimization**
   - No evidence that event handling will become complex
   - Creating a module now adds overhead without clear benefit
   - Can refactor later if needed

3. **Changes Required**
   - Would need to update ~10 import statements
   - EventManager would need updated imports
   - All routers (sources, flows, objects, segments) import events
   - Minimal benefit for the overhead

### **WHEN to Separate?**

Separate into `events/` module if:

1. **Event Handling Grows**
   - Event processors, transformers, or handlers
   - Event persistence or replay
   - Event sourcing patterns

2. **Multiple Delivery Mechanisms**
   - Beyond webhooks, add SSE, WebSocket, or message queues
   - Delivery mechanism abstraction

3. **Event Processing Logic**
   - Event filtering, routing, or transformation
   - Event validation or enrichment
   - Event correlation or aggregation

4. **File Size**
   - `common/models.py` exceeds 500-600 lines
   - Event-related code exceeds 200 lines

### **Alternative: Hybrid Approach**

If some separation is needed without full module:

```
src/vasttams/
├── common/
│   ├── models.py          # Keep core models (TimeRange, Tags, etc.)
│   └── event_models.py   # Extract ONLY event models
└── core/
    └── event_manager.py   # Keep EventManager here
```

**Pros:**
- Partially separates events without creating new module
- Keeps all models accessible from `common/`
- Minimal import changes needed

**Cons:**
- Still in `common/`, doesn't solve architectural concerns
- Creates split between model files

### **Proposed Module Structure (If Separated)**

```
src/vasttams/events/
├── __init__.py
├── models.py              # Event models (Event, EventData, SourceEventData, etc.)
├── manager.py             # EventManager (move from core/)
└── handlers.py            # Future: event handlers, processors
```

**Import changes required:**
```python
# Before:
from ..common.models import Event, EventData, SourceEventData
from ..core.event_manager import EventManager

# After:
from ..events.models import Event, EventData, SourceEventData
from ..events.manager import EventManager
```

## Decision Matrix

| Factor | Keep in `common/` | Separate to `events/` |
|--------|-------------------|----------------------|
| **Current size** | ✅ Small (9 classes) | ❌ Unjustified overhead |
| **Future growth** | ⚠️ Unknown | ✅ Prepared for growth |
| **Import complexity** | ✅ Simple | ❌ Update ~10 files |
| **Architectural clarity** | ⚠️ Events mixed with common models | ✅ Explicit module |
| **Refactoring cost** | ✅ None | ❌ Medium (~2 hours) |
| **Maintenance** | ✅ Simple | ✅ Clear structure |

## Final Recommendation

**Keep events in `common/models.py` but document the extraction point:**

Add a comment to `common/models.py`:
```python
# ============================================================================
# Event Models
# TODO: Consider extracting to events/models.py if event handling grows complex
#       or if we add event processors, multiple delivery mechanisms, or event
#       persistence. See docs/dev-docs/SHOULD_EVENTS_BE_SEPARATED.md
# ============================================================================
```

This provides:
1. Current simplicity
2. Clear migration path if needed
3. No premature optimization
4. Documentation for future developers

## Next Steps

1. ✅ Keep events in `common/models.py` for now
2. ✅ Fix EventManager to use WebhookService instead of VASTStore
3. ✅ Document the potential extraction point
4. ⏳ Monitor event handling complexity
5. ⏳ Extract to `events/` module when warranted by growth

