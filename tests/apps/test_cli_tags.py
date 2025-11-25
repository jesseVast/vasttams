#!/usr/bin/env python3
"""
Tests for CLI tag parsing functionality in stream_ingestor and folder_ingestor.

Tests the parse_tags() function that handles:
- Comma-separated tags
- Both ':' and '=' as separators
- Values with spaces

Note: We copy the parse_tags function here to avoid importing the full CLI modules
which have external dependencies (jthaloor-ffmpeg).
"""

import pytest
import logging

logger = logging.getLogger(__name__)


def parse_tags(tags_str: str) -> dict:
    """
    Parse tags from CLI string format.
    
    Supports both ':' and '=' as key-value separators.
    Format: 'key1:value1,key2=value2,key3:value with spaces'
    Values can contain spaces and will be preserved as-is.
    
    Args:
        tags_str: Comma-separated tags string
        
    Returns:
        Dictionary of tag key-value pairs
    """
    tags = {}
    if not tags_str:
        return tags
    
    # Split by comma to get individual tags
    tag_pairs = tags_str.split(',')
    
    for tag_pair in tag_pairs:
        tag_pair = tag_pair.strip()
        if not tag_pair:
            continue
        
        # Try to split by ':' first, then '=' if ':' not found
        if ':' in tag_pair:
            # Split by ':' - take first occurrence as separator
            parts = tag_pair.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
        elif '=' in tag_pair:
            # Split by '=' - take first occurrence as separator
            parts = tag_pair.split('=', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
        else:
            # No separator found, treat as key with empty value
            logger.warning(f"Tag '{tag_pair}' has no separator (':' or '='), skipping")
            continue
        
        if key:
            tags[key] = value
    
    return tags


def test_parse_tags_colon_separator():
    """Test parsing tags with colon separator"""
    tags_str = "key1:value1,key2:value2,key3:value3"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }


def test_parse_tags_equals_separator():
    """Test parsing tags with equals separator"""
    tags_str = "key1=value1,key2=value2"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2"
    }


def test_parse_tags_mixed_separators():
    """Test parsing tags with mixed separators"""
    tags_str = "key1:value1,key2=value2,key3:value3"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }


def test_parse_tags_with_spaces():
    """Test parsing tags with values containing spaces"""
    tags_str = "location:New York,status=in progress,owner:John Doe"
    result = parse_tags(tags_str)
    
    assert result == {
        "location": "New York",
        "status": "in progress",
        "owner": "John Doe"
    }


def test_parse_tags_empty_string():
    """Test parsing empty string"""
    result = parse_tags("")
    assert result == {}


def test_parse_tags_none():
    """Test parsing None"""
    result = parse_tags(None)
    assert result == {}


def test_parse_tags_whitespace_trimming():
    """Test that keys and values are trimmed of whitespace"""
    tags_str = " key1 : value1 , key2 = value2 "
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "value1",
        "key2": "value2"
    }


def test_parse_tags_empty_value():
    """Test parsing tags with empty values"""
    tags_str = "key1:,key2=value2"
    result = parse_tags(tags_str)
    
    assert result == {
        "key1": "",
        "key2": "value2"
    }


def test_parse_tags_no_separator():
    """Test parsing tags without separator (should be skipped)"""
    # The function logs a warning but doesn't raise, so we just check the result
    tags_str = "key1:value1,invalid_tag,key2=value2"
    result = parse_tags(tags_str)
    
    # Should only include valid tags
    assert "key1" in result
    assert "key2" in result
    assert "invalid_tag" not in result


def test_parse_tags_complex_values():
    """Test parsing tags with complex values (special characters, numbers, etc.)"""
    tags_str = "version:1.2.3,path=/home/user/data,description=Test with numbers 123 and symbols !@#"
    result = parse_tags(tags_str)
    
    assert result == {
        "version": "1.2.3",
        "path": "/home/user/data",
        "description": "Test with numbers 123 and symbols !@#"
    }

