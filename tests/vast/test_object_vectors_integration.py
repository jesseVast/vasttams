#!/usr/bin/env python3
"""
Integration Tests for Object Vectors Table via Server API

These tests interact with the real API server using HTTP requests to test
object_vectors table operations through the full stack.

Tests include:
- Creating and updating vectors via PUT /api/vast/objects/{object_id}/vector
- Retrieving vectors via direct database queries (to verify storage)
- Vector similarity search via POST /api/vast/objects/vector/search
- Direct database queries on object_vectors table

These are real integration tests that require:
- A running TAMS server
- A configured VAST database connection
- Authentication (uses auth_headers fixture)
"""

import pytest
import sys
import requests
import uuid
import random
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "server"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings
from vasttamsserver.core.dependencies import get_vast_db

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}/api/tams/latest"
VAST_BASE_URL = f"http://{settings.host}:{settings.port}/api/vast/objects"


def generate_test_vector(dimension: int = 768) -> List[float]:
    """Generate a random test vector of specified dimension"""
    return [random.uniform(-1.0, 1.0) for _ in range(dimension)]


def normalize_vector(vector: List[float]) -> List[float]:
    """Normalize a vector to unit length (for cosine similarity)"""
    magnitude = sum(x * x for x in vector) ** 0.5
    if magnitude == 0:
        return vector
    return [x / magnitude for x in vector]


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        # Check health endpoint (doesn't require auth)
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.fixture(scope="module")
def vast_db():
    """Get VAST database connection for direct queries"""
    try:
        db = get_vast_db()
        if db is None:
            pytest.skip("VAST database not configured")
        return db
    except Exception as e:
        pytest.skip(f"Failed to connect to VAST database: {e}")


@pytest.fixture
def test_object_id(api_available, auth_headers):
    """Create a test object via API and return its ID"""
    if not api_available:
        pytest.skip("API not available")
    
    # Create a source first
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Vector Test Source {source_id[:8]}"
    }
    
    response = requests.post(
        f"{BASE_URL}/sources",
        json=source_data,
        headers=auth_headers,
        timeout=10
    )
    
    if response.status_code not in [200, 201]:
        pytest.skip(f"Failed to create test source: {response.status_code}")
    
    # Create a flow
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "label": f"Vector Test Flow {flow_id[:8]}",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/flows",
        json=flow_data,
        headers=auth_headers,
        timeout=10
    )
    
    if response.status_code not in [200, 201]:
        pytest.skip(f"Failed to create test flow: {response.status_code}")
    
    # Allocate storage to get an object
    storage_request = {"limit": 1}
    response = requests.post(
        f"{BASE_URL}/flows/{flow_id}/storage",
        json=storage_request,
        headers=auth_headers,
        timeout=10
    )
    
    if response.status_code != 201:
        pytest.skip(f"Failed to allocate storage: {response.status_code}")
    
    storage_data = response.json()
    media_objects = storage_data.get("media_objects", [])
    if not media_objects:
        pytest.skip("No media objects allocated")
    
    object_id = media_objects[0].get("object_id")
    if not object_id:
        pytest.skip("No object_id in storage allocation response")
    
    yield object_id
    
    # Cleanup: Try to delete the flow (which will cascade delete segments and objects)
    try:
        requests.delete(
            f"{BASE_URL}/flows/{flow_id}",
            headers=auth_headers,
            timeout=10
        )
    except Exception:
        pass  # Ignore cleanup errors


@pytest.mark.usefixtures("api_available")
class TestObjectVectorsIntegration:
    """Integration tests for object_vectors table via API"""
    
    def test_insert_vector_via_api(self, api_available, auth_headers, test_object_id):
        """Test inserting a vector via PUT /api/vast/objects/{object_id}/vector (upsert behavior)"""
        if not api_available:
            pytest.skip("API not available")
        
        vector = generate_test_vector(768)
        vector_data = {
            "vector": vector,
            "summary": f"Test vector for {test_object_id}",
            "embedding_model": "test-model-1.0"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Expected 200 or 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        assert result["object_id"] == test_object_id
    
    def test_query_vector_direct_after_api_insert(self, api_available, auth_headers, vast_db, test_object_id):
        """Test querying vector directly from database after API insert"""
        if not api_available:
            pytest.skip("API not available")
        
        # First insert a vector via API
        vector = generate_test_vector(768)
        summary = f"Direct query test for {test_object_id}"
        vector_data = {
            "vector": vector,
            "summary": summary
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert vector via API: {response.status_code}"
        
        # Now query directly from database
        escaped_object_id = test_object_id.replace("'", "''")
        result = vast_db.query("object_vectors").select("*").where(f"object_id = '{escaped_object_id}'").execute()
        
        assert result is not None, "Query should return a result"
        assert isinstance(result, dict), "Result should be a dictionary"
        assert 'data' in result, "Result should have 'data' key"
        
        data = result['data']
        assert isinstance(data, dict), "Data should be a dictionary"
        
        # Check that we have the object_id
        object_ids = data.get('object_id', [])
        assert len(object_ids) > 0, "Should have at least one object_id"
        assert object_ids[0] == test_object_id, "Object ID should match"
        
        # Check vector exists
        vectors = data.get('vector', [])
        assert len(vectors) > 0, "Should have a vector"
        assert len(vectors[0]) == 768, "Vector should be 768 dimensions"
        
        # Check summary
        summaries = data.get('summary', [])
        if summaries:
            assert summaries[0] == summary, "Summary should match"
    
    def test_insert_overwrites_existing_vector_via_api(self, api_available, auth_headers, vast_db, test_object_id):
        """Test that inserting a vector overwrites existing vector (upsert behavior)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Insert initial vector via API
        initial_vector = generate_test_vector(768)
        initial_summary = "Initial summary"
        initial_data = {
            "vector": initial_vector,
            "summary": initial_summary
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=initial_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert initial vector: {response.status_code}"
        
        # Insert new vector (should overwrite existing)
        updated_vector = generate_test_vector(768)
        updated_summary = "Updated summary"
        updated_model = "updated-model-2.0"
        updated_data = {
            "vector": updated_vector,
            "summary": updated_summary,
            "embedding_model": updated_model
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=updated_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert updated vector: {response.status_code}"
        
        # Verify overwrite by querying database
        escaped_object_id = test_object_id.replace("'", "''")
        result = vast_db.query("object_vectors").select("*").where(f"object_id = '{escaped_object_id}'").execute()
        
        data = result['data']
        object_ids = data.get('object_id', [])
        assert len(object_ids) == 1, "Should have exactly one vector record"
        
        summaries = data.get('summary', [])
        if summaries:
            assert summaries[0] == updated_summary, "Summary should be updated"
        
        embedding_models = data.get('embedding_model', [])
        if embedding_models:
            assert embedding_models[0] == updated_model, "Embedding model should be updated"
    
    def test_delete_vector_via_api(self, api_available, auth_headers, vast_db, test_object_id):
        """Test deleting a vector via DELETE /api/vast/objects/{object_id}/vector"""
        if not api_available:
            pytest.skip("API not available")
        
        # First insert a vector
        vector = generate_test_vector(768)
        vector_data = {
            "vector": vector,
            "summary": "Vector to be deleted"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert vector: {response.status_code}"
        
        # Verify vector exists
        escaped_object_id = test_object_id.replace("'", "''")
        result = vast_db.query("object_vectors").select("object_id").where(f"object_id = '{escaped_object_id}'").execute()
        data = result['data']
        object_ids = data.get('object_id', [])
        assert len(object_ids) > 0, "Vector should exist before deletion"
        
        # Delete vector via API
        response = requests.delete(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 204], \
            f"Expected 200 or 204, got {response.status_code}: {response.text}"
        
        # Verify vector is deleted
        result = vast_db.query("object_vectors").select("object_id").where(f"object_id = '{escaped_object_id}'").execute()
        data = result['data']
        object_ids = data.get('object_id', [])
        assert len(object_ids) == 0, "Vector should be deleted"
    
    def test_vector_search_via_api(self, api_available, auth_headers, test_object_id):
        """Test vector similarity search via POST /api/vast/objects/vector/search"""
        if not api_available:
            pytest.skip("API not available")
        
        # Insert a vector via API
        vector = generate_test_vector(768)
        vector = normalize_vector(vector)
        
        vector_data = {
            "vector": vector,
            "summary": f"Search test vector for {test_object_id}"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert vector: {response.status_code}"
        
        # Perform search via API with similar vector
        query_vector = vector.copy()  # Use same vector (should match)
        # Add small random noise
        query_vector = [v + random.uniform(-0.1, 0.1) for v in query_vector]
        query_vector = normalize_vector(query_vector)
        
        search_data = {
            "vector": query_vector,
            "num_matches": 10,
            "distance_metric": "cosine",
            "distance_numerical_value": 0.9  # Relaxed threshold
        }
        
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.text}"
        
        results = response.json()
        assert "matches" in results, "Results should have 'matches' key"
        assert isinstance(results["matches"], list), "Matches should be a list"
        
        # Should find at least our test object
        match_object_ids = [m.get('object_id') for m in results["matches"]]
        assert test_object_id in match_object_ids, \
            f"Should find test object {test_object_id} in search results"
    
    def test_vector_search_with_different_metrics(self, api_available, auth_headers, test_object_id):
        """Test vector search with different distance metrics via API"""
        if not api_available:
            pytest.skip("API not available")
        
        # Insert a vector via API
        vector = generate_test_vector(768)
        vector = normalize_vector(vector)
        
        vector_data = {
            "vector": vector,
            "summary": "Distance metric test"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert vector: {response.status_code}"
        
        query_vector = normalize_vector(generate_test_vector(768))
        
        # Test cosine similarity
        search_data = {
            "vector": query_vector,
            "num_matches": 10,
            "distance_metric": "cosine"
        }
        
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code == 200
        results_cosine = response.json()
        assert "matches" in results_cosine
        
        # Test euclidean distance
        search_data["distance_metric"] = "euclidean"
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code == 200
        results_euclidean = response.json()
        assert "matches" in results_euclidean
        
        # Test dot product
        search_data["distance_metric"] = "dot_product"
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code == 200
        results_dot = response.json()
        assert "matches" in results_dot
    
    def test_list_vectors_direct(self, api_available, auth_headers, vast_db, test_object_id):
        """Test listing all vectors directly from database"""
        if not api_available:
            pytest.skip("API not available")
        
        # Insert a vector via API
        vector = generate_test_vector(768)
        vector_data = {
            "vector": vector,
            "summary": "List test vector"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 201], \
            f"Failed to insert vector: {response.status_code}"
        
        # Query all vectors directly from database (with limit)
        result = vast_db.query("object_vectors").select(
            "object_id", "summary", "embedding_date", "embedding_model"
        ).limit(100).execute()
        
        assert result is not None
        assert isinstance(result, dict)
        assert 'data' in result
        
        data = result['data']
        object_ids = data.get('object_id', [])
        assert len(object_ids) > 0, "Should have at least one vector"
        
        # Our test object should be in the list
        assert test_object_id in object_ids, \
            f"Test object {test_object_id} should be in the list"
    
    def test_vector_validation_via_api(self, api_available, auth_headers, test_object_id):
        """Test vector validation (wrong dimension) via API"""
        if not api_available:
            pytest.skip("API not available")
        
        # Try to insert invalid vector (wrong dimension)
        invalid_vector = generate_test_vector(512)  # Should be 768
        vector_data = {
            "vector": invalid_vector,
            "summary": "Invalid vector test"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{test_object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 400 or 422 (validation error)
        assert response.status_code in [400, 422], \
            f"Expected 400 or 422 for invalid vector, got {response.status_code}: {response.text}"
    
    def test_vector_for_nonexistent_object_via_api(self, api_available, auth_headers):
        """Test that updating vector for non-existent object fails via API"""
        if not api_available:
            pytest.skip("API not available")
        
        nonexistent_id = str(uuid.uuid4())
        vector = generate_test_vector(768)
        vector_data = {
            "vector": vector,
            "summary": "Test"
        }
        
        response = requests.put(
            f"{VAST_BASE_URL}/{nonexistent_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 404
        assert response.status_code == 404, \
            f"Expected 404 for non-existent object, got {response.status_code}: {response.text}"
    
    def test_multiple_vectors_via_api(self, api_available, auth_headers, vast_db):
        """Test inserting vectors for multiple objects via API"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create multiple test objects via API
        test_object_ids = []
        
        for i in range(3):
            # Create source
            source_id = str(uuid.uuid4())
            source_data = {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": f"Multi Test Source {i}"
            }
            
            response = requests.post(
                f"{BASE_URL}/sources",
                json=source_data,
                headers=auth_headers,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                continue
            
            # Create flow
            flow_id = str(uuid.uuid4())
            flow_data = {
                "id": flow_id,
                "source_id": source_id,
                "format": "urn:x-nmos:format:video",
                "codec": "video/H264",
                "essence_parameters": {
                    "frame_width": 1920,
                    "frame_height": 1080,
                    "frame_rate": {"numerator": 25, "denominator": 1}
                }
            }
            
            response = requests.post(
                f"{BASE_URL}/flows",
                json=flow_data,
                headers=auth_headers,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                continue
            
            # Allocate storage
            storage_request = {"limit": 1}
            response = requests.post(
                f"{BASE_URL}/flows/{flow_id}/storage",
                json=storage_request,
                headers=auth_headers,
                timeout=10
            )
            
            if response.status_code == 201:
                storage_data = response.json()
                media_objects = storage_data.get("media_objects", [])
                if media_objects:
                    object_id = media_objects[0].get("object_id")
                    if object_id:
                        test_object_ids.append((object_id, flow_id))
        
        try:
            # Insert vectors for each object via API
            for i, (obj_id, flow_id) in enumerate(test_object_ids):
                vector = generate_test_vector(768)
                vector_data = {
                    "vector": vector,
                    "summary": f"Multi-object test {i+1}"
                }
                
                response = requests.put(
                    f"{VAST_BASE_URL}/{obj_id}/vector",
                    json=vector_data,
                    headers=auth_headers,
                    timeout=30
                )
                
                assert response.status_code in [200, 201], \
                    f"Should insert vector for object {obj_id}"
            
            # Verify all vectors exist via direct database query
            for obj_id, flow_id in test_object_ids:
                escaped_id = obj_id.replace("'", "''")
                result = vast_db.query("object_vectors").select("object_id").where(
                    f"object_id = '{escaped_id}'"
                ).execute()
                
                data = result['data']
                object_ids = data.get('object_id', [])
                assert len(object_ids) > 0, f"Should have vector for {obj_id}"
                assert object_ids[0] == obj_id, f"Object ID should match for {obj_id}"
        
        finally:
            # Cleanup: Delete flows (will cascade delete objects)
            for obj_id, flow_id in test_object_ids:
                try:
                    requests.delete(
                        f"{BASE_URL}/flows/{flow_id}",
                        headers=auth_headers,
                        timeout=10
                    )
                except Exception:
                    pass
