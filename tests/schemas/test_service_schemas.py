#!/usr/bin/env python3
"""
Tests for Service Schemas

Tests the service schema functions in src/vasttams/service/schemas.py
"""

import pytest
import sys
import pyarrow as pa
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.service.schemas import (
    get_webhooks_schema,
    get_deletion_requests_schema,
    get_webhooks_projections,
    get_deletion_requests_projections
)


class TestWebhooksSchema:
    """Test webhooks schema functions"""
    
    def test_get_webhooks_schema_returns_schema(self):
        """Test that get_webhooks_schema returns a PyArrow Schema"""
        schema = get_webhooks_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_webhooks_schema_has_expected_fields(self):
        """Test that webhooks schema has expected fields"""
        schema = get_webhooks_schema()
        field_names = [field.name for field in schema]
        expected_fields = [
            "id", "url", "api_key_name", "api_key_value", "events",
            "flow_ids", "source_ids", "flow_collected_by_ids", "source_collected_by_ids",
            "accept_get_urls", "accept_storage_ids", "presigned", "verbose_storage",
            "tags", "enabled", "created", "updated"
        ]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in webhooks schema"
    
    def test_get_webhooks_schema_field_types(self):
        """Test that webhooks schema fields have correct types"""
        schema = get_webhooks_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["url"] == pa.string()
        assert field_dict["enabled"] == pa.bool_()
        assert isinstance(field_dict["created"], pa.TimestampType)
    
    def test_get_webhooks_projections_returns_list(self):
        """Test that get_webhooks_projections returns a list"""
        projections = get_webhooks_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_get_webhooks_projections_are_lists(self):
        """Test that projections are lists of column names"""
        projections = get_webhooks_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_webhooks_projections_contains_expected(self):
        """Test that webhooks projections contain expected columns"""
        projections = get_webhooks_projections()
        all_columns = [col for proj in projections for col in proj]
        assert "id" in all_columns
        assert "enabled" in all_columns


class TestDeletionRequestsSchema:
    """Test deletion requests schema functions"""
    
    def test_get_deletion_requests_schema_returns_schema(self):
        """Test that get_deletion_requests_schema returns a PyArrow Schema"""
        schema = get_deletion_requests_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_deletion_requests_schema_has_expected_fields(self):
        """Test that deletion_requests schema has expected fields"""
        schema = get_deletion_requests_schema()
        field_names = [field.name for field in schema]
        expected_fields = [
            "id", "flow_id", "timerange_to_delete", "delete_flow",
            "status", "timerange_remaining", "created", "created_by",
            "updated", "expiry", "error"
        ]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in deletion_requests schema"
    
    def test_get_deletion_requests_schema_field_types(self):
        """Test that deletion_requests schema fields have correct types"""
        schema = get_deletion_requests_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["flow_id"] == pa.string()
        assert field_dict["delete_flow"] == pa.bool_()
        assert isinstance(field_dict["created"], pa.TimestampType)
    
    def test_get_deletion_requests_projections_returns_list(self):
        """Test that get_deletion_requests_projections returns a list"""
        projections = get_deletion_requests_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0
    
    def test_get_deletion_requests_projections_are_lists(self):
        """Test that projections are lists of column names"""
        projections = get_deletion_requests_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_deletion_requests_projections_contains_expected(self):
        """Test that deletion_requests projections contain expected columns"""
        projections = get_deletion_requests_projections()
        all_columns = [col for proj in projections for col in proj]
        assert "id" in all_columns
        assert "status" in all_columns

