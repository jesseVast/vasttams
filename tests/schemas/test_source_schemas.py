#!/usr/bin/env python3
"""
Schema Tests for Sources

Tests sources/schemas.py PyArrow schema definitions.
"""

import pytest
import sys
from pathlib import Path
import pyarrow as pa

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.sources.schemas import (
    get_sources_schema,
    get_source_collections_schema,
    get_sources_projections,
    get_source_collections_projections
)


class TestSourceSchemas:
    """Test source schema definitions"""
    
    def test_get_sources_schema(self):
        """Test get_sources_schema returns valid PyArrow schema"""
        schema = get_sources_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "format" in schema.names
        assert "label" in schema.names
    
    def test_get_source_collections_schema(self):
        """Test get_source_collections_schema returns valid PyArrow schema"""
        schema = get_source_collections_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "source_id" in schema.names
        assert "collection_name" in schema.names
    
    def test_get_sources_projections(self):
        """Test get_sources_projections returns list of projections"""
        projections = get_sources_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
        assert all(isinstance(proj, list) for proj in projections)
    
    def test_get_source_collections_projections(self):
        """Test get_source_collections_projections returns list of projections"""
        projections = get_source_collections_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_schema_field_nullable(self):
        """Test schema fields are nullable (VAST requirement)"""
        schema = get_sources_schema()
        for field in schema:
            assert field.nullable is True, f"Field {field.name} should be nullable"

