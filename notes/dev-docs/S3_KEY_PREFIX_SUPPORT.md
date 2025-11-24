# S3 Key Prefix Support Added

## Summary
Added support for `s3_root_path` configuration to be used as `key_prefix` in S3Client initialization.

## Changes Made

### Issue
The `s3_root_path` setting in `config/config.yaml` was not being used when creating the S3 client. VAST S3 supports a `key_prefix` parameter which acts the same way - prefixing all object keys.

### Solution
1. **Added `s3_root_path` to Settings model** (`src/vasttams/core/config.py`):
   - Optional field with default `None`
   - Description: "S3 key prefix for all objects (e.g., /tams8-dev)"

2. **Updated S3Client initialization** (`src/vasttams/core/dependencies.py`):
   - Attempts to pass `key_prefix` parameter to `S3Config`
   - Handles gracefully if S3Config doesn't support the parameter

## How It Works

### Configuration
```json
{
  "s3_root_path": "/tams8-dev"
}
```

### Behavior
- If `s3_root_path` is set, it's passed to S3Config as `key_prefix`
- All S3 operations will prefix object keys with this value
- Example: Key `segment123.mp4` becomes `/tams8-dev/segment123.mp4` in the bucket

## Benefits
1. ✅ Namespace isolation for different TAMS environments
2. ✅ All objects organized under a prefix
3. ✅ Easy cleanup - delete entire prefix to remove all TAMS objects
4. ✅ Multi-tenant support

## Status
✅ `s3_root_path` configuration added
✅ Support for passing to S3Config as `key_prefix`
✅ Graceful handling if parameter not supported
✅ No breaking changes

---

# Universal Vector Search Support

## Summary
Updated vector model and schema to support universal search across flows, sources, objects, and segments. Added support for text/file ingestion and text-based vector search.

## Changes Made

### 1. Vector Schema Updates for Universal Search

**Issue**: The vector model only supported `object_id`, limiting search to objects only.

**Solution**: 
- Changed `object_id` field to `entity_id` to support any entity type (flow, source, object, segment)
- Added `entity_type` field to indicate the type of entity for retrieval purposes
- Updated schema in `src/server/vasttamsserver/vast/schemas.py`:
  - `entity_id`: Entity ID (flow, source, object, or segment ID)
  - `entity_type`: Entity type ("flow", "source", "object", or "segment")
  - Maintained backward compatibility with legacy `object_id` field

**Files Modified**:
- `src/server/vasttamsserver/vast/schemas.py`: Updated `get_object_vector_schema()` and projections

### 2. File Ingestion Support

**Added**: Endpoint to ingest text/JSON files, embed them, and store embeddings in vector database.

**Implementation**:
- New endpoint: `POST /api/vast/objects/entities/ingest`
- Accepts text or JSON files via multipart form upload
- Extracts text content from files
- Sends text to embedding service
- Stores embedding in vector database with entity_id and entity_type

**Files Created**:
- `src/server/vasttamsserver/vast/embedding_service.py`: Service for text-to-vector conversion

**Files Modified**:
- `src/server/vasttamsserver/vast/service.py`: Added `ingest_text_file()` method
- `src/server/vasttamsserver/vast/router.py`: Added file ingestion endpoint
- `src/server/vasttamsserver/vast/models.py`: Added `TextFileIngestRequest` model

### 3. Text Search Support

**Added**: Endpoint for text-based vector search that embeds text, performs vector search, and returns results with entity information.

**Implementation**:
- New endpoint: `POST /api/vast/search/text`
- Accepts text query
- Converts text to embedding vector
- Performs vector similarity search
- Returns results with:
  - `entity_id`: Matching entity ID
  - `entity_type`: Entity type (flow, source, object, segment)
  - `distance`: Similarity distance score
  - `search_algorithm`: Algorithm used (cosine, euclidean, etc.)

**Files Modified**:
- `src/server/vasttamsserver/vast/service.py`: Added `search_by_text()` method
- `src/server/vasttamsserver/vast/router.py`: Added text search endpoint
- `src/server/vasttamsserver/vast/models.py`: Added `TextSearchRequest` and `TextSearchResult` models
- `src/server/vasttamsserver/main.py`: Registered search router

### 4. Updated Vector Models

**Changes**:
- Added `EntityVectorPut` model for universal entity vector updates
- Updated `VectorSearchMatch` to include:
  - `entity_id`: Universal entity ID field
  - `entity_type`: Entity type field
  - `search_algorithm`: Search algorithm used
  - Maintained legacy fields for backward compatibility
- Updated `VectorSearchResult` to include `search_algorithm` and `total` count

**Files Modified**:
- `src/server/vasttamsserver/vast/models.py`: Added new models and updated existing ones

### 5. Updated Vector Service

**Changes**:
- Added `update_entity_vector()` method for universal entity support
- Updated `search_vectors()` to return entity_id, entity_type, and search_algorithm
- Added `ingest_text_file()` method for file ingestion
- Added `search_by_text()` method for text-based search
- Maintained backward compatibility with `update_object_vector()` method

**Files Modified**:
- `src/server/vasttamsserver/vast/service.py`: Added new methods and updated existing ones

## API Endpoints

### Universal Entity Vector Update
```
PUT /api/vast/objects/entities/{entity_id}/vector
Body: {
  "entity_id": "flow_123",
  "entity_type": "flow",
  "vector": [0.1, 0.2, ...],
  "summary": "Optional summary",
  "embedding_model": "nomic-embed-1.5"
}
```

### File Ingestion
```
POST /api/vast/objects/entities/ingest
Form Data:
  - entity_id: "flow_123"
  - entity_type: "flow"
  - file: (text or JSON file)
  - embedding_model: (optional)
  - summary: (optional)
```

### Text Search
```
POST /api/vast/search/text
Body: {
  "text": "search query text",
  "entity_types": ["flow", "source", "object", "segment"],  // optional filter
  "limit": 10,
  "distance_threshold": 0.8,
  "embedding_model": "nomic-embed-1.5",
  "distance_metric": "cosine"
}
```

## Benefits

1. ✅ Universal search across all entity types (flows, sources, objects, segments)
2. ✅ Entity type identification for proper retrieval
3. ✅ File ingestion support for batch embedding
4. ✅ Text-based search with automatic embedding
5. ✅ Backward compatibility maintained with legacy object_id field
6. ✅ Search algorithm and distance metrics included in results

## Status

✅ Vector schema updated with entity_id and entity_type
✅ Models updated to support universal entities
✅ File ingestion endpoint implemented
✅ Text search endpoint implemented
✅ Embedding service created
✅ Backward compatibility maintained
✅ All endpoints tested and working

