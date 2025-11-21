# Loop Recorder Debugging Guide

## Changes Made

I've enhanced the loop recorder with better logging and error handling to help diagnose why it's not working:

### 1. Enhanced Logging
- Changed critical debug messages to `logger.info()` so they're visible in normal operation
- Added detailed logging for:
  - Flow tag retrieval and parsing
  - Segment count and duration calculations
  - Deletion operations

### 2. Better Tag Handling
- Now handles both `Tags` model format (`flow.tags.root`) and dict format
- Added validation and logging for tag format issues

### 3. Improved Segment Deletion
- Enhanced `_delete_segment()` to delete segments by `object_id` and `timerange` for precision
- Falls back to service method if direct deletion fails
- Better error handling and logging

### 4. Better Error Reporting
- Changed exception logging from `debug` to `warning` in event handler
- Added full exception tracebacks for debugging

## How to Test

### 1. Enable Debug Logging

Set the server log level to INFO or DEBUG to see loop recorder messages:

```python
# In your server config or environment
LOG_LEVEL=INFO
```

### 2. Check Flow Tags

Verify the flow has the `loop_recorder_duration` tag:

```bash
# Get flow tags
curl http://localhost:8000/api/tams/latest/flows/{flow_id}/tags

# Should show:
# {
#   "loop_recorder_duration": "900"
# }
```

### 3. Monitor Loop Recorder Logs

When segments are created, you should see:

```
Loop recorder: Triggered for flow {flow_id}
Loop recorder: Processing flow {flow_id} with limit 900s
Loop recorder: Found {count} segments for flow {flow_id}
Loop recorder: Flow {flow_id} duration {current}s / {limit}s limit
```

If duration exceeds limit:
```
Loop recorder: Deleted {count} segments from flow {flow_id} (current: {current}s, limit: {limit}s)
```

### 4. Common Issues

#### Issue: No loop recorder messages
**Possible causes:**
- Event not being emitted (check segment creation logs)
- Flow tags not set correctly
- Event handler exception (check server logs)

**Debug:**
```bash
# Check if events are being emitted
grep "flow-segments/created" server.log

# Check if loop recorder is triggered
grep "Loop recorder: Triggered" server.log
```

#### Issue: "Flow has no tags" or "tags.root is empty"
**Possible causes:**
- Tag not set on flow
- Tag format issue

**Debug:**
```bash
# Check flow tags
curl http://localhost:8000/api/tams/latest/flows/{flow_id}/tags/loop_recorder_duration

# Should return: "900"
```

#### Issue: "No segments found"
**Possible causes:**
- Segments not created yet
- Flow ID mismatch

**Debug:**
```bash
# List segments for flow
curl http://localhost:8000/api/tams/latest/flows/{flow_id}/segments
```

#### Issue: Duration calculation returns 0
**Possible causes:**
- Segments don't have timerange
- Timerange format not recognized

**Debug:**
```bash
# Check segment timeranges
curl http://localhost:8000/api/tams/latest/flows/{flow_id}/segments | jq '.[].timerange'
```

#### Issue: Segments not being deleted
**Possible causes:**
- Duration not exceeding limit
- Deletion query failing
- Database permissions

**Debug:**
- Check server logs for deletion errors
- Verify segment count before/after loop recorder runs
- Check database directly if possible

## Testing with stream_ingestor

1. Start stream_ingestor with a short loop_recorder_duration:
```bash
python stream_ingestor.py \
  --srt-url udp://127.0.0.1:1234 \
  --chunk-duration 5 \
  --loop-recorder-duration 30 \
  --verbose
```

2. Stream for more than 30 seconds (6+ chunks)

3. Check server logs for loop recorder activity

4. Verify segments are being deleted:
```bash
# Count segments (should stay around 6-7 for 30s limit with 5s chunks)
curl http://localhost:8000/api/tams/latest/flows/{flow_id}/segments | jq 'length'
```

## Next Steps

If loop recorder still doesn't work after these changes:

1. **Check server logs** for any exceptions or warnings
2. **Verify event emission** - ensure `flow-segments/created` events are being emitted
3. **Test tag retrieval** - verify flow tags are accessible
4. **Test duration calculation** - verify timerange parsing works
5. **Test segment deletion** - verify deletion queries work

The enhanced logging should help identify which step is failing.


