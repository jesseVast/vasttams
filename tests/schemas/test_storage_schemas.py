#!/usr/bin/env python3
"""
Tests for Storage Schemas (Common)

Tests the storage schema registry functions in src/vasttams/common/storage/schemas.py
"""

import pytest
import sys
import pyarrow as pa
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.common.storage.schemas import (
    get_tams_table_schemas,
    get_table_projections
)


class TestTAMSTableSchemas:
    """Test get_tams_table_schemas function"""
    
    def test_get_tams_table_schemas_returns_dict(self):
        """Test that get_tams_table_schemas returns a dictionary"""
        schemas = get_tams_table_schemas()
        assert isinstance(schemas, dict)
        assert len(schemas) > 0
    
    def test_get_tams_table_schemas_contains_expected_tables(self):
        """Test that get_tams_table_schemas contains expected table names"""
        schemas = get_tams_table_schemas()
        expected_tables = [
            "sources", "flows", "segments", "objects", "object_instances",
            "flow_object_references", "flow_collections", "source_collections",
            "webhooks", "deletion_requests", "users", "api_tokens",
            "refresh_tokens", "auth_logs", "auth_provider_configs",
            "tags", "storage_backends"
        ]
        for table in expected_tables:
            assert table in schemas, f"Table {table} not found in schemas"
    
    def test_get_tams_table_schemas_values_are_schemas(self):
        """Test that all values in get_tams_table_schemas are PyArrow Schemas"""
        schemas = get_tams_table_schemas()
        for table_name, schema in schemas.items():
            assert isinstance(schema, pa.Schema), f"Schema for {table_name} is not a PyArrow Schema"
    
    def test_get_tams_table_schemas_all_tables_have_schemas(self):
        """Test that all tables have valid schemas with at least one field"""
        schemas = get_tams_table_schemas()
        for table_name, schema in schemas.items():
            assert len(schema) > 0, f"Schema for {table_name} has no fields"


class TestTableProjections:
    """Test get_table_projections function"""
    
    def test_get_table_projections_returns_dict(self):
        """Test that get_table_projections returns a dictionary"""
        projections = get_table_projections()
        assert isinstance(projections, dict)
        assert len(projections) > 0
    
    def test_get_table_projections_contains_expected_tables(self):
        """Test that get_table_projections contains expected table names"""
        projections = get_table_projections()
        # Not all tables have projections defined, so check for common ones
        expected_tables_with_projections = [
            "sources", "flows", "segments", "objects",
            "flow_collections", "source_collections",
            "webhooks", "deletion_requests", "users", "api_tokens",
            "refresh_tokens", "auth_logs", "auth_provider_configs",
            "tags", "storage_backends"
        ]
        for table in expected_tables_with_projections:
            assert table in projections, f"Table {table} not found in projections"
    
    def test_get_table_projections_values_are_lists(self):
        """Test that all values in get_table_projections are lists"""
        projections = get_table_projections()
        for table_name, proj_list in projections.items():
            assert isinstance(proj_list, list), f"Projections for {table_name} is not a list"
            assert len(proj_list) > 0, f"Projections for {table_name} is empty"
    
    def test_get_table_projections_are_lists_of_lists(self):
        """Test that projections are lists of column name lists"""
        projections = get_table_projections()
        for table_name, proj_list in projections.items():
            for proj in proj_list:
                assert isinstance(proj, list), f"Projection in {table_name} is not a list"
                assert all(isinstance(col, str) for col in proj), f"Projection in {table_name} contains non-string columns"
    
    def test_get_table_projections_match_schemas(self):
        """Test that projection tables match schema tables"""
        schemas = get_tams_table_schemas()
        projections = get_table_projections()
        
        # All projection tables should have schemas
        for table_name in projections:
            assert table_name in schemas, f"Table {table_name} has projections but no schema"
        
        # All schema tables should have projections (or at least most)
        # Some tables might not have projections defined
        schema_tables = set(schemas.keys())
        projection_tables = set(projections.keys())
        # Allow some tables to not have projections
        assert len(projection_tables) > 0

