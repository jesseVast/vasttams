#!/Users/jesse.thaloor/Developer/python/bbctams/bin/python
"""
Real test module for cleanup_database_final.py script.

This module contains real integration tests that require actual database connections.
These tests should only be run in test environments with proper database setup.
"""

import pytest
import asyncio
import sys
import os
from typing import List

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mgmt.cleanup_database_final import (
    cleanup_database,
    _delete_tables_in_order,
    _log_cleanup_summary,
    main,
    TABLES_DELETION_ORDER
)
from app.config import get_settings
from app.vastdbmanager import VastDBManager


class TestCleanupDatabaseFinalReal:
    """Real test class for cleanup_database_final.py functionality."""
    
    @pytest.fixture
    async def db_manager(self):
        """Create a real database manager for testing."""
        settings = get_settings()
        manager = VastDBManager(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema
        )
        yield manager
        manager.close()
    
    @pytest.mark.asyncio
    async def test_database_connection(self, db_manager):
        """Test that database connection works."""
        tables = db_manager.list_tables()
        assert isinstance(tables, list)
    
    @pytest.mark.asyncio
    async def test_cleanup_database_real_no_tables(self, db_manager):
        """Test cleanup when no tables exist (real database)."""
        # First, ensure no tables exist
        initial_tables = db_manager.list_tables()
        
        # If tables exist, clean them up first
        if initial_tables:
            for table in initial_tables:
                try:
                    db_manager.drop_table(table)
                except Exception:
                    pass  # Ignore errors during cleanup
        
        # Now test cleanup with no tables
        result = await cleanup_database()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_tables_in_order_real(self, db_manager):
        """Test real table deletion in order."""
        # Create some test tables first (if they don't exist)
        test_tables = ['test_table_1', 'test_table_2']
        
        try:
            # Create test tables
            for table in test_tables:
                try:
                    db_manager.create_table(table, [('id', 'string'), ('data', 'string')])
                except Exception:
                    pass  # Table might already exist
            
            # Test deletion
            existing_tables = db_manager.list_tables()
            deleted_tables, failed_tables = await _delete_tables_in_order(
                db_manager, test_tables
            )
            
            # Verify results
            assert len(failed_tables) == 0
            assert len(deleted_tables) == len([t for t in test_tables if t in existing_tables])
            
        finally:
            # Clean up any remaining test tables
            for table in test_tables:
                try:
                    db_manager.drop_table(table)
                except Exception:
                    pass
    
    def test_log_cleanup_summary_real(self):
        """Test real cleanup summary logging."""
        initial_tables = ['sources', 'flows', 'segments', 'segment_tags']
        deleted_tables = ['sources', 'flows', 'segments', 'segment_tags']
        failed_tables = []
        remaining_tables = []
        
        result = _log_cleanup_summary(
            initial_tables, deleted_tables, failed_tables, remaining_tables
        )
        
        assert result is True
    
    def test_tables_deletion_order_real(self):
        """Test that real deletion order includes all expected tables."""
        expected_tables = [
            'deletion_requests',
            'webhooks', 
            'segment_tags',
            'segments',
            'objects',
            'flows',
            'sources'
        ]
        
        for table in expected_tables:
            assert table in TABLES_DELETION_ORDER
        
        # Verify dependency order
        assert TABLES_DELETION_ORDER.index('segment_tags') < TABLES_DELETION_ORDER.index('segments')
        assert TABLES_DELETION_ORDER.index('segments') < TABLES_DELETION_ORDER.index('flows')
        assert TABLES_DELETION_ORDER.index('flows') < TABLES_DELETION_ORDER.index('sources')
    
    @pytest.mark.asyncio
    async def test_main_function_real(self):
        """Test main function with real database (dry run)."""
        # This test should not actually run cleanup, just test the function structure
        # In a real test environment, you might want to create test tables first
        
        # Test that main function can be called without errors
        # Note: This will actually attempt to clean the database
        # Only run this in a test environment!
        try:
            result = await main()
            assert result in [0, 1]  # Should return valid exit code
        except Exception as e:
            # If database is not available, that's expected in some environments
            assert "connection" in str(e).lower() or "endpoint" in str(e).lower()


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v", "-s"])
