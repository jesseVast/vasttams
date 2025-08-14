#!/usr/bin/env python3
"""
Simple script to drop all tables in VAST database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager.core import VastDBManager
from app.config import get_settings

def drop_all_tables():
    """Drop all existing tables"""
    try:
        # Get settings
        settings = get_settings()
        
        # Create VastDBManager instance
        db_manager = VastDBManager(
            endpoints=settings.vast_endpoint
        )
        
        print("🔧 Starting table cleanup process...")
        
        # List existing tables
        existing_tables = db_manager.list_tables()
        print(f"📋 Existing tables: {existing_tables}")
        
        # Drop all existing tables using VAST connection directly
        with db_manager.connection.transaction() as tx:
            bucket = tx.bucket(db_manager.bucket)
            schema = bucket.schema(db_manager.schema)
            
            for table_name in existing_tables:
                try:
                    print(f"🗑️  Dropping table: {table_name}")
                    table = schema.table(table_name)
                    # Try to drop the table
                    if hasattr(table, 'drop'):
                        table.drop()
                        print(f"✅ Dropped table: {table_name}")
                    elif hasattr(schema, 'drop_table'):
                        schema.drop_table(table_name)
                        print(f"✅ Dropped table: {table_name}")
                    else:
                        print(f"⚠️  No drop method found for table {table_name}")
                        
                except Exception as e:
                    print(f"⚠️  Could not drop table {table_name}: {e}")
        
        print("🎉 Table cleanup completed!")
        
    except Exception as e:
        print(f"❌ Failed to cleanup tables: {e}")
        raise

if __name__ == "__main__":
    drop_all_tables()
