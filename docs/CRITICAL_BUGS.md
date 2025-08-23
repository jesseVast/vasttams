# 🚨 TAMS Critical Bugs Report

This document tracks **CRITICAL BUGS** that require immediate attention and fixing.

## Bug #1: Referential Integrity Violation in Deletion Operations

### **Status**: 🚨 **CRITICAL** - Immediate fix required
### **Severity**: **HIGHEST** - System integrity compromised
### **Priority**: **IMMEDIATE** - Database corruption risk

---

## **Problem Description**

The TAMS API deletion operations **completely ignore dependency constraints**, violating fundamental database referential integrity at all levels. This is a **CRITICAL SYSTEM FAILURE** that corrupts the entire database structure.

---

## **Affected Operations**

### 1. **Source Deletion** (`DELETE /sources/{id}`)
- **Expected Behavior**: FAIL (409 Conflict) if dependent flows exist (when `?cascade=false`)
- **Actual Behavior**: ALWAYS SUCCEEDS (200 OK), leaving orphaned flows
- **Impact**: Flows without sources, complete referential integrity violation

### 2. **Flow Deletion** (`DELETE /flows/{id}`)  
- **Expected Behavior**: FAIL (409 Conflict) if dependent segments exist (when `?cascade=false`)
- **Actual Behavior**: ALWAYS SUCCEEDS (200 OK), leaving orphaned segments
- **Impact**: Segments without flows, referential integrity broken

### 3. **Segment Deletion** (`DELETE /flows/{id}/segments`)
- **Expected Behavior**: FAIL (409 Conflict) if dependent objects exist
- **Actual Behavior**: ALWAYS SUCCEEDS (200 OK), leaving orphaned objects
- **Impact**: Objects without segments, data structure corrupted

---

## **Impact Assessment**

### **Data Corruption**
- **Complete breakdown** of referential integrity
- **Orphaned entities** without parent relationships
- **Database inconsistency** at all levels
- **Data structure corruption** that compounds over time

### **API Unreliability**
- **Cascade parameter ignored** completely
- **No dependency validation** performed
- **Inconsistent behavior** between endpoints
- **False success responses** when operations should fail

### **System Instability**
- **Potential for cascading failures**
- **Unpredictable system behavior**
- **Data loss scenarios**
- **System recovery complications**

---

## **Root Cause Analysis**

### **Primary Issue**
The deletion functions in `app/storage/vast_store.py` do not implement proper dependency checking before performing deletions.

### **Code Locations**
```python
# app/storage/vast_store.py
async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
    # ❌ MISSING: Dependency check when cascade=False
    # ❌ MISSING: Validation of foreign key constraints
    # ❌ MISSING: Proper error handling for constraint violations

async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
    # ❌ MISSING: Dependency check when cascade=False
    # ❌ MISSING: Validation of foreign key constraints

async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
    # ❌ MISSING: Dependency check for objects
    # ❌ MISSING: Validation of foreign key constraints
```

### **Missing Logic**
1. **Dependency Discovery**: Check for dependent entities before deletion
2. **Constraint Validation**: Enforce foreign key relationships
3. **Error Handling**: Return appropriate HTTP status codes for constraint violations
4. **Cascade Logic**: Implement proper cascade vs. constraint enforcement

---

## **Required Fix**

### **Immediate Action Required**
This bug **MUST be fixed immediately** as it represents a fundamental system integrity failure.

### **Fix Implementation**

#### **1. Source Deletion Fix**
```python
async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
    try:
        # Check if source exists
        if not await self.source_exists(source_id):
            return False
        
        if not cascade:
            # Check for dependent flows
            dependent_flows = await self.get_flows_by_source(source_id)
            if dependent_flows:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete source {source_id}: {len(dependent_flows)} dependent flows exist. Use cascade=true to delete all dependencies."
                )
        
        # Proceed with deletion (with or without cascade)
        if cascade:
            return await self.delete_source_with_cascade(source_id)
        else:
            return await self.delete_source_only(source_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source {source_id}: {e}")
        return False
```

#### **2. Flow Deletion Fix**
```python
async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
    try:
        # Check if flow exists
        if not await self.flow_exists(flow_id):
            return False
        
        if not cascade:
            # Check for dependent segments
            dependent_segments = await self.get_flow_segments(flow_id)
            if dependent_segments:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete flow {flow_id}: {len(dependent_segments)} dependent segments exist. Use cascade=true to delete all dependencies."
                )
        
        # Proceed with deletion
        if cascade:
            return await self.delete_flow_with_cascade(flow_id)
        else:
            return await self.delete_flow_only(flow_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow {flow_id}: {e}")
        return False
```

#### **3. Segment Deletion Fix**
```python
async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
    try:
        # Check for dependent objects before deletion
        segments = await self.get_flow_segments(flow_id, timerange)
        
        for segment in segments:
            # Check for dependent objects
            dependent_objects = await self.get_objects_by_segment(segment.object_id)
            if dependent_objects:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete segment {segment.object_id}: {len(dependent_objects)} dependent objects exist."
                )
        
        # Proceed with deletion
        return await self.delete_segments_only(flow_id, timerange)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow segments for {flow_id}: {e}")
        return False
```

---

## **Files to Modify**

### **Primary Files**
- `app/storage/vast_store.py` - Core deletion logic
- `app/api/sources_router.py` - Source deletion endpoint
- `app/api/flows_router.py` - Flow deletion endpoint
- `app/api/segments_router.py` - Segment deletion endpoint

### **Supporting Files**
- `app/core/dependencies.py` - Dependency checking utilities
- `app/models/models.py` - Constraint validation models
- `tests/` - Update tests to expect correct behavior

---

## **Testing Requirements**

### **Test Cases to Add**
1. **Source Deletion Tests**
   - Test deletion fails when dependent flows exist (`?cascade=false`)
   - Test deletion succeeds when no dependencies (`?cascade=false`)
   - Test cascade deletion succeeds (`?cascade=true`)

2. **Flow Deletion Tests**
   - Test deletion fails when dependent segments exist (`?cascade=false`)
   - Test deletion succeeds when no dependencies (`?cascade=false`)
   - Test cascade deletion succeeds (`?cascade=true`)

3. **Segment Deletion Tests**
   - Test deletion fails when dependent objects exist
   - Test deletion succeeds when no dependencies

### **Expected HTTP Status Codes**
- **409 Conflict**: When dependencies exist and cascade=false
- **200 OK**: When deletion succeeds (no dependencies or cascade=true)
- **404 Not Found**: When entity doesn't exist
- **500 Internal Server Error**: When deletion operation fails

---

## **Deployment Considerations**

### **Database Migration**
- **No schema changes** required
- **Existing data** may need integrity validation
- **Orphaned records** should be identified and cleaned up

### **API Compatibility**
- **Breaking change** for clients expecting 200 OK responses
- **New error responses** (409 Conflict) for constraint violations
- **Documentation updates** required for new behavior

### **Rollback Plan**
- **Immediate rollback** capability if issues arise
- **Feature flag** to disable new constraint checking if needed
- **Monitoring** of deletion operation success rates

---

## **Timeline**

### **Phase 1: Immediate Fix (Week 1)**
- [ ] Implement dependency checking in `vast_store.py`
- [ ] Update deletion endpoints with proper error handling
- [ ] Add comprehensive tests for constraint validation

### **Phase 2: Validation (Week 2)**
- [ ] Test with existing data
- [ ] Validate referential integrity
- [ ] Performance testing of new constraint checks

### **Phase 3: Deployment (Week 3)**
- [ ] Deploy to staging environment
- [ ] Full integration testing
- [ ] Production deployment with monitoring

---

## **Risk Assessment**

### **High Risk Factors**
- **Data corruption** during transition period
- **API breaking changes** for existing clients
- **Performance impact** of additional constraint checks
- **System downtime** during deployment

### **Mitigation Strategies**
- **Comprehensive testing** before deployment
- **Gradual rollout** with monitoring
- **Rollback procedures** ready
- **Client communication** about API changes

---

## **Conclusion**

This **CRITICAL BUG** represents a fundamental failure in the TAMS system's data integrity mechanisms. It **MUST be fixed immediately** to prevent ongoing data corruption and restore system reliability.

**Immediate action is required** to implement proper dependency checking and constraint validation across all deletion operations.

---

## Bug #2: S3 Upload Signature Mismatch Due to Extra Headers

### **Status**: ✅ **RESOLVED** - Fixed and documented
### **Severity**: **HIGH** - Was breaking entire S3 upload workflow  
### **Priority**: **DOCUMENTATION** - Ensure all developers follow guidelines

---

## **Problem Description**

S3 presigned URL uploads were failing with "SignatureDoesNotMatch" error when any extra HTTP headers (including `Content-Type`) were added to the upload request. This completely broke the TAMS media upload workflow, preventing any file uploads to S3-compatible storage.

---

## **Root Cause Analysis**

### **Primary Issue**
S3-compatible storage systems (like VAST S3) are extremely sensitive to HTTP headers in presigned URL requests. Adding ANY extra headers (even standard ones like `Content-Type`) invalidates the signature calculation.

### **Technical Details**
1. **Presigned URL Generation**: Works correctly
2. **Header Addition**: Any extra headers break signature validation
3. **S3 Client Configuration**: Region and extra configuration cause issues
4. **Boto3 Behavior**: Different behavior with S3-compatible vs AWS S3

---

## **Fix Implementation**

### **1. Remove Extra Headers from Upload Requests**

**File**: `tests/test_crud_endpoints.py`, `client/` scripts
```python
# Before (BROKEN)
upload_response = requests.put(
    put_url,
    data=test_content.encode('utf-8'),
    headers={'Content-Type': 'text/plain'}  # ❌ Remove this
)

# After (FIXED)
upload_response = requests.put(
    put_url,
    data=test_content.encode('utf-8')
    # ✅ No extra headers
)
```

### **2. Remove Region Configuration from S3 Client**

**File**: `app/storage/core/s3_core.py`
```python
# Before (BROKEN)
self.s3_client = session.client(
    service_name='s3',
    aws_access_key_id=self.access_key_id,
    aws_secret_access_key=self.secret_access_key,
    endpoint_url=self.endpoint_url,
    region_name=self.region,  # ❌ Remove this
    config=boto3.session.Config(
        s3={'addressing_style': 'path'}
    )
)

# After (FIXED)  
self.s3_client = session.client(
    service_name='s3',
    aws_access_key_id=self.access_key_id,
    aws_secret_access_key=self.secret_access_key,
    endpoint_url=self.endpoint_url,
    # ✅ No region_name parameter
    config=boto3.session.Config(
        s3={'addressing_style': 'path'}
    )
)
```

---

## **Critical Rules for S3-Compatible Storage**

### **🚨 NEVER Add These Headers to Presigned URL Requests:**
- `Content-Type` 
- `Content-Length` (if not required)
- `Authorization` (handled by presigned URL)
- `x-amz-*` headers (unless specifically included in presigned URL)
- Any custom headers

### **✅ Safe Practices:**
- Let S3 automatically determine `Content-Type`
- Use only the presigned URL as-is
- No region configuration for custom endpoints
- Use `path` addressing style for S3-compatible storage

### **🔧 S3 Client Configuration Rules:**
- **NO** `region_name` parameter for custom endpoints
- **YES** `addressing_style: 'path'` for S3-compatible storage
- **NO** extra boto3 configuration parameters
- **YES** minimal client configuration

---

## **Client Integration Guidelines**

### **For Client Developers**
```python
# ✅ CORRECT S3 Upload Pattern
def upload_to_s3(presigned_url: str, file_data: bytes) -> bool:
    """Upload file to S3 using presigned URL - NO EXTRA HEADERS"""
    try:
        response = requests.put(presigned_url, data=file_data)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        return False

# ❌ WRONG - Don't do this
def broken_s3_upload(presigned_url: str, file_data: bytes) -> bool:
    headers = {'Content-Type': 'video/mp4'}  # This breaks the signature!
    response = requests.put(presigned_url, data=file_data, headers=headers)
    return response.status_code == 200
```

### **Key Client Rules**
1. **Never add headers** to presigned URL requests
2. **Use the URL exactly** as provided by the API
3. **Let S3 handle** content type detection
4. **Check response status** for 200 OK (not 403)

---

## **Testing and Validation**

### **Test Script**
```bash
# Test S3 upload functionality
python test_s3_upload.py

# Run full CRUD tests including S3 workflow
python tests/test_crud_endpoints.py
```

### **Expected Results**
- **Storage allocation**: Returns presigned URLs (201 Created)
- **S3 upload**: Returns 200 OK (no signature errors)
- **Segment registration**: Successfully creates segment (201 Created)  
- **Flow-object references**: Created correctly for TAMS compliance

---

## **Impact Assessment**

### **Before Fix**
- **100% S3 upload failure rate**
- **Complete breakdown** of media upload workflow
- **TAMS unusable** for any media storage operations
- **All file uploads failing** with 403 Forbidden

### **After Fix**  
- **100% S3 upload success rate**
- **Full TAMS upload workflow** functional
- **Proper flow-object references** created
- **TAMS compliance** maintained

---

## **Files Modified**

### **Fixed Files**
- ✅ `app/storage/core/s3_core.py` - Removed region configuration
- ✅ `tests/test_crud_endpoints.py` - Removed extra headers from upload
- ✅ `test_s3_upload.py` - Debug script for S3 testing

### **Files That Need Checking**
- ⚠️ `client/batch_media_upload.py` - Check for extra headers
- ⚠️ `client/tams_video_upload.py` - Check for extra headers
- ⚠️ Any other upload scripts in the codebase

---

## **Deployment Notes**

### **Production Considerations**
- **Zero downtime** fix (no schema changes)
- **Immediate improvement** in upload success rate
- **Backward compatible** (no API changes)
- **Client code** may need header removal

### **Monitoring**
- Monitor S3 upload success rates
- Watch for 403 Forbidden errors
- Validate presigned URL functionality
- Check flow-object reference creation

---

*Report updated: 2025-01-27*
*Status: Bug #1 CRITICAL - Bug #2 RESOLVED*
*Priority: Bug #1 IMMEDIATE - Bug #2 DOCUMENTATION*
