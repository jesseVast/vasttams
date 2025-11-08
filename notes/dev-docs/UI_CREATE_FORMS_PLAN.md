# UI Create Forms Implementation Plan

## Summary
The user requested to add create buttons for Sources, Flows, Segments, Objects, Webhooks, and Storage Backends to the UI, using TAMS 8.0 examples for field definitions.

## Completed ✅
1. Added `Webhook` and `StorageBackend` types to `ui/src/types.ts`
2. Added `webhookService` and `storageBackendService` to `ui/src/services/api.ts`
3. Read TAMS 8.0 examples to understand field requirements

## TAMS 8.0 Examples Found

### Source (from examples/sources-get-200.json)
```json
{
  "id": "2aa143ac-0ab7-4d75-bc32-5c00c13d186f",
  "format": "urn:x-nmos:format:video",
  "label": "bbb",
  "description": "Big Buck Bunny video"
}
```
**Required fields:** format, label (optional but recommended)

### Flow (from examples/flow-put.json)
```json
{
  "id": "6101df05-06bb-41b8-8af4-cf7cd33df209",
  "source_id": "41d7f7eb-c48d-4513-9b37-17b418d26d7f",
  "generation": 1,
  "label": "capture_1",
  "format": "urn:x-nmos:format:audio",
  "codec": "audio/aac",
  "container": "video/mp2t"
}
```
**Required fields:** source_id, format, generation

### Segment (from examples/flow-segment-post.json)
```json
{
  "object_id": "99c27f3f-ab67-47ae-8dd3-e5c146912b50",
  "timerange": "[20:0_21:0)"
}
```
**Required fields:** object_id, timerange

### Webhook (from examples/webhook-post.json)
```json
{
  "url": "https://hook.example.com",
  "api_key_name": "Authorization",
  "api_key_value": "Bearer 21238dksdjqwpqscj9",
  "events": ["flows/created", "flows/updated"]
}
```
**Required fields:** url, events

### Storage Backend (from examples/storage-backends-get-200.json)
```json
{
  "label": "example-store-name",
  "store_type": "http_object_store",
  "provider": "example-cloud-provider",
  "region": "eu-west-1",
  "availability_zone": "a",
  "store_product": "example-storage-product",
  "default_storage": true
}
```
**Required fields:** label, store_type, provider

## Next Steps Needed

### 1. Update Sources.tsx
- Add "Create Source" button
- Add Dialog with form fields: label, description, format
- Format dropdown: urn:x-nmos:format:video, urn:x-nmos:format:audio, urn:x-nmos:format:data

### 2. Create Flows Page
- File: `ui/src/pages/Flows.tsx` exists
- Add "Create Flow" button
- Add Dialog with: source_id (select), label, description, format, codec, container
- Add generation field (default: 1)

### 3. Create Segments Page  
- Update `ui/src/pages/Segments.tsx`
- Add "Create Segment" button
- Add Dialog with: flow_id (select), object_id, timerange

### 4. Create Webhooks Page
- New file: `ui/src/pages/Webhooks.tsx`
- List existing webhooks in table
- Add "Create Webhook" button
- Add Dialog with: url, api_key_name, api_key_value, events (multi-select)

### 5. Create Storage Backends Page
- New file: `ui/src/pages/StorageBackends.tsx`
- List existing backends in table
- Add "Create Backend" button
- Add Dialog with: label, store_type, provider, region, etc.

### 6. Update App.tsx
- Add routes for Webhooks and StorageBackends
- Update navigation

### 7. Update Layout.tsx
- Add nav links for new pages

## Files to Create/Update

1. `ui/src/pages/Webhooks.tsx` - NEW
2. `ui/src/pages/StorageBackends.tsx` - NEW
3. Update `ui/src/pages/Sources.tsx` - Add create dialog
4. Update `ui/src/pages/Flows.tsx` - Add create dialog
5. Update `ui/src/pages/Segments.tsx` - Add create dialog
6. Update `ui/src/App.tsx` - Add routes
7. Update `ui/src/components/Layout.tsx` - Add nav links

This is a large task that will require several pages of code. Each page needs:
- List display (table)
- Create dialog with form validation
- Delete functionality
- Error handling

