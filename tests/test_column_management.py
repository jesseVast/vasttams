"""
Test Column Management Methods for VastDBManager

This test module verifies the column management functionality including:
- Adding new columns to existing tables
- Renaming columns
- Dropping columns
- Checking column existence

The tests use a real VAST database connection and create/cleanup test tables.
"""

import logging
import pytest
import pyarrow as pa
from datetime import datetime, timezone
from typing import Dict, Any

from app.storage.vastdbmanager import VastDBManager
from app.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestColumnManagement:
    """Test suite for column management operations."""
    
    @pytest.fixture(scope="class")
    def vast_manager(self):
        """Create a VastDBManager instance for testing."""
        settings = get_settings()
        
        manager = VastDBManager(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema="test_column_mgmt_schema"
        )
        
        yield manager
        
        # Cleanup
        try:
            manager.close()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
    
    @pytest.fixture(scope="function")
    def test_table(self, vast_manager):
        """Create a test table for column management operations."""
        table_name = f"test_column_mgmt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create initial schema with basic columns
        initial_schema = pa.schema([
            ('id', pa.string()),
            ('name', pa.string()),
            ('created_at', pa.timestamp('us')),
            ('value', pa.int32())
        ])
        
        try:
            vast_manager.create_table(table_name, initial_schema)
            logger.info(f"Created test table: {table_name}")
            
            # Insert some test data
            test_data = {
                'id': ['1', '2', '3'],
                'name': ['Alice', 'Bob', 'Charlie'],
                'created_at': [datetime.now(timezone.utc)] * 3,
                'value': [100, 200, 300]
            }
            vast_manager.insert(table_name, test_data)
            logger.info(f"Inserted test data into {table_name}")
            
            yield table_name
            
        finally:
            # Cleanup test table
            try:
                vast_manager.drop_table(table_name)
                logger.info(f"Cleaned up test table: {table_name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup test table {table_name}: {e}")
    
    def test_get_table_columns(self, vast_manager, test_table):
        """Test getting table columns."""
        columns = vast_manager.get_table_columns(test_table)
        
        assert columns is not None
        assert len(columns) == 4
        
        column_names = [field.name for field in columns]
        expected_columns = ['id', 'name', 'created_at', 'value']
        
        for expected in expected_columns:
            assert expected in column_names
        
        logger.info(f"Table columns: {column_names}")
    
    def test_column_exists(self, vast_manager, test_table):
        """Test checking if columns exist."""
        # Test existing columns
        assert vast_manager.column_exists(test_table, 'id') is True
        assert vast_manager.column_exists(test_table, 'name') is True
        assert vast_manager.column_exists(test_table, 'created_at') is True
        assert vast_manager.column_exists(test_table, 'value') is True
        
        # Test non-existing columns
        assert vast_manager.column_exists(test_table, 'non_existent') is False
        assert vast_manager.column_exists(test_table, 'random_column') is False
        
        logger.info("Column existence checks passed")
    
    def test_add_columns(self, vast_manager, test_table):
        """Test adding new columns to a table."""
        # Define new columns to add
        new_columns = pa.schema([
            ('email', pa.string()),
            ('age', pa.int32()),
            ('is_active', pa.bool_()),
            ('metadata', pa.string())
        ])
        
        # Add columns
        success = vast_manager.add_columns(test_table, new_columns)
        assert success is True
        
        # Verify columns were added
        updated_columns = vast_manager.get_table_columns(test_table)
        column_names = [field.name for field in updated_columns]
        
        # Check original columns still exist
        original_columns = ['id', 'name', 'created_at', 'value']
        for col in original_columns:
            assert col in column_names
        
        # Check new columns were added
        new_column_names = ['email', 'age', 'is_active', 'metadata']
        for col in new_column_names:
            assert col in column_names
        
        assert len(column_names) == 8  # 4 original + 4 new
        
        logger.info(f"Added columns successfully. Updated schema: {column_names}")
    
    def test_rename_column(self, vast_manager, test_table):
        """Test renaming a column."""
        # First add a column to rename
        new_column = pa.schema([('temp_column', pa.string())])
        vast_manager.add_columns(test_table, new_column)
        
        # Verify column exists
        assert vast_manager.column_exists(test_table, 'temp_column') is True
        
        # Rename the column
        success = vast_manager.rename_column(test_table, 'temp_column', 'renamed_column')
        assert success is True
        
        # Verify old name doesn't exist
        assert vast_manager.column_exists(test_table, 'temp_column') is False
        
        # Verify new name exists
        assert vast_manager.column_exists(test_table, 'renamed_column') is True
        
        # Check column type is preserved
        columns = vast_manager.get_table_columns(test_table)
        renamed_field = next(field for field in columns if field.name == 'renamed_column')
        assert renamed_field.type == pa.string()
        
        logger.info("Column rename successful")
    
    def test_drop_column(self, vast_manager, test_table):
        """Test dropping columns from a table."""
        # First add a column to drop
        new_column = pa.schema([('column_to_drop', pa.int64())])
        vast_manager.add_columns(test_table, new_column)
        
        # Verify column exists
        assert vast_manager.column_exists(test_table, 'column_to_drop') is True
        
        # Drop the column
        success = vast_manager.drop_column(test_table, new_column)
        assert success is True
        
        # Verify column no longer exists
        assert vast_manager.column_exists(test_table, 'column_to_drop') is False
        
        # Verify other columns still exist
        assert vast_manager.column_exists(test_table, 'id') is True
        assert vast_manager.column_exists(test_table, 'name') is True
        
        logger.info("Column drop successful")
    
    def test_comprehensive_column_operations(self, vast_manager, test_table):
        """Test a comprehensive sequence of column operations."""
        # Step 1: Add multiple columns
        new_columns = pa.schema([
            ('status', pa.string()),
            ('priority', pa.int32()),
            ('tags', pa.string())
        ])
        
        success = vast_manager.add_columns(test_table, new_columns)
        assert success is True
        
        # Step 2: Rename one of the new columns
        success = vast_manager.rename_column(test_table, 'priority', 'importance')
        assert success is True
        
        # Step 3: Add another column
        another_column = pa.schema([('notes', pa.string())])
        success = vast_manager.add_columns(test_table, another_column)
        assert success is True
        
        # Step 4: Drop one column
        drop_schema = pa.schema([('tags', pa.string())])
        success = vast_manager.drop_column(test_table, drop_schema)
        assert success is True
        
        # Step 5: Verify final state
        final_columns = vast_manager.get_table_columns(test_table)
        column_names = [field.name for field in final_columns]
        
        # Should have: id, name, created_at, value, status, importance, notes
        expected_columns = ['id', 'name', 'created_at', 'value', 'status', 'importance', 'notes']
        for expected in expected_columns:
            assert expected in column_names
        
        # Should not have: priority, tags
        assert 'priority' not in column_names
        assert 'tags' not in column_names
        
        assert len(column_names) == 7
        
        logger.info(f"Comprehensive column operations successful. Final schema: {column_names}")
    
    def test_error_handling(self, vast_manager, test_table):
        """Test error handling for invalid operations."""
        # Test adding column that already exists
        existing_column = pa.schema([('id', pa.string())])
        success = vast_manager.add_columns(test_table, existing_column)
        # This should fail gracefully
        assert success is False
        
        # Test renaming non-existent column
        success = vast_manager.rename_column(test_table, 'non_existent', 'new_name')
        assert success is False
        
        # Test dropping non-existent column
        non_existent_schema = pa.schema([('non_existent', pa.string())])
        success = vast_manager.drop_column(test_table, non_existent_schema)
        assert success is False
        
        # Test operations on non-existent table
        success = vast_manager.add_columns('non_existent_table', pa.schema([('test', pa.string())]))
        assert success is False
        
        logger.info("Error handling tests passed")


def run_column_management_tests():
    """Run column management tests manually."""
    logger.info("Starting Column Management Tests")
    
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
        logger.info(f"Created test table: {table_name}")
        
        # Insert test data
        test_data = {
            'id': ['1', '2', '3'],
            'name': ['Alice', 'Bob', 'Charlie'],
            'created_at': [datetime.now(timezone.utc)] * 3,
            'value': [100, 200, 300]
        }
        manager.insert(table_name, test_data)
        logger.info("Inserted test data")
        
        # Test 1: Get columns
        columns = manager.get_table_columns(table_name)
        logger.info(f"Initial columns: {[field.name for field in columns]}")
        
        # Test 2: Add columns
        new_columns = pa.schema([
            ('email', pa.string()),
            ('age', pa.int32())
        ])
        success = manager.add_columns(table_name, new_columns)
        logger.info(f"Add columns success: {success}")
        
        # Test 3: Check column exists
        exists = manager.column_exists(table_name, 'email')
        logger.info(f"Email column exists: {exists}")
        
        # Test 4: Rename column
        success = manager.rename_column(table_name, 'age', 'user_age')
        logger.info(f"Rename column success: {success}")
        
        # Test 5: Drop column
        drop_schema = pa.schema([('email', pa.string())])
        success = manager.drop_column(table_name, drop_schema)
        logger.info(f"Drop column success: {success}")
        
        # Final state
        final_columns = manager.get_table_columns(table_name)
        logger.info(f"Final columns: {[field.name for field in final_columns]}")
        
        logger.info("All column management tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        # Cleanup
        try:
            manager.drop_table(table_name)
            manager.close()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


if __name__ == "__main__":
    run_column_management_tests()
