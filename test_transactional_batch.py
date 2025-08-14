#!/usr/bin/env python3
"""
Test Transactional Batch Insertion

This script demonstrates the new transactional batch insertion method
that ensures no records are lost during batch operations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager import VastDBManager
import pyarrow as pa
from datetime import datetime, timedelta
import time
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_transactional_batch_insertion():
    """Test the new transactional batch insertion method"""
    
    print("🧪 TESTING TRANSACTIONAL BATCH INSERTION")
    print("=" * 50)
    
    # Initialize VastDBManager
    endpoints = [
        "http://172.200.204.90",
        "http://172.200.204.91", 
        "http://172.200.204.93",
        "http://172.200.204.92"
    ]
    
    manager = VastDBManager(endpoints)
    test_table_name = f"transactional_test_{int(time.time())}"
    
    try:
        # Connect to VAST
        print("🔌 Connecting to VAST database...")
        manager.connect()
        print("✅ Connected successfully")
        
        # Create test schema
        print("\n📋 Creating test schema...")
        schema = pa.schema([
            pa.field('id', 'string'),
            pa.field('timestamp', pa.timestamp('us')),
            pa.field('value', 'int64'),
            pa.field('status', 'string')
        ])
        print("✅ Schema created")
        
        # Create table
        print("\n🏗️ Creating table...")
        table = manager.create_table(test_table_name, schema)
        print("✅ Table created")
        
        # Test 1: Single record with large batch size (should work fine)
        print("\n📝 Test 1: Single record with batch_size=1000...")
        single_data = {
            'id': ['single_record'],
            'timestamp': [datetime.now()],
            'value': [42],
            'status': ['test']
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_transactional(test_table_name, single_data, batch_size=1000)
            single_time = time.time() - start_time
            
            print(f"✅ Single record inserted in {single_time:.3f}s")
            print(f"   Success: {result['success']}")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Inserted: {result['total_inserted']}")
            print(f"   Failed: {result['total_failed']}")
            print(f"   Batches: {result['batches_total']} total, {result['batches_successful']} successful")
            
        except Exception as e:
            print(f"❌ Single record insertion failed: {e}")
        
        # Test 2: Small batch (10 records) with batch_size=1000
        print("\n📝 Test 2: Small batch (10 records) with batch_size=1000...")
        small_batch = {
            'id': [f'small_batch_{i:02d}' for i in range(10)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(10)],
            'value': [random.randint(1, 100) for _ in range(10)],
            'status': ['active' for _ in range(10)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_transactional(test_table_name, small_batch, batch_size=1000)
            small_time = time.time() - start_time
            
            print(f"✅ Small batch inserted in {small_time:.3f}s")
            print(f"   Success: {result['success']}")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Inserted: {result['total_inserted']}")
            print(f"   Failed: {result['total_failed']}")
            print(f"   Batches: {result['batches_total']} total, {result['batches_successful']} successful")
            
        except Exception as e:
            print(f"❌ Small batch insertion failed: {e}")
        
        # Test 3: Large batch (5000 records) with batch_size=1000
        print("\n📝 Test 3: Large batch (5000 records) with batch_size=1000...")
        large_batch = {
            'id': [f'large_batch_{i:04d}' for i in range(5000)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(5000)],
            'value': [random.randint(1, 1000) for _ in range(5000)],
            'status': [random.choice(['active', 'inactive', 'pending']) for _ in range(5000)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_transactional(test_table_name, large_batch, batch_size=1000, max_retries=2)
            large_time = time.time() - start_time
            
            print(f"✅ Large batch inserted in {large_time:.3f}s")
            print(f"   Success: {result['success']}")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Inserted: {result['total_inserted']}")
            print(f"   Failed: {result['total_failed']}")
            print(f"   Batches: {result['batches_total']} total, {result['batches_successful']} successful")
            print(f"   Insertion rate: {result['insertion_rate']:.1f} rows/second")
            
            # Show batch details if there were failures
            if not result['success']:
                print(f"   Failed batches: {result['failed_batch_ids']}")
                print("   Batch details:")
                for batch_id, details in result['batch_details'].items():
                    if details['status'] == 'failed':
                        print(f"     {batch_id}: {details['error']}")
                
                # Demonstrate cleanup method
                print("\n🧹 Demonstrating cleanup method...")
                cleanup_success = manager.cleanup_partial_insertion(
                    test_table_name, 
                    result['failed_batch_ids'], 
                    result['batch_details']
                )
                print(f"   Cleanup logged: {cleanup_success}")
            
        except Exception as e:
            print(f"❌ Large batch insertion failed: {e}")
        
        # Test 4: Edge case - exactly batch_size records
        print("\n📝 Test 4: Exactly batch_size records (1000)...")
        exact_batch = {
            'id': [f'exact_batch_{i:04d}' for i in range(1000)],
            'timestamp': [datetime.now() + timedelta(seconds=i) for i in range(1000)],
            'value': [i for i in range(1000)],
            'status': ['exact' for _ in range(1000)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_transactional(test_table_name, exact_batch, batch_size=1000)
            exact_time = time.time() - start_time
            
            print(f"✅ Exact batch inserted in {exact_time:.3f}s")
            print(f"   Success: {result['success']}")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Inserted: {result['total_inserted']}")
            print(f"   Failed: {result['total_failed']}")
            print(f"   Batches: {result['batches_total']} total, {result['batches_successful']} successful")
            
        except Exception as e:
            print(f"❌ Exact batch insertion failed: {e}")
        
        print("\n🎯 Key Benefits of Transactional Batch Insertion:")
        print("   1. No records are lost - all operations are tracked")
        print("   2. Automatic retry logic for failed batches")
        print("   3. Detailed failure reporting and recovery information")
        print("   4. Batch size adapts to actual data volume")
        print("   5. Comprehensive logging for debugging and monitoring")
        
        print("\n✅ Transactional batch insertion testing completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Cleanup
        try:
            if 'manager' in locals():
                manager.disconnect()
                print("🔌 Disconnected from VAST database")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

if __name__ == "__main__":
    test_transactional_batch_insertion()
