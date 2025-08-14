"""Scalability testing for VastDBManager"""

import unittest
import time
import random
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import numpy as np

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_BATCH_SIZE_BASE = 1000  # Base batch size for scalability testing
DEFAULT_WORKER_DIVISOR = 4  # Divisor for calculating adaptive workers
DEFAULT_RECORD_DIVISOR = 1000  # Divisor for calculating adaptive batch sizes
DEFAULT_MIN_BATCH_SIZE = 100  # Minimum batch size for adaptive batching
DEFAULT_MAX_WORKERS = 4  # Maximum number of parallel workers

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import concurrent.futures
from typing import List, Dict, Any
import logging

# Import the new modular components
from app.storage.vastdbmanager import VastDBManager

# Configure logging for scalability tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVastDBManagerScalability:
    """Scalability tests for VastDBManager to find performance sweet spot"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Initialize with multiple endpoints for load testing
        self.endpoints = [
            "http://172.200.204.90",
            "http://172.200.204.91", 
            "http://172.200.204.93",
            "http://172.200.204.92"
        ]
        
        self.manager = VastDBManager(self.endpoints)
        self.test_table_name = f"scalability_{int(time.time())}"
        
        # Test different dataset sizes
        self.dataset_sizes = [2000, 5000, 10000, 15000, 20000]
        self.time_range_days = 7
        
        logger.info(f"Setting up scalability test with dataset sizes: {self.dataset_sizes}")
    
    def teardown_method(self):
        """Clean up after tests"""
        try:
            if hasattr(self, 'manager'):
                self.manager.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def generate_test_data(self, num_records: int) -> List[Dict[str, Any]]:
        """Generate realistic test data for scalability testing"""
        logger.info(f"Generating {num_records} test records...")
        
        start_time = datetime.now() - timedelta(days=self.time_range_days)
        end_time = datetime.now()
        
        data = []
        for i in range(num_records):
            # Generate timestamp within the range
            timestamp = start_time + timedelta(
                seconds=random.randint(0, int((end_time - start_time).total_seconds()))
            )
            
            # Generate realistic media segment data
            record = {
                'id': f"segment_{i:06d}",
                'timestamp': timestamp,
                'format': random.choice(['urn:x-nmos:format:video', 'urn:x-nmos:format:audio']),
                'duration': random.uniform(1.0, 60.0),
                'bitrate': random.randint(1000000, 50000000),
                'resolution_width': random.choice([1920, 3840]),
                'resolution_height': random.choice([1080, 2160]),
                'file_size': random.randint(1000000, 10000000),
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
            batch_size = min(DEFAULT_BATCH_SIZE_BASE, len(data) // DEFAULT_WORKER_DIVISOR)  # Adaptive batch size
            max_workers = min(4, len(data) // 1000)  # Adaptive workers
            
            self.manager.insert_batch_efficient(self.test_table_name, batch_dict, 
                                             batch_size=batch_size, max_workers=max_workers)
            
            insertion_time = time.time() - start_time
            logger.info(f"Data population completed in {insertion_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to populate test data: {e}")
            raise
    
    def test_query_performance(self, num_records: int) -> Dict[str, float]:
        """Test query performance for a specific dataset size"""
        logger.info(f"\n🧪 Testing performance with {num_records:,} records...")
        
        # Generate and populate data
        test_data = self.generate_test_data(num_records)
        self.create_test_table()
        self.populate_test_data(test_data)
        
        # Wait for cache to be populated
        time.sleep(3)
        
        # Define test queries
        test_queries = [
            {'format': 'urn:x-nmos:format:video'},
            {'timestamp': {'between': [datetime.now() - timedelta(days=3), datetime.now()]}},
            {'bitrate': {'gte': 10000000}},
            {
                'format': 'urn:x-nmos:format:video',
                'resolution_width': {'gte': 1920}
            }
        ]
        
        # Test each query
        query_times = []
        for i, predicates in enumerate(test_queries):
            start_time = time.time()
            
            result = self.manager.query_with_predicates(
                table_name=self.test_table_name,
                columns=['id', 'timestamp', 'format'],
                predicates=predicates,
                limit=min(500, num_records // 4)  # Adaptive limit
            )
            
            execution_time = time.time() - start_time
            rows_returned = len(result) if result else 0
            
            query_times.append(execution_time)
            logger.info(f"  Query {i+1}: {execution_time:.3f}s, returned {rows_returned} rows")
        
        # Calculate performance metrics
        avg_time = sum(query_times) / len(query_times)
        max_time = max(query_times)
        min_time = min(query_times)
        
        logger.info(f"  📊 Performance Summary:")
        logger.info(f"    Average: {avg_time:.3f}s")
        logger.info(f"    Min: {min_time:.3f}s")
        logger.info(f"    Max: {max_time:.3f}s")
        
        # Check if performance target is met
        target_met = avg_time < 5.0
        status = "✅ PASS" if target_met else "❌ FAIL"
        logger.info(f"    Target <5s: {status}")
        
        return {
            'num_records': num_records,
            'avg_time': avg_time,
            'max_time': max_time,
            'min_time': min_time,
            'target_met': target_met,
            'query_times': query_times
        }
    
    def test_scalability(self):
        """Test scalability across different dataset sizes"""
        logger.info("🚀 Starting VastDBManager scalability test...")
        logger.info("=" * 60)
        
        results = []
        
        for dataset_size in self.dataset_sizes:
            try:
                result = self.test_query_performance(dataset_size)
                results.append(result)
                
                # Clean up table for next test
                if hasattr(self, 'manager') and self.manager.connection:
                    with self.manager.connection.transaction() as tx:
                        bucket = tx.bucket(self.manager.bucket)
                        schema_obj = bucket.schema(self.manager.schema)
                        table = schema_obj.table(self.test_table_name, fail_if_missing=False)
                        if table:
                            table.drop()
                            logger.info(f"Dropped table for next test")
                
            except Exception as e:
                logger.error(f"Failed to test {dataset_size} records: {e}")
                results.append({
                    'num_records': dataset_size,
                    'avg_time': float('inf'),
                    'max_time': float('inf'),
                    'min_time': float('inf'),
                    'target_met': False,
                    'error': str(e)
                })
        
        # Analyze scalability results
        logger.info("\n" + "=" * 60)
        logger.info("📈 SCALABILITY ANALYSIS RESULTS")
        logger.info("=" * 60)
        
        successful_tests = [r for r in results if r['target_met']]
        failed_tests = [r for r in results if not r['target_met']]
        
        if successful_tests:
            max_successful_size = max(r['num_records'] for r in successful_tests)
            logger.info(f"✅ Maximum successful dataset size: {max_successful_size:,} records")
            logger.info(f"✅ Performance target met for {len(successful_tests)}/{len(results)} dataset sizes")
        
        if failed_tests:
            min_failed_size = min(r['num_records'] for r in failed_tests)
            logger.info(f"❌ Performance target failed starting at: {min_failed_size:,} records")
        
        # Performance breakdown
        logger.info("\n📊 DETAILED PERFORMANCE BREAKDOWN:")
        logger.info(f"{'Records':>8} {'Avg (s)':>8} {'Min (s)':>8} {'Max (s)':>8} {'Status':>8}")
        logger.info("-" * 50)
        
        for result in results:
            if result['target_met']:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            logger.info(f"{result['num_records']:>8,} {result['avg_time']:>8.3f} "
                       f"{result['min_time']:>8.3f} {result['max_time']:>8.3f} {status:>8}")
        
        # Recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        if successful_tests:
            optimal_size = max(r['num_records'] for r in successful_tests)
            logger.info(f"• Optimal dataset size for <5s performance: {optimal_size:,} records")
            logger.info(f"• This provides {optimal_size/1000:.1f}x the data volume of baseline tests")
        
        if failed_tests:
            logger.info(f"• Consider reducing dataset size or optimizing queries for larger datasets")
            logger.info(f"• Current optimizations may need enhancement for datasets >{min_failed_size:,} records")
        
        logger.info("\n🎯 SCALABILITY TEST COMPLETED!")


if __name__ == "__main__":
    # Run the scalability test
    test_instance = TestVastDBManagerScalability()
    test_instance.setup_method()
    
    try:
        test_instance.test_scalability()
    finally:
        test_instance.teardown_method()
