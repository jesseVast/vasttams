# Source Create Form Complete

## Summary
Updated the Sources UI create form to include all required fields and auto-generate IDs.

## Changes Made

### Added UUID Generation
- Added `generateUUID()` function to create RFC 4122 compliant UUIDs
- Format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- Version 4 UUID with proper variant bits

### Required Fields Added
- `id` - Auto-generated UUID
- `format` - Content format (video, audio, data, multi)
- `created` - Auto-generated ISO timestamp
- `updated` - Auto-generated ISO timestamp
- `created_by` - User field (optional, defaults to 'admin')
- `updated_by` - User field (optional, defaults to 'admin')

### Optional Fields
- `label` - Freeform string label
- `description` - Description text
- `tags` - Key-value metadata (not in form yet)
- `source_collection` - Nested sources (not in form yet)
- `collected_by` - Parent sources (read-only, computed)

## Form Fields
1. **Label** - Text input
2. **Description** - Text input
3. **Format** - Dropdown (Video, Audio, Data, Multi)
4. **Created By** - Text input (optional, defaults to 'admin')

## Auto-Generated Fields
- **ID** - Valid UUID v4
- **Created** - Current timestamp
- **Updated** - Current timestamp
- **Created By** - Defaults to 'admin' if empty
- **Updated By** - Defaults to 'admin' if empty

## API Payload Example
```json
{
  "id": "12345678-1234-4123-a123-123456789012",
  "format": "urn:x-nmos:format:video",
  "label": "Test",
  "description": "this is a test",
  "created": "2025-10-28T02:15:00.000Z",
  "updated": "2025-10-28T02:15:00.000Z",
  "created_by": "admin",
  "updated_by": "admin"
}
```

## Status
✅ Source creation form now includes all required fields
✅ UUID auto-generation working
✅ Timestamps auto-generated
✅ Form validates before submission
✅ Ready to create sources

