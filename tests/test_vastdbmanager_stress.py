"""Comprehensive stress tests for the new modular VastDBManager"""

import pytest
import time
import random
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Import the new modular components
from app.storage.vastdbmanager import VastDBManager
from app.storage.vastdbmanager.cache import CacheManager
from app.storage.vastdbmanager.analytics import TimeSeriesAnalytics, HybridAnalytics
from app.storage.vastdbmanager.queries import PredicateBuilder

# Configure logging for stress tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVastDBManagerStress:
    """Stress tests for VastDBManager with real database operations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Use the endpoints from config
        from app.core.config import get_settings
        
        # Initialize with multiple endpoints for load testing
        self.endpoints = [
            "http://172.200.204.90",
            "http://172.200.204.91", 
            "http://172.200.204.93",
            "http://172.200.204.92"
        ]
        
        self.manager = VastDBManager(self.endpoints)
        self.test_table_name = f"stress_test_{int(time.time())}"
        
        # Test data parameters
        self.num_records = 10000  # Start with 10K records for stress testing
        self.time_range_days = 30  # 30 days of time-series data
        
        logger.info(f"Setting up stress test with {self.num_records} records over {self.time_range_days} days")
    
    def teardown_method(self):
        """Clean up after tests"""
        try:
            if hasattr(self, 'manager'):
                self.manager.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def generate_test_data(self) -> List[Dict[str, Any]]:
        """Generate realistic test data for stress testing"""
        logger.info("Generating test data...")
        
        start_time = datetime.now() - timedelta(days=self.time_range_days)
        end_time = datetime.now()
        
        data = []
        for i in range(self.num_records):
            # Generate timestamp within the range
            timestamp = start_time + timedelta(
                seconds=random.randint(0, int((end_time - start_time).total_seconds()))
            )
            
            # Generate realistic media segment data
            record = {
                'id': f"segment_{i:06d}",
                'timestamp': timestamp,  # Use Python datetime object directly for optimal VAST performance
                'format': random.choice(['urn:x-nmos:format:video', 'urn:x-nmos:format:audio']),
                'duration': random.uniform(1.0, 60.0),  # 1-60 seconds
                'bitrate': random.randint(1000000, 50000000),  # 1-50 Mbps
                'resolution_width': random.choice([1920, 3840, 4096]),
                'resolution_height': random.choice([1080, 2160, 2160]),
                'file_size': random.randint(1000000, 100000000),  # 1-100 MB
                'codec': random.choice(['H.264', 'H.265', 'ProRes', 'DNxHD']),
                'fps': random.choice([24, 25, 30, 50, 60]),
                'tags': random.choice(['live', 'archive', 'news', 'sports', 'entertainment']),
                'source_id': f"source_{random.randint(1, 10):02d}",
                'flow_id': f"flow_{random.randint(1, 5):02d}",
                'segment_number': i,
                'is_keyframe': random.choice([True, False]),
                'metadata': {
                    'location': random.choice(['studio_a', 'studio_b', 'remote_location']),
                    'operator': f"operator_{random.randint(1, 5)}",
                    'quality_score': random.uniform(0.8, 1.0)
                }
            }
            data.append(record)
        
        logger.info(f"Generated {len(data)} test records")
        return data
    
    def create_test_table(self):
        """Create test table with appropriate schema"""
        try:
            import pyarrow as pa
            
            # Create comprehensive schema for media segments
            schema = pa.schema([
                pa.field('id', 'string'),
                pa.field('timestamp', pa.timestamp('us')),  # Use PyArrow timestamp for optimal VAST performance
                pa.field('format', 'string'),
                pa.field('duration', 'float64'),
                pa.field('bitrate', 'int64'),
                pa.field('resolution_width', 'int32'),
                pa.field('resolution_height', 'int32'),
                pa.field('file_size', 'int64'),
                pa.field('codec', 'string'),
                pa.field('fps', 'int32'),
                pa.field('tags', 'string'),
                pa.field('source_id', 'string'),
                pa.field('flow_id', 'string'),
                pa.field('segment_number', 'int32'),
                pa.field('is_keyframe', 'bool'),
                pa.field('metadata', 'string')  # JSON string for metadata
            ])
            
            # Define VAST projections for optimal performance
            projections = {
                'time_series': ['timestamp'],  # Sorted for time-range queries
                'categorical': ['format', 'codec', 'tags', 'source_id', 'flow_id'],  # Unsorted for filtering
                'numeric_ranges': ['bitrate', 'resolution_width', 'duration']  # Unsorted for range queries
            }
            
            # Connect and create table with VAST projections
            self.manager.connect()
            self.manager.create_table(self.test_table_name, schema, projections=projections)
            
            logger.info(f"Created test table with VAST projections: {self.test_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create test table: {e}")
            raise
    
    def populate_test_data(self, data: List[Dict[str, Any]]):
        """Populate test table with data"""
        try:
            logger.info(f"Populating table with {len(data)} records...")
            start_time = time.time()
            
            # Insert data in batches for better performance
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Convert to column-oriented format for efficient insertion
                batch_dict = {}
                for key in batch[0].keys():
                    if key == 'metadata':
                        # Convert metadata dict to JSON string
                        batch_dict[key] = [str(record[key]) for record in batch]
                    else:
                        batch_dict[key] = [record[key] for record in batch]
                
                self.manager.insert_pydict(self.test_table_name, batch_dict)
                
                if (i + batch_size) % 5000 == 0:
                    logger.info(f"Inserted {i + batch_size}/{len(data)} records...")
            
            insertion_time = time.time() - start_time
            logger.info(f"Data population completed in {insertion_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to populate test data: {e}")
            raise
    
    def test_concurrent_query_stress(self):
        """Test concurrent query performance under stress"""
        logger.info("Starting concurrent query stress test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Define query patterns for stress testing
        query_patterns = [
            # Time-range queries
            {'timestamp': {'between': [datetime.now() - timedelta(days=7), datetime.now()]}},
            {'timestamp': {'between': [datetime.now() - timedelta(days=14), datetime.now() - timedelta(days=7)]}},
            {'timestamp': {'between': [datetime.now() - timedelta(days=21), datetime.now() - timedelta(days=14)]}},
            
            # Format-based queries
            {'format': 'urn:x-nmos:format:video'},
            {'format': 'urn:x-nmos:format:audio'},
            
            # Resolution queries
            {'resolution_width': {'gte': 1920}},
            {'resolution_width': {'gte': 3840}},
            
            # Bitrate queries
            {'bitrate': {'gte': 10000000}},  # 10 Mbps
            {'bitrate': {'between': [5000000, 20000000]}},  # 5-20 Mbps
            
            # Complex combined queries
            {
                'format': 'urn:x-nmos:format:video',
                'resolution_width': {'gte': 1920},
                'bitrate': {'gte': 10000000}
            },
            {
                'tags': 'live',
                'duration': {'gte': 30},
                'is_keyframe': True
            }
        ]
        
        # Test concurrent query execution
        num_concurrent_queries = 20
        query_results = []
        
        def execute_query(query_id: int, predicates: Dict[str, Any]):
            """Execute a single query and return results"""
            try:
                start_time = time.time()
                
                result = self.manager.query_with_predicates(
                    table_name=self.test_table_name,
                    columns=['id', 'timestamp', 'format', 'duration', 'bitrate'],
                    predicates=predicates,
                    limit=1000
                )
                
                execution_time = time.time() - start_time
                
                return {
                    'query_id': query_id,
                    'execution_time': execution_time,
                    'rows_returned': len(result) if result else 0,
                    'success': True
                }
                
            except Exception as e:
                return {
                    'query_id': query_id,
                    'execution_time': 0,
                    'rows_returned': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute queries concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_queries) as executor:
            # Submit all queries
            future_to_query = {
                executor.submit(execute_query, i, query_patterns[i % len(query_patterns)]): i
                for i in range(num_concurrent_queries)
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_query):
                result = future.result()
                query_results.append(result)
                
                if result['success']:
                    logger.info(f"Query {result['query_id']} completed in {result['execution_time']:.3f}s, "
                              f"returned {result['rows_returned']} rows")
                else:
                    logger.error(f"Query {result['query_id']} failed: {result.get('error', 'Unknown error')}")
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_queries = [r for r in query_results if r['success']]
        failed_queries = [r for r in query_results if not r['success']]
        
        if successful_queries:
            avg_execution_time = sum(r['execution_time'] for r in successful_queries) / len(successful_queries)
            max_execution_time = max(r['execution_time'] for r in successful_queries)
            min_execution_time = min(r['execution_time'] for r in successful_queries)
            
            logger.info(f"Concurrent query stress test completed:")
            logger.info(f"  Total time: {total_time:.2f}s")
            logger.info(f"  Successful queries: {len(successful_queries)}/{num_concurrent_queries}")
            logger.info(f"  Failed queries: {len(failed_queries)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
            logger.info(f"  Min execution time: {min_execution_time:.3f}s")
            logger.info(f"  Max execution time: {max_execution_time:.3f}s")
        
        # Assertions for test validation
        assert len(successful_queries) >= num_concurrent_queries * 0.8, "Too many queries failed"
        assert avg_execution_time < 5.0, "Average query time too high"
    
    def test_time_series_analytics_stress(self):
        """Test time-series analytics performance under stress"""
        logger.info("Starting time-series analytics stress test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Test different time-series analytics operations
        analytics_tests = [
            {
                'name': 'Moving Average - 1 Hour',
                'operation': 'moving_average',
                'params': {'window_size': '1 hour'}
            },
            {
                'name': 'Moving Average - 1 Day',
                'operation': 'moving_average',
                'params': {'window_size': '1 day'}
            },
            {
                'name': 'Trend Analysis - 7 Days',
                'operation': 'trends',
                'params': {'trend_period': '1 day'}
            },
            {
                'name': 'Anomaly Detection',
                'operation': 'anomalies',
                'params': {'threshold': 2.0}
            }
        ]
        
        # Execute analytics operations
        analytics_results = []
        
        for test in analytics_tests:
            try:
                start_time = time.time()
                
                if test['operation'] == 'moving_average':
                    result = self.manager.time_series_analytics.calculate_moving_average(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        window_size=test['params']['window_size'],
                        start_time=datetime.now() - timedelta(days=7),
                        end_time=datetime.now()
                    )
                elif test['operation'] == 'trends':
                    result = self.manager.time_series_analytics.calculate_trends(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        trend_period=test['params']['trend_period'],
                        start_time=datetime.now() - timedelta(days=7),
                        end_time=datetime.now()
                    )
                elif test['operation'] == 'anomalies':
                    result = self.manager.time_series_analytics.detect_anomalies(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        threshold=test['params']['threshold'],
                        start_time=datetime.now() - timedelta(days=7),
                        end_time=datetime.now()
                    )
                
                execution_time = time.time() - start_time
                
                analytics_results.append({
                    'test_name': test['name'],
                    'execution_time': execution_time,
                    'result_size': len(result) if isinstance(result, list) else 1,
                    'success': True
                })
                
                logger.info(f"Analytics test '{test['name']}' completed in {execution_time:.3f}s")
                
            except Exception as e:
                analytics_results.append({
                    'test_name': test['name'],
                    'execution_time': 0,
                    'result_size': 0,
                    'success': False,
                    'error': str(e)
                })
                
                logger.error(f"Analytics test '{test['name']}' failed: {e}")
        
        # Analyze analytics results
        successful_analytics = [r for r in analytics_results if r['success']]
        failed_analytics = [r for r in analytics_results if not r['success']]
        
        if successful_analytics:
            avg_execution_time = sum(r['execution_time'] for r in successful_analytics) / len(successful_analytics)
            
            logger.info(f"Time-series analytics stress test completed:")
            logger.info(f"  Successful operations: {len(successful_analytics)}/{len(analytics_tests)}")
            logger.info(f"  Failed operations: {len(failed_analytics)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
        
        # Assertions
        assert len(successful_analytics) >= len(analytics_tests) * 0.7, "Too many analytics operations failed"
    
    def test_cache_performance_stress(self):
        """Test cache performance under stress"""
        logger.info("Starting cache performance stress test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Test cache performance with repeated operations
        cache_operations = 1000
        cache_results = []
        
        def cache_operation(operation_id: int):
            """Perform a cache operation"""
            try:
                start_time = time.time()
                
                # Randomly choose operation type
                operation_type = random.choice(['columns', 'stats', 'tables'])
                
                if operation_type == 'columns':
                    result = self.manager.get_table_columns(self.test_table_name)
                    success = result is not None
                elif operation_type == 'stats':
                    result = self.manager.get_table_stats(self.test_table_name)
                    success = 'total_rows' in result
                else:  # tables
                    result = self.manager.tables
                    success = self.test_table_name in result
                
                execution_time = time.time() - start_time
                
                return {
                    'operation_id': operation_id,
                    'operation_type': operation_type,
                    'execution_time': execution_time,
                    'success': success
                }
                
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'operation_type': 'unknown',
                    'execution_time': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute cache operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_operation = {
                executor.submit(cache_operation, i): i
                for i in range(cache_operations)
            }
            
            for future in concurrent.futures.as_completed(future_to_operation):
                result = future.result()
                cache_results.append(result)
        
        total_time = time.time() - start_time
        
        # Analyze cache performance
        successful_operations = [r for r in cache_results if r['success']]
        failed_operations = [r for r in cache_results if not r['success']]
        
        if successful_operations:
            avg_execution_time = sum(r['execution_time'] for r in successful_operations) / len(successful_operations)
            max_execution_time = max(r['execution_time'] for r in successful_operations)
            
            logger.info(f"Cache performance stress test completed:")
            logger.info(f"  Total operations: {cache_operations}")
            logger.info(f"  Successful operations: {len(successful_operations)}")
            logger.info(f"  Failed operations: {len(failed_operations)}")
            logger.info(f"  Total time: {total_time:.2f}s")
            logger.info(f"  Average operation time: {avg_execution_time:.6f}s")
            logger.info(f"  Max operation time: {max_execution_time:.6f}s")
            logger.info(f"  Operations per second: {cache_operations / total_time:.1f}")
        
        # Get cache statistics
        cache_stats = self.manager.get_cache_stats()
        logger.info(f"Cache statistics: {cache_stats}")
        
        # Assertions
        assert len(successful_operations) >= cache_operations * 0.95, "Too many cache operations failed"
        assert avg_execution_time < 0.001, "Cache operations too slow"
    
    def test_endpoint_load_balancing_stress(self):
        """Test endpoint load balancing under stress"""
        logger.info("Starting endpoint load balancing stress test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Test endpoint selection under load
        endpoint_selections = 100
        endpoint_results = []
        
        def endpoint_operation(operation_id: int):
            """Test endpoint selection for different operation types"""
            try:
                start_time = time.time()
                
                # Randomly choose operation type
                operation_type = random.choice(['read', 'write', 'analytics'])
                
                # Get endpoint for operation
                endpoint = self.manager.load_balancer.get_endpoint(operation_type)
                
                execution_time = time.time() - start_time
                
                return {
                    'operation_id': operation_id,
                    'operation_type': operation_type,
                    'endpoint': endpoint,
                    'execution_time': execution_time,
                    'success': endpoint is not None
                }
                
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'operation_type': 'unknown',
                    'endpoint': None,
                    'execution_time': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute endpoint operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_operation = {
                executor.submit(endpoint_operation, i): i
                for i in range(endpoint_selections)
            }
            
            for future in concurrent.futures.as_completed(future_to_operation):
                result = future.result()
                endpoint_results.append(result)
        
        total_time = time.time() - start_time
        
        # Analyze endpoint load balancing
        successful_operations = [r for r in endpoint_results if r['success']]
        failed_operations = [r for r in endpoint_results if not r['success']]
        
        # Count endpoint distribution
        endpoint_distribution = {}
        for result in successful_operations:
            endpoint = result['endpoint']
            endpoint_distribution[endpoint] = endpoint_distribution.get(endpoint, 0) + 1
        
        logger.info(f"Endpoint load balancing stress test completed:")
        logger.info(f"  Total operations: {endpoint_selections}")
        logger.info(f"  Successful operations: {len(successful_operations)}")
        logger.info(f"  Failed operations: {len(failed_operations)}")
        logger.info(f"  Total time: {total_time:.2f}s")
        logger.info(f"  Endpoint distribution: {endpoint_distribution}")
        
        # Get endpoint statistics
        endpoint_stats = self.manager.get_endpoint_stats()
        logger.info(f"Endpoint statistics: {endpoint_stats}")
        
        # Assertions
        assert len(successful_operations) >= endpoint_selections * 0.9, "Too many endpoint operations failed"
        assert len(endpoint_distribution) > 1, "Load balancing not working - only one endpoint used"
    
    def test_performance_monitoring_stress(self):
        """Test performance monitoring under stress"""
        logger.info("Starting performance monitoring stress test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Generate load to create performance data
        num_operations = 100
        operation_results = []
        
        def generate_load(operation_id: int):
            """Generate load for performance monitoring"""
            try:
                start_time = time.time()
                
                # Randomly choose operation type
                operation_type = random.choice(['select', 'insert', 'update', 'delete'])
                
                if operation_type == 'select':
                    # Execute a query
                    result = self.manager.query_with_predicates(
                        table_name=self.test_table_name,
                        columns=['id', 'timestamp', 'format'],
                        predicates={'format': 'urn:x-nmos:format:video'},
                        limit=100
                    )
                    rows_returned = len(result) if result else 0
                else:
                    # Simulate other operations
                    rows_returned = random.randint(1, 100)
                    time.sleep(random.uniform(0.01, 0.1))  # Simulate processing time
                
                execution_time = time.time() - start_time
                
                return {
                    'operation_id': operation_id,
                    'operation_type': operation_type,
                    'execution_time': execution_time,
                    'rows_returned': rows_returned,
                    'success': True
                }
                
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'operation_type': 'unknown',
                    'execution_time': 0,
                    'rows_returned': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute load generation
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_operation = {
                executor.submit(generate_load, i): i
                for i in range(num_operations)
            }
            
            for future in concurrent.futures.as_completed(future_to_operation):
                result = future.result()
                operation_results.append(result)
        
        total_time = time.time() - start_time
        
        # Test performance monitoring capabilities
        logger.info("Testing performance monitoring capabilities...")
        
        # Get performance summary
        performance_summary = self.manager.get_performance_summary(time_window=timedelta(hours=1))
        logger.info(f"Performance summary: {performance_summary}")
        
        # Get slow queries
        slow_queries = self.manager.performance_monitor.get_slow_queries(threshold=0.1)
        logger.info(f"Slow queries (threshold 0.1s): {len(slow_queries)}")
        
        # Get table performance
        table_performance = self.manager.performance_monitor.get_table_performance(
            self.test_table_name, time_window=timedelta(hours=1)
        )
        logger.info(f"Table performance: {table_performance}")
        
        # Export metrics
        exported_metrics = self.manager.performance_monitor.export_metrics()
        logger.info(f"Exported {len(exported_metrics)} metrics")
        
        # Analyze load generation results
        successful_operations = [r for r in operation_results if r['success']]
        failed_operations = [r for r in operation_results if not r['success']]
        
        if successful_operations:
            avg_execution_time = sum(r['execution_time'] for r in successful_operations) / len(successful_operations)
            
            logger.info(f"Performance monitoring stress test completed:")
            logger.info(f"  Total operations: {num_operations}")
            logger.info(f"  Successful operations: {len(successful_operations)}")
            logger.info(f"  Failed operations: {len(failed_operations)}")
            logger.info(f"  Total time: {total_time:.2f}s")
            logger.info(f"  Average operation time: {avg_execution_time:.3f}s")
        
        # Assertions
        assert len(successful_operations) >= num_operations * 0.8, "Too many operations failed"
        assert 'total_queries' in performance_summary, "Performance summary missing key metrics"
        assert len(exported_metrics) > 0, "No metrics exported"


if __name__ == "__main__":
    # Run stress tests
    pytest.main([__file__, "-v", "-s"])
