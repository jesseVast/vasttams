#!/usr/bin/env python3
"""
Test script to test VASTDBManager directly on a simple table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager.core import VastDBManager
from app.config import get_settings
import pyarrow as pa
from ibis import _ as ibis_
import random

def test_simple_table_operations():
    """Test insert, update, and delete on a simple table"""
    try:
        # Get settings
        settings = get_settings()
        
        # Create VastDBManager instance
        db_manager = VastDBManager(
            endpoints=settings.vast_endpoint
        )
        
        table_name = "test_simple_table"
        
        print("🧪 Testing simple table operations...")
        
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
        
        # Step 2: Insert 100 records
        print("\n📥 Step 2: Inserting 100 records...")
        try:
            # Generate 100 test records
            names = []
            test_data = {
                'id': [],
                'name': [],
                'address_zip': []
            }
            
            for i in range(100):
                test_data['id'].append(f"test-{i:03d}")
                name = f"Person {i}"
                names.append(name)
                test_data['name'].append(name)
                test_data['address_zip'].append(f"{10000 + i}")
            
            # Insert using VASTDBManager
            result = db_manager.insert_batch_efficient(table_name, test_data)
            print(f"✅ Insert successful: {result} rows")
            print(f"📋 Names tracked: {names[:5]}... (showing first 5)")
            
        except Exception as e:
            print(f"❌ Insert failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 3: Query to verify insert and get row IDs
        print("\n🔍 Step 3: Querying to verify insert...")
        try:
            # Query without predicate to get all records
            result = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            print(f"✅ Query successful")
            print(f"Result type: {type(result)}")
            print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if isinstance(result, dict):
                print(f"Total rows: {len(result.get('id', []))}")
                print(f"Row IDs available: {len(result.get('$row_id', []))}")
                print(f"First few names: {result.get('name', [])[:5]}")
                print(f"First few row IDs: {result.get('$row_id', [])[:5]}")
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 4: Randomly update 10 rows with new address_zip values
        print("\n🔧 Step 4: Randomly updating 10 rows...")
        try:
            # Get all row IDs
            all_data = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            if not isinstance(all_data, dict) or '$row_id' not in all_data:
                print(f"❌ Could not get row IDs for updates")
                return False
            
            row_ids = all_data['$row_id']
            names = all_data['name']
            
            print(f"📋 Available row IDs: {len(row_ids)}")
            print(f"📋 Available names: {len(names)}")
            
            # Randomly select 10 row IDs to update
            if len(row_ids) >= 10:
                selected_indices = random.sample(range(len(row_ids)), 10)
                selected_row_ids = [row_ids[i] for i in selected_indices]
                selected_names = [names[i] for i in selected_indices]
                
                print(f"🎲 Randomly selected 10 rows to update:")
                for i, (row_id, name) in enumerate(zip(selected_row_ids, selected_names)):
                    print(f"  {i+1}. Row ID {row_id}: {name}")
                
                # Update each selected row with a new address_zip
                update_count = 0
                for i, row_id in enumerate(selected_row_ids):
                    # Create predicate to find the specific row
                    predicate = (ibis_.id == f"test-{selected_indices[i]:03d}")
                    
                    # Update data - new address_zip value
                    new_zip = f"UPDATED-{90000 + i}"
                    update_data = {
                        'address_zip': [new_zip]
                    }
                    
                    # Update using VASTDBManager
                    result = db_manager.update(table_name, update_data, predicate)
                    if result > 0:
                        update_count += 1
                        print(f"  ✅ Updated row {row_id} ({selected_names[i]}): {new_zip}")
                    else:
                        print(f"  ❌ Failed to update row {row_id} ({selected_names[i]})")
                
                print(f"🎯 Successfully updated {update_count}/10 rows")
                
            else:
                print(f"⚠️  Not enough rows to update (have {len(row_ids)}, need 10)")
                
        except Exception as e:
            print(f"❌ Random updates failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 5: Query again to verify updates
        print("\n🔍 Step 5: Querying to verify updates...")
        try:
            result = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            print(f"✅ Query after updates successful")
            
            if isinstance(result, dict):
                print(f"Total rows after updates: {len(result.get('id', []))}")
                
                # Check for updated address_zip values
                address_zips = result.get('address_zip', [])
                updated_zips = [zip_code for zip_code in address_zips if zip_code.startswith('UPDATED-')]
                print(f"Updated address_zip values found: {len(updated_zips)}")
                print(f"Sample updated zips: {updated_zips[:5]}")
            
        except Exception as e:
            print(f"❌ Query after updates failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 6: Clean up - delete all records
        print("\n🗑️  Step 6: Cleaning up - deleting all records...")
        try:
            # Delete all records by using a predicate that matches all
            predicate = (ibis_.id != "NONEXISTENT")
            
            # Delete using VASTDBManager
            result = db_manager.delete(table_name, predicate)
            print(f"✅ Delete successful: {result} rows deleted")
            
        except Exception as e:
            print(f"❌ Delete failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 7: Query again to verify deletion
        print("\n🔍 Step 7: Querying to verify deletion...")
        try:
            result = db_manager.query_with_predicates(table_name, None, include_row_ids=True)
            print(f"✅ Query after deletion successful")
            
            if isinstance(result, dict):
                print(f"Total rows after deletion: {len(result.get('id', []))}")
                print(f"Row IDs after deletion: {len(result.get('$row_id', []))}")
            
        except Exception as e:
            print(f"❌ Query after deletion failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n🎉 Simple table operations test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_table_operations()
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        exit(1)
