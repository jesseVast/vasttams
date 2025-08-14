# TAMS Development Documentation

This document consolidates all development-related information for the TAMS (Time-addressable Media Store) API.

## 🚀 **Phase 3 Implementation & Refactoring Complete!**

### **What We've Accomplished**

#### **1. Complete Modular Refactoring** ✅
- **Broke down monolithic `vastdbmanager.py`** (1600+ lines) into focused, maintainable modules
- **Created clean separation of concerns** with single responsibility principle
- **Maintained backward compatibility** while adding powerful new features

#### **2. New Modular Architecture** 🏗️
```
app/storage/vastdbmanager/
├── __init__.py              # Main module exports
├── core.py                  # Main VastDBManager orchestrator
├── cache/                   # Intelligent caching system
│   ├── __init__.py
│   ├── table_cache.py       # Cache entry with TTL
│   └── cache_manager.py     # Thread-safe cache operations
├── queries/                 # Query processing & optimization
│   ├── __init__.py
│   ├── predicate_builder.py # Python → VAST SQL conversion
│   ├── query_optimizer.py   # Dynamic QueryConfig optimization
│   └── query_executor.py    # Splits-optimized execution
├── analytics/               # Advanced analytics capabilities
│   ├── __init__.py
│   ├── time_series_analytics.py    # Moving averages, trends, anomalies
│   ├── aggregation_analytics.py    # Percentiles, correlations, distributions
│   ├── performance_monitor.py      # Query performance tracking
│   └── hybrid_analytics.py        # VAST + DuckDB integration
└── endpoints/               # Multi-endpoint management
    ├── __init__.py
    ├── endpoint_manager.py  # Health monitoring & status
    └── load_balancer.py     # Intelligent endpoint selection
```

#### **3. Phase 3: Advanced Analytics & Monitoring** 📊

##### **Real-Time Analytics**
- **Moving Averages**: Time-windowed calculations with configurable periods
- **Trend Analysis**: Linear regression approximation for time-series data
- **Anomaly Detection**: Statistical outlier detection using z-scores
- **Window Functions**: Advanced time-based aggregations

##### **Advanced Aggregation Analytics**
- **Percentile Calculations**: P25, P50, P75, P90, P95, P99 with DuckDB
- **Correlation Analysis**: Statistical correlation between columns
- **Distribution Analysis**: Histogram generation with custom binning
- **Top-N Analysis**: Ranked aggregations by group

##### **Performance Monitoring**
- **Query Metrics**: Execution times, row counts, splits utilization
- **Slow Query Detection**: Automatic identification of performance issues
- **Performance Trends**: Historical analysis and capacity planning
- **Export Capabilities**: Metrics export for external analysis

##### **Operational Intelligence**
- **Endpoint Health**: Real-time monitoring of VAST cluster nodes
- **Load Balancing**: Intelligent routing based on operation type and performance
- **Cache Analytics**: Hit rates, expiration tracking, memory usage
- **System Health**: Comprehensive health checks and status reporting

#### **4. Hybrid Analytics Architecture** 🦆
- **VAST for Filtering**: Efficient data extraction using predicates
- **DuckDB for Processing**: Advanced SQL analytics on filtered data
- **Memory Efficiency**: Only load relevant data into DuckDB
- **Best of Both Worlds**: Performance + functionality

#### **5. Enhanced Performance Features** ⚡
- **Intelligent Caching**: TTL-based cache with background updates
- **Query Optimization**: Dynamic splits/subsplits based on table size
- **Load Balancing**: Performance-based endpoint selection
- **Background Processing**: Non-blocking cache and stats updates

### **Technical Implementation Details**

#### **Cache System**
- **Thread-Safe**: RLock-based concurrent access
- **TTL Management**: Automatic expiration with configurable timeouts
- **Background Updates**: Periodic refresh without blocking operations
- **Memory Efficient**: Configurable cache size limits

#### **Query Optimization**
- **Dynamic Configuration**: Auto-calculate splits based on table characteristics
- **Type-Specific Tuning**: Different optimizations for time-series vs aggregation
- **Memory Management**: Adjust row limits for small tables
- **Performance Monitoring**: Track optimization effectiveness

#### **Endpoint Management**
- **Health Monitoring**: Track response times and error rates
- **Automatic Failover**: Mark endpoints unhealthy after multiple failures
- **Load Distribution**: Round-robin and performance-based routing
- **Statistics Collection**: Comprehensive endpoint performance metrics

#### **Analytics Engine**
- **Modular Design**: Easy to add new analytical functions
- **Error Handling**: Robust error handling with detailed logging
- **Performance Tracking**: Monitor analytics operation performance
- **Extensible**: Clean interfaces for custom analytics

## 🔧 **Column Management Implementation**

### **Core Column Management Methods**

The following methods have been implemented in the `VastDBManager` class:

#### `add_columns(table_name: str, new_columns: Schema) -> bool`
- **Purpose**: Add new columns to an existing table
- **Behavior**: Transactional metadata operation with no data updates or allocations
- **Usage**: 
```python
new_columns = pa.schema([
    ('email', pa.string()),
    ('age', pa.int32()),
    ('is_active', pa.bool_())
])
success = manager.add_columns('users', new_columns)
```

#### `rename_column(table_name: str, current_column_name: str, new_column_name: str) -> bool`
- **Purpose**: Rename an existing column
- **Behavior**: Preserves column type and data
- **Usage**:
```python
success = manager.rename_column('users', 'age', 'user_age')
```

#### `drop_column(table_name: str, column_to_drop: Schema) -> bool`
- **Purpose**: Remove columns from a table
- **Behavior**: Column is tombstoned and becomes immediately inaccessible
- **Usage**:
```python
drop_schema = pa.schema([('unused_column', pa.string())])
success = manager.drop_column('users', drop_schema)
```

#### `column_exists(table_name: str, column_name: str) -> bool`
- **Purpose**: Check if a column exists in a table
- **Usage**:
```python
exists = manager.column_exists('users', 'email')
```

#### `get_table_columns(table_name: str) -> Schema`
- **Purpose**: Get column definitions for a table
- **Returns**: PyArrow schema containing column definitions

### **High-Level Interface in VASTStore**

The `VASTStore` class provides a higher-level interface with additional utility methods:

#### `list_table_columns(table_name: str) -> List[str]`
- Returns a list of column names for a table

#### `get_column_info(table_name: str, column_name: str) -> Optional[Dict[str, Any]]`
- Returns detailed information about a specific column including type, nullability, and metadata

### **Implementation Details**

#### **Architecture**
```
VASTStore (High-level interface)
    ↓
VastDBManager (Low-level operations)
    ↓
VAST Database (via vastdb Python SDK)
```

#### **Key Features**
1. **Transactional Operations**: All column operations are transactional
2. **Schema Caching**: Table schemas are cached for performance
3. **Error Handling**: Comprehensive error handling with graceful failures
4. **Logging**: Detailed logging for debugging and monitoring
5. **Type Safety**: Uses PyArrow schemas for type safety

#### **Performance Characteristics**
- **Add Columns**: Instant metadata operation, no data movement
- **Rename Columns**: Instant metadata operation, preserves data
- **Drop Columns**: Immediate tombstoning, background cleanup
- **Column Existence**: Fast schema lookup

## 🗑️ **Soft Delete Extension**

### **Overview**

This document describes the **Soft Delete Extension** to the official TAMS (Time-addressable Media Store) API specification. This is a vendor-specific enhancement that provides data safety and audit capabilities beyond the base specification.

### **Extension Status**
- **Type**: Vendor-specific enhancement
- **Compliance**: NOT part of the official TAMS API specification
- **Status**: Implemented and active by default
- **Version**: 1.0

### **What is Soft Delete?**

Soft delete is a data management technique where records are marked as "deleted" rather than being physically removed from the database. This provides several benefits:

- **Data Recovery**: Deleted records can be restored
- **Audit Trail**: Complete history of who deleted what and when
- **Data Integrity**: Maintains referential relationships
- **Compliance**: Meets regulatory requirements for data retention

### **Schema Extensions**

All database tables include additional soft delete fields:

```sql
-- Example schema extension for sources table
ALTER TABLE sources ADD COLUMN deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE sources ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE sources ADD COLUMN deleted_by VARCHAR(255);
```

### **API Extensions**

All delete endpoints support these additional query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `soft_delete` | boolean | `true` | Perform soft delete (flag as deleted) or hard delete (remove from database) |
| `cascade` | boolean | `true` | Cascade delete to associated records |
| `deleted_by` | string | `"system"` | User/system performing the deletion |

### **Examples**

#### Soft Delete a Source
```bash
# Default behavior (soft delete with cascade)
DELETE /sources/123e4567-e89b-12d3-a456-426614174000

# Explicit soft delete
DELETE /sources/123e4567-e89b-12d3-a456-426614174000?soft_delete=true&cascade=true&deleted_by=user123
```

#### Hard Delete a Source
```bash
# Hard delete with cascade (removes from database)
DELETE /sources/123e4567-e89b-12d3-a456-426614174000?soft_delete=false&cascade=true&deleted_by=admin
```

## 🐛 **Known Issues & Solutions**

### **Boto3 Version Compatibility Issue**

#### **Problem**
The TAMS application was experiencing S3 upload failures with boto3 version 1.38.46. The error was:
```
An error occurred (NotImplemented) when calling the PutObject operation: A header you provided implies functionality that is not implemented.
```

#### **Root Cause**
Boto3 version 1.38.46 automatically adds headers that are not supported by the MinIO S3-compatible storage backend:
- `Expect: 100-continue`
- `x-amz-checksum-crc32`
- `x-amz-sdk-checksum-algorithm`

These headers are automatically added by boto3 and cannot be easily disabled.

#### **Solution**
Downgrade to boto3 version 1.34.135 which doesn't add these problematic headers.

#### **Fixed Versions**
```txt
boto3==1.34.135
botocore==1.34.162
```

#### **Testing**
After downgrading, S3 operations work correctly with the MinIO backend.

#### **Notes**
- This issue affects MinIO S3-compatible storage backends
- The vasts3.py implementation works because it uses an older boto3 version
- Future boto3 versions may need to be tested for compatibility

## 📊 **Performance Improvements**

### **Query Performance**
- **VAST Integration**: Native VAST database operations
- **Intelligent Caching**: Schema and metadata caching
- **Query Optimization**: Dynamic splits and subsplits configuration
- **Load Balancing**: Multi-endpoint support with health monitoring

### **Analytics Performance**
- **Hybrid Architecture**: VAST for filtering, DuckDB for processing
- **Memory Efficiency**: Only load relevant data for analysis
- **Parallel Processing**: Background analytics operations
- **Performance Monitoring**: Real-time performance tracking

### **Storage Performance**
- **S3 Integration**: Efficient object storage with metadata
- **Batch Operations**: Bulk insert and update capabilities
- **Transaction Safety**: ACID compliance for data integrity
- **Background Cleanup**: Non-blocking maintenance operations
