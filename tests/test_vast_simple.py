#!/usr/bin/env python3
"""
Simple test script to test basic VAST operations
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_vast_operations():
    """Test basic VAST operations"""
    try:
        print("🔍 Testing VAST operations...")
        
        # Initialize VastDBManager
        print("📡 Initializing VastDBManager...")
        from storage.vastdbmanager.core import VastDBManager
        
        db_manager = VastDBManager(
            endpoints=["http://172.200.204.90"]
        )
        
        print("✅ VastDBManager initialized")
        
        # Test basic operations
        print("🔍 Testing table discovery...")
        tables = db_manager.tables
        print(f"📋 Found tables: {tables}")
        
        if 'sources' in tables:
            print("🔍 Testing sources table operations...")
            
            # Test select
            print("📥 Testing select operation...")
            try:
                results = db_manager.select('sources')
                print(f"✅ Select successful: {len(results) if results else 0} results")
                print(f"Results type: {type(results)}")
                
                if isinstance(results, dict):
                    print(f"Results keys: {list(results.keys())}")
                    for key, values in results.items():
                        if key == 'id':
                            print(f"ID column: {values[:5]}")  # Show first 5
                        elif key in ['label', 'format']:
                            print(f"{key} column: {values[:3]}")  # Show first 3
                elif isinstance(results, list):
                    print(f"First result: {results[0] if results else 'None'}")
                
                # Check schema for sources table
                print("🔍 Checking sources table schema...")
                schema = db_manager.cache_manager.get_table_columns('sources')
                if schema:
                    print(f"📋 Sources table schema: {[f.name for f in schema]}")
                else:
                    print("❌ No schema found for sources table")
                    
            except Exception as e:
                print(f"❌ Select failed: {e}")
            
            # Test simple update (without complex logic)
            print("📝 Testing simple update operation...")
            try:
                # Create a simple predicate
                from ibis import _ as ibis_
                predicate = (ibis_.id == "550e8400-e29b-41d4-a716-446655440000")
                
                # Simple update data
                update_data = {
                    'label': ['Updated Test Label'],
                    'updated': ['2025-08-14T19:21:21.902997+00:00']
                }
                
                print(f"🔧 Attempting update with data: {update_data}")
                print(f"🔧 Predicate: {predicate}")
                
                # First, let's test the query_with_predicates to see what it returns
                print("🔍 Testing query_with_predicates with include_row_ids=True...")
                query_result = db_manager.query_with_predicates('sources', predicate, include_row_ids=True)
                print(f"Query result type: {type(query_result)}")
                print(f"Query result: {query_result}")
                
                if hasattr(query_result, 'to_pydict'):
                    print(f"Query result as dict: {query_result.to_pydict()}")
                elif isinstance(query_result, dict):
                    print(f"Query result keys: {list(query_result.keys())}")
                
                # Let's check what sources actually exist
                print("🔍 Checking what sources exist...")
                all_sources = db_manager.select('sources')
                if all_sources and isinstance(all_sources, dict) and 'id' in all_sources:
                    print(f"Available source IDs: {all_sources['id'][:5]}")  # Show first 5
                elif all_sources and isinstance(all_sources, list):
                    print(f"Available source IDs: {[s.get('id', 'N/A') for s in all_sources[:5]]}")
                
                # Test with a simpler query - no predicate
                print("🔍 Testing query_with_predicates without predicate...")
                simple_result = db_manager.query_with_predicates('sources', None, include_row_ids=True)
                print(f"Simple query result type: {type(simple_result)}")
                if isinstance(simple_result, dict):
                    print(f"Simple query result keys: {list(simple_result.keys())}")
                    if '$row_id' in simple_result:
                        print(f"Row IDs found: {len(simple_result['$row_id'])}")
                    else:
                        print("No $row_id in simple query result")
                
                # Try the update
                result = db_manager.update('sources', update_data, predicate)
                print(f"✅ Update successful: {result}")
                
            except Exception as e:
                print(f"❌ Update failed: {e}")
                import traceback
                traceback.print_exc()
        
        print("✅ VAST operations test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vast_operations()
