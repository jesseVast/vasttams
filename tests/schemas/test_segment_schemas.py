#!/usr/bin/env python3
"""
Schema Tests for Segments

Tests segments/schemas.py PyArrow schema definitions.
"""

import pytest
import sys
from pathlib import Path
import pyarrow as pa

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.segments.schemas import (
    get_segments_schema,
    get_segments_projections
)


class TestSegmentSchemas:
    """Test segment schema definitions"""
    
    def test_get_segments_schema(self):
        """Test get_segments_schema returns valid PyArrow schema"""
        schema = get_segments_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "flow_id" in schema.names
        assert "object_id" in schema.names
        assert "timerange_start" in schema.names
        assert "timerange_end" in schema.names
        assert "get_urls" in schema.names
    
    def test_get_segments_projections(self):
        """Test get_segments_projections returns list of projections"""
        projections = get_segments_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
        assert all(isinstance(proj, list) for proj in projections)
        # Should include timerange projections
        assert any("timerange_start" in proj for proj in projections)
        assert any("timerange_end" in proj for proj in projections)
    
    def test_schema_field_nullable(self):
        """Test schema fields are nullable (VAST requirement)"""
        schema = get_segments_schema()
        for field in schema:
            assert field.nullable is True, f"Field {field.name} should be nullable"
    
    def test_schema_timerange_fields(self):
        """Test timerange fields are properly defined"""
        schema = get_segments_schema()
        timerange_start = schema.field("timerange_start")
        timerange_end = schema.field("timerange_end")
        assert timerange_start.type == pa.string()
        assert timerange_end.type == pa.string()

