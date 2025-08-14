"""Test row pooling and efficient batch insertion"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager import VastDBManager
import pyarrow as pa
from datetime import datetime, timedelta
import time
import random

def test_row_pooling():
    """Test row pooling and efficient batch insertion"""
    
    print("🧪 TESTING ROW POOLING AND EFFICIENT BATCH INSERTION")
    print("=" * 60)
    
    # Initialize VastDBManager
    endpoints = [
        "http://172.200.204.90",
        "http://172.200.204.91", 
        "http://172.200.204.93",
        "http://172.200.204.92"
    ]
    
    manager = VastDBManager(endpoints)
    test_table_name = f"pooling_test_{int(time.time())}"
    
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
        
        # Test 1: Small dataset (100 rows) - sequential processing
        print("\n📝 Test 1: Small dataset (100 rows) - sequential processing...")
        small_data = {
            'id': [f'small_{i:03d}' for i in range(100)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(100)],
            'format': [random.choice(['video', 'audio']) for _ in range(100)],
            'bitrate': [random.randint(1000000, 50000000) for _ in range(100)],
            'tags': [random.choice(['live', 'recorded', 'test']) for _ in range(100)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_efficient(test_table_name, small_data, batch_size=50, max_workers=1)
            small_time = time.time() - start_time
            print(f"✅ Small dataset inserted in {small_time:.3f}s, result: {result}")
        except Exception as e:
            print(f"❌ Small dataset insertion failed: {e}")
            small_time = 0
        
        # Test 2: Medium dataset (1,000 rows) - parallel processing
        print("\n📝 Test 2: Medium dataset (1,000 rows) - parallel processing...")
        medium_data = {
            'id': [f'medium_{i:04d}' for i in range(1000)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(1000)],
            'format': [random.choice(['video', 'audio']) for _ in range(1000)],
            'bitrate': [random.randint(1000000, 50000000) for _ in range(1000)],
            'tags': [random.choice(['live', 'recorded', 'test']) for _ in range(1000)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_efficient(test_table_name, medium_data, batch_size=200, max_workers=4)
            medium_time = time.time() - start_time
            print(f"✅ Medium dataset inserted in {medium_time:.3f}s, result: {result}")
        except Exception as e:
            print(f"❌ Medium dataset insertion failed: {e}")
            medium_time = 0
        
        # Test 3: Large dataset (5,000 rows) - optimized parallel processing
        print("\n📝 Test 3: Large dataset (5,000 rows) - optimized parallel processing...")
        large_data = {
            'id': [f'large_{i:05d}' for i in range(5000)],
            'timestamp': [datetime.now() + timedelta(minutes=i) for i in range(5000)],
            'format': [random.choice(['video', 'audio']) for _ in range(5000)],
            'bitrate': [random.randint(1000000, 50000000) for _ in range(5000)],
            'tags': [random.choice(['live', 'recorded', 'test']) for _ in range(5000)]
        }
        
        start_time = time.time()
        try:
            result = manager.insert_batch_efficient(test_table_name, large_data, batch_size=500, max_workers=4)
            large_time = time.time() - start_time
            print(f"✅ Large dataset inserted in {large_time:.3f}s, result: {result}")
        except Exception as e:
            print(f"❌ Large dataset insertion failed: {e}")
            large_time = 0
        
        # Verify data and cache
        print("\n🔍 Verifying data and cache...")
        try:
            # Check total rows
            all_data = manager.query_with_predicates(test_table_name, ['id'], {})
            total_rows = len(all_data) if all_data else 0
            print(f"✅ Total rows in table: {total_rows}")
            
            # Check table stats (should now be updated)
            stats = manager.get_table_stats(test_table_name)
            print(f"✅ Table stats: {stats}")
            
            # Check cache stats
            cache_stats = manager.get_cache_stats()
            print(f"✅ Cache stats: {cache_stats}")
            
        except Exception as e:
            print(f"❌ Data verification failed: {e}")
            total_rows = 0
        
        # Performance analysis
        print("\n" + "=" * 60)
        print("📊 ROW POOLING PERFORMANCE ANALYSIS:")
        
        if small_time > 0:
            print(f"  Small dataset (100 rows): {small_time:.3f}s")
            print(f"    Rate: {100/small_time:.1f} rows/second")
        
        if medium_time > 0:
            print(f"  Medium dataset (1,000 rows): {medium_time:.3f}s")
            print(f"    Rate: {1000/medium_time:.1f} rows/second")
            if small_time > 0:
                efficiency = (small_time * 10) / medium_time
                print(f"    Efficiency gain: {efficiency:.1f}x")
        
        if large_time > 0:
            print(f"  Large dataset (5,000 rows): {large_time:.3f}s")
            print(f"    Rate: {5000/large_time:.1f} rows/second")
            if small_time > 0:
                efficiency = (small_time * 50) / large_time
                print(f"    Efficiency gain: {efficiency:.1f}x")
        
        print(f"  Total rows inserted: {total_rows}")
        
        # Test query performance on populated table
        print("\n⏱️ Testing query performance on populated table...")
        if total_rows > 0:
            # Time-range query
            start_time = time.time()
            time_query = manager.query_with_predicates(
                test_table_name, 
                ['id', 'timestamp'], 
                {'timestamp': {'between': [datetime.now() - timedelta(hours=2), datetime.now()]}}
            )
            query_time = time.time() - start_time
            print(f"  Time query: {query_time:.3f}s, returned {len(time_query) if time_query else 0} rows")
            
            if query_time < 5.0:
                print("✅ Query performance target met (<5s)!")
            else:
                print(f"⚠️ Query performance target not met: {query_time:.3f}s (target: <5s)")
        
        print("\n" + "=" * 60)
        print("✅ ROW POOLING TEST COMPLETED!")
        
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
    test_row_pooling()
