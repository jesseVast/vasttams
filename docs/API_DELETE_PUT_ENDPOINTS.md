# DELETE, PUT, and PATCH Endpoints - Testing Checklist

This document lists all DELETE, PUT, and PATCH endpoints per TAMS 8.0 specification and their implementation status.

## 📋 PATCH Operations Status

**TAMS 8.0 does NOT include PATCH operations** per ADR 0025. The specification uses:
- **PUT** for full resource updates or individual property updates
- **DELETE** for removing individual properties
- **PUT** on individual property endpoints for partial updates

This approach was chosen over PATCH to keep the API simple and consistent with REST principles.

## ✅ Sources Endpoints

### Per TAMS 8.0 Spec (ADR 0018):
**Note**: Sources do NOT have PUT/DELETE on the source itself per ADR 0018. They are implicitly created/deleted with flows.

| Method | Endpoint | Description | Status | Notes |
|--------|----------|-------------|--------|-------|
| `GET` | `/sources/{source_id}/tags` | Get all source tags | ✅ Implemented | Returns Tags object |
| `PUT` | `/sources/{source_id}/tags/{name}` | Update/create source tag | ✅ Implemented | Status 204, string value |
| `DELETE` | `/sources/{source_id}/tags/{name}` | Delete source tag | ✅ Implemented | Status 204 |
| `GET` | `/sources/{source_id}/tags/{name}` | Get source tag value | ✅ Implemented | Returns string value |
| `PUT` | `/sources/{source_id}/tags` | ❌ **NOT IN SPEC** | N/A | Bulk tag update not supported - use individual tag operations |
| `PUT` | `/sources/{source_id}/description` | Update description | ✅ Implemented | Status 200/204 |
| `DELETE` | `/sources/{source_id}/description` | Delete description | ✅ Implemented | Status 200/204 |
| `PUT` | `/sources/{source_id}/label` | Update label | ✅ Implemented | Status 200/204 |
| `DELETE` | `/sources/{source_id}/label` | Delete label | ✅ Implemented | Status 200/204 |

### Extended (Not in TAMS 8.0 Spec):
| Method | Endpoint | Description | Status | Notes |
|--------|----------|-------------|--------|-------|
| `DELETE` | `/sources/{source_id}` | Delete source | ✅ Implemented | Extension - requires cascade handling |
| `PUT` | `/sources/{source_id}` | Update source | ❌ **NOT IMPLEMENTED** | Not in spec per ADR 0018 |

---

## ✅ Flows Endpoints

### Per TAMS 8.0 Spec:

| Method | Endpoint | Description | Status | Notes |
|--------|----------|-------------|--------|-------|
| `PUT` | `/flows/{flow_id}` | Update flow | ✅ Implemented | Full flow update |
| `DELETE` | `/flows/{flow_id}` | Delete flow | ✅ Implemented | Hard delete, cascade support |
| `GET` | `/flows/{flow_id}/tags` | Get all flow tags | ✅ Implemented | Returns Tags object |
| `PUT` | `/flows/{flow_id}/tags/{name}` | Update/create flow tag | ✅ Implemented | Status 204, string value |
| `DELETE` | `/flows/{flow_id}/tags/{name}` | Delete flow tag | ✅ Implemented | Status 204 |
| `GET` | `/flows/{flow_id}/tags/{name}` | Get flow tag value | ✅ Implemented | Returns string value |
| `PUT` | `/flows/{flow_id}/tags` | ❌ **NOT IN SPEC** | N/A | Bulk tag update not supported - use individual tag operations |
| `PUT` | `/flows/{flow_id}/description` | Update description | ✅ Implemented | Status 204 |
| `DELETE` | `/flows/{flow_id}/description` | Delete description | ✅ Implemented | Status 204 |
| `PUT` | `/flows/{flow_id}/label` | Update label | ✅ Implemented | Status 204 |
| `DELETE` | `/flows/{flow_id}/label` | Delete label | ✅ Implemented | Status 204 |
| `PUT` | `/flows/{flow_id}/read_only` | Set read-only status | ✅ Implemented | Status 204, boolean value |
| `DELETE` | `/flows/{flow_id}/read_only` | ❌ **NOT IN SPEC** | N/A | read_only only has PUT (set to false) |
| `PUT` | `/flows/{flow_id}/flow_collection` | Update flow collection | ✅ Implemented | Status 201 |
| `DELETE` | `/flows/{flow_id}/flow_collection` | Delete flow collection | ✅ Implemented | Status 204 |
| `PUT` | `/flows/{flow_id}/max_bit_rate` | Update max bit rate | ✅ Implemented | Status 201 |
| `DELETE` | `/flows/{flow_id}/max_bit_rate` | Delete max bit rate | ✅ Implemented | Status 204 |
| `PUT` | `/flows/{flow_id}/avg_bit_rate` | Update avg bit rate | ✅ Implemented | Status 201 |
| `DELETE` | `/flows/{flow_id}/avg_bit_rate` | Delete avg bit rate | ✅ Implemented | Status 204 |

---

## ✅ Flow Segments Endpoints

### Per TAMS 8.0 Spec:

| Method | Endpoint | Description | Status | Notes |
|--------|----------|-------------|--------|-------|
| `DELETE` | `/flows/{flow_id}/segments` | Delete flow segments | ✅ Implemented | Supports timerange and object_id filters |
| `PUT` | `/flows/{flow_id}/segments` | ❌ **NOT IN SPEC** | N/A | Segments are immutable - use DELETE + POST |

**Query Parameters for DELETE:**
- `timerange` (optional): Only delete segments completely covered by timerange
- `object_id` (optional): Filter on object identifier

---

## ✅ Objects Endpoints

### Per TAMS 8.0 Spec:

| Method | Endpoint | Description | Status | Notes |
|--------|----------|-------------|--------|-------|
| `DELETE` | `/objects/{object_id}` | Delete object | ✅ Implemented | Hard delete, includes S3 cleanup |
| `PUT` | `/objects/{object_id}` | ❌ **NOT IN SPEC** | N/A | Objects are immutable |
| `DELETE` | `/objects/{object_id}/instances` | Delete object instance | ✅ Implemented | By label or storage_id, **deletes S3 if controlled** |

**Query Parameters for DELETE instances:**
- `label` (optional): Delete instance with this label
- `storage_id` (optional): Delete instance with this storage_id
- **Note**: One of `label` or `storage_id` MUST be provided

**S3 Deletion Behavior:**
- ✅ **Implemented**: `DELETE /objects/{object_id}/instances` deletes S3 files for controlled instances
- ✅ **Implemented**: `DELETE /objects/{object_id}` deletes all instances and S3 files
- ✅ **Implemented**: Automatic S3 cleanup for unreferenced objects after flow/segment deletion

---

## 🧪 Testing Recommendations

### Critical DELETE Tests:
1. **Flow DELETE with cascade** - Test cascade deletion of segments
2. **Source DELETE with cascade** - Test cascade deletion of flows and segments
3. **Segment DELETE with timerange filter** - Test timerange-based deletion
4. **Segment DELETE with object_id filter** - Test object-based deletion
5. **Object DELETE** - Test deletion when referenced by segments (should fail with dependency)
6. **Object instance DELETE** - Test deleting instances while keeping object
7. **Object instance DELETE with S3 cleanup** - Test that controlled instances delete S3 files
8. **Automatic S3 cleanup** - Test that unreferenced objects are deleted from S3 after flow/segment deletion

### Critical PUT Tests:
1. **Flow PUT** - Test full flow update with all properties
2. **Flow property updates** - Test individual property updates (tags, description, label, etc.)
3. **Flow read_only** - Test setting read-only flag and verifying it blocks modifications
4. **Source property updates** - Test tags, description, label updates

### Critical Tag Tests:
1. **GET all tags** - Test retrieving all tags for source/flow
2. **GET individual tag** - Test retrieving specific tag value
3. **PUT tag** - Test creating new tag and updating existing tag
4. **DELETE tag** - Test deleting individual tags
5. **Tag name encoding** - Test tags with special characters (URL encoding required)
6. **Multiple tags** - Test managing multiple tags on same resource
7. **Tag value types** - Test tags with string values (JSON strings allowed)
8. **Tag conflicts** - Test updating same tag multiple times
9. **Tag deletion** - Test deleting non-existent tag (should return 404)
10. **Tags persistence** - Test tags persist across resource updates

### Edge Cases to Test:
1. **PUT flow to read_only=true** then try to DELETE/PUT - should fail with 403
2. **DELETE flow with segments** - verify segments are deleted and unreferenced objects cleaned up
3. **DELETE segment with timerange** - verify only matching segments are deleted
4. **DELETE object when referenced** - should handle dependency violation
5. **PUT flow with invalid data** - should return 400
6. **DELETE non-existent resource** - should return 404
7. **DELETE controlled instance** - verify S3 file is deleted
8. **DELETE uncontrolled instance** - verify only database record is deleted (S3 file preserved)
9. **DELETE object with multiple instances** - verify all controlled instances delete from S3
10. **Automatic cleanup after partial segment deletion** - verify only truly unreferenced objects are cleaned up

---

## 📝 Implementation Notes

1. **Sources**: Per ADR 0018, Sources should NOT have PUT/DELETE on the endpoint itself. However, we have DELETE implemented as an extension. PUT on source endpoint is NOT implemented (correct per spec).

2. **Segments**: Segments are immutable per TAMS spec. To "modify" a segment, you must DELETE and recreate with POST.

3. **Objects**: Objects are immutable per TAMS spec. Only instances can be deleted.

4. **read_only property**: Only has PUT (no DELETE). To "remove" read_only, set it to `false` via PUT.

5. **Cascade deletion**: Both Sources and Flows support cascade deletion which deletes dependent resources.

6. **S3 Deletion for Object Instances**: 
   - When deleting a controlled instance via `DELETE /objects/{object_id}/instances`, the S3 file is automatically deleted per TAMS 8.0 spec
   - Storage path is extracted from instance metadata (`storage_path`) or parsed from URL
   - Uncontrolled instances do not delete S3 files (database record only)

7. **Automatic S3 Cleanup**:
   - After deleting flows or segments, unreferenced objects are automatically identified and cleaned up
   - Objects with no remaining segment references are deleted from both database and S3
   - This implements TAMS 8.0 spec requirement: "Media Objects that are no longer referenced by any Segments will be deleted"
   - Cleanup happens automatically but failures don't block the deletion operation

---

## 🚨 Known Issues / Missing Features

### Missing from Implementation:
- None identified - all spec-required DELETE/PUT endpoints are implemented ✅

### Extended Features (Beyond Spec):
- `DELETE /sources/{source_id}` - Extension for explicit source deletion
- All other endpoints match TAMS 8.0 specification

---

## 🗂️ S3 Deletion Implementation Details

### S3 Deletion Features

#### 1. Object Instance Deletion with S3 Cleanup

**Endpoint**: `DELETE /objects/{object_id}/instances`

**Behavior**:
- When deleting a controlled instance (`controlled: true`), the S3 file is automatically deleted
- Storage path is determined from:
  1. Instance metadata (`metadata.storage_path`)
  2. URL parsing (fallback)
- Uncontrolled instances (`controlled: false` or `null`) only delete database record

**Testing Steps**:
```
1. Create an object with a controlled instance
2. Upload file to S3 via presigned URL
3. Verify file exists in S3
4. DELETE /objects/{object_id}/instances?label={label}
5. Verify instance removed from database
6. Verify S3 file deleted (for controlled instances)
```

#### 2. Automatic Cleanup of Unreferenced Objects

**Trigger**: After `DELETE /flows/{flow_id}` or `DELETE /flows/{flow_id}/segments`

**Behavior**:
- Automatically identifies objects with no remaining segment references
- Deletes unreferenced objects from database and S3 storage
- Implements TAMS 8.0 spec: "Media Objects that are no longer referenced by any Segments will be deleted"

**Testing Steps**:
```
1. Create a flow with segments referencing objects
2. Verify objects exist in database and S3
3. DELETE /flows/{flow_id}
4. Verify flow and segments deleted
5. Verify unreferenced objects deleted from database
6. Verify unreferenced objects deleted from S3
7. Verify objects still referenced by other flows are preserved
```

### S3 Deletion Methods

The implementation uses multiple methods to delete from S3:

1. **Primary**: `S3Client.delete_object(key=storage_path)` if available
2. **Fallback**: `S3Client.delete(key=storage_path)` if available
3. **Boto3**: Direct boto3 client if S3Client methods unavailable

### Storage Path Resolution

Storage paths are determined in this order:
1. Object/instance metadata: `metadata.storage_path`
2. URL parsing: Extract path from `url` field
3. Default: Uses TAMS path format: `{tams_storage_path}/{year}/{month}/{date}/{object_id}`

### Error Handling

- S3 deletion failures are logged but don't block database deletion
- Unreferenced object cleanup failures are logged but don't fail the flow/segment deletion
- This ensures data consistency while maintaining system reliability

---

## 🔖 Tag Operations Details

### Tag Endpoints Summary:

**Sources:**
- `GET /sources/{source_id}/tags` - Returns all tags as JSON object
- `GET /sources/{source_id}/tags/{name}` - Returns single tag value as string
- `PUT /sources/{source_id}/tags/{name}` - Create or update tag (body: string value)
- `DELETE /sources/{source_id}/tags/{name}` - Delete tag

**Flows:**
- `GET /flows/{flow_id}/tags` - Returns all tags as JSON object
- `GET /flows/{flow_id}/tags/{name}` - Returns single tag value as string
- `PUT /flows/{flow_id}/tags/{name}` - Create or update tag (body: string value)
- `DELETE /flows/{flow_id}/tags/{name}` - Delete tag

### Tag Testing Scenarios:

1. **Basic CRUD:**
   - Create tag: `PUT /sources/{id}/tags/ingested_by` with body `"service_v1"`
   - Read tag: `GET /sources/{id}/tags/ingested_by` → `"service_v1"`
   - Update tag: `PUT /sources/{id}/tags/ingested_by` with body `"service_v2"`
   - Delete tag: `DELETE /sources/{id}/tags/ingested_by`

2. **Special Characters:**
   - Tag names with special chars must be URL encoded
   - Example: `tag:name:with:colons` → URL encode as `tag%3Aname%3Awith%3Acolons`

3. **Tag Values:**
   - Tag values are strings
   - JSON strings can be stored (e.g., `"{\"key\":\"value\"}"`)
   - Empty strings are valid

4. **Multiple Tags:**
   - Resources can have multiple tags
   - Tags are independent - updating one doesn't affect others
   - Use `GET /{resource}/tags` to see all tags at once

5. **Error Cases:**
   - PUT tag on non-existent resource → 404
   - GET tag that doesn't exist → 404
   - DELETE tag that doesn't exist → 404
   - Invalid tag name in path → 400/404

---

## 📚 Reference

- **TAMS 8.0 Spec**: `tams-8.0/api/TimeAddressableMediaStore.yaml`
- **ADR 0018**: `tams-8.0/docs/adr/0018-restrict-direct-source-modification.md` - Sources cannot be directly PUT/DELETEd
- **ADR 0025**: `tams-8.0/docs/adr/0025-flow-property-updates.md` - Flow property update restrictions (explicitly rejects PATCH)

