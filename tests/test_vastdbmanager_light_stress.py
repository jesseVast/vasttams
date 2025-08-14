"""Light stress tests for VastDBManager with smaller datasets for performance validation"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
import random
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Import the new modular components
from app.storage.vastdbmanager import VastDBManager

# Configure logging for stress tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVastDBManagerLightStress:
    """Light stress tests for VastDBManager with smaller datasets"""
    
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
        self.test_table_name = f"light_stress_{int(time.time())}"
        
        # Test data parameters - reduced for performance testing
        self.num_records = 2000  # Reduced from 10K to 2K for faster testing
        self.time_range_days = 7  # Reduced from 30 to 7 days
        
        logger.info(f"Setting up light stress test with {self.num_records} records over {self.time_range_days} days")
    
    def teardown_method(self):
        """Clean up after tests"""
        try:
            if hasattr(self, 'manager'):
                self.manager.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def generate_test_data(self) -> List[Dict[str, Any]]:
        """Generate realistic test data for light stress testing"""
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
                'id': f"segment_{i:04d}",
                'timestamp': timestamp,
                'format': random.choice(['urn:x-nmos:format:video', 'urn:x-nmos:format:audio']),
                'duration': random.uniform(1.0, 60.0),
                'bitrate': random.randint(1000000, 50000000),
                'resolution_width': random.choice([1920, 3840]),
                'resolution_height': random.choice([1080, 2160]),
                'file_size': random.randint(1000000, 10000000),  # Reduced file sizes
                'codec': random.choice(['H.264', 'H.265']),
                'fps': random.choice([24, 25, 30]),
                'tags': random.choice(['live', 'archive', 'news']),
                'source_id': f"source_{random.randint(1, 5):02d}",
                'flow_id': f"flow_{random.randint(1, 3):02d}",
                'segment_number': i,
                'is_keyframe': random.choice([True, False]),
                'metadata': {
                    'location': random.choice(['studio_a', 'studio_b']),
                    'operator': f"operator_{random.randint(1, 3)}",
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
                pa.field('timestamp', pa.timestamp('us')),
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
                pa.field('metadata', 'string')
            ])
            
            # Define VAST projections for optimal performance
            projections = {
                'time_series': ['timestamp'],
                'categorical': ['format', 'codec', 'tags', 'source_id', 'flow_id'],
                'numeric_ranges': ['bitrate', 'resolution_width', 'duration']
            }
            
            # Connect and create table with VAST projections
            self.manager.connect()
            self.manager.create_table(self.test_table_name, schema, projections=projections)
            
            logger.info(f"Created test table with VAST projections: {self.test_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create test table: {e}")
            raise
    
    def populate_test_data(self, data: List[Dict[str, Any]]):
        """Populate test table with data using efficient batch insertion"""
        try:
            logger.info(f"Populating table with {len(data)} records...")
            start_time = time.time()
            
            # Convert to column-oriented format for efficient insertion
            batch_dict = {}
            for key in data[0].keys():
                if key == 'metadata':
                    # Convert metadata dict to JSON string
                    batch_dict[key] = [str(record[key]) for record in data]
                else:
                    batch_dict[key] = [record[key] for record in data]
            
            # Use our efficient batch insertion method
            self.manager.insert_batch_efficient(self.test_table_name, batch_dict, batch_size=500, max_workers=2)
            
            insertion_time = time.time() - start_time
            logger.info(f"Data population completed in {insertion_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to populate test data: {e}")
            raise
    
    def test_light_concurrent_query_stress(self):
        """Test concurrent query performance with lighter dataset"""
        logger.info("Starting light concurrent query stress test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(3)
        
        # Define simpler query patterns for light stress testing
        query_patterns = [
            # Simple time-range queries
            {'timestamp': {'between': [datetime.now() - timedelta(days=3), datetime.now()]}},
            {'timestamp': {'between': [datetime.now() - timedelta(days=7), datetime.now() - timedelta(days=3)]}},
            
            # Simple format queries
            {'format': 'urn:x-nmos:format:video'},
            {'format': 'urn:x-nmos:format:audio'},
            
            # Simple resolution queries
            {'resolution_width': {'gte': 1920}},
            
            # Simple bitrate queries
            {'bitrate': {'gte': 10000000}},
            
            # Simple combined queries
            {
                'format': 'urn:x-nmos:format:video',
                'resolution_width': {'gte': 1920}
            },
            {
                'tags': 'live',
                'duration': {'gte': 30}
            }
        ]
        
        # Test concurrent query execution with fewer queries
        num_concurrent_queries = 10  # Reduced from 20
        query_results = []
        
        def execute_query(query_id: int, predicates: Dict[str, Any]):
            """Execute a single query and return results"""
            try:
                start_time = time.time()
                
                result = self.manager.query_with_predicates(
                    table_name=self.test_table_name,
                    columns=['id', 'timestamp', 'format', 'duration', 'bitrate'],
                    predicates=predicates,
                    limit=500  # Reduced limit for faster queries
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
            
            logger.info(f"Light concurrent query stress test completed:")
            logger.info(f"  Total time: {total_time:.2f}s")
            logger.info(f"  Successful queries: {len(successful_queries)}/{num_concurrent_queries}")
            logger.info(f"  Failed queries: {len(failed_queries)}")
            logger.info(f"  Average execution time: {avg_execution_time:.3f}s")
            logger.info(f"  Min execution time: {min_execution_time:.3f}s")
            logger.info(f"  Max execution time: {max_execution_time:.3f}s")
        
        # Assertions for test validation
        assert len(successful_queries) >= num_concurrent_queries * 0.8, "Too many queries failed"
        assert avg_execution_time < 5.0, f"Average query time too high: {avg_execution_time:.3f}s"
        
        logger.info("✅ Light stress test passed - performance targets met!")
    
    def test_single_query_performance(self):
        """Test single query performance for baseline measurement"""
        logger.info("Starting single query performance test...")
        
        # Create and populate test table
        test_data = self.generate_test_data()
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(2)
        
        # Test simple queries
        test_queries = [
            {'format': 'urn:x-nmos:format:video'},
            {'timestamp': {'between': [datetime.now() - timedelta(days=3), datetime.now()]}},
            {'bitrate': {'gte': 10000000}}
        ]
        
        for i, predicates in enumerate(test_queries):
            start_time = time.time()
            
            result = self.manager.query_with_predicates(
                table_name=self.test_table_name,
                columns=['id', 'timestamp', 'format'],
                predicates=predicates,
                limit=100
            )
            
            execution_time = time.time() - start_time
            rows_returned = len(result) if result else 0
            
            logger.info(f"Query {i+1} completed in {execution_time:.3f}s, returned {rows_returned} rows")
            
            # Assert performance target
            assert execution_time < 2.0, f"Single query too slow: {execution_time:.3f}s"
        
        logger.info("✅ Single query performance test passed!")


if __name__ == "__main__":
    # Run the light stress test
    test_instance = TestVastDBManagerLightStress()
    test_instance.setup_method()
    
    try:
        test_instance.test_single_query_performance()
        test_instance.test_light_concurrent_query_stress()
        print("🎉 All light stress tests passed!")
    finally:
        test_instance.teardown_method()
