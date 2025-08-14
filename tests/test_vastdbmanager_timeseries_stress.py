"""Time-series stress testing for VastDBManager"""

import unittest
import time
import random
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import numpy as np

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_NUM_RECORDS = 50000  # Default number of records for time-series stress testing
DEFAULT_TIME_RANGE_DAYS = 90  # Default time range in days for time-series data
DEFAULT_SAMPLING_INTERVAL_MINUTES = 15  # Default sampling interval in minutes
DEFAULT_BASE_BITRATE = 20000000  # Default base bitrate (20 Mbps)
DEFAULT_DAILY_PATTERN_PEAK = 0.3  # Default daily pattern peak factor
DEFAULT_WEEKLY_PATTERN_PEAK = 0.2  # Default weekly pattern peak factor
DEFAULT_BATCH_SIZE = 2000  # Default batch size for time-series data
DEFAULT_BATCH_LOG_INTERVAL = 10000  # Default interval for batch logging
DEFAULT_CONCURRENT_QUERIES = 30  # Default number of concurrent queries

# Import the new modular components
from app.storage.vastdbmanager import VastDBManager

# Configure logging for time-series tests
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVastDBManagerTimeSeriesStress:
    """Specialized time-series stress tests for VastDBManager"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Initialize with multiple endpoints
        self.endpoints = [
            "http://172.200.204.90",
            "http://172.200.204.91", 
            "http://172.200.204.93",
            "http://172.200.204.92"
        ]
        
        self.manager = VastDBManager(self.endpoints)
        self.test_table_name = f"timeseries_stress_{int(time.time())}"
        
        # Time-series specific parameters
        self.num_records = DEFAULT_NUM_RECORDS  # Default number of records for time-series stress testing
        self.time_range_days = DEFAULT_TIME_RANGE_DAYS  # Default time range in days for time-series data
        self.sampling_interval_minutes = DEFAULT_SAMPLING_INTERVAL_MINUTES  # Default sampling interval in minutes
        
        logger.info(f"Setting up time-series stress test with {self.num_records} records over {self.time_range_days} days")
        logger.info(f"Sampling interval: {self.sampling_interval_minutes} minutes")
    
    def teardown_method(self):
        """Clean up after tests"""
        try:
            if hasattr(self, 'manager'):
                self.manager.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def generate_timeseries_data(self) -> List[Dict[str, Any]]:
        """Generate realistic time-series data for stress testing"""
        logger.info("Generating time-series test data...")
        
        start_time = datetime.now() - timedelta(days=self.time_range_days)
        end_time = datetime.now()
        
        # Calculate number of intervals
        total_minutes = int((end_time - start_time).total_seconds() / 60)
        num_intervals = total_minutes // self.sampling_interval_minutes
        
        data = []
        current_time = start_time
        
        for i in range(self.num_records):
            # Generate timestamp at regular intervals with some jitter
            base_interval = i % num_intervals
            jitter_minutes = random.randint(-2, 2)  # ±2 minutes jitter
            timestamp = start_time + timedelta(
                minutes=base_interval * self.sampling_interval_minutes + jitter_minutes
            )
            
            # Generate realistic time-series metrics
            # Simulate daily/weekly patterns
            hour_of_day = timestamp.hour
            day_of_week = timestamp.weekday()
            
            # Base values with daily patterns
                    base_bitrate = DEFAULT_BASE_BITRATE  # Default base bitrate
        daily_pattern = 1.0 + DEFAULT_DAILY_PATTERN_PEAK * (hour_of_day - 12) / 12  # Peak at noon
        weekly_pattern = 1.0 + DEFAULT_WEEKLY_PATTERN_PEAK * (5 - day_of_week) / 5  # Peak on Friday
            
            # Add some random variation
            random_factor = random.uniform(0.8, 1.2)
            
            # Calculate final values
            bitrate = int(base_bitrate * daily_pattern * weekly_pattern * random_factor)
            duration = random.uniform(10.0, 60.0)  # 10-60 seconds
            file_size = int(bitrate * duration / 8)  # Convert bits to bytes
            
            # Generate record
            record = {
                'id': f"segment_{i:06d}",
                'timestamp': timestamp,  # Use Python datetime object directly for optimal VAST performance
                'hour_of_day': hour_of_day,
                'day_of_week': day_of_week,
                'bitrate': bitrate,
                'duration': duration,
                'file_size': file_size,
                'quality_score': random.uniform(0.7, 1.0),
                'error_count': random.randint(0, 5),
                'buffer_level': random.uniform(0.1, 1.0),
                'cpu_usage': random.uniform(0.1, 0.9),
                'memory_usage': random.uniform(0.2, 0.8),
                'network_latency': random.uniform(1, 100),  # 1-100ms
                'packet_loss': random.uniform(0, 0.05),  # 0-5%
                'format': random.choice(['urn:x-nmos:format:video', 'urn:x-nmos:format:audio']),
                'source_id': f"source_{random.randint(1, 5):02d}",
                'flow_id': f"flow_{random.randint(1, 3):02d}",
                'segment_number': i,
                'is_keyframe': random.choice([True, False]),
                'metadata': {
                    'location': random.choice(['studio_a', 'studio_b', 'remote_location']),
                    'operator': f"operator_{random.randint(1, 3)}",
                    'equipment': random.choice(['camera_1', 'camera_2', 'audio_mixer'])
                }
            }
            data.append(record)
        
        logger.info(f"Generated {len(data)} time-series records")
        logger.info(f"Time range: {start_time} to {end_time}")
        logger.info(f"Average records per day: {len(data) / self.time_range_days:.1f}")
        
        return data
    
    def create_timeseries_table(self):
        """Create test table optimized for time-series operations"""
        try:
            import pyarrow as pa
            
            # Create schema optimized for time-series analytics
            schema = pa.schema([
                pa.field('id', 'string'),
                pa.field('timestamp', pa.timestamp('us')),  # Use PyArrow timestamp for optimal VAST performance
                pa.field('hour_of_day', 'int8'),
                pa.field('day_of_week', 'int8'),
                pa.field('bitrate', 'int64'),
                pa.field('duration', 'float64'),
                pa.field('file_size', 'int64'),
                pa.field('quality_score', 'float64'),
                pa.field('error_count', 'int32'),
                pa.field('buffer_level', 'float64'),
                pa.field('cpu_usage', 'float64'),
                pa.field('memory_usage', 'float64'),
                pa.field('network_latency', 'float64'),
                pa.field('packet_loss', 'float64'),
                pa.field('format', 'string'),
                pa.field('source_id', 'string'),
                pa.field('flow_id', 'string'),
                pa.field('segment_number', 'int32'),
                pa.field('is_keyframe', 'bool'),
                pa.field('metadata', 'string')
            ])
            
            # Define VAST projections for time-series optimization
            projections = {
                'time_series': ['timestamp'],  # Sorted for optimal time queries
                'metrics': ['bitrate', 'duration', 'quality_score'],  # Unsorted for analytics
                'categorical': ['format', 'source_id', 'flow_id']  # Unsorted for filtering
            }
            
            # Connect and create table with VAST projections
            self.manager.connect()
            self.manager.create_table(self.test_table_name, schema, projections=projections)
            
            logger.info(f"Created time-series test table with VAST projections: {self.test_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create time-series test table: {e}")
            raise
    
    def populate_timeseries_data(self, data: List[Dict[str, Any]]):
        """Populate test table with time-series data"""
        try:
            logger.info(f"Populating time-series table with {len(data)} records...")
            start_time = time.time()
            
            # Insert data in batches optimized for time-series
            batch_size = DEFAULT_BATCH_SIZE  # Default batch size for time-series data
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Convert to column-oriented format
                batch_dict = {}
                for key in batch[0].keys():
                    if key == 'metadata':
                        batch_dict[key] = [str(record[key]) for record in batch]
                    else:
                        batch_dict[key] = [record[key] for record in batch]
                
                self.manager.insert_pydict(self.test_table_name, batch_dict)
                
                if (i + batch_size) % DEFAULT_BATCH_LOG_INTERVAL == 0:
                    logger.info(f"Inserted {i + batch_size}/{len(data)} time-series records...")
            
            insertion_time = time.time() - start_time
            logger.info(f"Time-series data population completed in {insertion_time:.2f}s")
            logger.info(f"Insertion rate: {len(data) / insertion_time:.1f} records/second")
            
        except Exception as e:
            logger.error(f"Failed to populate time-series data: {e}")
            raise
    
    def test_temporal_query_stress(self):
        """Test temporal query performance under stress"""
        logger.info("Starting temporal query stress test...")
        
        # Create and populate time-series table
        test_data = self.generate_timeseries_data()
        self.create_timeseries_table()
        self.populate_timeseries_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Define temporal query patterns
        temporal_patterns = [
            # Recent time ranges
            {'timestamp': {'between': [datetime.now() - timedelta(hours=1), datetime.now()]}},
            {'timestamp': {'between': [datetime.now() - timedelta(hours=6), datetime.now()]}},
            {'timestamp': {'between': [datetime.now() - timedelta(hours=24), datetime.now()]}},
            
            # Historical time ranges
            {'timestamp': {'between': [datetime.now() - timedelta(days=7), datetime.now() - timedelta(days=6)]}},
            {'timestamp': {'between': [datetime.now() - timedelta(days=30), datetime.now() - timedelta(days=29)]}},
            {'timestamp': {'between': [datetime.now() - timedelta(days=60), datetime.now() - timedelta(days=59)]}},
            
            # Time-based aggregations
            {'hour_of_day': {'gte': 9, 'lte': 17}},  # Business hours
            {'hour_of_day': {'gte': 18, 'lte': 23}},  # Evening hours
            {'day_of_week': {'gte': 0, 'lte': 4}},   # Weekdays
            
            # Complex temporal patterns
            {
                'timestamp': {'between': [datetime.now() - timedelta(days=7), datetime.now()]},
                'hour_of_day': {'gte': 9, 'lte': 17},
                'day_of_week': {'gte': 0, 'lte': 4}
            },
            {
                'timestamp': {'between': [datetime.now() - timedelta(days=30), datetime.now()]},
                'quality_score': {'gte': 0.9},
                'error_count': {'lte': 1}
            }
        ]
        
        # Test concurrent temporal query execution
        num_concurrent_queries = DEFAULT_CONCURRENT_QUERIES
        query_results = []
        
        def execute_temporal_query(query_id: int, predicates: Dict[str, Any]):
            """Execute a single temporal query"""
            try:
                start_time = time.time()
                
                result = self.manager.query_with_predicates(
                    table_name=self.test_table_name,
                    columns=['id', 'timestamp', 'bitrate', 'quality_score', 'error_count'],
                    predicates=predicates,
                    limit=2000
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
        
        # Execute temporal queries concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_queries) as executor:
            future_to_query = {
                executor.submit(execute_temporal_query, i, temporal_patterns[i % len(temporal_patterns)]): i
                for i in range(num_concurrent_queries)
            }
            
            for future in concurrent.futures.as_completed(future_to_query):
                result = future.result()
                query_results.append(result)
                
                if result['success']:
                    logger.info(f"Temporal query {result['query_id']} completed in {result['execution_time']:.3f}s, "
                              f"returned {result['rows_returned']} rows")
                else:
                    logger.error(f"Temporal query {result['query_id']} failed: {result.get('error', 'Unknown error')}")
        
        total_time = time.time() - start_time
        
        # Analyze temporal query results
        successful_queries = [r for r in query_results if r['success']]
        failed_queries = [r for r in query_results if not r['success']]
        
        if successful_queries:
            avg_execution_time = sum(r['execution_time'] for r in successful_queries) / len(successful_queries)
            max_execution_time = max(r['execution_time'] for r in successful_queries)
            min_execution_time = min(r['execution_time'] for r in successful_queries)
            
            logger.info(f"Temporal query stress test completed:")
            logger.info(f"  Total time: {total_time:.2f}s")
            logger.info(f"  Successful queries: {len(successful_queries)}/{num_concurrent_queries}")
            logger.info(f"  Failed queries: {len(failed_queries)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
            logger.info(f"  Min execution time: {min_execution_time:.3f}s")
            logger.info(f"  Max execution time: {max_execution_time:.3f}s")
        
        # Assertions
        assert len(successful_queries) >= num_concurrent_queries * 0.8, "Too many temporal queries failed"
        assert avg_execution_time < 10.0, "Average temporal query time too high"
    
    def test_timeseries_analytics_stress(self):
        """Test time-series analytics performance under stress"""
        logger.info("Starting time-series analytics stress test...")
        
        # Create and populate time-series table
        test_data = self.generate_timeseries_data()
        self.create_timeseries_table()
        self.populate_timeseries_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Test different time-series analytics operations
        analytics_tests = [
            {
                'name': 'Moving Average - 1 Hour',
                'operation': 'moving_average',
                'params': {'window_size': '1 hour', 'days': 7}
            },
            {
                'name': 'Moving Average - 6 Hours',
                'operation': 'moving_average',
                'params': {'window_size': '6 hours', 'days': 7}
            },
            {
                'name': 'Moving Average - 1 Day',
                'operation': 'moving_average',
                'params': {'window_size': '1 day', 'days': 30}
            },
            {
                'name': 'Trend Analysis - 7 Days',
                'operation': 'trends',
                'params': {'trend_period': '1 day', 'days': 7}
            },
            {
                'name': 'Trend Analysis - 30 Days',
                'operation': 'trends',
                'params': {'trend_period': '1 day', 'days': 30}
            },
            {
                'name': 'Anomaly Detection - 7 Days',
                'operation': 'anomalies',
                'params': {'threshold': 2.0, 'days': 7}
            },
            {
                'name': 'Anomaly Detection - 30 Days',
                'operation': 'anomalies',
                'params': {'threshold': 2.5, 'days': 30}
            }
        ]
        
        # Execute analytics operations
        analytics_results = []
        
        for test in analytics_tests:
            try:
                start_time = time.time()
                
                # Calculate time range
                days = test['params']['days']
                start_time_range = datetime.now() - timedelta(days=days)
                end_time_range = datetime.now()
                
                if test['operation'] == 'moving_average':
                    result = self.manager.time_series_analytics.calculate_moving_average(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        window_size=test['params']['window_size'],
                        start_time=start_time_range,
                        end_time=end_time_range
                    )
                elif test['operation'] == 'trends':
                    result = self.manager.time_series_analytics.calculate_trends(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        trend_period=test['params']['trend_period'],
                        start_time=start_time_range,
                        end_time=end_time_range
                    )
                elif test['operation'] == 'anomalies':
                    result = self.manager.time_series_analytics.detect_anomalies(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        threshold=test['params']['threshold'],
                        start_time=start_time_range,
                        end_time=end_time_range
                    )
                
                execution_time = time.time() - start_time
                
                analytics_results.append({
                    'test_name': test['name'],
                    'execution_time': execution_time,
                    'result_size': len(result) if isinstance(result, list) else 1,
                    'success': True
                })
                
                logger.info(f"Time-series analytics test '{test['name']}' completed in {execution_time:.3f}s")
                
            except Exception as e:
                analytics_results.append({
                    'test_name': test['name'],
                    'execution_time': 0,
                    'result_size': 0,
                    'success': False,
                    'error': str(e)
                })
                
                logger.error(f"Time-series analytics test '{test['name']}' failed: {e}")
        
        # Analyze analytics results
        successful_analytics = [r for r in analytics_results if r['success']]
        failed_analytics = [r for r in analytics_results if r['success'] == False]
        
        if successful_analytics:
            avg_execution_time = sum(r['execution_time'] for r in successful_analytics) / len(successful_analytics)
            
            logger.info(f"Time-series analytics stress test completed:")
            logger.info(f"  Successful operations: {len(successful_analytics)}/{len(analytics_tests)}")
            logger.info(f"  Failed operations: {len(failed_analytics)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
        
        # Assertions
        assert len(successful_analytics) >= len(analytics_tests) * 0.7, "Too many time-series analytics operations failed"
    
    def test_hybrid_analytics_timeseries_stress(self):
        """Test hybrid analytics (VAST + DuckDB) for time-series data"""
        logger.info("Starting hybrid analytics time-series stress test...")
        
        # Create and populate time-series table
        test_data = self.generate_timeseries_data()
        self.create_timeseries_table()
        self.populate_timeseries_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Test hybrid analytics operations
        hybrid_tests = [
            {
                'name': 'Hybrid Moving Average - 1 Hour',
                'operation': 'moving_average_hybrid',
                'params': {'window_size': '1 hour', 'days': 7}
            },
            {
                'name': 'Hybrid Moving Average - 1 Day',
                'operation': 'moving_average_hybrid',
                'params': {'window_size': '1 day', 'days': 30}
            },
            {
                'name': 'Hybrid Percentiles',
                'operation': 'percentiles_hybrid',
                'params': {'percentiles': [25, 50, 75, 90, 95, 99]}
            },
            {
                'name': 'Hybrid Correlation',
                'operation': 'correlation_hybrid',
                'params': {'column1': 'bitrate', 'column2': 'quality_score'}
            }
        ]
        
        # Execute hybrid analytics operations
        hybrid_results = []
        
        for test in hybrid_tests:
            try:
                start_time = time.time()
                
                # Calculate time range
                days = test['params']['days']
                start_time_range = datetime.now() - timedelta(days=days)
                end_time_range = datetime.now()
                
                if test['operation'] == 'moving_average_hybrid':
                    result = self.manager.hybrid_analytics.calculate_moving_average_hybrid(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        time_column='timestamp',
                        window_size=test['params']['window_size'],
                        start_time=start_time_range,
                        end_time=end_time_range
                    )
                elif test['operation'] == 'percentiles_hybrid':
                    result = self.manager.hybrid_analytics.calculate_percentiles_hybrid(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        value_column='bitrate',
                        percentiles=test['params']['percentiles']
                    )
                elif test['operation'] == 'correlation_hybrid':
                    result = self.manager.hybrid_analytics.calculate_correlation_hybrid(
                        table=self.manager.connection.schema.table(self.test_table_name),
                        config=self.manager.default_query_config,
                        column1=test['params']['column1'],
                        column2=test['params']['column2']
                    )
                
                execution_time = time.time() - start_time
                
                hybrid_results.append({
                    'test_name': test['name'],
                    'execution_time': execution_time,
                    'result_size': len(result) if isinstance(result, list) else 1,
                    'success': True
                })
                
                logger.info(f"Hybrid analytics test '{test['name']}' completed in {execution_time:.3f}s")
                
            except Exception as e:
                hybrid_results.append({
                    'test_name': test['name'],
                    'execution_time': 0,
                    'result_size': 0,
                    'success': False,
                    'error': str(e)
                })
                
                logger.error(f"Hybrid analytics test '{test['name']}' failed: {e}")
        
        # Analyze hybrid analytics results
        successful_hybrid = [r for r in hybrid_results if r['success']]
        failed_hybrid = [r for r in hybrid_results if r['success'] == False]
        
        if successful_hybrid:
            avg_execution_time = sum(r['execution_time'] for r in successful_hybrid) / len(successful_hybrid)
            
            logger.info(f"Hybrid analytics time-series stress test completed:")
            logger.info(f"  Successful operations: {len(successful_hybrid)}/{len(hybrid_tests)}")
            logger.info(f"  Failed operations: {len(failed_hybrid)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
        
        # Assertions
        assert len(successful_hybrid) >= len(hybrid_tests) * 0.6, "Too many hybrid analytics operations failed"
    
    def test_temporal_pattern_detection(self):
        """Test detection of temporal patterns in time-series data"""
        logger.info("Starting temporal pattern detection test...")
        
        # Create and populate time-series table
        test_data = self.generate_timeseries_data()
        self.create_timeseries_table()
        self.populate_timeseries_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(5)
        
        # Test different temporal pattern queries
        pattern_tests = [
            {
                'name': 'Business Hours Pattern',
                'predicates': {
                    'hour_of_day': {'gte': 9, 'lte': 17},
                    'day_of_week': {'gte': 0, 'lte': 4}
                }
            },
            {
                'name': 'Evening Peak Pattern',
                'predicates': {
                    'hour_of_day': {'gte': 18, 'lte': 23},
                    'day_of_week': {'gte': 5, 'lte': 6}
                }
            },
            {
                'name': 'High Quality Business Hours',
                'predicates': {
                    'hour_of_day': {'gte': 9, 'lte': 17},
                    'day_of_week': {'gte': 0, 'lte': 4},
                    'quality_score': {'gte': 0.9}
                }
            },
            {
                'name': 'Low Error Periods',
                'predicates': {
                    'error_count': {'lte': 1},
                    'quality_score': {'gte': 0.8}
                }
            }
        ]
        
        # Execute pattern detection queries
        pattern_results = []
        
        for test in pattern_tests:
            try:
                start_time = time.time()
                
                result = self.manager.query_with_predicates(
                    table_name=self.test_table_name,
                    columns=['id', 'timestamp', 'hour_of_day', 'day_of_week', 'quality_score', 'error_count'],
                    predicates=test['predicates'],
                    limit=1000
                )
                
                execution_time = time.time() - start_time
                
                pattern_results.append({
                    'test_name': test['name'],
                    'execution_time': execution_time,
                    'rows_returned': len(result) if result else 0,
                    'success': True
                })
                
                logger.info(f"Pattern detection test '{test['name']}' completed in {execution_time:.3f}s, "
                          f"returned {len(result) if result else 0} rows")
                
            except Exception as e:
                pattern_results.append({
                    'test_name': test['name'],
                    'execution_time': 0,
                    'rows_returned': 0,
                    'success': False,
                    'error': str(e)
                })
                
                logger.error(f"Pattern detection test '{test['name']}' failed: {e}")
        
        # Analyze pattern detection results
        successful_patterns = [r for r in pattern_results if r['success']]
        failed_patterns = [r for r in pattern_results if r['success'] == False]
        
        if successful_patterns:
            avg_execution_time = sum(r['execution_time'] for r in successful_patterns) / len(successful_patterns)
            
            logger.info(f"Temporal pattern detection test completed:")
            logger.info(f"  Successful tests: {len(successful_patterns)}/{len(pattern_tests)}")
            logger.info(f"  Failed tests: {len(failed_patterns)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
        
        # Assertions
        assert len(successful_patterns) >= len(pattern_tests) * 0.8, "Too many pattern detection tests failed"


if __name__ == "__main__":
    # Run time-series stress tests
    pytest.main([__file__, "-v", "-s"])
