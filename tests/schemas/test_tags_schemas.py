#!/usr/bin/env python3
"""
Tests for Tags Schemas

Tests the tags schema functions in src/vasttams/common/tags/schemas.py
"""

import pytest
import sys
import pyarrow as pa
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.common.tags.schemas import (
    get_tags_schema,
    get_tags_projections
)


class TestTagsSchema:
    """Test tags schema functions"""
    
    def test_get_tags_schema_returns_schema(self):
        """Test that get_tags_schema returns a PyArrow Schema"""
        schema = get_tags_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_tags_schema_has_expected_fields(self):
        """Test that tags schema has expected fields"""
        schema = get_tags_schema()
        field_names = [field.name for field in schema]
        expected_fields = [
            "id", "entity_type", "entity_id", "tag_name", "tag_value",
            "created_at", "updated_at", "created_date", "updated_date", "deleted_date"
        ]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in tags schema"
    
    def test_get_tags_schema_field_types(self):
        """Test that tags schema fields have correct types"""
        schema = get_tags_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["entity_type"] == pa.string()
        assert field_dict["entity_id"] == pa.string()
        assert field_dict["tag_name"] == pa.string()
        assert field_dict["tag_value"] == pa.string()
        assert isinstance(field_dict["created_at"], pa.TimestampType)
        assert isinstance(field_dict["updated_at"], pa.TimestampType)
    
    def test_get_tags_schema_all_fields_nullable(self):
        """Test that all fields in tags schema are nullable"""
        schema = get_tags_schema()
        for field in schema:
            assert field.nullable, f"Field {field.name} is not nullable"
    
    def test_get_tags_projections_returns_list(self):
        """Test that get_tags_projections returns a list"""
        projections = get_tags_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_get_tags_projections_are_lists(self):
        """Test that projections are lists of column names"""
        projections = get_tags_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_tags_projections_contains_expected_projections(self):
        """Test that tags projections contain expected column combinations"""
        projections = get_tags_projections()
        all_columns = [col for proj in projections for col in proj]
        
        # Should have common query patterns
        assert "id" in all_columns
        assert "entity_type" in all_columns
        assert "entity_id" in all_columns
        assert "tag_name" in all_columns
    
    def test_get_tags_projections_entity_type_entity_id(self):
        """Test that there's a projection for entity_type and entity_id"""
        projections = get_tags_projections()
        # Should have projection for entity_type + entity_id
        has_entity_projection = any(
            "entity_type" in proj and "entity_id" in proj
            for proj in projections
        )
        assert has_entity_projection, "Missing projection for entity_type + entity_id"

