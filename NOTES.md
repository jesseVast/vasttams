# BBC TAMS Project Notes

## Current Status: Integration Test Results - 4 Model Validation Tests Need Fixing ⚠️

### 🔍 **Latest Integration Test Results (2025-08-16)**
- **Status**: 4 FAILED, 78 PASSED, 10 SKIPPED
- **Total Tests**: 92
- **Execution Time**: 2 minutes 46 seconds
- **Database**: Clean (fresh start after table cleanup)
- **Server**: Fresh restart with clean database

#### ❌ **Failed Tests (4) - Model Validation Issues**
1. **TestSourceModelReal.test_source_validation_with_invalid_format** - Expected ValueError not raised
2. **TestVideoFlowModelReal.test_video_flow_validation_with_invalid_dimensions** - Expected ValueError not raised  
3. **TestFlowSegmentModelReal.test_flow_segment_timerange_validation** - Expected ValueError not raised
4. **TestWebhookModelReal.test_webhook_url_validation** - Expected ValueError not raised

#### ✅ **Passed Tests (78) - All Major Systems Working**
- API Integration Tests: 8/8 PASSED
- VastDBManager Tests: 5/5 PASSED  
- Performance Tests: 12/12 PASSED
- S3 Store Tests: 12/12 PASSED
- Server Health Tests: 6/6 PASSED
- Connectivity Tests: 6/6 PASSED
- Real API Endpoints: 15/15 PASSED
- Model Creation Tests: 14/14 PASSED

#### ⏭️ **Skipped Tests (10) - Expected Behavior**
- Error handling tests (4) - Intentionally skipped for now
- VastDBManager connection tests (6) - Database dependency tests

### 🎯 **Next Priority: Fix Model Validation Tests**
The 4 failed tests indicate that Pydantic model validation is not working as expected. These tests expect ValueError exceptions for invalid data but the models are accepting invalid input.

### ✅ **Fix #16 Complete: Test Reorganization - Performance Tests Separated**
- **Status**: COMPLETED ✅
- **Issues Resolved**:
  - Moved performance tests from `tests/real_tests/` to dedicated `tests/performance_tests/` module
  - Created dedicated performance test runner (`tests/run_performance_tests.py`)
  - Updated consolidated test runner to exclude performance tests from integration tests
  - Added `--performance-only` option to consolidated test runner
  - Performance tests now focus on: performance benchmarking, stress testing, scalability testing
  - Integration tests now focus on: functionality, workflows, real backend integration
- **Results**: Clean separation of concerns, faster integration test runs, dedicated performance testing
- **Files Created**: 
  - `tests/performance_tests/__init__.py`
  - `tests/performance_tests/README.md`
  - `tests/run_performance_tests.py`
- **Files Moved**:
  - `tests/real_tests/test_performance_stress_real.py` → `tests/performance_tests/`
- **Files Updated**:
  - `tests/run_consolidated_tests.py` - Added performance-only option, updated test paths
  - `tests/README.md` - Updated to reflect new test organization

### ✅ **Fix #17 Complete: End-to-End Workflow Test Created**
- **Status**: COMPLETED ✅
- **Issues Resolved**:
  - Created comprehensive end-to-end workflow test (`tests/real_tests/test_end_to_end_workflow.py`)
  - Test validates complete workflow lifecycle: source → flow → segments → dependencies → cleanup
  - Uses existing test harness for proper UUID handling and test utilities
  - Tests dependency validation, data integrity, and proper deletion order
  - Created dedicated runner (`tests/run_end_to_end_test.py`) with database cleanup options
  - **Added file upload functionality** including presigned URL simulation and actual file handling
  - **Added real HTTP API calls** to TAMS for actual segment creation and file upload
- **Results**: Comprehensive end-to-end testing of TAMS workflow, proper dependency management validation, **file upload workflow testing**, **real API integration testing**
- **Files Created**: 
  - `tests/real_tests/test_end_to_end_workflow.py` - Main end-to-end test
  - `tests/run_end_to_end_test.py` - Dedicated test runner
- **Test Coverage**:
  - Complete workflow lifecycle (14 steps)
  - Dependency validation
  - Data integrity verification
  - Proper cleanup order enforcement
  - UUID handling through test harness
  - **File upload workflow with presigned URLs**
  - **Real API file upload simulation**
  - **Temporary file creation and cleanup**
  - **File size validation and metadata verification**
  - **Real HTTP API calls to TAMS server**
  - **Actual segment creation via API endpoints**
  - **Multipart form data file uploads**
  - **Segment metadata retrieval and validation**

### ✅ **Fix #18 Complete: Sample Workflow Documentation Created**
- **Status**: COMPLETED ✅
- **Issues Resolved**:
  - Created comprehensive sample workflow documentation (`docs/SAMPLE_WORKFLOW.md`)
  - Documents complete TAMS API workflow with detailed examples
  - Shows real API calls, requests, and responses from end-to-end test
  - Includes storage endpoint usage and presigned URL generation
  - Provides developer reference for API integration
  - **Enhanced to include complete lifecycle** with all 15 workflow steps
  - **Enhanced actual test** to include real deletion workflow testing
- **Results**: Complete API workflow reference with real examples, request/response formats, usage notes, **full lifecycle testing**, and **real deletion workflow validation**
- **Files Created**: 
  - `docs/SAMPLE_WORKFLOW.md` - Complete workflow documentation with examples
- **Documentation Coverage**:
  - **15 Complete Workflow Steps** with HTTP requests and responses
  - **Phase 1: Creation & Setup** (Steps 1-8) - Source, flow, segment creation
  - **Phase 2: Dependency Validation** (Steps 9-11) - Flow management and constraints
  - **Phase 3: Deletion Workflow** (Steps 12-15) - Cleanup order and dependency testing
  - **Source Creation** - POST /sources with full response
  - **Flow Creation** - POST /flows with video metadata
  - **Storage Allocation** - POST /flows/{flow_id}/storage with presigned URLs
  - **Segment Creation** - Both JSON-only and file upload methods
  - **File Upload** - Multipart form data examples
  - **Data Retrieval** - GET endpoints and responses
  - **Dependency Testing** - Foreign key constraints and validation
  - **Cleanup Workflow** - Proper deletion order and dependency resolution
  - **Real API Examples** - Actual UUIDs, timestamps, and S3 URLs
  - **Developer Notes** - Usage patterns, error handling, and best practices
  - **Production Considerations** - Security, scalability, and monitoring
  - **Test Execution Guide** - How to run the complete workflow test
- **Test Enhancement**:
  - **Added `test_complete_deletion_workflow`** method to actual test
  - **Real HTTP API calls** for deletion workflow testing
  - **Dependency constraint validation** with actual API responses
  - **Cleanup order testing** with real deletion operations
  - **Final state verification** with actual system state checks

### 🚨 **CRITICAL BUG #1: Referential Integrity Violation in Deletion Operations**
- **Status**: CRITICAL BUG IDENTIFIED ❌
- **Severity**: **CRITICAL** - Data corruption and referential integrity violation
- **Issue**: TAMS API deletion operations ignore dependency constraints, violating fundamental database referential integrity
- **Affected Operations**:
  1. **Source Deletion**: `DELETE /sources/{id}?cascade=false` succeeds even with dependent flows
  2. **Flow Deletion**: `DELETE /flows/{id}?cascade=false` succeeds even with dependent segments  
  3. **Segment Deletion**: `DELETE /flows/{id}/segments` succeeds even with dependent objects
- **Expected Behavior**: 
  - **Without cascade** (`?cascade=false`): MUST FAIL (400/409/422) if dependencies exist
  - **With cascade** (`?cascade=true`): MUST SUCCEED (200) by deleting parent + all dependencies
- **Actual Behavior**:
  - **All deletion operations SUCCEED** regardless of cascade parameter
  - **Dependencies ignored** completely
  - **Referential integrity violated** at all levels
- **Impact**: 
  - **Data Corruption**: Orphaned entities without parents
  - **Database Inconsistency**: Referential integrity completely broken
  - **API Unreliability**: Cascade parameter has no effect
  - **System Instability**: Potential for cascading failures
- **Location**: Multiple files across the deletion chain:
  - `app/api/sources_router.py` - Source deletion
  - `app/api/flows_router.py` - Flow deletion  
  - `app/api/segments_router.py` - Segment deletion
  - `app/storage/vast_store.py` - Core deletion logic
- **Fix Required**: **IMMEDIATE** - Implement proper dependency checking before ANY deletion operation
- **Priority**: **HIGHEST** - This is a fundamental system integrity issue
- **Detailed Report**: See `docs/CRITICAL_BUGS.md` for comprehensive analysis and fix implementation

## 📚 **Logging Best Practices Implementation Guide**

### **Overview**
This guide documents the logging best practices implemented across the BBC TAMS application, providing a template for applying these patterns to other projects.

### **Best Practices Applied**

#### **1. Structured Logging Levels**
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about application flow
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for actual problems

#### **2. Conditional Debug Logging**
```python
# ✅ GOOD: Conditional debug logging
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Processing complex data: %s", complex_data)

# ❌ BAD: Always executed debug logging
logger.debug(f"Processing complex data: {complex_data}")
```

#### **3. Performance-Optimized String Formatting**
```python
# ✅ GOOD: %s formatting (lazy evaluation)
logger.info("Created %d objects for flow %s", count, flow_id)
logger.error("Failed to process %s: %s", object_type, error)

# ❌ BAD: f-string formatting (always evaluated)
logger.info(f"Created {count} objects for flow {flow_id}")
logger.error(f"Failed to process {object_type}: {error}")
```

#### **4. Context-Rich Messages**
```python
# ✅ GOOD: Include relevant context
logger.error("Failed to get flow %s from store %s: %s", 
            flow_id, store_type, error)

# ❌ BAD: Generic messages
logger.error("Failed to get flow: %s", error)
```

#### **5. Environment-Aware Configuration**
```python
# config.py
import os
from pydantic import Field

class Settings(BaseSettings):
    log_level: str = Field(
        default="DEBUG" if os.getenv("ENVIRONMENT") == "development" else "INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s" if os.getenv("ENVIRONMENT") == "production" else "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        description="Log message format"
    )
```

#### **6. Structured Debug Data**
```python
# ✅ GOOD: Structured debug information
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Building VAST predicates from input: %s", predicates)
    logger.debug("Processing AND logic at top level")
    logger.debug("AND logic result: %s", result)

# ❌ BAD: Unstructured debug output
logger.debug(f"Building predicates: {predicates}")
```

#### **7. Performance-Aware Logging**
```python
# ✅ GOOD: Avoid expensive operations in logging
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Complex object: %s", str(complex_object))

# ❌ BAD: Expensive operations always executed
logger.debug(f"Complex object: {complex_object.expensive_method()}")
```

### **Implementation Steps**

#### **Step 1: Update Configuration**
```python
# config.py
import os
from pydantic import Field

class Settings(BaseSettings):
    log_level: str = Field(
        default="DEBUG" if os.getenv("ENVIRONMENT") == "development" else "INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s" if os.getenv("ENVIRONMENT") == "production" else "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        description="Log message format"
    )
```

#### **Step 2: Update Main Application**
```python
# main.py
from .config import get_settings

def setup_logging():
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format
    )
```

#### **Step 3: Convert F-String Logging**
```python
# Before
logger.error(f"Failed to process {object_id}: {error}")
logger.info(f"Created {count} items")

# After
logger.error("Failed to process %s: %s", object_id, error)
logger.info("Created %d items", count)
```

#### **Step 4: Add Conditional Debug Logging**
```python
# Before
logger.debug(f"Processing data: {data}")

# After
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Processing data: %s", data)
```

#### **Step 5: Environment Setup**
```bash
# Development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Production
export ENVIRONMENT=production
export LOG_LEVEL=INFO
```

### **Benefits Achieved**

#### **Performance**
- **Lazy evaluation** of log arguments
- **Reduced string interpolation overhead**
- **Conditional debug logging** prevents unnecessary processing

#### **Maintainability**
- **Consistent patterns** across all modules
- **Environment-aware configuration** for different deployment scenarios
- **Structured debug information** for easier troubleshooting

#### **Production Readiness**
- **Performance optimized** for high-traffic environments
- **Configurable logging levels** without code changes
- **Professional logging standards** for production deployments

### **Files to Update When Applying These Practices**

1. **Configuration files** - Add environment-aware logging settings
2. **Main application files** - Update logging setup
3. **All Python modules** - Convert f-string logging to %s formatting
4. **Test configuration** - Set appropriate environment variables
5. **Management scripts** - Apply consistent logging patterns

### **Verification Commands**

```bash
# Check for remaining f-string logging
grep_search "logger\.(error|info|warning|debug)\(f\"" "**/*.py"

# Check for proper logging imports
grep_search "import logging|logger = logging\.getLogger" "**/*.py"

# Verify environment variables are set
echo "ENVIRONMENT: $ENVIRONMENT"
echo "LOG_LEVEL: $LOG_LEVEL"
```

This logging implementation provides a robust, performant, and maintainable logging system that can be easily replicated across other projects! 🚀

## 📊 **Current Test Status**
- **✅ PASSED**: 71 tests
- **⏭️ SKIPPED**: 4 tests (environment-related, not code issues)
- **❌ FAILED**: 0 tests

## 🔧 **Technical Solutions Implemented**

### **1. FastAPI Dependency Override Pattern**
```python
# Instead of unittest.mock.patch, use FastAPI's dependency override
app.dependency_overrides[get_vast_store] = lambda: mock_store

# Clean up after each test
@pytest.fixture(autouse=True)
def cleanup_mock_store():
    yield
    app.dependency_overrides.clear()
```

### **2. MockVASTStore Class**
```python
class MockVASTStore:
    def __init__(self):
        self.sources = {}
        self.flows = {}
        self.segments = {}
        self.objects = {}
    
    async def create_source(self, source, *args, **kwargs):
        self.sources[str(source.id)] = source
        return True
    
    # ... other async methods
```

### **3. TAMS TimeRange Format**
- **Official Format**: `^(\\[|\\()?(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?(_(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?)?(\\]|\\))?$`
- **Examples**: `[0:0_10:0)`, `(5:0_`, `[1694429247:0_1694429248:0)`
- **Correct Usage**: `"0:0_3600:0"` (1 hour range)

### **4. VastDBManager Enhancements**
- **Lazy Connection**: `auto_connect=False` for testing
- **Backward Compatibility**: `insert_record()` alias
- **General Caching**: Extended CacheManager with `set()`/`get()` methods

## 🎯 **Remaining Work**
- **4 skipped tests**: Environment-related (VAST store availability)
- **No code issues remaining**
- **Test suite is production-ready**

## 📝 **Key Learnings**
1. **FastAPI Testing**: Use `app.dependency_overrides` not `unittest.mock.patch`
2. **TAMS Standards**: Follow official API specification for data formats
3. **Performance Testing**: Set realistic thresholds based on environment
4. **Mock Implementation**: Create comprehensive mock classes that match real behavior
5. **Type Consistency**: Ensure UUID/string handling is consistent across mocks

## 🚀 **Next Steps**
- Monitor the 4 environment-dependent skipped tests
- Consider adding more comprehensive integration tests
- Document the testing patterns for future development

## 🔮 **Planned Enhancements**

### **Trino Integration for Advanced Query Capabilities**

#### **Overview**
Integration of Trino (formerly PrestoSQL) to provide advanced SQL query capabilities alongside the existing VAST database infrastructure.

#### **Key Benefits**
- **SQL Interface**: Standard SQL queries for complex analytics
- **Federated Queries**: Query across multiple data sources simultaneously
- **Advanced Functions**: Window functions, complex aggregations, and analytics
- **Performance**: Optimized for large-scale data processing
- **Compatibility**: Works with existing VAST database and S3 storage

#### **Implementation Plan**

##### **Phase 1: Core Integration**
- [ ] Install and configure Trino server
- [ ] Create Trino connector for VAST database
- [ ] Set up S3 connector for direct S3 queries
- [ ] Implement basic query routing

##### **Phase 2: Advanced Features**
- [ ] Federated queries across VAST + S3
- [ ] Complex analytics queries (window functions, aggregations)
- [ ] Performance optimization for large datasets
- [ ] Query caching and optimization

##### **Phase 3: Production Features**
- [ ] Query monitoring and performance metrics
- [ ] Security integration with existing auth system
- [ ] Load balancing and high availability
- [ ] Integration with observability stack

#### **Technical Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App  │    │   Trino Server  │    │   VAST Store    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Query API  │◄┼────┼►│ Coordinator │ │    │ │ Database    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Auth &     │ │    │ ┌─────────────┐ │    │ │ S3 Storage  │ │
│ │ Security   │ │    │ │ Workers     │ │    │ └─────────────┘ │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Use Cases**
1. **Complex Analytics**: Multi-table joins and aggregations
2. **Data Exploration**: Ad-hoc SQL queries for data analysis
3. **Reporting**: Scheduled reports with complex business logic
4. **Data Integration**: Federated queries across multiple sources
5. **Performance Analysis**: Query performance optimization and monitoring

#### **Dependencies**
- **Trino Server**: Core query engine
- **VAST Connector**: Custom connector for VAST database
- **S3 Connector**: Hive connector for S3 data
- **Authentication**: Integration with existing auth system
- **Monitoring**: Integration with Prometheus/Grafana stack

#### **Performance Considerations**
- **Query Optimization**: Trino's cost-based optimizer
- **Parallel Processing**: Distributed query execution
- **Caching**: Query result caching for repeated queries
- **Resource Management**: Memory and CPU allocation per query
- **Monitoring**: Query performance metrics and alerting

This enhancement will significantly expand the analytical capabilities of the TAMS system while maintaining compatibility with existing infrastructure.
