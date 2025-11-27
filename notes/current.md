# TAMS Project - Current Status & TODO

**Last Updated**: November 27, 2025  
**Status**: Search & Tags Enhancements in Progress

## ✅ Recent Updates (November 27, 2025)

1. **Flow & Source Tag Editing UI Improvements**
   - **Sources**: Separated tag editing into dedicated edit icon next to info icon
     - Info icon opens read-only DetailModal
     - Edit icon opens TagEditModal directly
   - **Flows**: Combined tag and flow property editing into single modal
     - Single edit icon opens EditFlowModal with tabs (Properties and Tags)
     - Tag editing integrated directly into modal (no separate modal)
     - Compact layout with reduced spacing and side-by-side fields

2. **UI Cleanup**
   - Removed source ID filter from flows table
   - Added tags display at top of segments page (year, genre, sport)
   - Made EditFlowModal more compact with tabbed interface

3. **Tag Visibility Improvements**
   - Sources and flows tables display `year`, `genre`, and `sport` tags (chips with values).
   - Backend list endpoints now enrich responses with tags (including cache hits).

4. **HLS Direct URL Testing**
   - Playlist endpoint accepts `use_proxy`; UI requests direct presigned URLs while testing VAST-side CORS.
   - Manifest rewriting only appends auth tokens when proxying is enabled.

5. **Multiview Autoplay**
   - Multiview player respects the global Auto-Play toggle (previously forced off).
   - Keeps scrollable and multiview behavior consistent for operators.

## 🎯 **CURRENT FOCUS: SEARCH AND TAGS ENHANCEMENT** (November 23, 2025)

### **📋 TODO: Search and Tags Implementation**

**Status**: Planning Phase  
**Priority**: High

This document tracks the implementation of search functionality, tag enhancements, and related improvements across the UI, CLI applications, and server components.

---

## UI Tasks

### 1. Show Tags in Info Modals
**Status**: Pending  
**Priority**: Medium

**Description**: Display tags information in all info modals throughout the UI.

**Requirements**:
- Show tags in **flows** info modals
- Show tags in **sources** info modals
- For **segments**, use tags from the underlying object (not segment-level tags)

**Files to Modify**:
- Flow info modal component
- Source info modal component
- Segment info modal component

**Notes**:
- Segments should display tags from their associated object
- Ensure consistent tag display format across all modals

---

### 2. Investigate Source Deletion Issue
**Status**: Pending  
**Priority**: High

**Description**: Investigate why deleting sources via UI does not delete underlying flows and segments, while deleting flows correctly cleans up dependent resources.

**Requirements**:
- Investigate source deletion endpoint behavior
- Compare with flow deletion cascade logic
- Ensure source deletion properly cascades to flows and segments
- Fix any inconsistencies in deletion behavior

**Investigation Areas**:
- Source deletion endpoint implementation
- Cascade delete logic for sources
- UI deletion request handling
- Backend cascade delete service

**Expected Behavior**:
- Deleting a source should delete all associated flows
- Deleting flows should delete all associated segments
- Both should follow TAMS cascade rules

---

### 3. Background Delete Operations
**Status**: Pending  
**Priority**: High

**Description**: Make all delete operations in the UI use background tasks that return immediately.

**Requirements**:
- All delete operations should be asynchronous
- UI should return immediately after initiating delete
- Use deletion request system (similar to segment deletion)
- Show deletion status/progress to user
- Poll for completion status

**Implementation Notes**:
- Leverage existing deletion request service
- Update UI to handle 202 Accepted responses
- Add status polling for deletion requests
- Show progress indicators in UI

**Files to Modify**:
- Source deletion UI components
- Flow deletion UI components
- Segment deletion UI components (may already be implemented)
- Deletion request status polling logic

---

### 4. Search Page Implementation
**Status**: Pending  
**Priority**: High

**Description**: Add a comprehensive search page in the left navigation pane between dashboard and sources.

**Requirements**:

#### Navigation
- Add "Search" item in left pane between Dashboard and Sources
- Opens new page in main section

#### Search Functionality
- Search tags across:
  - Flows
  - Sources
  - Objects
  - Segments
- Search by flow data (codec, etc.) in a compact manner
- Text-based search input

#### Results Display
- Results shown as table below search window
- Table includes links to the data type (flow, source, object, segment)
- Object data shown only with tags
- Compact, readable format

#### Object Flow Creation
- Enable selecting objects from search results
- Allow creating new flow based on selected objects
- Multi-select capability for objects

**Files to Create**:
- `ui/src/components/SearchPage.tsx`
- `ui/src/components/SearchResults.tsx`
- `ui/src/components/SearchFilters.tsx`

**Files to Modify**:
- Left navigation component
- Routing configuration
- API client for search endpoints

**API Dependencies**:
- Requires server endpoints from tasks 6 and 7

---

## CLI Application Tasks

### 5. Add Tags Support to CLI
**Status**: Pending  
**Priority**: Medium

**Description**: Enable adding tags via CLI applications with flexible parsing.

**Requirements**:
- Support comma-separated tags
- Pattern: `key1:value1,key2=value2` (support both `:` and `=` separators)
- Values can contain spaces (handle quoted values)
- Parse and validate tag format
- Apply tags to appropriate entities (flows, sources, objects)

**Parsing Rules**:
- Comma-separated list
- Key-value pairs with `:` or `=` separator
- Values with spaces should be quoted: `key:"value with spaces"`
- Unquoted values without spaces work normally
- Handle edge cases (empty values, special characters)

**Files to Modify**:
- `apps/folder_ingestor/` - Add tag parameter
- `apps/stream_ingestor/` - Add tag parameter
- Tag parsing utility function

**Example Usage**:
```bash
# Using colon separator
--tags "location:studio,type:interview,status:approved"

# Using equals separator
--tags "location=studio,type=interview,status=approved"

# Mixed separators
--tags "location:studio,type=interview"

# Values with spaces
--tags "location:New York,type:live broadcast"
```

---

## Server Tasks

### 6. Universal Search Endpoint
**Status**: Pending  
**Priority**: High

**Description**: Create a universal search endpoint under `/api/vast` to support the search functionality described in task 4.

**Requirements**:
- Endpoint: `POST /api/vast/search` or `GET /api/vast/search`
- Support searching across:
  - Flows (by tags, codec, and other metadata)
  - Sources (by tags and metadata)
  - Objects (by tags)
  - Segments (by tags from underlying objects)
- Return unified results with entity type and links
- Support filtering and pagination

**Request Format**:
```json
{
  "query": "search text",
  "tags": {"key": "value"},
  "entity_types": ["flow", "source", "object", "segment"],
  "flow_filters": {
    "codec": "h264",
    ...
  },
  "limit": 100,
  "offset": 0
}
```

**Response Format**:
```json
{
  "results": [
    {
      "entity_type": "flow",
      "entity_id": "flow_123",
      "tags": {...},
      "metadata": {...},
      "link": "/api/flows/flow_123"
    },
    ...
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

**Files to Create**:
- `src/server/vasttamsserver/vast/search_service.py`
- `src/server/vasttamsserver/vast/search_schemas.py`

**Files to Modify**:
- `src/server/vasttamsserver/vast/router.py` - Add search endpoint

---

### 7. Searchable Items Metadata Endpoint
**Status**: Pending  
**Priority**: Medium

**Description**: Create an endpoint in `/api/vast` that provides metadata about searchable items needed for the search UI (task 4).

**Requirements**:
- Endpoint: `GET /api/vast/search/metadata` or `/api/vast/searchable-items`
- Return available search fields, filters, and options
- Include:
  - Available tag keys across entities
  - Flow metadata fields (codec, resolution, etc.)
  - Entity type information
  - Filter options and constraints

**Response Format**:
```json
{
  "entity_types": ["flow", "source", "object", "segment"],
  "tag_keys": {
    "flow": ["location", "type", "status", ...],
    "source": ["location", "type", ...],
    "object": ["location", "type", ...],
    "segment": []  // Uses object tags
  },
  "flow_filters": {
    "codec": ["h264", "h265", "vp9", ...],
    "resolution": ["1080p", "4k", ...],
    ...
  },
  "searchable_fields": {
    "flow": ["label", "description", "codec", ...],
    "source": ["label", "description", ...],
    ...
  }
}
```

**Files to Create/Modify**:
- `src/server/vasttamsserver/vast/router.py` - Add metadata endpoint
- `src/server/vasttamsserver/vast/search_service.py` - Add metadata collection logic

---

### 8. Enhanced Vector Search Response
**Status**: Pending  
**Priority**: Medium

**Description**: Update vector search to return additional metadata in results.

**Requirements**:
- Vector search should return:
  - `object_ids`: List of matching object IDs
  - `summary`: Summary/description of the search
  - `embedding_date`: When the embedding was created
  - `embedding_model`: Model used for embedding

**Current State**: Review existing vector search implementation

**Response Format**:
```json
{
  "object_ids": ["obj_123", "obj_456", ...],
  "summary": "Search results for query: ...",
  "embedding_date": "2025-01-27T10:00:00Z",
  "embedding_model": "text-embedding-ada-002",
  "distances": [0.85, 0.92, ...],
  "total": 25
}
```

**Files to Modify**:
- Vector search service/endpoint
- Vector search response schemas

---

### 9. Embedding Model Configuration
**Status**: Pending  
**Priority**: Medium

**Description**: Update configuration to support embedding model links and details.

**Requirements**:
- Add configuration section for embedding models
- Support:
  - Model name
  - Endpoint URL
  - Endpoint type (see `~/Developer/gitlab/jthaloor-ai` for supported types)
  - Authentication details if needed
  - Model-specific parameters

**Reference**: Check `~/Developer/gitlab/jthaloor-ai` for supported embedding models and endpoint types

**Configuration Format** (YAML):
```yaml
embedding:
  models:
    - name: "text-embedding-ada-002"
      endpoint: "https://api.openai.com/v1/embeddings"
      endpoint_type: "openai"
      api_key_env: "OPENAI_API_KEY"
    - name: "custom-model"
      endpoint: "http://localhost:8000/embed"
      endpoint_type: "custom"
      headers:
        Authorization: "Bearer ${CUSTOM_API_KEY}"
```

**Files to Modify**:
- `config/config.yaml.example` - Add embedding configuration
- `src/server/vasttamsserver/core/config.py` - Parse embedding config
- `src/server/vasttamsserver/vast/embedding_service.py` - Use config (may need to create)

**Files to Create**:
- Embedding service/client for different endpoint types

---

### 10. Text-to-Embedding Search
**Status**: Pending  
**Priority**: High

**Description**: Add support for searching by text in VAST. Convert text to embedding, perform vector search, return object data.

**Requirements**:
- Endpoint: `POST /api/vast/search/text` or parameter in main search endpoint
- Accept text input
- Send text to embedding endpoint (using config from task 9)
- Get embedding vector back
- Perform vector search using embedding
- Return object data (not just IDs)

**Flow**:
1. Receive text query
2. Call embedding service with text
3. Get embedding vector
4. Perform vector search using embedding
5. Retrieve full object data for matching object_ids
6. Return combined results

**Request Format**:
```json
{
  "text": "search query text",
  "limit": 10,
  "threshold": 0.8  // similarity threshold
}
```

**Response Format**:
```json
{
  "query_text": "search query text",
  "embedding_model": "text-embedding-ada-002",
  "embedding_date": "2025-01-27T10:00:00Z",
  "results": [
    {
      "object_id": "obj_123",
      "object_data": {...},
      "similarity": 0.92,
      "tags": {...}
    },
    ...
  ],
  "total": 15
}
```

**Files to Create**:
- `src/server/vasttamsserver/vast/text_search_service.py`
- Embedding client/service

**Files to Modify**:
- `src/server/vasttamsserver/vast/router.py` - Add text search endpoint
- Vector search service - Integrate with text search

**Dependencies**:
- Task 9 (embedding model configuration)
- Task 8 (enhanced vector search response)

---

## Implementation Order

### Phase 1: Foundation (Server)
1. Task 9: Embedding model configuration
2. Task 8: Enhanced vector search response
3. Task 10: Text-to-embedding search

### Phase 2: Search Infrastructure (Server)
4. Task 7: Searchable items metadata endpoint
5. Task 6: Universal search endpoint

### Phase 3: UI Search
6. Task 4: Search page implementation

### Phase 4: Tag Enhancements
7. Task 1: Show tags in info modals
8. Task 5: Add tags support to CLI

### Phase 5: Deletion Fixes
9. Task 2: Investigate source deletion issue
10. Task 3: Background delete operations

---

## Dependencies

- **Task 4** depends on **Tasks 6 and 7** (search endpoints)
- **Task 10** depends on **Task 9** (embedding config) and **Task 8** (vector search)
- **Task 3** may leverage existing deletion request infrastructure

---

## Notes

- Review existing deletion request service for task 3
- Check `~/Developer/gitlab/jthaloor-ai` for embedding model reference
- Ensure all search functionality follows TAMS compliance
- Consider performance implications of cross-entity searches
- Vector search should leverage existing VAST vector capabilities

---

## Related Documentation

- TAMS API Specification: `./tams-8.0/api/`
- TAMS App Notes: `./tams-8.0/docs/appnotes/`
- Current deletion request implementation (see task 3 notes)
- Vector search implementation (see task 8 notes)

---

## 🎯 **CURRENT FOCUS: VECTOR TABLE SEPARATION** (November 20, 2025)

### **✅ COMPLETED: Vectors Moved to Separate Table**

**Implementation**: Vectors are now stored in separate `object_vector` table managed by vast module.

#### **Architecture**
- **Separate Table**: `object_vector` table (not part of TAMS specification)
- **Location**: Managed by vast module (`vast/schemas.py`)
- **Rationale**: Vectors are not part of TAMS spec, managed separately from TAMS objects
- **vastdbmanager 1.1.10+**: Automatic query routing based on table type
  - Vector operations → ADBC/vector_client (via query builder `search()`)
  - Regular queries → Trino (objects, segments, flows tables)

#### **Operations**
- **INSERT/UPSERT**: `insert_record("object_vector", ...)` - automatically routes to ADBC
- **QUERY/SEARCH**: Query builder `search()` method - automatically routes to ADBC
- **DELETE**: Standard delete operations
- **No UPDATE**: Only INSERT (upsert) - `insert_record` handles replacements

#### **Query Pattern**
1. Vector search uses `vast_db.search("object_vector").vector(...)` to get object_ids with distances
2. Extract object_ids from vector search results
3. Use `execute_sql()` for JOIN query excluding object_vector table (avoids Trino reading vectors)
4. Combine JOIN results (objects, segments, flows) with distances from vector search

#### **Benefits**
- Eliminates Trino errors when querying objects table (no vector columns in schema)
- Clean separation: TAMS objects table contains only TAMS-compliant fields
- Automatic routing: vastdbmanager handles vector vs regular query routing
- Performance: Vector operations use optimized ADBC path

**See**: `notes/edits/2025-11-20.md` for detailed implementation notes

---

## 🎯 **RECENT COMPLETED: PERFORMANCE OPTIMIZATIONS** (November 18, 2025)

### **✅ COMPLETED: Analytics Caching and Storage Backend Query Optimization**
**Status**: ✅ **COMPLETED** - Analytics endpoints cached, storage backend queries optimized

#### **🏗️ Key Achievements**
- **Analytics Endpoint Caching**: Added Redis caching (5 min TTL) for `/analytics/sources` and `/analytics/flows`
  - Prevents duplicate queries when React StrictMode causes double renders
  - Reduces database load for expensive JOIN queries
  - Uses `refresh=true` query parameter to bypass cache when needed

- **Storage Backends Query Optimization**: Added caching for full storage backends list
  - Cache key: `storage_backends:list` (5 min TTL)
  - Eliminated repeated `SELECT * FROM storage_backends` queries
  - Always resolve and store `storage_id` at object creation time

- **Performance Impact**: Flow segments endpoint improved from ~18s to ~2s (9x faster)

#### **📝 Files Modified**
- `src/server/vasttamsserver/analytics/router.py` - Added Redis caching with datetime serialization
- `src/server/vasttamsserver/segments/get_url_factory.py` - Added storage backends list caching
- `src/server/vasttamsserver/common/storage/main_service.py` - Always resolve storage_id at creation

---

## 🎯 **PREVIOUS FOCUS: CONFIGURATION FILE IMPROVEMENTS**

### **✅ COMPLETED: YAML CONFIGURATION SUPPORT** (January 27, 2025)
**Status**: ✅ **COMPLETED** - YAML config file support added with backward compatibility

#### **🏗️ Key Achievements**
- **YAML Support**: Added support for YAML configuration files (`.yaml`, `.yml`)
  - Native comment support for documentation
  - More readable than JSON for nested structures
  - Backward compatible with existing JSON configs
  
- **File Priority**: Config loader checks YAML files in multiple locations
  - Priority: production > development, .yaml > .yml
  - Supports: `/etc/tams/config.yaml`, `/etc/tams/config.yml`
  - Development: `config/config.yaml`, `config/config.yml`

- **Dependencies**: Added `pyyaml>=6.0` to requirements.txt
- **Documentation**: Updated `config/README.md` with YAML format information
- **Example**: Created `config/config.yaml.example` with helpful comments

#### **📝 Files Modified**
- `src/server/requirements.txt` - Added pyyaml>=6.0
- `src/server/vasttamsserver/core/config.py` - Added YAML parsing with backward compatibility
- `config/README.md` - Updated with YAML format documentation

#### **📝 Files Created**
- `config/config.yaml.example` - Example YAML config with comments
- `docs/CONFIG_FORMAT_RECOMMENDATION.md` - Detailed comparison of config formats

#### **💡 Benefits**
- **Comments**: Can now document settings directly in config files
- **Readability**: YAML is more human-readable than JSON
- **Backward Compatible**: Existing JSON configs continue to work
- **No Breaking Changes**: Seamless migration path

---

## 🎯 **PREVIOUS FOCUS: NON-BLOCKING DELETION REQUESTS**

### **✅ COMPLETED: NON-BLOCKING DELETION REQUESTS IMPLEMENTATION** (November 10, 2025)
**Status**: ✅ **COMPLETED** - Non-blocking deletion requests implemented with hybrid quantity/time thresholds, full client support

#### **🏗️ Key Achievements**
- **Deletion Request Service**: Complete service for managing async deletions
  - Creates, stores, and processes deletion requests
  - Processes in batches of 50 segments
  - Updates status: created → started → done/error
  - Handles "all segments" deletion case

- **Hybrid Threshold System**: Smart deletion routing
  - **Quantity Threshold**: >50 segments → immediate async deletion (202 Accepted)
  - **Time Threshold**: ≤50 segments with 30s timeout → switch to async if timeout
  - Small, fast deletions remain synchronous (200/204)

- **Client Support**: Full 202 response handling
  - Updated segment deletion API to handle 202 responses
  - Created `TAMSDeletionRequest` domain object
  - Added `get_deletion_request()` and `list_deletion_requests()` to client
  - Easy status polling and progress tracking

- **Comprehensive Tests**: Full test coverage
  - 6 unit tests for deletion service
  - 6 integration tests for async deletion flow
  - 6 client tests for deletion request functionality
  - Updated existing tests for 202 response handling

#### **📊 Test Results**
- **Unit Tests**: ✅ 6/6 passing (deletion service)
- **Client Tests**: ✅ 6/6 passing (deletion request API and domain)
- **Integration Tests**: ✅ Ready (require server)

#### **📝 Files Created**
- `src/server/vasttamsserver/service/deletion_service.py` (391 lines)
- `src/client/vasttamsclient/api/deletion_requests.py` (38 lines)
- `src/client/vasttamsclient/domain/deletion_request.py` (95 lines)
- `tests/service/test_deletion_service.py` (171 lines)
- `tests/segments/test_deletion_requests.py` (412 lines)
- `tests/client/test_deletion_requests.py` (141 lines)

#### **📝 Files Modified**
- `src/server/vasttamsserver/segments/router.py` - Hybrid threshold logic
- `src/server/vasttamsserver/common/storage/main_service.py` - Deletion request methods
- `src/client/vasttamsclient/api/segments.py` - 202 response handling
- `src/client/vasttamsclient/domain/flow.py` - Return deletion request info
- `src/client/vasttamsclient/domain/segment.py` - Return deletion request info
- `src/client/vasttamsclient/client.py` - Deletion request methods
- Multiple test files updated

### **✅ COMPLETED: FLOW TAG ARRAY FIX & READ-ONLY PROTECTION** (November 9, 2025)
**Status**: ✅ **COMPLETED** - Flow tag array retrieval fixed, read-only flow protection implemented, Docker management scripts ready

#### **🏗️ Key Achievements**
- **Flow Tag Array Retrieval Fix**: Fixed 500 error when retrieving array tag values
  - Updated `get_flow_tag` endpoint to detect array values
  - Returns arrays as JSON with `application/json` content type
  - Returns strings as plain text with `text/plain` content type
  - Handles both list objects and JSON-encoded strings
  - Result: `test_get_flow_tag_array` now passes

- **Read-Only Flow Protection**: Implemented comprehensive protection
  - Added `_check_flow_not_read_only()` helper function
  - Added checks to all flow update/delete endpoints (9 endpoints total)
  - Read-only flows return `403 Forbidden` when modification attempted
  - `PUT /flows/{flow_id}/read_only` remains unprotected (allows unlocking)
  - Result: `test_read_only_flow_update` now passes

- **Docker Management Scripts**: Made scripts container-ready
  - Updated all 7 management scripts for container compatibility
  - Scripts automatically detect container vs development environment
  - Added comprehensive documentation for container usage
  - Scripts available at `/app/mgmt/` in container
  - Result: All scripts work in both container and development environments

- **Logging Documentation**: Created comprehensive logging guide
  - Created `docker/LOGGING.md` with full documentation
  - Covers console logs, file logs, volume persistence, rotation
  - Production considerations and troubleshooting
  - Updated `docker/README.md` with logging section

#### **📊 Test Results**
- **Flow Tag Array**: ✅ `test_get_flow_tag_array` passing
- **Read-Only Protection**: ✅ `test_read_only_flow_update` passing
- **Management Scripts**: ✅ All scripts tested in container
- **Documentation**: ✅ Comprehensive guides created

#### **📝 Files Modified**
- `src/server/vasttamsserver/flows/router.py` - Tag array fix, read-only protection
- `docker/Dockerfile` - Made scripts executable
- `docker/README.md` - Added logging and management script sections
- `docker/LOGGING.md` - New comprehensive logging guide
- `mgmt/*.py` (7 files) - Container compatibility updates
- `mgmt/README.md` - Added container usage examples

### **✅ COMPLETED: TEST AUTHENTICATION & CONTENT-TYPE FIXES** (October 31, 2025)
**Status**: ✅ **COMPLETED** - Test infrastructure updated, content-type fixes applied, S3 uploads working

#### **🏗️ Key Achievements**
- **Test Authentication Infrastructure**: Added `auth_headers` fixture to conftest.py
  - Updated 4 test files to use authentication (sources, flows, segments)
  - 103 tests now passing with authentication
  - Pattern established for remaining 24 tests

- **Content-Type Serialization Fix**: Fixed `content-type` field serializing as None
  - Root cause: Pydantic alias handling requires `model_validate()` with alias key
  - Fixed in `segments/service.py` and `common/storage/main_service.py`
  - Result: `test_storage_allocation_with_content_type` now passes

- **S3 Upload Fix**: Fixed 403 Forbidden errors
  - Added `Content-Type` header to S3 uploads matching presigned URL signature
  - Updated `upload_to_s3()` to extract and use `content-type` from response
  - Result: S3 uploads now successful

- **Presigned URL Credential Validation**: Fixed `InvalidAccessKeyId` errors
  - Added validation to ensure credentials are non-empty before use
  - Falls back to default client if backend credentials invalid
  - Result: Presigned URLs include valid credentials

- **Dynamic Video Discovery**: Refactored `ingest_test_data.py`
  - Removed hardcoded video file names
  - Added `discover_video_files()` function that scans `test_videos/` directory
  - Supports multiple formats: `.mp4`, `.ts`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`
  - Uses actual frame rate from video metadata for segment creation
  - Result: Script automatically processes any videos without code changes

- **Test Video Creation**: Created test videos for HLS and HTML5
  - `test_4k_5sec_hls.ts` - 4K HLS-compatible video (3840x2160, 25fps)
  - `test_480p_5sec.mp4` - 480p HTML5-compatible video (854x480, 30fps)

#### **📊 Test Results**
- **With Authentication**: ✅ 103 tests passing
- **Content-Type Fix**: ✅ `test_storage_allocation_with_content_type` passing
- **Video Discovery**: ✅ Successfully discovers and processes videos
- **S3 Uploads**: ✅ Working with content-type headers
- **Presigned URLs**: ✅ Valid credentials included

#### **⏳ Remaining Work**
- Update 24 test files to add `auth_headers` parameter
- Investigate 500 errors in objects endpoints

### **✅ COMPLETED: SOURCE CASCADE DELETE IMPLEMENTATION** (October 27, 2025)
**Status**: ✅ **COMPLETED** - Cascade delete implemented and tests updated

#### **🏗️ Key Achievements**
- **Source Cascade Delete**: Implemented proper cleanup of dependent resources
  - Added `_cascade_delete_flows` method in SourceStorageService
  - Handles both columnar and row-oriented VAST query results
  - Deletes all segments for dependent flows before deleting flows
  - Returns 409 Conflict when cascade=False and dependencies exist
  - Comprehensive debug logging for cascade operations

- **TAMS 8.0 Compliance Updates**: Updated tests for TAMS 8.0 specification
  - Changed from PUT /sources/{id} to PUT /sources/{id}/label and PUT /sources/{id}/description
  - Uses query parameters for partial updates
  - Aligns with TAMS 8.0 specification requirements

- **Test Improvements**:
  - Added cascade delete tests (test_delete_source_with_cascade_deletes_flows, test_delete_source_without_cascade_prevents_deletion)
  - Added segment deletion tests per ADR-0004
  - Updated format validation for supported formats (video/audio/data)
  - Removed problematic service mock tests (circular import issues)

#### **📊 Test Results**
- **Source Cascade Delete**: ✅ Working correctly (cascade=True deletes flows, cascade=False returns 409)
- **TAMS 8.0 Partial Updates**: ✅ Aligned with specification
- **Segment Deletion**: ✅ Per ADR-0004 compliance
- **Format Validation**: ✅ Updated for supported formats

#### **Files Modified**
- `src/vasttams/sources/router.py` - Added cascade logging
- `src/vasttams/sources/service.py` - Implemented cascade delete with flow/segment cleanup
- `tests/sources/test_database.py` - Added cascade delete tests
- `tests/sources/test_crud.py` - Updated for TAMS 8.0 partial updates
- `tests/sources/test_endpoint.py` - Updated for TAMS 8.0 partial updates
- `tests/sources/test_compliance.py` - Fixed format validation
- `tests/segments/test_database.py` - Added segment deletion tests
- `tests/flows/test_mock.py` - Removed problematic mock tests

## 🎯 **PREVIOUS FOCUS: TAMS APPNOTES INTEGRATION**

### **✅ COMPLETED: INTEGRATION PLAN CREATION**
**Date**: January 2025  
**Status**: ✅ **COMPLETED** - Comprehensive plan created

#### **📚 Plan Overview**
- **Document**: `notes/dev-docs/TAMS_APPNOTES_INTEGRATION_PLAN.md` created
- **Source**: Official TAMS appnotes from [GitHub](https://github.com/bbc/tams/tree/main/docs/appnotes)
- **Scope**: 4 key appnotes covering timestamps, tags, data types, and OpenTimelineIO integration
- **Phases**: 4-phase implementation plan over 8 weeks

#### **🔧 Key Appnotes to Integrate**
1. **Timestamps in TAMS** (0008) - High-resolution timestamp management
2. **Tag Names** (0003) - Enhanced metadata and tagging system
3. **TAMS for Non-Media Data** (0004) - Data type assessment and storage strategy
4. **OpenTimelineIO Integration** (0015) - Composition and render optimization

#### **📊 Implementation Status**
- **Planning**: ✅ Complete
- **Audit Phase**: 🔄 Pending
- **Core Improvements**: ⏳ Planned
- **Advanced Features**: ⏳ Planned
- **Testing & Validation**: ⏳ Planned

## 🏗️ **RECENT MAJOR ACHIEVEMENTS**

### **✅ TAMS APPNOTES INTEGRATION - PHASE 2 COMPLETE** (January 27, 2025)
- **Nanosecond Timestamp Support**: Updated all PyArrow schemas from microseconds to nanoseconds
- **High-Resolution Timestamp Utilities**: Created comprehensive timestamp management system
- **Timeline Synchronization**: Implemented linear clock and timeline sync utilities
- **Enhanced Tag Management**: Built VAST-optimized tag validation, querying, and analytics system
- **Tag Proposal Workflow**: Added standardized tag definitions and proposal system
- **VAST Query Optimization**: Leveraged VAST's JSON field capabilities for efficient tag filtering

### **✅ AUTOMATIC SOURCE CREATION** (September 28, 2025)
- Implemented automatic source creation when flows reference non-existent source IDs
- Follows TAMS specification compliance requirements
- Metadata replication from flows to sources working correctly

### **✅ TIMERANGE HANDLING** (September 28, 2025)
- Moved timerange logic to TAMS application layer
- Clean separation between domain-specific and generic storage code
- Proper timerange splitting and reconstruction implemented

## 📋 **NEXT PRIORITIES**

1. **Phase 1: Foundation Review** (Week 1-2)
   - Audit current TAMS implementation against appnotes
   - Review all available appnotes documentation
   - Document current architecture gaps

2. **Phase 2: Core Improvements** (Week 3-4)
   - Implement high-resolution timestamp management
   - Enhance tag management system
   - Add data type validation

3. **Phase 3: Advanced Features** (Week 5-6)
   - Research OpenTimelineIO integration
   - Implement essence reuse system
   - Add render optimization

## 🔧 **TECHNICAL STATUS**

### **Current Architecture**
- **Storage Layer**: VAST + S3 integration working
- **API Layer**: All endpoints implemented and tested
- **Authentication**: Multi-provider auth system active
- **Database**: Trino + Hive Metastore operational

### **Key Files**
- **Main App**: `app/main.py`
- **Storage Services**: `app/storage/`
- **API Routers**: `app/api/`
- **Models**: `app/models/`

## 📊 **METRICS**

- **API Endpoints**: 100% implemented
- **Test Coverage**: Comprehensive test suite
- **Documentation**: Complete API and architecture docs
- **Compliance**: Following TAMS specification

## 🚨 **ACTIVE ISSUES**

- None currently identified

## 📝 **NOTES STRUCTURE**

This project now uses date-based notes in the `notes/` folder:
- **Current Status**: This file (`current.md`)
- **Daily Notes**: `YYYY-MM-DD.md` files
- **Code Changes**: `edits/YYYY-MM-DD.md` files
- **Archives**: `archive/` folder for completed work
