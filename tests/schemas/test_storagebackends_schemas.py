#!/usr/bin/env python3
"""
Tests for Storage Backends Schemas

Tests the storage backends schema functions in src/vasttams/storagebackends/schemas.py
"""

import pytest
import sys
import pyarrow as pa
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.storagebackends.schemas import (
    get_storage_backends_schema,
    get_storage_backends_projections
)


class TestStorageBackendsSchema:
    """Test storage backends schema functions"""
    
    def test_get_storage_backends_schema_returns_schema(self):
        """Test that get_storage_backends_schema returns a PyArrow Schema"""
        schema = get_storage_backends_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_storage_backends_schema_has_expected_fields(self):
        """Test that storage_backends schema has expected fields"""
        schema = get_storage_backends_schema()
        field_names = [field.name for field in schema]
        expected_fields = ["id", "label", "store_type", "provider", "store_product",
                          "region", "endpoint_url", "access_key", "secret_key",
                          "bucket_name", "default_storage", "created_at", "updated_at"]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in storage_backends schema"
    
    def test_get_storage_backends_schema_field_types(self):
        """Test that storage_backends schema fields have correct types"""
        schema = get_storage_backends_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["label"] == pa.string()
        assert field_dict["default_storage"] == pa.bool_()
        assert isinstance(field_dict["created_at"], pa.TimestampType)
    
    def test_get_storage_backends_projections_returns_list(self):
        """Test that get_storage_backends_projections returns a list"""
        projections = get_storage_backends_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_get_storage_backends_projections_are_lists(self):
        """Test that projections are lists of column names"""
        projections = get_storage_backends_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_storage_backends_projections_contains_id(self):
        """Test that projections contain id field"""
        projections = get_storage_backends_projections()
        all_columns = [col for proj in projections for col in proj]
        assert "id" in all_columns
    
    def test_get_storage_backends_schema_all_fields(self):
        """Test that storage_backends schema has all expected fields"""
        schema = get_storage_backends_schema()
        field_names = [field.name for field in schema]
        # Check all fields from the schema
        assert "root_path" in field_names
        assert "use_ssl" in field_names
        assert "availability_zone" in field_names
    
    def test_get_storage_backends_schema_field_nullability(self):
        """Test that storage_backends schema fields have correct nullability"""
        schema = get_storage_backends_schema()
        # Most fields should be nullable (VAST requirement)
        # But check that bool fields are correct
        field_dict = {field.name: field.nullable for field in schema}
        # Bool fields can be nullable
        assert isinstance(field_dict.get("default_storage"), bool)
        assert isinstance(field_dict.get("use_ssl"), bool)

