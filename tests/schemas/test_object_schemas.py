#!/usr/bin/env python3
"""
Schema Tests for Objects

Tests objects/schemas.py PyArrow schema definitions.
"""

import pytest
import sys
from pathlib import Path
import pyarrow as pa

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.objects.schemas import (
    get_objects_schema,
    get_object_instances_schema,
    get_objects_projections,
    get_object_instances_projections
)


class TestObjectSchemas:
    """Test object schema definitions"""
    
    def test_get_objects_schema(self):
        """Test get_objects_schema returns valid PyArrow schema"""
        schema = get_objects_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "timerange" in schema.names  # TAMS 8.0 requirement
        assert "size" in schema.names
    
    def test_get_object_instances_schema(self):
        """Test get_object_instances_schema returns valid PyArrow schema"""
        schema = get_object_instances_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "object_id" in schema.names
        assert "storage_id" in schema.names
        assert "url" in schema.names
    
    def test_get_objects_projections(self):
        """Test get_objects_projections returns list of projections"""
        projections = get_objects_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
        assert all(isinstance(proj, list) for proj in projections)
    
    def test_get_object_instances_projections(self):
        """Test get_object_instances_projections returns list of projections"""
        projections = get_object_instances_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_schema_field_nullable(self):
        """Test schema fields are nullable (VAST requirement)"""
        schema = get_objects_schema()
        for field in schema:
            assert field.nullable is True, f"Field {field.name} should be nullable"

