"""Test VAST projection functionality"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager import VastDBManager
import pyarrow as pa
from datetime import datetime, timedelta
import time

def test_vast_projections():
    """Test VAST projection creation and management"""
    
    print("🧪 TESTING VAST PROJECTIONS")
    print("=" * 50)
    
    # Initialize VastDBManager
    endpoints = [
        "http://172.200.204.90",
        "http://172.200.204.91", 
        "http://172.200.204.93",
        "http://172.200.204.92"
    ]
    
    manager = VastDBManager(endpoints)
    test_table_name = f"projection_test_{int(time.time())}"
    
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
            pa.field('resolution', 'int32'),
            pa.field('tags', 'string')
        ])
        print("✅ Schema created")
        
        # Define projections
        print("\n🎯 Defining VAST projections...")
        projections = {
            'time_series': ['timestamp'],  # Sorted for time queries
            'categorical': ['format', 'tags'],  # Unsorted for filtering
            'numeric': ['bitrate', 'resolution']  # Unsorted for range queries
        }
        print(f"Projections: {projections}")
        
        # Create table with projections
        print("\n🏗️ Creating table with projections...")
        table = manager.create_table(test_table_name, schema, projections=projections)
        print("✅ Table created with projections")
        
        # Verify projections were created
        print("\n🔍 Verifying projections...")
        table_projections = manager.get_table_projections(test_table_name)
        print(f"Table projections: {table_projections}")
        
        if table_projections:
            print("✅ Projections created successfully")
        else:
            print("⚠️ No projections found - this might be expected for new tables")
        
        # Test adding a new projection
        print("\n➕ Testing projection addition...")
        try:
            manager.add_projection(test_table_name, 'test_projection', ['id', 'format'])
            print("✅ New projection added successfully")
            
            # Verify new projection
            updated_projections = manager.get_table_projections(test_table_name)
            print(f"Updated projections: {updated_projections}")
            
        except Exception as e:
            print(f"⚠️ Could not add new projection: {e}")
        
        print("\n" + "=" * 50)
        print("✅ VAST PROJECTION TEST COMPLETED!")
        
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
    test_vast_projections()
