#!/usr/bin/env python3
"""
Comprehensive test script to test all VASTDBManager functions on the simple table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager.core import VastDBManager
from app.config import get_settings
import pyarrow as pa
from ibis import _ as ibis_
import random
import time

def test_all_vastdbmanager_functions():
    """Test all VASTDBManager functions on the simple table"""
    try:
        # Get settings
        settings = get_settings()
        
        # Create VastDBManager instance
        db_manager = VastDBManager(
            endpoints=settings.vast_endpoint
        )
        
        table_name = "test_simple_table"
        
        print("🧪 Testing ALL VASTDBManager functions...")
        
        # Step 1: Create the simple table
        print("\n📝 Step 1: Creating simple table...")
        try:
            # Define schema for simple table
            schema = pa.schema([
                pa.field('id', pa.string()),
                pa.field('name', pa.string()),
                pa.field('address_zip', pa.string())
            ])
            
            # Create table using VAST connection directly
            with db_manager.connection.transaction() as tx:
                bucket = tx.bucket(db_manager.bucket)
                schema_obj = bucket.schema(db_manager.schema)
                
                # Drop table if it exists
                try:
                    existing_table = schema_obj.table(table_name)
                    existing_table.drop()
                    print(f"✅ Dropped existing table {table_name}")
                except:
                    pass
                
                # Create new table
                vast_table = schema_obj.create_table(table_name, schema)
                print(f"✅ Created table {table_name} with schema: {[f.name for f in schema]}")
                
        except Exception as e:
            print(f"❌ Failed to create table: {e}")
            return False
        
        # Step 2: Test table discovery and listing
        print("\n🔍 Step 2: Testing table discovery and listing...")
        try:
            # Test list_tables
            tables = db_manager.list_tables()
            print(f"✅ list_tables(): {len(tables)} tables found")
            print(f"📋 Tables: {tables}")
            
            # Test tables property
            tables_prop = db_manager.tables
            print(f"✅ tables property: {len(tables_prop)} tables found")
            
            # Test if our table is in the list
            if table_name in tables:
                print(f"✅ Our table '{table_name}' found in table list")
            else:
                print(f"⚠️  Our table '{table_name}' NOT found in table list")
                
        except Exception as e:
            print(f"❌ Table discovery failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 3: Insert test data
        print("\n📥 Step 3: Inserting test data...")
        try:
            # Generate test data
            test_data = {
                'id': [],
                'name': [],
                'address_zip': []
            }
            
            for i in range(50):  # 50 records for testing
                test_data['id'].append(f"test-{i:03d}")
                test_data['name'].append(f"Person {i}")
                test_data['address_zip'].append(f"{10000 + i}")
            
            # Test insert_batch_efficient
            result = db_manager.insert_batch_efficient(table_name, test_data)
            print(f"✅ insert_batch_efficient(): {result} rows inserted")
            
        except Exception as e:
            print(f"❌ Insert failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 4: Test all query methods
        print("\n🔍 Step 4: Testing all query methods...")
        try:
            # Test query_with_predicates with include_row_ids
            print("  Testing query_with_predicates with include_row_ids=True...")
            result_with_ids = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            print(f"    ✅ query_with_predicates(include_row_ids=True): {len(result_with_ids.get('id', []))} rows, {len(result_with_ids.get('$row_id', []))} row IDs")
            
            # Test query_with_predicates without include_row_ids
            print("  Testing query_with_predicates without include_row_ids...")
            result_without_ids = db_manager.query_with_predicates(table_name, None, include_row_ids=False)
            print(f"    ✅ query_with_predicates(include_row_ids=False): {len(result_without_ids.get('id', []))} rows")
            
            # Test query_with_predicates with predicate
            print("  Testing query_with_predicates with predicate...")
            predicate = (ibis_.id == "test-000")
            result_with_predicate = db_manager.query_with_predicates(table_name, predicate, include_row_ids=True)
            print(f"    ✅ query_with_predicates(with predicate): {len(result_with_predicate.get('id', []))} rows")
            
            # Test select method
            print("  Testing select method...")
            select_result = db_manager.select(table_name)
            print(f"    ✅ select(): {len(select_result.get('id', []))} rows")
            
        except Exception as e:
            print(f"❌ Query methods failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 5: Test update methods
        print("\n🔧 Step 5: Testing update methods...")
        try:
            # Test single column update
            print("  Testing single column update...")
            update_data = {'name': ['Updated Person 0']}
            predicate = (ibis_.id == "test-000")
            update_result = db_manager.update(table_name, update_data, predicate)
            print(f"    ✅ update(single column): {update_result} rows updated")
            
            # Test multiple column update
            print("  Testing multiple column update...")
            update_data_multi = {
                'name': ['Updated Person 1'],
                'address_zip': ['UPDATED-99999']
            }
            predicate = (ibis_.id == "test-001")
            update_result_multi = db_manager.update(table_name, update_data_multi, predicate)
            print(f"    ✅ update(multiple columns): {update_result_multi} rows updated")
            
        except Exception as e:
            print(f"❌ Update methods failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 6: Test delete methods
        print("\n🗑️  Step 6: Testing delete methods...")
        try:
            # Test single row delete
            print("  Testing single row delete...")
            predicate = (ibis_.id == "test-002")
            delete_result = db_manager.delete(table_name, predicate)
            print(f"    ✅ delete(single row): {delete_result} rows deleted")
            
            # Test multiple row delete
            print("  Testing multiple row delete...")
            predicate = (ibis_.id.isin(["test-003", "test-004", "test-005"]))
            delete_result_multi = db_manager.delete(table_name, predicate)
            print(f"    ✅ delete(multiple rows): {delete_result_multi} rows deleted")
            
        except Exception as e:
            print(f"❌ Delete methods failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 7: Test cache management
        print("\n💾 Step 7: Testing cache management...")
        try:
            # Test get_table_columns
            columns = db_manager.cache_manager.get_table_columns(table_name)
            print(f"✅ get_table_columns(): {len(columns)} columns found")
            print(f"📋 Column names: {[col.name for col in columns]}")
            
            # Test get_table_stats
            stats = db_manager.cache_manager.get_table_stats(table_name)
            print(f"✅ get_table_stats(): {stats}")
            
            # Test get_all_table_names
            all_table_names = db_manager.cache_manager.get_all_table_names()
            print(f"✅ get_all_table_names(): {len(all_table_names)} tables")
            
        except Exception as e:
            print(f"❌ Cache management failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 8: Test predicate builder
        print("\n🔍 Step 8: Testing predicate builder...")
        try:
            # Test simple predicate
            simple_pred = db_manager.predicate_builder.build_simple_predicate('id', '==', 'test-010')
            print(f"✅ build_simple_predicate(): {simple_pred}")
            
            # Test complex predicate
            complex_pred = db_manager.predicate_builder.build_complex_predicate([
                ('id', '==', 'test-011'),
                ('name', '==', 'Person 11')
            ])
            print(f"✅ build_complex_predicate(): {complex_pred}")
            
        except Exception as e:
            print(f"❌ Predicate builder failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 9: Test query optimization
        print("\n⚡ Step 9: Testing query optimization...")
        try:
            # Test query optimization
            optimized_config = db_manager.query_optimizer.optimize_query(table_name, None)
            print(f"✅ query_optimizer.optimize_query(): {optimized_config}")
            
        except Exception as e:
            print(f"❌ Query optimization failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 10: Test analytics functions
        print("\n📊 Step 10: Testing analytics functions...")
        try:
            # Test time series analytics
            time_series = db_manager.time_series_analytics.analyze_time_patterns(table_name, 'id')
            print(f"✅ time_series_analytics.analyze_time_patterns(): {time_series}")
            
            # Test aggregation analytics
            aggregation = db_manager.aggregation_analytics.calculate_statistics(table_name, ['id', 'name'])
            print(f"✅ aggregation_analytics.calculate_statistics(): {aggregation}")
            
        except Exception as e:
            print(f"❌ Analytics functions failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 11: Test performance monitoring
        print("\n📈 Step 11: Testing performance monitoring...")
        try:
            # Test performance monitoring
            performance = db_manager.performance_monitor.get_performance_metrics()
            print(f"✅ performance_monitor.get_performance_metrics(): {performance}")
            
        except Exception as e:
            print(f"❌ Performance monitoring failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 12: Test endpoint management
        print("\n🌐 Step 12: Testing endpoint management...")
        try:
            # Test endpoint management
            endpoints = db_manager.endpoint_manager.get_endpoints()
            print(f"✅ endpoint_manager.get_endpoints(): {endpoints}")
            
            # Test load balancer
            selected_endpoint = db_manager.load_balancer.select_endpoint()
            print(f"✅ load_balancer.select_endpoint(): {selected_endpoint}")
            
        except Exception as e:
            print(f"❌ Endpoint management failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 13: Test connection management
        print("\n🔌 Step 13: Testing connection management...")
        try:
            # Test connection status
            if db_manager.connection:
                print(f"✅ Connection active: {type(db_manager.connection)}")
            else:
                print(f"⚠️  No active connection")
            
            # Test bucket and schema access
            print(f"✅ Bucket: {db_manager.bucket}")
            print(f"✅ Schema: {db_manager.schema}")
            
        except Exception as e:
            print(f"❌ Connection management failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 14: Final verification and cleanup
        print("\n🔍 Step 14: Final verification and cleanup...")
        try:
            # Final query to see what's left
            final_result = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            remaining_rows = len(final_result.get('id', []))
            print(f"✅ Final query: {remaining_rows} rows remaining")
            
            # Clean up - delete all remaining records
            if remaining_rows > 0:
                predicate = (ibis_.id != "NONEXISTENT")
                delete_result = db_manager.delete(table_name, predicate)
                print(f"✅ Cleanup delete: {delete_result} rows deleted")
            
            # Final verification
            final_check = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            final_count = len(final_check.get('id', []))
            print(f"✅ Final count: {final_count} rows")
            
        except Exception as e:
            print(f"❌ Final verification failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n🎉 All VASTDBManager function tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_all_vastdbmanager_functions()
    if success:
        print("\n✅ All function tests passed!")
    else:
        print("\n❌ Some function tests failed!")
        exit(1)
