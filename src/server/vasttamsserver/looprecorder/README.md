# Loop Recorder Module

## Overview

The Loop Recorder module automatically deletes old segments from flows when they exceed a configured duration limit. This is useful for live recording or loop recording scenarios where you want to maintain a rolling buffer of content.

## How It Works

1. **Tag Configuration**: Add a `loop_recorder_duration` tag to a flow (in seconds)
2. **Segment Creation**: When a new segment is created, an event is emitted
3. **Automatic Check**: The loop recorder checks if the flow duration exceeds the limit
4. **Segment Deletion**: If exceeded, oldest segments are deleted to bring duration back within limit

## Usage

### Adding Loop Recording to a Flow

```python
# Create a flow with loop recording enabled
flow_data = {
    "id": "flow-123",
    "source_id": "source-456",
    "format": "urn:x-nmos:format:video",
    "label": "Live Camera Feed",
    "tags": {
        "loop_recorder_duration": "3600"  # 1 hour (in seconds)
    }
}

# Create the flow
response = requests.post(f"{BASE_URL}/flows", json=flow_data)
```

### How It Behaves

- When segments are added via `POST /flows/{flow_id}/segments`
- The loop recorder is automatically triggered
- It checks if total flow duration > `loop_recorder_duration`
- If yes, deletes the oldest segments until within limit
- Process is automatic and non-blocking

## Configuration

### Flow Tags

| Tag Name | Type | Description |
|----------|------|-------------|
| `loop_recorder_duration` | integer (seconds) | Maximum duration to keep segments |

### Example Scenarios

**Live Camera Feed (1 hour buffer)**
```json
{
  "tags": {
    "loop_recorder_duration": "3600"
  }
}
```

**Quick Loop (30 second buffer)**
```json
{
  "tags": {
    "loop_recorder_duration": "30"
  }
}
```

**Extended Recording (24 hour buffer)**
```json
{
  "tags": {
    "loop_recorder_duration": "86400"
  }
}
```

## Architecture

### Components

1. **LoopRecorderManager** (`src/vasttams/looprecorder/manager.py`)
   - Main loop recorder logic
   - Calculates flow duration
   - Determines segments to delete
   - Performs segment deletion

2. **Event Integration** (`src/vasttams/events/manager.py`)
   - Listens for `flow-segments/created` events
   - Triggers loop recorder check (async)
   - Non-blocking event processing

### Flow

```
Segment Created
    ↓
Event Emitted (flow-segments/created)
    ↓
LoopRecorderManager.check_flow()
    ↓
Get flow tags (loop_recorder_duration)
    ↓
Calculate current flow duration
    ↓
If duration > limit:
    ↓
    Delete oldest segments until within limit
```

## Implementation Details

### Duration Calculation

The loop recorder calculates flow duration in two ways:

1. **Timerange-based** (preferred):
   - Parses TAMS timerange format: `[sec:nanosec_sec:nanosec)`
   - Uses first and last segment timeranges
   - Calculates total duration

2. **Sample-based** (fallback):
   - Uses `sample_count` field
   - Estimates: samples / 30 (assumes 30 fps)
   - Used when timerange unavailable

### Segment Deletion

Segments are deleted in chronological order (oldest first):

```python
# Sort segments by timerange (oldest first)
sorted_segments = sorted(segments, key=lambda s: _get_timerange_start(s.timerange))

# Calculate how many to delete
excess_duration = current_duration - limit_duration
segments_to_delete = int(excess_duration / duration_per_segment) + 1

# Delete oldest segments
for segment in sorted_segments[:segments_to_delete]:
    delete_segment(segment)
```

## Logging

The loop recorder logs important events:

```
Loop recorder: Processing flow {flow_id} with limit {limit}s
Loop recorder: Flow {flow_id} duration {current}s / {limit}s limit
Loop recorder: Deleted {count} segments from flow {flow_id}
```

## Error Handling

- Errors in loop recorder don't affect segment creation
- Logged as warnings/debug messages
- Graceful degradation if duration cannot be calculated

## Testing

See `tests/looprecorder/` for test files.

## Compatibility

- Works with TAMS 8.0 specification
- Integrates with existing event system
- Compatible with all flow types (video, audio, etc.)

