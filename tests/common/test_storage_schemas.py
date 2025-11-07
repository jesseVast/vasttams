#!/usr/bin/env python3
"""
Tests for Storage Schemas

Tests the storage schema functions in src/vasttams/common/storage/schemas.py
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.common.storage.schemas import get_tams_table_schemas, get_table_projections


class TestStorageSchemas:
    """Test storage schema functions"""
    
    def test_get_tams_table_schemas_returns_dict(self):
        """Test that get_tams_table_schemas returns a dictionary"""
        schemas = get_tams_table_schemas()
        assert isinstance(schemas, dict)
        assert len(schemas) > 0
    
    def test_get_tams_table_schemas_contains_expected_tables(self):
        """Test that schemas contain expected table names"""
        schemas = get_tams_table_schemas()
        expected_tables = ["sources", "flows", "segments", "objects", "webhooks"]
        for table in expected_tables:
            assert table in schemas, f"Table {table} not found in schemas"
    
    def test_get_tams_table_schemas_schemas_are_pyarrow(self):
        """Test that schemas are PyArrow Schema objects"""
        import pyarrow as pa
        schemas = get_tams_table_schemas()
        for table_name, schema in schemas.items():
            assert isinstance(schema, pa.Schema), f"Schema for {table_name} is not a PyArrow Schema"
    
    def test_get_table_projections_returns_dict(self):
        """Test that get_table_projections returns a dictionary"""
        projections = get_table_projections()
        assert isinstance(projections, dict)
        assert len(projections) > 0
    
    def test_get_table_projections_contains_expected_tables(self):
        """Test that projections contain expected table names"""
        projections = get_table_projections()
        expected_tables = ["sources", "flows", "segments", "objects"]
        for table in expected_tables:
            assert table in projections, f"Table {table} not found in projections"
    
    def test_get_table_projections_are_lists(self):
        """Test that projections are lists of lists"""
        projections = get_table_projections()
        for table_name, proj_list in projections.items():
            assert isinstance(proj_list, list), f"Projections for {table_name} is not a list"
            if len(proj_list) > 0:
                assert isinstance(proj_list[0], list), f"First projection for {table_name} is not a list"

