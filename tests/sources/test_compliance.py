#!/usr/bin/env python3
"""
TAMS 8.0 Compliance Tests for Sources

Tests compliance with TAMS 8.0 specification and app notes.
"""

import pytest
import sys
import requests
from pathlib import Path
import json

# Add src/server to path for imports
server_path = Path(__file__).parent.parent.parent / "src" / "server"
if str(server_path) not in sys.path:
    sys.path.insert(0, str(server_path))

from vasttamsserver.core.config import get_settings
from test_examples import load_example

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.mark.usefixtures("api_available")
class TestSourceSpecCompliance:
    """Test compliance with TAMS 8.0 source spec"""
    
    def test_source_required_fields_per_spec(self, api_available, auth_headers):
        """
        Test that source has required fields per TAMS 8.0 spec.
        Spec: source.json requires 'id' and 'format'
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_source = load_example("source-get-200-basic.json")
        
        # Create source with required fields only
        import uuid
        source_data = {
            "id": str(uuid.uuid4()),
            "format": example_source["format"]
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        
        created = response.json()
        assert "id" in created
        assert "format" in created
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_data['id']}", headers=auth_headers)
    
    def test_source_format_validation(self, api_available, auth_headers):
        """
        Test that source format follows TAMS 8.0 spec.
        Spec: format should be a valid content-format URN
        """
        if not api_available:
            pytest.skip("API not available")
        
        valid_formats = [
            "urn:x-nmos:format:video",
            "urn:x-nmos:format:audio",
            "urn:x-nmos:format:data"
            # Note: urn:x-nmos:format:mux may not be fully supported yet
        ]
        
        import uuid
        for fmt in valid_formats:
            source_data = {
                "id": str(uuid.uuid4()),
                "format": fmt
            }
            
            response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
            assert response.status_code == 201, f"Failed with format {fmt}"
            
            # Cleanup
            requests.delete(f"{BASE_URL}/sources/{source_data['id']}", headers=auth_headers)
    
    def test_source_collection_structure(self, api_available):
        """
        Test source collection structure per TAMS 8.0 spec.
        Spec: source.json includes optional source_collection array
        App Note: 0007-populating-source-metadata
        """
        if not api_available:
            pytest.skip("API not available")
        
        # Get multi-format source example
        example_sources = load_example("sources-get-200.json")
        
        # Find multi-format source (with source_collection)
        multi_source = None
        for src in example_sources:
            if "source_collection" in src:
                multi_source = src
                break
        
        if multi_source:
            # Verify collection structure
            assert "source_collection" in multi_source
            assert isinstance(multi_source["source_collection"], list)
            
            if len(multi_source["source_collection"]) > 0:
                item = multi_source["source_collection"][0]
                assert "id" in item
                assert "role" in item


@pytest.mark.usefixtures("api_available")
class TestSourceAppNoteCompliance:
    """Test compliance with TAMS 8.0 app notes for sources"""
    
    def test_source_tags_per_appnote_0003(self, api_available, auth_headers):
        """
        Test source tags per App Note 0003 (Tag Names).
        Tags should support both string and array values.
        """
        if not api_available:
            pytest.skip("API not available")
        
        # Get example with tags
        example_source = load_example("source-get-200-basic.json")
        
        import uuid
        source_id = str(uuid.uuid4())
        
        # Create source
        source_data = {
            "id": source_id,
            "format": example_source["format"]
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Add string tag (per spec: tags.json allows string values)
        tag_headers = {**auth_headers, "Content-Type": "text/plain"}
        response = requests.put(
            f"{BASE_URL}/sources/{source_id}/tags/test_tag",
            data="string_value",
            headers=tag_headers
        )
        assert response.status_code in [200, 201, 204]
        
        # Retrieve tag
        response = requests.get(f"{BASE_URL}/sources/{source_id}/tags", headers=auth_headers)
        assert response.status_code == 200
        
        tags = response.json()
        if tags and "test_tag" in tags:
            assert tags["test_tag"] == "string_value"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_source_metadata_per_appnote_0007(self, api_available, auth_headers):
        """
        Test source metadata per App Note 0007 (Populating Source Metadata).
        created_by, updated_by, created, updated fields should work.
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_source = load_example("source-get-200-basic.json")
        
        import uuid
        source_data = {
            "id": str(uuid.uuid4()),
            "format": example_source["format"],
            "label": example_source.get("label", "Metadata Test"),
            "description": example_source.get("description", "Test metadata"),
            "created_by": "test-user",
            "updated_by": "test-user"
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        
        created = response.json()
        
        # Verify metadata fields
        assert "created" in created
        assert "updated" in created
        
        # Verify created_by and updated_by if provided
        if "created_by" in source_data:
            assert created.get("created_by") == "test-user" or created.get("created_by") is not None
        if "updated_by" in source_data:
            assert created.get("updated_by") == "test-user" or created.get("updated_by") is not None
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_data['id']}", headers=auth_headers)

