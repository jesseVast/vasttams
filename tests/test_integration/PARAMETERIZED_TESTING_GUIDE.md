# ✅ FINAL Implementation Guide: Parameterized Storage Testing

## 🎯 **What You Need to Do:**

### **Step 1: Add Configuration to Your Test File**

Add these lines after your existing imports:

```python
import os

# Simple storage backend configuration
USE_MOCK_STORAGE = os.getenv("TAMS_TEST_BACKEND", "mock") == "mock"
```

### **Step 2: Replace Lines 24-26 in test_basic_media_workflow Method**

**REPLACE THIS:**
```python
        # Initialize mock storage
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
```

**WITH THIS:**
```python
        # EASY SWITCHING: Environment variable controls storage backend
        if USE_MOCK_STORAGE:
            # Use mock storage (fast, no external dependencies)
            vast_storage = MockVastDBManager()
            s3_storage = MockS3Store()
            print(f"Using MOCK storage for testing")
        else:
            # Use real storage (requires external services) 
            from app.storage.vastdbmanager import VastDBManager
            from app.storage.s3_store import S3Store
            from app.core.config import get_settings
            
            settings = get_settings()
            # VastDBManager expects endpoints as a parameter
            vast_storage = VastDBManager(endpoints=settings.vast_endpoint)
            s3_storage = S3Store(
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                bucket_name=settings.s3_bucket_name
            )
            print(f"Using REAL storage from config.py")
```

### **Step 3: Add Success Message at End of test_basic_media_workflow**

Add these lines at the very end of your test method (after the analytics assertions):

```python
        backend = "mock" if USE_MOCK_STORAGE else "real"
        print(f"✅ Test completed successfully with {backend} storage")
```

### **Step 4: Apply Same Pattern to Other Test Methods (Optional)**

For any other test methods in your file, use the same pattern:

```python
def test_your_other_method(self):
    """Your test description"""
    
    # Add the same storage switching logic
    if USE_MOCK_STORAGE:
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
    else:
        from app.storage.vastdbmanager import VastDBManager
        from app.storage.s3_store import S3Store
        from app.core.config import get_settings
        
        settings = get_settings()
        vast_storage = VastDBManager(endpoints=settings.vast_endpoint)
        s3_storage = S3Store(
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            bucket_name=settings.s3_bucket_name
        )
    
    # Your existing test logic...
    # No changes needed to the rest of your test!
    
    # Add success message at the end
    backend = "mock" if USE_MOCK_STORAGE else "real"
    print(f"✅ Test completed with {backend} storage")
```

## 🚀 **How to Use Your Updated Test:**

### **Mock Storage (Fast, Default):**
```bash
# Default behavior - uses mock storage
pytest tests/test_integration/test_end_to_end_workflow.py -v

# Explicitly set mock mode
export TAMS_TEST_BACKEND=mock
pytest tests/test_integration/test_end_to_end_workflow.py -v
```

### **Real Storage (Requires Services):**
```bash
# Use real VAST and S3 storage from config.py
export TAMS_TEST_BACKEND=real
pytest tests/test_integration/test_end_to_end_workflow.py -v
```

### **Clean Output (No Warnings):**
```bash
# Mock with clean output
PYTHONWARNINGS="ignore" pytest tests/test_integration/test_end_to_end_workflow.py -v

# Real with clean output
TAMS_TEST_BACKEND=real PYTHONWARNINGS="ignore" pytest tests/test_integration/test_end_to_end_workflow.py -v
```

## ✅ **Benefits of This Approach:**

1. **✅ No Code Duplication** - Same test logic runs against both implementations
2. **✅ Easy Maintenance** - Changes only need to be made in one place  
3. **✅ Real Credentials** - Uses S3 and database credentials from config.py as requested
4. **✅ Flexible Execution** - Can run mock tests quickly, real tests when needed
5. **✅ Simple Switching** - Just set environment variable to switch modes
6. **✅ Minimal Changes** - Only a few lines changed in your existing test file

## 🎯 **Real Storage Configuration:**

Your test will automatically use these credentials from config.py when in real mode:

**VAST Database:**
- Endpoint: `http://172.200.204.90`
- Access Key: `SRSPW0DQT9T70Y787U68`
- Secret Key: `WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr`
- Bucket: `jthaloor-db`
- Schema: `tams7`

**S3 Storage:**
- Endpoint: `http://172.200.204.91`
- Access Key ID: `SRSPW0DQT9T70Y787U68`
- Secret Access Key: `WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr`
- Bucket: `jthaloor-s3`

## 🔧 **Example Output:**

**Mock Mode:**
```
Using MOCK storage for testing
✅ Test completed successfully with mock storage
```

**Real Mode:**
```
Using REAL storage from config.py
✅ Test completed successfully with real storage
```

## 📁 **Files Created for You:**

- ✅ `tests/test_integration/test_config.py` - Configuration management
- ✅ `tests/test_integration/example_usage.py` - Usage examples
- ✅ `tests/test_integration/test_end_to_end_workflow_parametrized.py` - Full parametrized example  
- ✅ `tests/test_integration/test_end_to_end_workflow_fixed.py` - Working example
- ✅ `tests/test_integration/README_PARAMETRIZATION.md` - Complete guide

**That's it!** Your test can now seamlessly switch between mock and real storage with just an environment variable. 🎉
