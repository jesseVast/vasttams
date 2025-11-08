# UI API Response Format Fix

## Summary

Fixed UI to correctly handle API response format for TAMS endpoints that return `{data: [], paging: null}`.

## Issue

The React UI was getting errors like `sources.map is not a function` because the API response format for TAMS endpoints is:
```json
{
  "data": [...],
  "paging": null
}
```

But the UI code was expecting just an array directly.

## Fix

Updated `ui/src/services/api.ts` to handle both formats using optional chaining:

### Before
```typescript
export const sourceService = {
  list: async (): Promise<Source[]> => {
    const response = await api.get('/sources');
    return response.data || [];
  },
```

### After
```typescript
export const sourceService = {
  list: async (): Promise<Source[]> => {
    const response = await api.get('/sources');
    return response.data?.data || response.data || [];
  },
```

This checks for `response.data.data` first (TAMS format), then `response.data` (direct array), or falls back to an empty array.

## Updated Services

- `sourceService.list()` - Returns `response.data?.data || response.data || []`
- `flowService.list()` - Returns `response.data?.data || response.data || []`
- `segmentService.listByFlow()` - Returns `response.data?.data || response.data || []`

## API Response Formats

### TAMS Endpoints (sources, flows, segments)
```json
{
  "data": [...],
  "paging": null
}
```

### Users Endpoint
```json
[
  {
    "user_id": "...",
    "username": "...",
    ...
  }
]
```

The fix handles both formats automatically.

## Status

✅ UI now correctly parses TAMS API responses
✅ Handles both `{data: []}` and direct array formats
✅ Ready to display sources, flows, and segments

