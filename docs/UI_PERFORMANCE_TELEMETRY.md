# UI List Performance Telemetry

## Overview

Added comprehensive telemetry to track and diagnose UI list performance issues. The telemetry system now tracks detailed timing metrics for list operations to identify bottlenecks.

## Metrics Added

### Prometheus Metrics

1. **`tams_list_query_duration_seconds`** - Database query duration for list operations
   - Labels: `entity_type` (flows, sources, etc.), `has_filters` (true/false)
   - Buckets: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0 seconds

2. **`tams_list_json_parse_duration_seconds`** - JSON parsing duration for list operations
   - Labels: `entity_type`
   - Buckets: 0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5 seconds

3. **`tams_list_processing_duration_seconds`** - Total processing duration for list operations
   - Labels: `entity_type`, `record_count` (small/medium/large)
   - Buckets: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 seconds

4. **`tams_list_record_count`** - Number of records returned in list operations
   - Labels: `entity_type`
   - Buckets: 1, 5, 10, 25, 50, 100, 250, 500, 1000

## Implementation

### Service Layer Telemetry

Added telemetry tracking to:
- `FlowStorageService.get_flows()` - Tracks query time, JSON parsing time, total time, record count
- `SourceStorageService.get_sources()` - Tracks query time, JSON parsing time, total time, record count

### Metrics Recorded

For each list operation, the system now tracks:
1. **Query Duration**: Time spent executing the database query
2. **JSON Parse Duration**: Time spent parsing JSON fields (tags, essence_parameters, flow_collection)
3. **Total Duration**: End-to-end processing time
4. **Record Count**: Number of records returned
5. **Filter Status**: Whether filters were applied

### Logging Enhancements

- List endpoints (`/flows`, `/sources`, `/segments`, `/objects`) are now logged at INFO level
- Slow list operations (>1s) are logged with detailed breakdown:
  ```
  Slow list operation: flows - query=0.523s, json_parse=0.234s, total=0.789s, records=150, filters=true
  ```
- HTTP requests to list endpoints show warnings if duration > 0.5s:
  ```
  GET /flows - user=admin, duration=0.623s, status=200 [SLOW LIST - UI may be unresponsive]
  ```

## Usage

### Viewing Metrics

Metrics are available via Prometheus endpoint:
```bash
curl http://localhost:8000/metrics | grep tams_list
```

### Analyzing Performance

1. **Query Performance**: Check `tams_list_query_duration_seconds` to identify slow database queries
2. **JSON Parsing**: Check `tams_list_json_parse_duration_seconds` to identify JSON parsing bottlenecks
3. **Total Performance**: Check `tams_list_processing_duration_seconds` for overall list operation performance
4. **Record Count Impact**: Check `tams_list_record_count` to see how many records are being returned

### Log Analysis

Check logs for slow operations:
```bash
grep "Slow list operation" logs/tams.log
grep "SLOW LIST" logs/tams.log
```

## Performance Thresholds

- **Fast**: < 0.25s total duration
- **Acceptable**: 0.25s - 0.5s total duration
- **Slow**: 0.5s - 1.0s total duration (logged with warning)
- **Very Slow**: > 1.0s total duration (logged with detailed breakdown)

## Common Bottlenecks

1. **Large Result Sets**: High `record_count` with slow queries
   - Solution: Add pagination or reduce limit
   
2. **Complex Filters**: JSON_EXTRACT queries for frame_width/frame_height
   - Solution: Consider indexing or materialized views
   
3. **JSON Parsing**: High `json_parse_duration` for many records
   - Solution: Optimize JSON parsing or cache parsed results
   
4. **Tag Filtering**: JOIN queries for tag filters
   - Solution: Ensure proper indexes on tags table

## Next Steps

1. Add telemetry to analytics endpoints (used by UI in parallel)
2. Add telemetry to segment list operations
3. Create dashboard for UI performance monitoring
4. Add alerts for consistently slow operations

