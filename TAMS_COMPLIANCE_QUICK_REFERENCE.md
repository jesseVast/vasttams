# TAMS API Compliance Quick Reference

## 🚨 **CRITICAL ISSUES TO FIX IMMEDIATELY**

### **1. Object Model - COMPLETELY OUT OF SPEC**
**Current (WRONG):**
```python
class Object(BaseModel):
    object_id: str  # ❌ Should be 'id'
    flow_references: List[Dict[str, Any]]  # ❌ Should be 'referenced_by_flows: List[str]'
    size: Optional[int] = None
    created: Optional[datetime] = None
```

**TAMS Required (CORRECT):**
```python
class Object(BaseModel):
    id: str  # ✅ Required by TAMS
    referenced_by_flows: List[str]  # ✅ Required by TAMS (UUID strings)
    first_referenced_by_flow: Optional[str] = None  # ✅ Optional by TAMS
    size: Optional[int] = None  # Additional for implementation
    created: Optional[datetime] = None  # Additional for implementation
```

### **2. Database Schema Changes Needed**
**Objects Table:**
- Rename `object_id` column → `id`
- Rename `flow_references` column → `referenced_by_flows`
- Add `first_referenced_by_flow` column
- Change data type from complex JSON to simple string array

### **3. API Response Changes**
**Current Response (WRONG):**
```json
{
  "object_id": "test-obj-1",
  "flow_references": [],
  "size": 1024,
  "created": "2025-08-17T17:47:51.075427+00:00"
}
```

**TAMS Required Response (CORRECT):**
```json
{
  "id": "test-obj-1",
  "referenced_by_flows": [],
  "first_referenced_by_flow": null,
  "size": 1024,
  "created": "2025-08-17T17:47:51.075427+00:00"
}
```

## 📁 **FILES TO UPDATE**

### **Priority 1 (CRITICAL):**
1. `app/models/models.py` - Rewrite Object model
2. `app/storage/vast_store.py` - Update database schema and operations
3. `app/api/objects.py` - Update object creation/retrieval logic
4. `app/api/objects_router.py` - Update API responses

### **Priority 2 (HIGH):**
1. `app/models/models.py` - Fix FlowSegment model (get_urls structure)
2. `app/models/models.py` - Fix Flow models (missing required fields)

## 🔧 **IMPLEMENTATION STEPS**

### **Step 1: Update Object Model**
- Change field names: `object_id` → `id`, `flow_references` → `referenced_by_flows`
- Change data types: `List[Dict[str, Any]]` → `List[str]`
- Add missing field: `first_referenced_by_flow: Optional[str]`

### **Step 2: Update Database Schema**
- Rename columns in objects table
- Update VAST store schema definition
- Handle data migration for existing objects

### **Step 3: Update API Logic**
- Fix object creation to use new field names
- Fix object retrieval to return TAMS-compliant format
- Update batch operations for new structure

### **Step 4: Test Compliance**
- Verify API responses match TAMS specification
- Test object creation and retrieval
- Validate field names and data types

## 📚 **TAMS SPECIFICATION REFERENCES**

- **Object Schema**: `api/schemas/object.json`
- **Flow Segment Schema**: `api/schemas/flow-segment.json`
- **Flow Core Schema**: `api/schemas/flow-core.json`
- **Source Schema**: `api/schemas/source.json`

## ⚠️ **IMPORTANT NOTES**

1. **This is NOT optional** - TAMS API compliance is required
2. **Field names must match exactly** - TAMS clients expect specific field names
3. **Data types must match exactly** - UUIDs as strings, not complex objects
4. **Required fields cannot be missing** - TAMS validation will fail without them

## 🎯 **SUCCESS CRITERIA**

- ✅ Object API returns responses with `id` field (not `object_id`)
- ✅ Object API returns responses with `referenced_by_flows` field (not `flow_references`)
- ✅ `referenced_by_flows` contains array of UUID strings (not complex objects)
- ✅ `first_referenced_by_flow` field is present (can be null)
- ✅ All object endpoints return TAMS-compliant responses
- ✅ Database schema matches new field names and types

## 🚀 **START HERE IN NEW CHAT**

Begin with updating the Object model in `app/models/models.py` to match the TAMS specification exactly. This is the foundation for all other changes.
