# Segment Query Parameters Analysis

## Current Implementation Status

The segments router now implements the following query parameters:

### ✅ **Implemented Parameters**
- ✅ `timerange` - Filter by time range
- ✅ `object_id` - Filter on object identifier  
- ✅ `reverse_order` - Return segments in reverse time order
- ✅ `verbose_storage` - Include storage metadata in get_urls
- ✅ `accept_get_urls` - Filter URLs by labels
- ✅ `accept_storage_ids` - Filter URLs by storage IDs
- ✅ `presigned` - Filter presigned vs non-presigned URLs
- ✅ `limit` - Limit number of results  
- ✅ `offset` - Offset for pagination

### ❌ **Still Missing Parameters**
- ❌ `page` - Cursor-based pagination

## Missing Query Parameters (Per TAMS API Spec)

### 1. **object_id** - Filter on Object Identifier
- **Spec**: Filter on object identifier
- **Type**: `string`
- **Purpose**: Return only segments that reference a specific media object
- **Implementation**: Add to GET endpoint query parameters

### 2. **reverse_order** - Reverse Time Order
- **Spec**: Return segments in reverse time order
- **Type**: `boolean` (default: false)
- **Purpose**: Sort segments by timestamp in descending order
- **Implementation**: Add sorting logic to segment retrieval

### 3. **verbose_storage** - Storage Metadata
- **Spec**: Include storage metadata in `get_urls`
- **Type**: `boolean` (default: false)
- **Purpose**: When false, only `url`, `presigned`, and `label` in get_urls
- **Implementation**: Control what storage metadata is included in response

### 4. **accept_get_urls** - Filter URLs by Labels
- **Spec**: Comma-separated list of labels of flow segment `get_urls` to include
- **Type**: `string` with pattern `^([^,]+(,[^,]+)*)?$`
- **Purpose**: Filter which get_urls are returned based on their labels
- **Implementation**: Filter get_urls array based on label matching

### 5. **accept_storage_ids** - Filter URLs by Storage IDs
- **Spec**: Comma-separated list of storage_id UUIDs to include
- **Type**: `string` with UUID pattern
- **Purpose**: Filter get_urls based on storage backend IDs
- **Implementation**: Filter get_urls array based on storage_id matching

### 6. **presigned** - Filter Presigned URLs
- **Spec**: Filter presigned vs non-presigned URLs
- **Type**: `boolean`
- **Purpose**: 
  - `true`: Only presigned URLs (presigned=true)
  - `false`: Only non-presigned URLs (presigned=false)
  - `null`: Both types
- **Implementation**: Filter get_urls based on presigned property

### 7. **page** - Cursor-based Pagination
- **Spec**: Opaque string for cursor-based pagination
- **Type**: `string`
- **Purpose**: Get next page of results using cursor from previous response
- **Implementation**: Replace offset-based pagination with cursor-based

## Additional Spec Requirements

### Response Headers
The spec requires these headers in GET responses:
- ✅ `Link` - References to cursors for paging
- ❌ `X-Paging-Limit` - Current limit being used
- ❌ `X-Paging-Timerange` - Timerange for returned data
- ❌ `X-Paging-Count` - Number of items in response
- ❌ `X-Paging-Reverse-Order` - Whether items are in reverse order
- ❌ `X-Paging-NextKey` - Next page cursor

### Advanced Features
- **Bulk Operations**: POST supports both single segment and array of segments
- **Partial Success**: POST can return 200 with failed segments list
- **Timerange Filtering**: DELETE supports timerange-based deletion
- **Object ID Filtering**: DELETE supports object_id-based deletion

## Implementation Status

### ✅ **Phase 1: Core Filtering - COMPLETED**
1. ✅ `object_id` - Basic object filtering
2. ✅ `reverse_order` - Sorting capability  
3. ✅ `verbose_storage` - Storage metadata control

### ❌ **Phase 2: URL Filtering - PENDING**
4. `accept_get_urls` - Label-based URL filtering
5. `accept_storage_ids` - Storage ID-based URL filtering
6. `presigned` - Presigned URL filtering

### ❌ **Phase 3: Advanced Pagination - PENDING**
7. `page` - Cursor-based pagination
8. Response headers for pagination metadata

## What Was Implemented

### **object_id Filtering**
- **GET /flows/{flowId}/segments?object_id=xxx** - Returns only segments with specified object_id
- **DELETE /flows/{flowId}/segments?object_id=xxx** - Deletes only segments with specified object_id
- **HEAD /flows/{flowId}/segments?object_id=xxx** - Supports object_id parameter

### **reverse_order Sorting**
- **GET /flows/{flowId}/segments?reverse_order=true** - Returns segments in descending order by timerange
- **GET /flows/{flowId}/segments?reverse_order=false** - Returns segments in ascending order (default)
- Sorts by `timerange.value` field

### **verbose_storage Control**
- **GET /flows/{flowId}/segments?verbose_storage=true** - Includes full storage metadata in get_urls
- **GET /flows/{flowId}/segments?verbose_storage=false** - Only includes url, presigned, and label in get_urls
- Filters out additional storage metadata for performance

### **Combined Parameters**
- All parameters can be combined: `?object_id=xxx&reverse_order=true&verbose_storage=false&limit=10&offset=0`
- Parameters are applied in order: object_id filtering → sorting → verbose_storage filtering → pagination

## Test Coverage Status

### ✅ **Covered by Tests**
- ✅ Object ID filtering (GET and DELETE)
- ✅ Reverse order sorting (ascending/descending)
- ✅ Storage metadata variations (verbose_storage)
- ✅ Combined parameter testing
- ✅ Basic pagination (limit/offset)

### ❌ **Still Missing Test Coverage**
- ❌ URL filtering scenarios (accept_get_urls, accept_storage_ids, presigned)
- ❌ Advanced pagination (cursor-based)
- ❌ Response header validation
- ❌ Edge cases and error conditions

## Next Steps

1. Document current implementation gaps
2. Implement Phase 1 parameters
3. Update tests to cover new parameters
4. Implement Phase 2 parameters
5. Add response headers
6. Implement Phase 3 cursor pagination
