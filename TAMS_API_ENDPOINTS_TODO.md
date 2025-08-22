# TAMS API Endpoints TODO

## 🚨 **CRITICAL ISSUES TO FIX**

### 1. **VAST Database Integration Issues**
- [ ] **FIXED**: `'VastDBManager' object has no attribute 'query_records'` - ✅ RESOLVED
- [ ] **FIXED**: `'pyarrow.lib.RecordBatchReader' object has no attribute 'limit'` - ✅ RESOLVED  
- [ ] **FIXED**: `'VastDBManager' object has no attribute 'insert_record'` - ✅ RESOLVED
- [ ] **CURRENT ISSUE**: `'Table' object has no attribute 'insert_pydict'` - ❌ NEEDS FIX
- [ ] **CURRENT ISSUE**: Collection creation endpoints failing due to insert method issues - ❌ NEEDS FIX

### 2. **Missing Collection Management Methods**
- [ ] **FIXED**: `'VASTStore' object has no attribute 'list_deletion_requests'` - ✅ RESOLVED
- [ ] **FIXED**: `'VASTStore' object has no attribute 'list_webhooks'` - ✅ RESOLVED
- [ ] **CURRENT ISSUE**: Collection creation methods need proper VAST integration - ❌ NEEDS FIX

## 📋 **MISSING API ENDPOINTS (Based on TAMS API Spec)**

### **Collections Management**
- [ ] **GET /collections** - List all collections (currently returns 405 Method Not Allowed)
- [ ] **GET /collections/{collection_id}** - Get specific collection details
- [ ] **PUT /collections/{collection_id}** - Update collection metadata
- [ ] **DELETE /collections/{collection_id}** - Delete collection
- [ ] **GET /collections/{collection_id}/flows** - List flows in collection
- [ ] **POST /collections/{collection_id}/flows** - Add flow to collection
- [ ] **DELETE /collections/{collection_id}/flows/{flow_id}** - Remove flow from collection

### **Source Collections Management**
- [ ] **GET /source-collections** - List all source collections (currently returns 405 Method Not Allowed)
- [ ] **GET /source-collections/{collection_id}** - Get specific source collection details
- [ ] **PUT /source-collections/{collection_id}** - Update source collection metadata
- [ ] **DELETE /source-collections/{collection_id}** - Delete source collection
- [ ] **GET /source-collections/{collection_id}/sources** - List sources in collection
- [ ] **POST /source-collections/{collection_id}/sources** - Add source to collection
- [ ] **DELETE /source-collections/{collection_id}/sources/{source_id}** - Remove source from collection

### **Objects Management**
- [ ] **GET /objects** - List all objects (currently returns 405 Method Not Allowed)
- [ ] **POST /objects** - Create new object
- [ ] **GET /objects/{object_id}** - Get specific object details
- [ ] **PUT /objects/{object_id}** - Update object metadata
- [ ] **DELETE /objects/{object_id}** - Delete object

### **Flow Management**
- [ ] **GET /flows/{flow_id}/segments** - List segments in flow
- [ ] **POST /flows/{flow_id}/segments** - Add segment to flow
- [ ] **DELETE /flows/{flow_id}/segments/{segment_id}** - Remove segment from flow
- [ ] **GET /flows/{flow_id}/metadata** - Get flow metadata
- [ ] **PUT /flows/{flow_id}/metadata** - Update flow metadata

### **Source Management**
- [ ] **GET /sources/{source_id}/flows** - List flows from source
- [ ] **GET /sources/{source_id}/metadata** - Get source metadata
- [ ] **PUT /sources/{source_id}/metadata** - Update source metadata

### **Segment Management**
- [ ] **GET /segments** - List all segments
- [ ] **POST /segments** - Create new segment
- [ ] **GET /segments/{segment_id}** - Get specific segment details
- [ ] **PUT /segments/{segment_id}** - Update segment metadata
- [ ] **DELETE /segments/{segment_id}** - Delete segment
- [ ] **GET /segments/{segment_id}/data** - Get segment data
- [ ] **PUT /segments/{segment_id}/data** - Update segment data

### **Analytics Endpoints (Partially Working)**
- [x] **GET /analytics/flow-usage** - ✅ WORKING (but returning empty data)
- [x] **GET /analytics/storage-usage** - ✅ WORKING (but returning empty data)
- [x] **GET /analytics/time-range-analysis** - ✅ WORKING (but returning empty data)
- [ ] **GET /analytics/source-usage** - Missing endpoint
- [ ] **GET /analytics/segment-usage** - Missing endpoint
- [ ] **GET /analytics/collection-usage** - Missing endpoint
- [ ] **GET /analytics/performance-metrics** - Missing endpoint

### **Service Management**
- [x] **GET /service** - ✅ WORKING
- [x] **GET /service/storage-backends** - ✅ WORKING
- [x] **GET /service/webhooks** - ✅ WORKING (but returning empty list)
- [ ] **POST /service/webhooks** - Create webhook
- [ ] **PUT /service/webhooks/{webhook_id}** - Update webhook
- [ ] **DELETE /service/webhooks/{webhook_id}** - Delete webhook

### **Flow Delete Requests**
- [x] **GET /flow-delete-requests** - ✅ WORKING (but returning empty list)
- [ ] **POST /flow-delete-requests** - Create deletion request
- [ ] **PUT /flow-delete-requests/{request_id}** - Update deletion request
- [ ] **DELETE /flow-delete-requests/{request_id}** - Cancel deletion request

## 🔧 **TECHNICAL DEBT & IMPROVEMENTS**

### **VAST Database Integration**
- [ ] **Fix `insert_pydict` method issue** - VAST Table objects need proper insert method
- [ ] **Improve query performance** - Analytics queries are slow and returning empty results
- [ ] **Add proper error handling** - Better error messages for database operations
- [ ] **Implement connection pooling** - Better database connection management

### **Data Validation & Schemas**
- [ ] **Add missing Pydantic schemas** - Collection schemas are missing from OpenAPI spec
- [ ] **Implement proper validation** - Input validation for all endpoints
- [ ] **Add response models** - Consistent response structures

### **Testing & Quality**
- [ ] **Fix collection creation tests** - Current tests are failing due to insert issues
- [ ] **Add integration tests** - Test real database operations
- [ ] **Performance testing** - Test endpoint response times
- [ ] **Error handling tests** - Test various error scenarios

### **Documentation**
- [ ] **Update OpenAPI spec** - Add missing endpoint definitions
- [ ] **API documentation** - Comprehensive endpoint documentation
- [ ] **Error code documentation** - Document all possible error responses

## 🎯 **PRIORITY ORDER**

### **HIGH PRIORITY (Fix Immediately)**
1. Fix `insert_pydict` method issue in VAST integration
2. Fix collection creation endpoints
3. Add missing GET endpoints for collections and objects

### **MEDIUM PRIORITY (Next Sprint)**
1. Implement missing CRUD operations for all entities
2. Add proper data validation and schemas
3. Improve analytics endpoint data retrieval

### **LOW PRIORITY (Future Releases)**
1. Add advanced analytics features
2. Implement webhook management
3. Add performance monitoring endpoints

## 📊 **CURRENT STATUS SUMMARY**

- **Total Endpoints**: ~40+ (estimated from TAMS API spec)
- **Working Endpoints**: ~15-20
- **Partially Working**: ~5-10 (returning data but with issues)
- **Missing Endpoints**: ~20-25
- **Critical Issues**: 2-3 (blocking core functionality)

## 🔄 **NEXT STEPS**

1. **Immediate**: Fix VAST `insert_pydict` method issue
2. **This Week**: Implement missing GET endpoints for collections and objects
3. **Next Week**: Add proper CRUD operations for all entities
4. **Ongoing**: Improve error handling and add comprehensive testing
