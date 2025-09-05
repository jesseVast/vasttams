#!/Users/jesse.thaloor/Developer/python/bbctams/bin/python
"""
Test module for cleanup_database_final.py script.

This module contains both mock and real tests for the database cleanup functionality.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import List

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mgmt.cleanup_database_final import (
    cleanup_database,
    _delete_tables_in_order,
    _log_cleanup_summary,
    main,
    TABLES_DELETION_ORDER
)


class TestCleanupDatabaseFinal:
    """Test class for cleanup_database_final.py functionality."""
    
    def test_tables_deletion_order_includes_segment_tags(self):
        """Test that segment_tags table is included in deletion order."""
        assert 'segment_tags' in TABLES_DELETION_ORDER
        assert TABLES_DELETION_ORDER.index('segment_tags') < TABLES_DELETION_ORDER.index('segments')
    
    def test_tables_deletion_order_dependencies(self):
        """Test that table deletion order respects dependencies."""
        # segment_tags should be deleted before segments
        assert TABLES_DELETION_ORDER.index('segment_tags') < TABLES_DELETION_ORDER.index('segments')
        
        # segments should be deleted before flows
        assert TABLES_DELETION_ORDER.index('segments') < TABLES_DELETION_ORDER.index('flows')
        
        # flows should be deleted before sources
        assert TABLES_DELETION_ORDER.index('flows') < TABLES_DELETION_ORDER.index('sources')
    
    @pytest.mark.asyncio
    async def test_cleanup_database_no_tables(self):
        """Test cleanup when no tables exist."""
        mock_db_manager = Mock()
        mock_db_manager.list_tables.return_value = []
        
        with patch('mgmt.cleanup_database_final.get_settings') as mock_settings, \
             patch('mgmt.cleanup_database_final.VastDBManager', return_value=mock_db_manager):
            
            result = await cleanup_database()
            
            assert result is True
            mock_db_manager.list_tables.assert_called_once()
            mock_db_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_database_success(self):
        """Test successful database cleanup."""
        mock_db_manager = Mock()
        mock_db_manager.list_tables.return_value = ['sources', 'flows', 'segments', 'segment_tags']
        
        with patch('mgmt.cleanup_database_final.get_settings') as mock_settings, \
             patch('mgmt.cleanup_database_final.VastDBManager', return_value=mock_db_manager):
            
            result = await cleanup_database()
            
            assert result is True
            # Verify drop_table was called for each table
            assert mock_db_manager.drop_table.call_count == 4
            mock_db_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_database_failure(self):
        """Test database cleanup with failures."""
        mock_db_manager = Mock()
        mock_db_manager.list_tables.return_value = ['sources', 'flows']
        mock_db_manager.drop_table.side_effect = Exception("Database error")
        
        with patch('mgmt.cleanup_database_final.get_settings') as mock_settings, \
             patch('mgmt.cleanup_database_final.VastDBManager', return_value=mock_db_manager):
            
            result = await cleanup_database()
            
            assert result is False
            mock_db_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_tables_in_order_success(self):
        """Test successful table deletion in order."""
        mock_db_manager = Mock()
        existing_tables = ['sources', 'flows', 'segments', 'segment_tags']
        
        deleted_tables, failed_tables = await _delete_tables_in_order(
            mock_db_manager, existing_tables
        )
        
        # Should delete all tables in order
        assert len(deleted_tables) == 4
        assert len(failed_tables) == 0
        assert mock_db_manager.drop_table.call_count == 4
    
    @pytest.mark.asyncio
    async def test_delete_tables_in_order_with_failures(self):
        """Test table deletion with some failures."""
        mock_db_manager = Mock()
        mock_db_manager.drop_table.side_effect = [None, Exception("Error"), None, None]
        existing_tables = ['deletion_requests', 'webhooks', 'segment_tags', 'segments']
        
        deleted_tables, failed_tables = await _delete_tables_in_order(
            mock_db_manager, existing_tables
        )
        
        assert len(deleted_tables) == 3
        assert len(failed_tables) == 1
        assert 'webhooks' in failed_tables
    
    def test_log_cleanup_summary_success(self):
        """Test cleanup summary logging for successful cleanup."""
        initial_tables = ['sources', 'flows', 'segments', 'segment_tags']
        deleted_tables = ['sources', 'flows', 'segments', 'segment_tags']
        failed_tables = []
        remaining_tables = []
        
        result = _log_cleanup_summary(
            initial_tables, deleted_tables, failed_tables, remaining_tables
        )
        
        assert result is True
    
    def test_log_cleanup_summary_with_failures(self):
        """Test cleanup summary logging with failures."""
        initial_tables = ['sources', 'flows', 'segments', 'segment_tags']
        deleted_tables = ['sources', 'flows']
        failed_tables = ['segments', 'segment_tags']
        remaining_tables = ['segments', 'segment_tags']
        
        result = _log_cleanup_summary(
            initial_tables, deleted_tables, failed_tables, remaining_tables
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_main_success(self):
        """Test main function with successful cleanup."""
        with patch('mgmt.cleanup_database_final.cleanup_database', return_value=True):
            result = await main()
            assert result == 0
    
    @pytest.mark.asyncio
    async def test_main_failure(self):
        """Test main function with failed cleanup."""
        with patch('mgmt.cleanup_database_final.cleanup_database', return_value=False):
            result = await main()
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_main_exception(self):
        """Test main function with exception."""
        with patch('mgmt.cleanup_database_final.cleanup_database', side_effect=Exception("Test error")):
            result = await main()
            assert result == 1


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
