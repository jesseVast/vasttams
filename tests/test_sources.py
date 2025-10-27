#!/usr/bin/env python3
"""
Tests for Sources Module

Comprehensive tests for the refactored sources module including:
- Router endpoints
- Service layer
- Models validation
- Integration with config.json
"""

import pytest
import sys
import os
import json
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import only specific modules to avoid loading full app
from vasttams.sources import models as source_models
from vasttams.common import filters as common_filters
from vasttams.common import models as common_models
from vasttams.core import config as core_config

# Use aliases for cleaner access
Source = source_models.Source
SourceFilters = common_filters.SourceFilters
Tags = common_models.Tags
get_settings = core_config.get_settings

import logging
logger = logging.getLogger(__name__)


class TestSourceModels:
    """Test Source Pydantic models"""
    
    def test_source_creation_minimal(self):
        """Test creating a source with minimal required fields"""
        source = Source(
            id="550e8400-e29b-41d4-a716-446655440000",
            format="urn:x-nmos:format:video"
        )
        assert source.id == "550e8400-e29b-41d4-a716-446655440000"
        assert source.format == "urn:x-nmos:format:video"
        assert source.label is None
        assert source.description is None
    
    def test_source_creation_with_all_fields(self):
        """Test creating a source with all fields"""
        from datetime import datetime, timezone
        
        source = Source(
            id="550e8400-e29b-41d4-a716-446655440000",
            format="urn:x-nmos:format:video",
            label="Test Source",
            description="A test source",
            created_by="test-user",
            updated_by="test-user",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
            tags=Tags({"environment": "test", "priority": "high"})
        )
        assert source.label == "Test Source"
        assert source.description == "A test source"
        assert source.tags is not None
        assert "environment" in source.tags.keys()
    
    def test_source_uuid_validation(self):
        """Test that source ID must be a valid UUID"""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            Source(id="invalid-uuid", format="urn:x-nmos:format:video")
    
    def test_source_format_validation(self):
        """Test that source format must be a valid content format URN"""
        # Valid format
        source = Source(
            id="550e8400-e29b-41d4-a716-446655440000",
            format="urn:x-nmos:format:video"
        )
        assert source.format == "urn:x-nmos:format:video"
        
        # Test invalid format (if validation exists)
        with pytest.raises(ValueError):
            Source(
                id="550e8400-e29b-41d4-a716-446655440000",
                format="invalid-format"
            )


class TestSourceFilters:
    """Test Source filter models"""
    
    def test_source_filters_creation(self):
        """Test creating source filters"""
        filters = SourceFilters(
            label="test-source",
            format="urn:x-nmos:format:video",
            limit=10
        )
        assert filters.label == "test-source"
        assert filters.format == "urn:x-nmos:format:video"
        assert filters.limit == 10
    
    def test_source_filters_with_tag_filters(self):
        """Test source filters with tag filtering (TAMS 8.0)"""
        filters = SourceFilters(
            label="test-source",
            limit=10,
            tag_filters={"environment": "test", "priority": ["high", "medium"]},
            tag_exists_filters={"location": True}
        )
        assert len(filters.tag_filters) == 2
        assert filters.tag_exists_filters == {"location": True}
    
    def test_source_filters_limit_validation(self):
        """Test that limit must be within valid range"""
        with pytest.raises(ValueError):
            SourceFilters(limit=0)
        
        with pytest.raises(ValueError):
            SourceFilters(limit=1001)


class TestSourceRouter:
    """Test Source router endpoints using HTTP client"""
    
    @pytest.fixture
    def api_base_url(self):
        """Get API base URL from config"""
        config = get_settings()
        return f"http://{config.host}:{config.port}"
    
    def test_placeholder(self, api_base_url):
        """Placeholder test for router endpoints"""
        # TODO: Add actual HTTP tests
        # These tests will use the API client to test endpoints
        # against a running server instance
        pass


class TestSourceServiceIntegration:
    """Test Source service integration with VAST database"""
    
    @pytest.fixture
    def config(self):
        """Get configuration from config.json"""
        return get_settings()
    
    def test_placeholder(self, config):
        """Placeholder test for service integration"""
        # TODO: Add actual integration tests
        # These tests will test the service layer with actual
        # VAST database connections
        assert config is not None  # Config is loaded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

