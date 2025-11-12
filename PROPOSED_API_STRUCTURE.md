# Proposed API Endpoint Structure

## Overview
This document shows the proposed endpoint structure with versioning support.

## Versioning Strategy
- **TAMS Spec Endpoints**: `/api/tams/v{version}/...` (TAMS 8.0 compliant)
- **VAST Extensions**: `/api/vast/...` (VAST-specific, outside TAMS spec)
- **Infrastructure/Monitoring**: Root level `/` (health, metrics, docs)
- **TAMS Extensions**: Under `/api/tams/v{version}/` (analytics, HLS, etc.)

## Default Version
- **v8.0** (current TAMS spec version)

## Structure Overview
Clear separation of concerns:
- **TAMS Spec**: `/api/tams/v8.0/...` - Official TAMS 8.0 endpoints
- **TAMS Extensions**: `/api/tams/v8.0/...` - Extensions that enhance TAMS (analytics, HLS)
- **VAST Extensions**: `/api/vast/...` - VAST-specific features (vectors, metadata updates, etc.)
- **Infrastructure**: `/` - Health, metrics, docs (standard practice)

---

## 📋 Complete Endpoint URL Structure

### **TAMS 8.0 Spec Endpoints** → `/api/tams/v8.0/`

#### Service Endpoints
```
GET    /api/tams/v8.0/
HEAD   /api/tams/v8.0/
GET    /api/tams/v8.0/service
HEAD   /api/tams/v8.0/service
POST   /api/tams/v8.0/service
```

#### Storage Backends (part of service)
```
GET    /api/tams/v8.0/service/storage-backends
HEAD   /api/tams/v8.0/service/storage-backends
POST   /api/tams/v8.0/service/storage-backends
GET    /api/tams/v8.0/service/storage-backends/{backend_id}
HEAD   /api/tams/v8.0/service/storage-backends/{backend_id}
PUT    /api/tams/v8.0/service/storage-backends/{backend_id}
DELETE /api/tams/v8.0/service/storage-backends/{backend_id}
```

#### Webhooks (part of service)
```
GET    /api/tams/v8.0/service/webhooks
HEAD   /api/tams/v8.0/service/webhooks
POST   /api/tams/v8.0/service/webhooks
GET    /api/tams/v8.0/service/webhooks/{webhook_id}
PUT    /api/tams/v8.0/service/webhooks/{webhook_id}
DELETE /api/tams/v8.0/service/webhooks/{webhook_id}
```

#### Sources
```
GET    /api/tams/v8.0/sources
HEAD   /api/tams/v8.0/sources
POST   /api/tams/v8.0/sources
POST   /api/tams/v8.0/sources/batch
GET    /api/tams/v8.0/sources/{source_id}
HEAD   /api/tams/v8.0/sources/{source_id}
DELETE /api/tams/v8.0/sources/{source_id}
GET    /api/tams/v8.0/sources/{source_id}/tags
HEAD   /api/tams/v8.0/sources/{source_id}/tags
GET    /api/tams/v8.0/sources/{source_id}/tags/{name}
HEAD   /api/tams/v8.0/sources/{source_id}/tags/{name}
PUT    /api/tams/v8.0/sources/{source_id}/tags/{name}
DELETE /api/tams/v8.0/sources/{source_id}/tags/{name}
GET    /api/tams/v8.0/sources/{source_id}/description
HEAD   /api/tams/v8.0/sources/{source_id}/description
PUT    /api/tams/v8.0/sources/{source_id}/description
DELETE /api/tams/v8.0/sources/{source_id}/description
GET    /api/tams/v8.0/sources/{source_id}/label
HEAD   /api/tams/v8.0/sources/{source_id}/label
PUT    /api/tams/v8.0/sources/{source_id}/label
DELETE /api/tams/v8.0/sources/{source_id}/label
```

#### Flows
```
GET    /api/tams/v8.0/flows
HEAD   /api/tams/v8.0/flows
POST   /api/tams/v8.0/flows
GET    /api/tams/v8.0/flows/{flow_id}
HEAD   /api/tams/v8.0/flows/{flow_id}
PUT    /api/tams/v8.0/flows/{flow_id}  (vendor extension)
DELETE /api/tams/v8.0/flows/{flow_id}
GET    /api/tams/v8.0/flows/{flow_id}/tags
HEAD   /api/tams/v8.0/flows/{flow_id}/tags
GET    /api/tams/v8.0/flows/{flow_id}/tags/{name}
HEAD   /api/tams/v8.0/flows/{flow_id}/tags/{name}
PUT    /api/tams/v8.0/flows/{flow_id}/tags/{name}
DELETE /api/tams/v8.0/flows/{flow_id}/tags/{name}
GET    /api/tams/v8.0/flows/{flow_id}/description
HEAD   /api/tams/v8.0/flows/{flow_id}/description
PUT    /api/tams/v8.0/flows/{flow_id}/description
DELETE /api/tams/v8.0/flows/{flow_id}/description
GET    /api/tams/v8.0/flows/{flow_id}/label
HEAD   /api/tams/v8.0/flows/{flow_id}/label
PUT    /api/tams/v8.0/flows/{flow_id}/label
DELETE /api/tams/v8.0/flows/{flow_id}/label
GET    /api/tams/v8.0/flows/{flow_id}/read_only
HEAD   /api/tams/v8.0/flows/{flow_id}/read_only
PUT    /api/tams/v8.0/flows/{flow_id}/read_only
DELETE /api/tams/v8.0/flows/{flow_id}/read_only
GET    /api/tams/v8.0/flows/{flow_id}/max_bit_rate
HEAD   /api/tams/v8.0/flows/{flow_id}/max_bit_rate
PUT    /api/tams/v8.0/flows/{flow_id}/max_bit_rate
DELETE /api/tams/v8.0/flows/{flow_id}/max_bit_rate
GET    /api/tams/v8.0/flows/{flow_id}/avg_bit_rate
HEAD   /api/tams/v8.0/flows/{flow_id}/avg_bit_rate
PUT    /api/tams/v8.0/flows/{flow_id}/avg_bit_rate
DELETE /api/tams/v8.0/flows/{flow_id}/avg_bit_rate
GET    /api/tams/v8.0/flows/{flow_id}/flow_collection
HEAD   /api/tams/v8.0/flows/{flow_id}/flow_collection
PUT    /api/tams/v8.0/flows/{flow_id}/flow_collection
DELETE /api/tams/v8.0/flows/{flow_id}/flow_collection
POST   /api/tams/v8.0/flows/{flow_id}/storage
GET    /api/tams/v8.0/flows/{flow_id}/segments
HEAD   /api/tams/v8.0/flows/{flow_id}/segments
POST   /api/tams/v8.0/flows/{flow_id}/segments
DELETE /api/tams/v8.0/flows/{flow_id}/segments
```

#### Objects
```
HEAD   /api/tams/v8.0/objects/{object_id}
GET    /api/tams/v8.0/objects/{object_id}
POST   /api/tams/v8.0/objects/{object_id}/instances
GET    /api/tams/v8.0/objects/{object_id}/instances
DELETE /api/tams/v8.0/objects/{object_id}/instances
```

#### Deletion Requests
```
GET    /api/tams/v8.0/flow-delete-requests
HEAD   /api/tams/v8.0/flow-delete-requests
GET    /api/tams/v8.0/flow-delete-requests/{request_id}
```

---

### **TAMS Extensions** (Enhance TAMS functionality) → `/api/tams/v8.0/`

#### Analytics Extension
```
GET    /api/tams/v8.0/analytics/summary
```

#### HLS Streaming Extension
```
GET    /api/tams/v8.0/hls/flows/{flow_id}/status
GET    /api/tams/v8.0/hls/flows/{flow_id}/playlist
```

#### Authentication & Users (Service Management)
```
POST   /api/tams/v8.0/auth/login
GET    /api/tams/v8.0/auth/providers
POST   /api/tams/v8.0/users
GET    /api/tams/v8.0/users
GET    /api/tams/v8.0/users/{user_id}
PUT    /api/tams/v8.0/users/{user_id}
DELETE /api/tams/v8.0/users/{user_id}
```

#### Configuration (Service Management)
```
GET    /api/tams/v8.0/config/async-deletion-threshold
PUT    /api/tams/v8.0/config/async-deletion-threshold
```

---

### **VAST Extensions** (VAST-specific, outside TAMS spec) → `/api/vast/`

#### Object Metadata Extensions
```
PATCH  /api/vast/objects/{object_id}/metadata
PUT    /api/vast/objects/{object_id}/metadata
GET    /api/vast/objects/{object_id}/metadata
```

#### Vector & Embeddings
```
PUT    /api/vast/objects/{object_id}/vector
GET    /api/vast/objects/{object_id}/vector
POST   /api/vast/objects/{object_id}/vector/search
DELETE /api/vast/objects/{object_id}/vector
```

#### Object Descriptions
```
PUT    /api/vast/objects/{object_id}/description
GET    /api/vast/objects/{object_id}/description
DELETE /api/vast/objects/{object_id}/description
```

#### VAST-Specific Features
```
GET    /api/vast/objects/{object_id}/extensions
POST   /api/vast/objects/{object_id}/extensions
PUT    /api/vast/objects/{object_id}/extensions/{extension_key}
DELETE /api/vast/objects/{object_id}/extensions/{extension_key}
```

---

### **Infrastructure Endpoints** (Root level - standard practice)

#### Health & Monitoring
```
GET    /health
HEAD   /health
GET    /health/cache
GET    /metrics
```

---

### **Documentation Endpoints** (Root level - standard practice)
```
GET    /docs
GET    /redoc
GET    /openapi.json
```

---

## 🔄 Version Support

### Multiple Version Support
The structure allows for multiple TAMS versions:

```
/api/tams/v8.0/...  (Current - TAMS 8.0)
/api/tams/v7.0/...  (Legacy - if needed)
/api/tams/v9.0/...  (Future - when available)
```

### Version Selection Strategy
1. **Default version**: v8.0 (current)
2. **Explicit versioning**: Required in path
3. **Backward compatibility**: Old versions remain available
4. **Version negotiation**: Could add header-based versioning later

---

## 📊 Summary

### Endpoint Categories

| Category | Count | Base Path |
|----------|-------|-----------|
| TAMS 8.0 Spec | ~70+ | `/api/tams/v8.0/` |
| TAMS Extensions | ~10 | `/api/tams/v8.0/` |
| VAST Extensions | ~10+ | `/api/vast/` |
| Infrastructure | 4 | `/` (health, metrics) |
| Documentation | 3 | `/` (docs, openapi) |
| **Total** | **~97+** | - |

### Migration Impact

**Before:**
- `/flows` → `/api/tams/v8.0/flows`
- `/sources` → `/api/tams/v8.0/sources`
- `/analytics` → `/api/tams/v8.0/analytics`
- `/hls` → `/api/tams/v8.0/hls`
- `/objects/{id}/metadata` → `/api/vast/objects/{id}/metadata` (new)
- `/health` → `/health` (unchanged)

**After:**
- **TAMS Spec endpoints** under `/api/tams/v8.0/`
- **TAMS Extensions** (analytics, HLS) under `/api/tams/v8.0/`
- **VAST Extensions** (vectors, metadata) under `/api/vast/`
- **Clear separation** - TAMS vs VAST-specific features
- Health/metrics/docs remain at root (standard practice)

---

## ✅ Benefits

1. **Clear Separation**: TAMS spec vs TAMS extensions vs VAST extensions
2. **Version Support**: Easy to add v7.0, v9.0, etc. for TAMS endpoints
3. **Best Practices**: Follows REST API versioning conventions
4. **Backward Compatible**: Can maintain old paths during transition
5. **Clear Documentation**: Each category clearly documented
6. **VAST-Specific**: `/api/vast/` clearly indicates VAST-only features
7. **TAMS Compliance**: `/api/tams/v8.0/` clearly indicates TAMS spec endpoints

---

## 🚀 Implementation Notes

1. **TAMS Router Prefixes**: Update TAMS spec routers to use `/api/tams/v8.0/` prefix
2. **TAMS Extensions**: Keep analytics, HLS, auth under `/api/tams/v8.0/`
3. **VAST Router**: Create new `/api/vast/` router for VAST-specific endpoints
4. **Version Config**: Make TAMS version configurable (default: v8.0)
5. **OpenAPI**: Update OpenAPI spec to reflect new paths, tag each category clearly
6. **Tests**: Update all test URLs to new paths
7. **Documentation**: Update README and API docs, clearly mark:
   - TAMS 8.0 Spec endpoints
   - TAMS Extensions
   - VAST Extensions

---

## ⚠️ Breaking Changes

This is a **breaking change** for existing clients. Consider:

1. **Deprecation Period**: Keep old paths with deprecation warnings
2. **Migration Guide**: Provide clear migration documentation
3. **Client Updates**: Update all client libraries
4. **Version Header**: Consider Accept-Version header as alternative

---

## 📝 Next Steps

1. Review this structure
2. Approve or suggest modifications
3. Implement router restructuring
4. Update tests and documentation
5. Plan migration strategy

