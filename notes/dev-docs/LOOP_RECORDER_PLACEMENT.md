# Loop Recorder - Where to Add

## Overview

The Loop Recorder should be added as an event-driven listener that monitors `flow-segments/created` events and automatically deletes old segments when flows exceed their `loop_recorder_duration` tag.

## Architecture Decision

### Option 1: Event Listener in EventManager ⭐ RECOMMENDED

**Location**: `src/vasttams/events/manager.py`

Add method to EventManager that listens for segment creation events:

```python
async def _handle_loop_recorder(self, event_type: str, event_data: FlowSegmentEventData):
    """Handle loop recorder logic for flow segment events"""
    if event_type != 'flow-segments/created':
        return
    
    flow_id = event_data.flow_id
    if not flow_id:
        return
    
    # Check if flow has loop_recorder_duration tag
    # Get flow to check tags
    # If duration exceeded, delete oldest segments
    ...
```

**Pros:**
- Centralized event handling
- Event-driven architecture
- No changes to existing code
- Easy to enable/disable

**Cons:**
- Adds complexity to EventManager
- May slow down event emission

### Option 2: Separate Loop Recorder Service

**Location**: `src/vasttams/looprecorder/`

Create dedicated module:
- `looprecorder/manager.py` - Loop recorder logic
- `looprecorder/router.py` - Optional API endpoints
- `looprecorder/__init__.py` - Exports

**Integration**: Add to EventManager or create background task

**Pros:**
- Separation of concerns
- Can be optional module
- Easier to test
- Can be deployed separately

**Cons:**
- More files to maintain
- Need to wire up event listeners

### Option 3: Background Task ⭐ ALTERNATIVE

**Location**: `src/vasttams/core/looprecorder.py`

Add background task that periodically checks flows with loop_recorder_duration tag.

**Pros:**
- Simple implementation
- Doesn't interfere with event processing

**Cons:**
- Not event-driven (less efficient)
- Periodic checking uses resources
- Delay in cleanup

## Recommended Implementation

### Step 1: Create Loop Recorder Module

```
src/vasttams/looprecorder/
├── __init__.py
├── manager.py
└── README.md
```

### Step 2: Add to EventManager

In `src/vasttams/events/manager.py`:

```python
async def emit_segment_event(self, event_type: str, segment: Any, ...):
    """Emit a flow segment-related event"""
    try:
        # ... existing event creation ...
        
        # Emit event
        await self.emit_event(event)
        
        # Check for loop recorder
        if event_type == 'flow-segments/created' and event_data.flow_id:
            await self._handle_loop_recorder(event_data.flow_id)
            
    except Exception as e:
        logger.error("Error creating segment event %s: %s", event_type, e)

async def _handle_loop_recorder(self, flow_id: str):
    """Handle loop recorder for flow"""
    try:
        from ..looprecorder.manager import LoopRecorderManager
        loop_recorder = LoopRecorderManager(self.vast_db)
        await loop_recorder.process_flow(flow_id)
    except Exception as e:
        logger.warning("Loop recorder check failed for flow %s: %s", flow_id, e)
```

### Step 3: Implement Loop Recorder Manager

`src/vasttams/looprecorder/manager.py`:

```python
"""
Loop Recorder Manager

Manages automatic deletion of old segments when flows exceed their loop_recorder_duration.
"""

import logging
from typing import Optional
from datetime import timedelta

from ..flows.service import FlowStorageService
from ..segments.service import SegmentStorageService
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class LoopRecorderManager:
    """Manages loop recording for flows"""
    
    def __init__(self, vast_db, s3_client=None):
        self.vast_db = vast_db
        self.s3_client = s3_client or get_s3_client()
        self.settings = get_settings()
        
        # Initialize services
        self.flow_service = FlowStorageService(vast_db, s3_client)
        self.segment_service = SegmentStorageService(vast_db, s3_client, self.settings)
    
    async def process_flow(self, flow_id: str) -> bool:
        """
        Process a flow for loop recorder
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            True if segments were deleted, False otherwise
        """
        try:
            # Get flow
            flow = await self.flow_service.get_flow(flow_id)
            if not flow:
                return False
            
            # Check if flow has loop_recorder_duration tag
            if not flow.tags or not flow.tags.root:
                return False
            
            duration_limit_sec = self._get_duration_limit(flow.tags.root)
            if not duration_limit_sec:
                return False
            
            # Get all segments
            segments = await self.segment_service.get_flow_segments(flow_id)
            
            if not segments:
                return False
            
            # Calculate current duration
            current_duration = self._calculate_flow_duration(segments)
            
            # If within limit, no action needed
            if current_duration <= duration_limit_sec:
                return False
            
            # Calculate segments to delete
            segments_to_delete = self._get_segments_to_delete(
                segments, 
                current_duration, 
                duration_limit_sec
            )
            
            if not segments_to_delete:
                return False
            
            # Delete old segments
            for segment in segments_to_delete:
                await self._delete_segment(flow_id, segment)
            
            logger.info(
                "Loop recorder: Deleted %d segments from flow %s "
                "(current: %d, limit: %d)",
                len(segments_to_delete), flow_id, current_duration, duration_limit_sec
            )
            
            return True
            
        except Exception as e:
            logger.error("Loop recorder error for flow %s: %s", flow_id, e)
            return False
    
    def _get_duration_limit(self, tags: dict) -> Optional[int]:
        """Get loop_recorder_duration from tags in seconds"""
        duration = tags.get('loop_recorder_duration')
        if duration:
            try:
                return int(duration)
            except ValueError:
                logger.warning("Invalid loop_recorder_duration tag: %s", duration)
        return None
    
    def _calculate_flow_duration(self, segments) -> float:
        """Calculate total duration of flow in seconds"""
        if not segments:
            return 0
        
        # Get first and last segment
        first_segment = segments[0]
        last_segment = segments[-1]
        
        if not first_segment.timerange or not last_segment.timerange:
            # Fallback: estimate from sample_count if available
            total_samples = sum(
                getattr(s, 'sample_count', 0) or 0 for s in segments
            )
            # Rough estimate: 30 samples per second (adjust as needed)
            return total_samples / 30.0
        
        # Parse timeranges
        start = self._parse_timerange(first_segment.timerange)
        end = self._parse_timerange(last_segment.timerange)
        
        if start and end:
            return (end - start).total_seconds()
        
        return 0
    
    def _parse_timerange(self, timerange) -> Optional[datetime]:
        """Parse TAMS timerange to datetime"""
        # Parse format: [start_seconds:start_nanos_end_seconds:end_nanos)
        # Implementation depends on timerange format
        ...
    
    def _get_segments_to_delete(self, segments, current_duration, limit_duration):
        """Get segments to delete to bring duration within limit"""
        excess_duration = current_duration - limit_duration
        
        # Calculate duration per segment
        duration_per_segment = current_duration / len(segments)
        
        # Calculate number of segments to delete
        segments_to_delete_count = int(excess_duration / duration_per_segment) + 1
        
        # Return oldest segments
        return segments[:segments_to_delete_count]
    
    async def _delete_segment(self, flow_id: str, segment):
        """Delete a specific segment"""
        # Implement segment deletion
        # This might need a new method in SegmentStorageService
        ...
```

### Step 4: Wire Up in EventManager

In `src/vasttams/events/manager.py`:

```python
async def emit_segment_event(self, event_type: str, segment: Any, user_id: Optional[str] = None, flow_id: Optional[str] = None) -> None:
    """Emit a flow segment-related event"""
    try:
        event_data = FlowSegmentEventData(...)
        event = Event(event_type=event_type, data=event_data)
        
        # Emit event
        await self.emit_event(event)
        
        # Handle loop recorder (async - don't block event emission)
        if event_type == 'flow-segments/created' and flow_id:
            asyncio.create_task(self._handle_loop_recorder(flow_id))
            
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
```

### Step 5: Configuration

Add to `config/config.yaml`:

```yaml
loop_recorder:
  enabled: true
  min_segment_duration: 0.5
  max_segment_age_seconds: 86400
```

## Alternative: Background Task

If you prefer a background task approach:

### In `src/vasttams/core/background_tasks.py`:

```python
async def loop_recorder_task():
    """Background task to check flows with loop_recorder_duration"""
    while True:
        try:
            # Find all flows with loop_recorder_duration tag
            # Check duration
            # Delete excess segments
            ...
        except Exception as e:
            logger.error("Loop recorder task error: %s", e)
        
        # Wait before next check
        await asyncio.sleep(60)  # Check every 60 seconds
```

## Summary

**Recommended Placement**: `src/vasttams/looprecorder/`

**Integration Point**: EventManager listens for `flow-segments/created` events

**Key Files**:
- `src/vasttams/looprecorder/manager.py` - Main loop recorder logic
- `src/vasttams/looprecorder/__init__.py` - Module exports
- Modify `src/vasttams/events/manager.py` - Add loop recorder trigger

**Benefits**:
- Event-driven (immediate)
- Doesn't slow down segment creation
- Can be enabled/disabled per flow via tag
- Optional module that can be deployed separately

