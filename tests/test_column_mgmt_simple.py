#!/usr/bin/env python3
"""
Simple Column Management Test Script

This script tests the column management functionality on a real VAST database table.
Run this script to verify that the column management methods work correctly.

Usage:
    python test_column_mgmt_simple.py
"""

import logging
import sys
import os
import pyarrow as pa
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.storage.vastdbmanager import VastDBManager
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_column_management():
    """Test column management operations on a real VAST database table."""
    logger.info("Starting Column Management Test")
    
    # Get settings
    settings = get_settings()
    
    # Create manager
    manager = VastDBManager(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema="test_column_mgmt_schema"
    )
    
    table_name = None
    
    try:
        # Create test table
        table_name = f"test_column_mgmt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        initial_schema = pa.schema([
            ('id', pa.string()),
            ('name', pa.string()),
            ('created_at', pa.timestamp('us')),
            ('value', pa.int32())
        ])
        
        manager.create_table(table_name, initial_schema)
        logger.info(f"✓ Created test table: {table_name}")
        
        # Insert test data
        test_data = {
            'id': ['1', '2', '3'],
            'name': ['Alice', 'Bob', 'Charlie'],
            'created_at': [datetime.now(timezone.utc)] * 3,
            'value': [100, 200, 300]
        }
        manager.insert(table_name, test_data)
        logger.info("✓ Inserted test data")
        
        # Test 1: Get initial columns
        columns = manager.get_table_columns(table_name)
        column_names = [field.name for field in columns]
        logger.info(f"✓ Initial columns: {column_names}")
        
        # Test 2: Check column existence
        assert manager.column_exists(table_name, 'id') is True
        assert manager.column_exists(table_name, 'non_existent') is False
        logger.info("✓ Column existence checks passed")
        
        # Test 3: Add new columns
        new_columns = pa.schema([
            ('email', pa.string()),
            ('age', pa.int32()),
            ('is_active', pa.bool_())
        ])
        
        success = manager.add_columns(table_name, new_columns)
        assert success is True
        logger.info("✓ Added new columns")
        
        # Verify columns were added
        updated_columns = manager.get_table_columns(table_name)
        updated_names = [field.name for field in updated_columns]
        assert 'email' in updated_names
        assert 'age' in updated_names
        assert 'is_active' in updated_names
        logger.info(f"✓ Updated columns: {updated_names}")
        
        # Test 4: Rename a column
        success = manager.rename_column(table_name, 'age', 'user_age')
        assert success is True
        logger.info("✓ Renamed column 'age' to 'user_age'")
        
        # Verify rename
        assert manager.column_exists(table_name, 'age') is False
        assert manager.column_exists(table_name, 'user_age') is True
        
        # Test 5: Drop a column
        drop_schema = pa.schema([('email', pa.string())])
        success = manager.drop_column(table_name, drop_schema)
        assert success is True
        logger.info("✓ Dropped column 'email'")
        
        # Verify drop
        assert manager.column_exists(table_name, 'email') is False
        
        # Test 6: Final state verification
        final_columns = manager.get_table_columns(table_name)
        final_names = [field.name for field in final_columns]
        expected_final = ['id', 'name', 'created_at', 'value', 'user_age', 'is_active']
        
        for expected in expected_final:
            assert expected in final_names
        
        logger.info(f"✓ Final columns: {final_names}")
        logger.info("✓ All column management tests passed!")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if table_name:
            try:
                manager.drop_table(table_name)
                logger.info(f"✓ Cleaned up test table: {table_name}")
            except Exception as e:
                logger.warning(f"⚠ Cleanup error: {e}")
        
        try:
            manager.close()
            logger.info("✓ Closed database connection")
        except Exception as e:
            logger.warning(f"⚠ Connection close error: {e}")


def main():
    """Main function to run the test."""
    logger.info("=" * 60)
    logger.info("VAST Database Column Management Test")
    logger.info("=" * 60)
    
    success = test_column_management()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        logger.error("❌ TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
