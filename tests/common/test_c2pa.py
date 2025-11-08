#!/usr/bin/env python3
"""
C2PA Validation Tests

Tests for C2PA provenance validation (App Note 0011).
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.common.c2pa_utils import (
    C2PAValidator,
    validate_c2pa_in_metadata,
    extract_c2pa_provenance
)

import logging
logger = logging.getLogger(__name__)


class TestC2PAValidation:
    """Test C2PA validation functions"""
    
    def test_validate_valid_c2pa_metadata(self):
        """Test validation with valid C2PA metadata"""
        metadata = {
            "c2pa": {
                "version": "1.0",
                "assertions": [
                    {
                        "assertion_type": "claim",
                        "assertion_data": {
                            "source": "camera_01",
                            "timestamp": "2024-01-01T00:00:00Z"
                        }
                    }
                ],
                "metadata": {
                    "creator": "BBC TAMS"
                }
            }
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert is_valid, f"Valid C2PA metadata was rejected: {error}"
    
    def test_validate_invalid_c2pa_metadata_missing_version(self):
        """Test validation with C2PA metadata missing version"""
        metadata = {
            "c2pa": {
                "assertions": []
            }
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert not is_valid, "Should reject C2PA metadata without version"
        assert error is not None
    
    def test_validate_invalid_c2pa_metadata_missing_assertions(self):
        """Test validation with C2PA metadata missing assertions"""
        metadata = {
            "c2pa": {
                "version": "1.0"
            }
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert not is_valid, "Should reject C2PA metadata without assertions"
    
    def test_validate_c2pa_metadata_malformed_structure(self):
        """Test validation with malformed C2PA structure"""
        metadata = {
            "c2pa": "invalid_string"
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert not is_valid, "Should reject malformed C2PA structure"
    
    def test_validate_c2pa_assertion_missing_type(self):
        """Test validation with assertion missing type"""
        metadata = {
            "c2pa": {
                "version": "1.0",
                "assertions": [
                    {
                        "assertion_data": {
                            "data": "test"
                        }
                        # Missing assertion_type
                    }
                ]
            }
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert not is_valid, "Should reject assertion without assertion_type"
    
    def test_validate_c2pa_assertion_missing_data(self):
        """Test validation with assertion missing data"""
        metadata = {
            "c2pa": {
                "version": "1.0",
                "assertions": [
                    {
                        "assertion_type": "claim"
                        # Missing assertion_data
                    }
                ]
            }
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert not is_valid, "Should reject assertion without assertion_data"
    
    def test_validate_metadata_without_c2pa(self):
        """Test validation of metadata without C2PA"""
        metadata = {
            "some_other_field": "value"
        }
        
        is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)
        assert is_valid, "Metadata without C2PA should be valid"
        assert error is None
    
    def test_extract_c2pa_from_tags(self):
        """Test extracting C2PA manifest from tags"""
        tags = {
            "c2pa": {
                "version": "1.0",
                "assertions": [
                    {
                        "assertion_type": "claim",
                        "assertion_data": {
                            "source": "camera_01"
                        }
                    }
                ]
            }
        }
        
        manifest = C2PAValidator.extract_c2pa_from_tags(tags)
        assert manifest is not None
        assert manifest.version == "1.0"
        assert len(manifest.assertions) == 1
    
    def test_extract_c2pa_from_tags_string_json(self):
        """Test extracting C2PA from tags with JSON string"""
        import json
        c2pa_data = {
            "version": "1.0",
            "assertions": [
                {
                    "assertion_type": "claim",
                    "assertion_data": {
                        "source": "camera_01"
                    }
                }
            ]
        }
        
        tags = {
            "c2pa": json.dumps(c2pa_data)
        }
        
        manifest = C2PAValidator.extract_c2pa_from_tags(tags)
        assert manifest is not None
        assert manifest.version == "1.0"
    
    def test_extract_c2pa_from_tags_missing(self):
        """Test extracting C2PA from tags without C2PA data"""
        tags = {
            "other_field": "value"
        }
        
        manifest = C2PAValidator.extract_c2pa_from_tags(tags)
        assert manifest is None
    
    def test_validate_c2pa_chain_valid(self):
        """Test C2PA chain validation with valid chain"""
        from vasttamsserver.common.c2pa_utils import C2PAAssertion, C2PAManifest
        
        assertions = [
            C2PAAssertion(
                assertion_type="claim",
                assertion_data={"data": "test"}
            )
        ]
        
        manifest = C2PAManifest(
            version="1.0",
            assertions=assertions
        )
        
        is_valid, error = C2PAValidator.validate_c2pa_chain(manifest)
        assert is_valid, f"Valid chain rejected: {error}"
    
    def test_convenience_function(self):
        """Test the convenience validate_c2pa_in_metadata function"""
        metadata = {
            "c2pa": {
                "version": "1.0",
                "assertions": [
                    {
                        "assertion_type": "claim",
                        "assertion_data": {}
                    }
                ]
            }
        }
        
        is_valid = validate_c2pa_in_metadata(metadata)
        assert is_valid
        
        # Test with invalid metadata
        metadata_invalid = {
            "c2pa": "invalid"
        }
        
        is_valid = validate_c2pa_in_metadata(metadata_invalid)
        assert not is_valid

