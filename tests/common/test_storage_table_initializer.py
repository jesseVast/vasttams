#!/usr/bin/env python3
"""
Tests for Storage Table Initializer

Tests the table initializer in src/vasttams/common/storage/table_initializer.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.common.storage.table_initializer import TAMSTableInitializer


class TestTAMSTableInitializer:
    """Test TAMSTableInitializer class"""
    
    def test_initializer_creation(self):
        """Test creating a table initializer"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        assert initializer.vast_db == mock_vast_db
        assert initializer.settings is not None
        assert initializer.table_schemas is not None
        assert initializer.table_projections is not None
    
    @pytest.mark.asyncio
    async def test_initialize_all_tables_calls_create_table(self):
        """Test that initialize_all_tables calls _create_table_with_projections"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        
        # Mock the _create_table_with_projections method
        initializer._create_table_with_projections = AsyncMock(return_value=True)
        
        results = await initializer.initialize_all_tables()
        
        # Should have called _create_table_with_projections for each table
        assert initializer._create_table_with_projections.called
        assert isinstance(results, dict)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_initialize_all_tables_handles_errors(self):
        """Test that initialize_all_tables handles errors gracefully"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        
        # Mock to raise an error for one table - use a more descriptive error message
        async def mock_create(table_name, force):
            if table_name == "sources":
                raise Exception("Table creation failed: sources table initialization error")
            return True
        
        initializer._create_table_with_projections = AsyncMock(side_effect=mock_create)
        
        results = await initializer.initialize_all_tables()
        
        # Should have results for all tables, with sources marked as False
        assert isinstance(results, dict)
        if "sources" in results:
            # If sources was in the table list, it should be False due to error
            assert results["sources"] is False
    
    def test_initializer_has_table_schemas(self):
        """Test that initializer has table schemas loaded"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        assert isinstance(initializer.table_schemas, dict)
        assert len(initializer.table_schemas) > 0
    
    def test_initializer_has_table_projections(self):
        """Test that initializer has table projections loaded"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        assert isinstance(initializer.table_projections, dict)
        assert len(initializer.table_projections) > 0

