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

from vasttamsserver.common.storage.table_initializer import TAMSTableInitializer


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
    
    @pytest.mark.asyncio
    async def test_create_table_with_projections_success(self):
        """Test creating a table with projections successfully"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = []
        mock_vast_db.create_table.return_value = MagicMock()
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.settings.enable_table_projections = True
        
        success = await initializer._create_table_with_projections("sources", force_recreate=False)
        
        assert success is True
        mock_vast_db.create_table.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_table_with_projections_table_exists(self):
        """Test creating a table when it already exists"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = ["sources"]
        
        initializer = TAMSTableInitializer(mock_vast_db)
        
        success = await initializer._create_table_with_projections("sources", force_recreate=False)
        
        assert success is True
        mock_vast_db.create_table.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_table_with_projections_force_recreate(self):
        """Test creating a table with force_recreate=True"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = ["sources"]
        mock_vast_db.create_table.return_value = MagicMock()
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer._drop_table = AsyncMock(return_value=True)
        initializer.settings.enable_table_projections = True
        
        success = await initializer._create_table_with_projections("sources", force_recreate=True)
        
        assert success is True
        initializer._drop_table.assert_called_once_with("sources")
        mock_vast_db.create_table.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_table_with_projections_no_schema(self):
        """Test creating a table when schema is missing"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {}  # Empty schemas
        
        success = await initializer._create_table_with_projections("nonexistent", force_recreate=False)
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_create_table_with_projections_create_fails(self):
        """Test creating a table when create_table returns None"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = []
        mock_vast_db.create_table.return_value = None
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.settings.enable_table_projections = True
        
        success = await initializer._create_table_with_projections("sources", force_recreate=False)
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_create_table_with_projections_projections_disabled(self):
        """Test creating a table with projections disabled"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = []
        mock_vast_db.create_table.return_value = MagicMock()
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.settings.enable_table_projections = False
        
        success = await initializer._create_table_with_projections("sources", force_recreate=False)
        
        assert success is True
        # Should pass empty projections dict
        mock_vast_db.create_table.assert_called_once()
        call_args = mock_vast_db.create_table.call_args
        # create_table is called with (table_name, schema, projections) as positional args
        # Check the third positional argument (projections)
        assert len(call_args[0]) >= 3
        projections_arg = call_args[0][2]
        assert projections_arg == {}
    
    @pytest.mark.asyncio
    async def test_drop_table(self):
        """Test dropping a table"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        
        success = await initializer._drop_table("sources")
        
        # Currently returns False as drop_table is not implemented
        assert success is False
    
    @pytest.mark.asyncio
    async def test_add_table_projections(self):
        """Test adding projections to a table"""
        mock_vast_db = MagicMock()
        mock_vast_db.add_projection = MagicMock()
        
        initializer = TAMSTableInitializer(mock_vast_db)
        
        projections = [["id"], ["id", "name"]]
        success = await initializer._add_table_projections("sources", projections)
        
        assert success is True
        assert mock_vast_db.add_projection.call_count == 2
    
    @pytest.mark.asyncio
    async def test_add_table_projections_empty(self):
        """Test adding empty projections list"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        
        success = await initializer._add_table_projections("sources", [])
        
        assert success is True
        mock_vast_db.add_projection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_table_projections_partial_failure(self):
        """Test adding projections when some fail"""
        mock_vast_db = MagicMock()
        mock_vast_db.add_projection.side_effect = [None, Exception("Failed")]
        
        initializer = TAMSTableInitializer(mock_vast_db)
        
        projections = [["id"], ["id", "name"]]
        success = await initializer._add_table_projections("sources", projections)
        
        # Should still return True even if some projections fail
        assert success is True
    
    @pytest.mark.asyncio
    async def test_verify_tables_exist_all_exist(self):
        """Test verifying tables when all exist"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = ["sources", "flows", "segments"]
        
        initializer = TAMSTableInitializer(mock_vast_db)
        # Set a known set of required tables
        initializer.table_schemas = {"sources": None, "flows": None, "segments": None}
        
        results = await initializer.verify_tables_exist()
        
        assert isinstance(results, dict)
        assert results.get("sources") is True
        assert results.get("flows") is True
        assert results.get("segments") is True
    
    @pytest.mark.asyncio
    async def test_verify_tables_exist_some_missing(self):
        """Test verifying tables when some are missing"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.return_value = ["sources", "flows"]
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": None, "flows": None, "segments": None}
        
        results = await initializer.verify_tables_exist()
        
        assert results.get("sources") is True
        assert results.get("flows") is True
        assert results.get("segments") is False
    
    @pytest.mark.asyncio
    async def test_verify_tables_exist_exception(self):
        """Test verifying tables when list_tables raises exception"""
        mock_vast_db = MagicMock()
        mock_vast_db.list_tables.side_effect = Exception("Database error")
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": None}
        
        results = await initializer.verify_tables_exist()
        
        assert isinstance(results, dict)
        assert results.get("sources") is False
    
    @pytest.mark.asyncio
    async def test_get_table_info(self):
        """Test getting table information"""
        mock_vast_db = MagicMock()
        mock_vast_db.get_table_stats.return_value = {"row_count": 100}
        mock_vast_db.get_table_projections.return_value = ["proj1", "proj2"]
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": MagicMock()}
        # Mock schema length
        initializer.table_schemas["sources"] = MagicMock()
        type(initializer.table_schemas["sources"]).__len__ = lambda x: 5
        
        info = await initializer.get_table_info()
        
        assert isinstance(info, dict)
        assert "sources" in info
        assert info["sources"]["exists"] is True
        assert "stats" in info["sources"]
        assert "projections" in info["sources"]
    
    @pytest.mark.asyncio
    async def test_get_table_info_exception(self):
        """Test getting table info when exception occurs"""
        mock_vast_db = MagicMock()
        mock_vast_db.get_table_stats.side_effect = Exception("Error")
        
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": MagicMock()}
        
        info = await initializer.get_table_info()
        
        assert isinstance(info, dict)
        assert "sources" in info
        assert info["sources"]["exists"] is False
        assert "error" in info["sources"]
    
    def test_get_required_tables(self):
        """Test getting list of required tables"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": None, "flows": None, "segments": None}
        
        tables = initializer.get_required_tables()
        
        assert isinstance(tables, list)
        assert "sources" in tables
        assert "flows" in tables
        assert "segments" in tables
    
    def test_get_table_schema(self):
        """Test getting schema for a specific table"""
        mock_vast_db = MagicMock()
        mock_schema = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": mock_schema}
        
        schema = initializer.get_table_schema("sources")
        
        assert schema == mock_schema
    
    def test_get_table_schema_not_found(self):
        """Test getting schema for non-existent table"""
        mock_vast_db = MagicMock()
        initializer = TAMSTableInitializer(mock_vast_db)
        initializer.table_schemas = {"sources": MagicMock()}
        
        schema = initializer.get_table_schema("nonexistent")
        
        assert schema is None

