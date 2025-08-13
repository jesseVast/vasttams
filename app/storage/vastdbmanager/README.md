# VastDBManager - Modular Architecture

## Overview

The VastDBManager has been refactored into a modular, maintainable architecture that provides:

- **Enhanced Performance**: Intelligent caching, query optimization, and load balancing
- **Advanced Analytics**: Hybrid VAST + DuckDB analytics for complex operations
- **Scalability**: Multi-endpoint support with intelligent routing
- **Monitoring**: Comprehensive performance monitoring and health checks
- **Maintainability**: Clean separation of concerns with focused modules

## Architecture Components

### 1. Core Module (`core.py`)
The main `VastDBManager` class that orchestrates all components and provides the unified interface.

**Key Features:**
- Modular component initialization
- Background cache updates
- Performance monitoring integration
- Resource cleanup and context management

### 2. Cache Module (`cache/`)
Efficient caching system for table schemas and statistics.

**Components:**
- `TableCacheEntry`: Cache entry with expiration logic
- `CacheManager`: Thread-safe cache operations with TTL management

**Benefits:**
- Reduces database calls for metadata
- Automatic expiration and background updates
- Thread-safe operations with RLock

### 3. Queries Module (`queries/`)
Query processing and optimization components.

**Components:**
- `PredicateBuilder`: Converts Python predicates to VAST SQL filters
- `QueryOptimizer`: Optimizes QueryConfig based on table characteristics
- `QueryExecutor`: Executes queries with splits optimization

**Features:**
- Support for complex predicates (equality, ranges, string operations)
- Dynamic QueryConfig optimization based on table size
- Intelligent splits and subsplits configuration

### 4. Analytics Module (`analytics/`)
Advanced analytics capabilities combining VAST and DuckDB.

**Components:**
- `TimeSeriesAnalytics`: Time-series operations (moving averages, trends, anomalies)
- `AggregationAnalytics`: Statistical operations (percentiles, correlations, distributions)
- `PerformanceMonitor`: Query performance tracking and analysis
- `HybridAnalytics`: VAST filtering + DuckDB processing

**Hybrid Approach Benefits:**
- VAST handles efficient data filtering and extraction
- DuckDB processes filtered data with advanced SQL functions
- Best of both worlds: performance + functionality

### 5. Endpoints Module (`endpoints/`)
Multi-endpoint management and load balancing.

**Components:**
- `EndpointManager`: Health monitoring and endpoint status
- `LoadBalancer`: Intelligent endpoint selection strategies

**Features:**
- Health monitoring with automatic failure detection
- Load balancing based on operation type and endpoint performance
- Round-robin and performance-based routing

## Usage Examples

### Basic Usage

```python
from app.storage.vastdbmanager import VastDBManager

# Initialize with multiple endpoints
manager = VastDBManager([
    "http://vast1.example.com",
    "http://vast2.example.com",
    "http://vast3.example.com"
])

# Connect to database
manager.connect()

# Query with predicates
results = manager.query_with_predicates(
    table_name="media_segments",
    columns=["id", "format", "duration"],
    predicates={
        "format": "urn:x-nmos:format:video",
        "duration": {"gte": 30},
        "tags": {"contains": "live"}
    }
)
```

### Advanced Analytics

```python
# Time-series analysis
moving_avg = manager.time_series_analytics.calculate_moving_average(
    table=table,
    config=query_config,
    value_column="bitrate",
    time_column="timestamp",
    window_size="1 hour",
    start_time=start_time,
    end_time=end_time
)

# Hybrid analytics with DuckDB
percentiles = manager.hybrid_analytics.calculate_percentiles_hybrid(
    table=table,
    config=query_config,
    value_column="file_size",
    percentiles=[25, 50, 75, 90, 95, 99]
)
```

### Performance Monitoring

```python
# Get performance summary
summary = manager.get_performance_summary(time_window=timedelta(hours=1))
print(f"Success rate: {summary['success_rate']:.1f}%")
print(f"Average execution time: {summary['avg_execution_time']:.3f}s")

# Get slow queries
slow_queries = manager.performance_monitor.get_slow_queries(threshold=5.0)
for query in slow_queries:
    print(f"Slow query: {query['query_type']} on {query['table_name']}")
```

### Endpoint Management

```python
# Get endpoint statistics
endpoint_stats = manager.get_endpoint_stats()
print(f"Healthy endpoints: {endpoint_stats['healthy_endpoints']}/{endpoint_stats['total_endpoints']}")

# Get cache statistics
cache_stats = manager.get_cache_stats()
print(f"Active cache entries: {cache_stats['active_entries']}")
```

## Configuration

### Cache Configuration

```python
from datetime import timedelta

# Custom cache TTL
manager = VastDBManager(
    endpoints=["http://vast.example.com"],
    cache_ttl=timedelta(hours=2)  # 2 hour cache
)
```

### Query Configuration

```python
# Custom QueryConfig
from vastdb.transaction.schema.table import QueryConfig

config = QueryConfig(
    num_splits=8,
    num_sub_splits=4,
    rows_per_split=2_000_000,
    limit_rows_per_sub_split=200_000
)

# Use custom config
results = manager.query_with_splits_optimization(
    table_name="large_table",
    columns=["*"],
    query_config=config
)
```

## Performance Optimizations

### 1. Intelligent Caching
- **Schema Caching**: Table schemas cached with TTL
- **Statistics Caching**: Row counts and table metadata cached
- **Background Updates**: Periodic cache refresh without blocking operations

### 2. Query Optimization
- **Dynamic Splits**: Auto-calculate splits based on table size
- **Subsplit Tuning**: Optimize subsplits for different query types
- **Memory Management**: Adjust row limits for small tables

### 3. Load Balancing
- **Health Monitoring**: Track endpoint health and performance
- **Operation Routing**: Route operations to optimal endpoints
- **Failure Handling**: Automatic failover to healthy endpoints

### 4. Hybrid Analytics
- **VAST Filtering**: Efficient data extraction with predicates
- **DuckDB Processing**: Advanced analytics on filtered data
- **Memory Efficiency**: Only load relevant data into DuckDB

## Monitoring and Observability

### Performance Metrics
- Query execution times
- Rows processed per query
- Splits and subsplits utilization
- Success/failure rates

### Health Checks
- Endpoint availability
- Response times
- Error counts and types
- Cache hit rates

### Operational Intelligence
- Slow query detection
- Resource utilization
- Performance trends
- Capacity planning data

## Migration from Legacy

The new architecture maintains backward compatibility while providing enhanced functionality:

```python
# Old way (still works)
manager = VastDBManager("http://vast.example.com")

# New way (enhanced)
manager = VastDBManager([
    "http://vast1.example.com",
    "http://vast2.example.com"
])

# New features available
manager.query_with_predicates(...)
manager.get_performance_summary(...)
manager.hybrid_analytics.calculate_percentiles_hybrid(...)
```

## Dependencies

```bash
# Core dependencies
vastdb>=1.0.0
pyarrow>=12.0.0

# Analytics dependencies
duckdb>=0.9.0
ibis>=8.0.0  # Optional
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/test_vastdbmanager_modular.py -v

# Run specific test classes
pytest tests/test_vastdbmanager_modular.py::TestCacheManager -v

# Run with coverage
pytest tests/test_vastdbmanager_modular.py --cov=app.storage.vastdbmanager
```

## Contributing

When adding new features:

1. **Follow the modular pattern**: Create focused modules with single responsibilities
2. **Add comprehensive tests**: Include unit tests for new functionality
3. **Update documentation**: Document new features and usage examples
4. **Maintain backward compatibility**: Ensure existing code continues to work

## Future Enhancements

- **Machine Learning Integration**: Predictive query optimization
- **Advanced Load Balancing**: AI-powered endpoint selection
- **Distributed Caching**: Redis integration for multi-instance deployments
- **Real-time Analytics**: Streaming analytics capabilities
- **Custom Analytics Functions**: User-defined analytics operations

## Support

For issues and questions:
1. Check the test suite for usage examples
2. Review the performance monitoring data
3. Check endpoint health and cache statistics
4. Enable debug logging for detailed operation information
