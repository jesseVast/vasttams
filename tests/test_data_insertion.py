"""Test data insertion and row pooling efficiency"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager import VastDBManager
import pyarrow as pa
from datetime import datetime, timedelta
import time
import random

def test_data_insertion():
    """Test data insertion methods and efficiency"""
    
    print("🧪 TESTING DATA INSERTION AND ROW POOLING")
    print("=" * 50)
    
    # Initialize VastDBManager
    endpoints = [
        "http://172.200.204.90",
        "http://172.200.204.91", 
        "http://172.200.204.93",
        "http://172.200.204.92"
    ]
    
    manager = VastDBManager(endpoints)
    test_table_name = f"insertion_test_{int(time.time())}"
    
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
            pa.field('format', 'string'),
            pa.field('bitrate', 'int64'),
            pa.field('tags', 'string')
        ])
        print("✅ Schema created")
        
        # Create table
        print("\n🏗️ Creating table...")
        table = manager.create_table(test_table_name, schema)
        print("✅ Table created")
        
        # Test 1: Single row insertion
        print("\n📝 Test 1: Single row insertion...")
        single_data = {
            'id': ['test_001'],
            'timestamp': [datetime.now()],
            'format': ['video'],
            'bitrate': [10000000],
            'tags': ['test']
        }
        
        start_time = time.time()
        try:
            result = manager.insert_pydict(test_table_name, single_data)
            single_time = time.time() - start_time
            print(f"✅ Single row inserted in {single_time:.3f}s, result: {result}")
        except Exception as e:
            print(f"❌ Single row insertion failed: {e}")
            single_time = 0
        
        # Test 2: Small batch insertion (10 rows)
        print("\n📝 Test 2: Small batch insertion (10 rows)...")
        small_batch = {
            'id': [f'batch_{i:03d}' for i in range(10)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(10)],
            'format': [random.choice(['video', 'audio']) for _ in range(10)],
            'bitrate': [random.randint(1000000, 50000000) for _ in range(10)],
            'tags': [random.choice(['live', 'recorded', 'test']) for _ in range(10)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_pydict(test_table_name, small_batch)
            small_batch_time = time.time() - start_time
            print(f"✅ Small batch inserted in {small_batch_time:.3f}s, result: {result}")
        except Exception as e:
            print(f"❌ Small batch insertion failed: {e}")
            small_batch_time = 0
        
        # Test 3: Large batch insertion (100 rows)
        print("\n📝 Test 3: Large batch insertion (100 rows)...")
        large_batch = {
            'id': [f'large_{i:03d}' for i in range(100)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(100)],
            'format': [random.choice(['video', 'audio']) for _ in range(100)],
            'bitrate': [random.randint(1000000, 50000000) for _ in range(100)],
            'tags': [random.choice(['live', 'recorded', 'test']) for _ in range(100)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_pydict(test_table_name, large_batch)
            large_batch_time = time.time() - start_time
            print(f"✅ Large batch inserted in {large_batch_time:.3f}s, result: {result}")
        except Exception as e:
            print(f"❌ Large batch insertion failed: {e}")
            large_batch_time = 0
        
        # Verify data
        print("\n🔍 Verifying data...")
        all_data = manager.query_with_predicates(test_table_name, {}, ['id'])
        print(f"Total rows: {len(all_data) if all_data else 0}")
        
        # Check table stats
        print("\n🔍 Verifying inserted data...")
        try:
            stats = manager.get_table_stats(test_table_name)
            print(f"✅ Table stats: {stats}")
            
        except Exception as e:
            print(f"❌ Data verification failed: {e}")
            total_rows = 0
        
        # Performance analysis
        print("\n" + "=" * 50)
        print("📊 INSERTION PERFORMANCE ANALYSIS:")
        if single_time > 0:
            print(f"  Single row: {single_time:.3f}s")
        if small_batch_time > 0:
            print(f"  Small batch (10 rows): {small_batch_time:.3f}s")
            if single_time > 0:
                efficiency = (single_time * 10) / small_batch_time
                print(f"    Efficiency gain: {efficiency:.1f}x")
        if large_batch_time > 0:
            print(f"  Large batch (100 rows): {large_batch_time:.3f}s")
            if single_time > 0:
                efficiency = (single_time * 100) / large_batch_time
                print(f"    Efficiency gain: {efficiency:.1f}x")
        
        print(f"  Total rows inserted: {total_rows}")
        
        if total_rows > 0:
            print("✅ Data insertion working correctly!")
        else:
            print("❌ No data was inserted - need to fix insertion method")
        
        print("\n" + "=" * 50)
        print("✅ DATA INSERTION TEST COMPLETED!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            if hasattr(manager, 'connection') and manager.connection:
                manager.disconnect()
                print("🔌 Disconnected from VAST")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    test_data_insertion()
