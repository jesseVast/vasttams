# Search and Tags Enhancement TODO

**Created**: November 23, 2025  
**Status**: Planning Phase  
**Priority**: High

## Overview

This document tracks the implementation of search functionality, tag enhancements, and related improvements across the UI, CLI applications, and server components.

---

## UI Tasks

### 1. Show Tags in Info Modals
**Status**: ✅ **COMPLETED**  
**Priority**: Medium

**Description**: Display tags information in all info modals throughout the UI.

**Requirements**:
- ✅ Show tags in **flows** info modals
- ✅ Show tags in **sources** info modals
- ✅ For **segments**, use tags from the underlying object (not segment-level tags)

**Files Modified**:
- ✅ `ui/src/components/DetailModal.tsx` - Updated to handle tags nested under 'root' or at top level
- ✅ `ui/src/components/SegmentMediaWidget.tsx` - Updated to properly display tags from objects

**Implementation Notes**:
- Tags can be nested under `root` property or at top level
- Both components now check for tags in both locations
- Tags are displayed using the `formatObject` function for consistent formatting
- Segments display tags from their associated object (fetched when modal opens)

**Date Completed**: January 2025

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
- Requires server text search endpoint (Server Task 4)

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

### 1. External Embedding Provider Support
**Status**: Pending  
**Priority**: High

**Description**: Add support for creating embeddings using an external embedding provider via the aifuel embedder library.

**Requirements**:
- Integrate aifuel embedder library
- Support multiple embedding providers (see `~/Developer/gitlab/aifuel` for options)
- Create embedding service that uses aifuel library
- Handle authentication and configuration for different providers

**Reference**: Check `~/Developer/gitlab/aifuel` for available embedding providers and options

**Files to Create**:
- `src/server/vasttamsserver/vast/embedding_service.py` - Embedding service using aifuel
- Embedding client wrapper for aifuel library

**Files to Modify**:
- `src/server/requirements.txt` - Add aifuel dependency
- Configuration files - Add embedding provider settings

**Dependencies**:
- aifuel embedder library

---

### 2. Text-to-Vector Ingestion Endpoint
**Status**: Pending  
**Priority**: High

**Description**: Create endpoint to support ingesting text, converting to vectors, and storing them in the VAST database.

**Requirements**:
- Endpoint: `POST /api/vast/vectors/ingest` or similar
- Accept text input
- Convert text to embedding vector using embedding service (task 1)
- Store vector in VAST database with associated metadata
- Support associating vectors with entity_id and entity_type

**Request Format**:
```json
{
  "text": "text to embed",
  "entity_id": "object_123",
  "entity_type": "object",
  "metadata": {
    "source": "user_input",
    "timestamp": "2025-11-23T10:00:00Z"
  }
}
```

**Response Format**:
```json
{
  "vector_id": "vec_123",
  "entity_id": "object_123",
  "entity_type": "object",
  "embedding_model": "text-embedding-ada-002",
  "embedding_date": "2025-11-23T10:00:00Z",
  "dimension": 1536
}
```

**Files to Create**:
- Vector ingestion endpoint in router
- Vector ingestion service

**Files to Modify**:
- `src/server/vasttamsserver/vast/router.py` - Add ingestion endpoint
- `src/server/vasttamsserver/vast/service.py` - Add ingestion logic

**Dependencies**:
- Task 1 (embedding provider support)
- Task 3 (updated vector table)

---

### 3. Update Vector Table Schema
**Status**: Pending  
**Priority**: High

**Description**: Update existing vector table to support any entity_id and entity_type. Change table name from "object_vector" to "vectors".

**Requirements**:
- Rename table from `object_vector` to `vectors`
- Add `entity_id` column (replaces object_id)
- Add `entity_type` column (e.g., "object", "flow", "source", "segment")
- Maintain existing vector column and metadata columns
- Update all references to use new table name and schema
- Support migration of existing data

**Schema Changes**:
- Table name: `object_vector` → `vectors`
- Add: `entity_id` (string, replaces object_id)
- Add: `entity_type` (string, enum: object, flow, source, segment)
- Keep: `vector` (array/vector type)
- Keep: `embedding_model`, `embedding_date`, `dimension`, etc.

**Files to Modify**:
- `src/server/vasttamsserver/vast/schemas.py` - Update table schema
- `src/server/vasttamsserver/vast/service.py` - Update all vector operations
- Any code referencing `object_vector` table

**Migration Notes**:
- Existing `object_vector` records should migrate with `entity_type="object"`
- `object_id` values become `entity_id` values
- Plan for zero-downtime migration if possible

---

### 4. Text Search Endpoint
**Status**: Pending  
**Priority**: High

**Description**: Create endpoint to support search by text. Get text, convert to vectors, search database, and return results with default distance and algorithm from config.

**Requirements**:
- Endpoint: `POST /api/vast/search/text` or `POST /api/vast/vectors/search`
- Accept text input
- Convert text to embedding vector using embedding service
- Perform vector search in VAST database
- Use default distance algorithm and threshold from config
- Return results with entity information and similarity scores

**Request Format**:
```json
{
  "text": "search query text",
  "entity_types": ["object", "flow"],  // optional filter
  "limit": 10,
  "distance_threshold": 0.8  // optional, overrides config default
}
```

**Response Format**:
```json
{
  "query_text": "search query text",
  "embedding_model": "text-embedding-ada-002",
  "distance_algorithm": "cosine",
  "distance_threshold": 0.8,
  "results": [
    {
      "entity_id": "obj_123",
      "entity_type": "object",
      "similarity": 0.92,
      "distance": 0.08,
      "metadata": {...}
    },
    ...
  ],
  "total": 15
}
```

**Files to Create**:
- Text search endpoint in router
- Text search service

**Files to Modify**:
- `src/server/vasttamsserver/vast/router.py` - Add text search endpoint
- `src/server/vasttamsserver/vast/service.py` - Add text search logic
- Configuration - Add default distance algorithm and threshold

**Dependencies**:
- Task 1 (embedding provider support)
- Task 3 (updated vector table)

---

### 5. Embedding Configuration
**Status**: Pending  
**Priority**: High

**Description**: Add embedding endpoint, model dimension, distance algorithm, and details to configuration.

**Requirements**:
- Add embedding configuration section to config
- Include:
  - Embedding endpoint/provider configuration
  - Model name and dimension
  - Default distance algorithm (cosine, euclidean, etc.)
  - Default distance threshold
  - Provider-specific settings (API keys, etc.)

**Reference**: Check `~/Developer/gitlab/aifuel` for supported embedding models, endpoints, and configuration options

**Configuration Format** (YAML):
```yaml
embedding:
  provider: "aifuel"  # or direct provider name
  endpoint: "https://api.example.com/embed"
  model_name: "text-embedding-ada-002"
  model_dimension: 1536
  distance_algorithm: "cosine"  # cosine, euclidean, dot_product
  default_distance_threshold: 0.8
  api_key_env: "EMBEDDING_API_KEY"
  # Provider-specific settings
  provider_config:
    timeout: 30
    retry_count: 3
```

**Files to Modify**:
- `config/config.yaml.example` - Add embedding configuration section
- `src/server/vasttamsserver/core/config.py` - Parse embedding config
- `src/server/vasttamsserver/vast/embedding_service.py` - Use config values

**Files to Create**:
- Configuration schema/validation for embedding settings

**Dependencies**:
- Task 1 (embedding provider support)

---

### 6. Automatic Entity Vectorization
**Status**: Pending  
**Priority**: High

**Description**: Automatically vectorize entities (flows, sources, objects) when they are created, edited, or deleted. Take the JSON representation of the entity (without ID) and convert it to a vector, storing it in the vector database. Update vector data when entity changes.

**Requirements**:
- Hook into create/update/delete operations for flows, sources, and objects
- Extract JSON representation of entity (excluding ID field)
- Convert JSON to text representation suitable for embedding
- Generate embedding vector using embedding service
- Store/update vector in VAST database with entity_id and entity_type
- Handle delete operations by removing associated vectors
- Ensure vector updates are atomic with entity operations (or handle failures gracefully)

**Implementation Approach**:
- Add hooks/middleware to entity creation/update/delete endpoints
- Serialize entity to JSON (excluding ID and internal fields)
- Convert JSON to text (flatten or format appropriately for embedding)
- Call embedding service to generate vector
- Store vector using entity_id and entity_type in vectors table
- For updates: upsert vector (replace existing)
- For deletes: remove vector from vectors table

**Entity Types to Vectorize**:
- **Flows**: Include label, description, tags, metadata, codec info, etc.
- **Sources**: Include label, description, tags, metadata, format, etc.
- **Objects**: Include label, description, tags, metadata, size, etc.

**JSON Serialization Rules**:
- Exclude: `id`, `object_id`, `flow_id`, `source_id` (entity identifiers)
- Exclude: Internal fields like `created_at`, `updated_at` (or include as metadata)
- Include: All descriptive fields (label, description, tags, metadata)
- Flatten nested structures appropriately for embedding

**Error Handling**:
- Vectorization failures should not block entity operations (log and continue)
- Consider async processing for vectorization to avoid blocking API responses
- Retry mechanism for transient embedding service failures

**Files to Modify**:
- `src/server/vasttamsserver/flows/router.py` - Add vectorization hooks
- `src/server/vasttamsserver/sources/router.py` - Add vectorization hooks
- `src/server/vasttamsserver/objects/router.py` - Add vectorization hooks
- Entity service files - Add vectorization logic

**Files to Create**:
- `src/server/vasttamsserver/vast/entity_vectorization.py` - Entity vectorization service
- Vectorization utility functions for JSON-to-text conversion

**Dependencies**:
- Task 1 (embedding provider support)
- Task 3 (updated vector table with entity_id/entity_type)
- Task 5 (embedding configuration)

**Configuration Options**:
- Enable/disable automatic vectorization per entity type
- Configure which fields to include/exclude from vectorization
- Set vectorization timeout and retry settings

---

## Implementation Order

### Phase 1: Foundation (Server)
1. Server Task 5: Embedding configuration
2. Server Task 1: External embedding provider support
3. Server Task 3: Update vector table schema

### Phase 2: Vector Operations (Server)
4. Server Task 2: Text-to-vector ingestion endpoint
5. Server Task 4: Text search endpoint
6. Server Task 6: Automatic entity vectorization

### Phase 3: UI Search
6. UI Task 4: Search page implementation

### Phase 4: Tag Enhancements
7. UI Task 1: Show tags in info modals
8. CLI Task 5: Add tags support to CLI

### Phase 5: Deletion Fixes
9. UI Task 2: Investigate source deletion issue
10. UI Task 3: Background delete operations

---

## Dependencies

**Server Tasks**:
- **Server Task 2** depends on **Server Task 1** (embedding provider) and **Server Task 3** (vector table)
- **Server Task 4** depends on **Server Task 1** (embedding provider) and **Server Task 3** (vector table)
- **Server Task 6** depends on **Server Task 1** (embedding provider), **Server Task 3** (vector table), and **Server Task 5** (embedding configuration)
- **Server Task 1** depends on **Server Task 5** (embedding configuration)

**UI Tasks**:
- **UI Task 4** (Search page) depends on **Server Task 4** (text search endpoint)
- **UI Task 3** may leverage existing deletion request infrastructure

---

## Notes

**Server Implementation**:
- Use aifuel embedder library for embedding provider support
- Check `~/Developer/gitlab/aifuel` for available embedding providers and configuration options
- Vector table migration from `object_vector` to `vectors` requires careful planning
- Default distance algorithm and threshold should be configurable
- Vector search should leverage existing VAST vector capabilities
- Automatic entity vectorization should be non-blocking (consider async processing)
- JSON-to-text conversion for entities should exclude IDs and internal fields
- Vector updates should be atomic with entity operations or handle failures gracefully

**UI Implementation**:
- Review existing deletion request service for background delete operations
- Search page should integrate with new text search endpoint

**General**:
- Ensure all search functionality follows TAMS compliance
- Consider performance implications of vector searches
- Tag parsing in CLI should handle edge cases (quotes, special characters)

---

## Related Documentation

- TAMS API Specification: `./tams-8.0/api/`
- TAMS App Notes: `./tams-8.0/docs/appnotes/`
- aifuel embedder library: `~/Developer/gitlab/aifuel`
- Current deletion request implementation (see UI Task 3 notes)
- Vector table implementation: `src/server/vasttamsserver/vast/schemas.py`

