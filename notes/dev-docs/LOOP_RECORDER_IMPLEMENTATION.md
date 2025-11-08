# Loop Recorder Implementation

## Summary

Created a separate loop recorder module as requested. The module automatically deletes old segments from flows when they exceed their `loop_recorder_duration` tag value.

## Files Created

### Module Structure
```
src/vasttams/looprecorder/
├── __init__.py          # Module exports
├── manager.py           # LoopRecorderManager implementation
└── README.md            # Module documentation
```

### Code Files

1. **src/vasttams/looprecorder/__init__.py**
   - Exports `LoopRecorderManager` class

2. **src/vasttams/looprecorder/manager.py**
   - `LoopRecorderManager` class
   - `process_flow()` - Main processing logic
   - Duration calculation
   - Segment deletion logic
   - Timerange parsing

3. **src/vasttams/looprecorder/README.md**
   - Usage documentation
   - Configuration guide
   - Architecture overview

### Integration

**Modified**: `src/vasttams/events/manager.py`
- Added `_handle_loop_recorder()` method
- Triggers automatically on `flow-segments/created` events
- Runs asynchronously (non-blocking)

## How It Works

### Event Flow

```
POST /flows/{flow_id}/segments
    ↓
Segment created in database
    ↓
Event emitted: 'flow-segments/created'
    ↓
EventManager receives event
    ↓
Calls _handle_loop_recorder(flow_id) async
    ↓
LoopRecorderManager.process_flow(flow_id)
    ↓
Checks if flow has loop_recorder_duration tag
    ↓
Calculates total flow duration
    ↓
If duration > limit:
    Delete oldest segments until within limit
```

### Key Features

1. **Tag-Driven**: Uses `loop_recorder_duration` tag on flows
2. **Event-Driven**: Triggered by segment creation events
3. **Non-Blocking**: Runs asynchronously, doesn't slow segment creation
4. **Automatic**: No manual intervention required
5. **Safe**: Never deletes all segments (keeps at least one)

### Example Usage

```python
# Create a flow with 1-hour loop recording
flow_data = {
    "id": "flow-123",
    "source_id": "source-456",
    "format": "urn:x-nmos:format:video",
    "label": "Security Camera",
    "tags": {
        "loop_recorder_duration": "3600"  # 1 hour in seconds
    }
}

# Create the flow
POST /flows
```

After segments are added:
- Flow duration is checked
- If > 1 hour, oldest segments are deleted
- Automatically maintains 1-hour rolling buffer

## Implementation Details

### Duration Calculation

Supports two methods:

1. **Timerange-based** (preferred):
   - Parses TAMS timerange: `[sec:nanosec_sec:nanosec)`
   - Uses first and last segment timeranges
   - Most accurate

2. **Sample-based** (fallback):
   - Uses `sample_count` fields
   - Estimates: samples / 30 fps
   - Used when timerange unavailable

### Segment Deletion

```python
# Calculates which segments to delete
excess_duration = current_duration - limit_duration
segments_to_delete = int(excess_duration / duration_per_segment) + 1

# Deletes oldest segments first
# NEVER deletes all segments (keeps at least one)
```

### Integration Points

**EventManager Integration**:
```python
# In src/vasttams/events/manager.py
async def emit_segment_event(self, event_type, segment, flow_id):
    # ... emit event ...
    
    # Handle loop recorder
    if event_type == 'flow-segments/created' and event_data.flow_id:
        asyncio.create_task(self._handle_loop_recorder(flow_id))

async def _handle_loop_recorder(self, flow_id):
    from ..looprecorder import LoopRecorderManager
    loop_recorder = LoopRecorderManager(self.vast_db)
    await loop_recorder.process_flow(flow_id)
```

## Benefits

1. **No Configuration Required**: Works automatically if tag is present
2. **Non-Invasive**: Doesn't affect flows without the tag
3. **Efficient**: Only runs when segments are created
4. **Scalable**: Handles any number of flows independently
5. **Safe**: Never corrupts data, graceful error handling

## Testing

To test the loop recorder:

1. Create a flow with `loop_recorder_duration` tag
2. Add multiple segments over time
3. Verify oldest segments are deleted when limit is exceeded
4. Check logs for loop recorder activity

## Status

✅ **Module Created**: `src/vasttams/looprecorder/`
✅ **Integration Complete**: Added to EventManager
✅ **No Linter Errors**: Code passes linting
⚠️ **Tests Pending**: Need to add tests

## Next Steps

1. Add tests in `tests/looprecorder/`
2. Test with real flows and segments
3. Verify segment deletion behavior
4. Monitor performance impact

