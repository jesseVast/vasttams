"""Test VAST optimization system with small dataset"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager import VastDBManager
import pyarrow as pa
from datetime import datetime, timedelta
import time

def test_vast_optimization():
    """Test VAST optimization with small dataset"""
    
    print("🧪 TESTING VAST OPTIMIZATION SYSTEM")
    print("=" * 50)
    
    # Initialize VastDBManager
    endpoints = [
        "http://172.200.204.90",
        "http://172.200.204.91", 
        "http://172.200.204.93",
        "http://172.200.204.92"
    ]
    
    manager = VastDBManager(endpoints)
    test_table_name = f"optimization_test_{int(time.time())}"
    
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
        
        # Define projections
        print("\n🎯 Creating VAST projections...")
        projections = {
            'time_series': ['timestamp'],  # Sorted for time queries
            'categorical': ['format', 'tags'],  # Unsorted for filtering
            'numeric': ['bitrate']  # Unsorted for range queries
        }
        
        # Create table with projections
        print("\n🏗️ Creating table with projections...")
        table = manager.create_table(test_table_name, schema, projections=projections)
        print("✅ Table created with projections")
        
        # Insert test data
        print("\n📝 Inserting test data...")
        test_data = {
            'id': ['row_001', 'row_002', 'row_003', 'row_004', 'row_005'],
            'timestamp': [
                datetime.now() - timedelta(hours=1),
                datetime.now() - timedelta(minutes=30),
                datetime.now() - timedelta(minutes=15),
                datetime.now() - timedelta(minutes=5),
                datetime.now()
            ],
            'format': ['video', 'audio', 'video', 'audio', 'video'],
            'bitrate': [10000000, 5000000, 20000000, 3000000, 15000000],
            'tags': ['live', 'recorded', 'live', 'recorded', 'live']
        }
        
        manager.insert_pydict(test_table_name, test_data)
        print("✅ Test data inserted")
        
        # Verify data
        print("\n🔍 Verifying data...")
        all_data = manager.query_with_predicates(test_table_name, ['id', 'timestamp', 'format'], {})
        print(f"Total rows: {len(all_data) if all_data else 0}")
        
        # Test time-series query
        print("\n⏰ Testing time-series query...")
        start_time = time.time()
        time_query = manager.query_with_predicates(
            test_table_name, 
            ['id', 'timestamp'], 
            {'timestamp': {'between': [datetime.now() - timedelta(hours=2), datetime.now()]}}
        )
        time_query_time = time.time() - start_time
        print(f"Time query completed in {time_query_time:.3f}s, returned {len(time_query) if time_query else 0} rows")
        
        # Test categorical query
        print("\n🏷️ Testing categorical query...")
        start_time = time.time()
        cat_query = manager.query_with_predicates(
            test_table_name, 
            ['id', 'format'], 
            {'format': 'video'}
        )
        cat_query_time = time.time() - start_time
        print(f"Categorical query completed in {cat_query_time:.3f}s, returned {len(cat_query) if cat_query else 0} rows")
        
        # Test numeric query
        print("\n🔢 Testing numeric query...")
        start_time = time.time()
        num_query = manager.query_with_predicates(
            test_table_name, 
            ['id', 'bitrate'], 
            {'bitrate': {'gte': 10000000}}
        )
        num_query_time = time.time() - start_time
        print(f"Numeric query completed in {num_query_time:.3f}s, returned {len(num_query) if num_query else 0} rows")
        
        # Performance summary
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE SUMMARY:")
        print(f"  Time-series query: {time_query_time:.3f}s")
        print(f"  Categorical query: {cat_query_time:.3f}s")
        print(f"  Numeric query: {time_query_time:.3f}s")
        print(f"  Average query time: {(time_query_time + cat_query_time + num_query_time) / 3:.3f}s")
        
        if (time_query_time + cat_query_time + num_query_time) / 3 < 1.0:
            print("✅ All queries under 1 second - VAST optimization working!")
        else:
            print("⚠️ Some queries slower than expected")
        
        print("\n" + "=" * 50)
        print("✅ VAST OPTIMIZATION TEST COMPLETED!")
        
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
    test_vast_optimization()
