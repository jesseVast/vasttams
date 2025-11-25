#!/usr/bin/env python3
"""
Tests for CLI tag parsing functionality in stream_ingestor and folder_ingestor.

Tests the parse_tags() function that handles:
- Comma-separated tags
- Both ':' and '=' as separators
- Values with spaces
"""

import pytest
import sys
from pathlib import Path

# Add apps to path for imports
apps_path = Path(__file__).parent.parent.parent / "apps"
sys.path.insert(0, str(apps_path))


def test_parse_tags_colon_separator():
    """Test parsing tags with colon separator"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = "key1:value1,key2:value2,key3:value3"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }


def test_parse_tags_equals_separator():
    """Test parsing tags with equals separator"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = "key1=value1,key2=value2"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2"
    }


def test_parse_tags_mixed_separators():
    """Test parsing tags with mixed separators"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = "key1:value1,key2=value2,key3:value3"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }


def test_parse_tags_with_spaces():
    """Test parsing tags with values containing spaces"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = "location:New York,status=in progress,owner:John Doe"
    result = parse_tags(tags_str)
    
    assert result == {
        "location": "New York",
        "status": "in progress",
        "owner": "John Doe"
    }


def test_parse_tags_empty_string():
    """Test parsing empty string"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    result = parse_tags("")
    assert result == {}


def test_parse_tags_none():
    """Test parsing None"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    result = parse_tags(None)
    assert result == {}


def test_parse_tags_whitespace_trimming():
    """Test that keys and values are trimmed of whitespace"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = " key1 : value1 , key2 = value2 "
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2"
    }


def test_parse_tags_empty_value():
    """Test parsing tags with empty values"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = "key1:,key2=value2"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "",
        "key2": "value2"
    }


def test_parse_tags_no_separator():
    """Test parsing tags without separator (should be skipped)"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    import logging
    
    # The function logs a warning but doesn't raise, so we just check the result
    tags_str = "key1:value1,invalid_tag,key2=value2"
    result = parse_tags(tags_str)
    
    # Should only include valid tags
    assert "key1" in result
    assert "key2" in result
    assert "invalid_tag" not in result


def test_parse_tags_folder_ingestor():
    """Test that folder_ingestor has the same parse_tags function"""
    from folder_ingestor.folder_ingestor.cli import parse_tags
    
    tags_str = "key1:value1,key2=value2"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2"
    }


def test_parse_tags_complex_values():
    """Test parsing tags with complex values (special characters, numbers, etc.)"""
    from stream_ingestor.stream_ingestor.cli import parse_tags
    
    tags_str = "version:1.2.3,path=/home/user/data,description=Test with numbers 123 and symbols !@#"
    result = parse_tags(tags_str)
    
    assert result == {
        "version": "1.2.3",
        "path": "/home/user/data",
        "description": "Test with numbers 123 and symbols !@#"
    }

