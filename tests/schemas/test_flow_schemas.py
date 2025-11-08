#!/usr/bin/env python3
"""
Schema Tests for Flows

Tests flows/schemas.py PyArrow schema definitions.
"""

import pytest
import sys
from pathlib import Path
import pyarrow as pa

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.flows.schemas import (
    get_flows_schema,
    get_flow_collections_schema,
    get_flow_object_references_schema,
    get_flows_projections,
    get_flow_collections_projections,
    get_flow_object_references_projections
)


class TestFlowSchemas:
    """Test flow schema definitions"""
    
    def test_get_flows_schema(self):
        """Test get_flows_schema returns valid PyArrow schema"""
        schema = get_flows_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "source_id" in schema.names
        assert "format" in schema.names
        assert "vfr" in schema.names  # TAMS 8.0 VFR support
    
    def test_get_flow_collections_schema(self):
        """Test get_flow_collections_schema returns valid PyArrow schema"""
        schema = get_flow_collections_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "flow_id" in schema.names
        assert "collection_name" in schema.names
    
    def test_get_flow_object_references_schema(self):
        """Test get_flow_object_references_schema returns valid PyArrow schema"""
        schema = get_flow_object_references_schema()
        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "flow_id" in schema.names
        assert "object_id" in schema.names
    
    def test_get_flows_projections(self):
        """Test get_flows_projections returns list of projections"""
        projections = get_flows_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
        assert all(isinstance(proj, list) for proj in projections)
    
    def test_get_flow_collections_projections(self):
        """Test get_flow_collections_projections returns list of projections"""
        projections = get_flow_collections_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_get_flow_object_references_projections(self):
        """Test get_flow_object_references_projections returns list of projections"""
        projections = get_flow_object_references_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_schema_field_types(self):
        """Test schema field types are correct"""
        schema = get_flows_schema()
        id_field = schema.field("id")
        assert id_field.type == pa.string()
        assert id_field.nullable is True
        
        vfr_field = schema.field("vfr")
        assert vfr_field.type == pa.bool_()
        assert vfr_field.nullable is True

