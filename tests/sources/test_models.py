#!/usr/bin/env python3
"""
Model Unit Tests for Sources Module

Unit tests for Source Pydantic models (no API calls, no database).
Tests model validation, field constraints, and data structures.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.sources.models import Source
from vasttams.common.filters import SourceFilters
from vasttams.common.models import Tags

import logging
logger = logging.getLogger(__name__)


class TestSourceModels:
    """Test Source Pydantic models - unit tests only (no API, no DB)"""
    
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



