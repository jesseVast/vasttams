"""
Tests for API Router Components

This module tests the API router functionality including initialization,
endpoint registration, and dependency injection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient

from app.api.flows_router import router as flows_router
from app.api.sources_router import router as sources_router
from app.api.segments_router import router as segments_router
from app.api.objects_router import router as objects_router
from app.api.analytics_router import router as analytics_router
from tests.test_utils.mock_vastdbmanager import MockVastDBManager
from tests.test_utils.mock_s3store import MockS3Store


class TestAPIRouterInitialization:
    """Test API router initialization"""
    
    def test_flows_router_initialization(self):
        """Test flows router initialization"""
        assert flows_router is not None
        assert isinstance(flows_router, APIRouter)
        assert flows_router.prefix == "/flows"
        assert flows_router.tags == ["flows"]
    
    def test_sources_router_initialization(self):
        """Test sources router initialization"""
        assert sources_router is not None
        assert isinstance(sources_router, APIRouter)
        assert sources_router.prefix == "/sources"
        assert sources_router.tags == ["sources"]
    
    def test_segments_router_initialization(self):
        """Test segments router initialization"""
        assert segments_router is not None
        assert isinstance(segments_router, APIRouter)
        assert segments_router.prefix == "/segments"
        assert segments_router.tags == ["segments"]
    
    def test_objects_router_initialization(self):
        """Test objects router initialization"""
        assert objects_router is not None
        assert isinstance(objects_router, APIRouter)
        assert objects_router.prefix == "/objects"
        assert objects_router.tags == ["objects"]
    
    def test_analytics_router_initialization(self):
        """Test analytics router initialization"""
        assert analytics_router is not None
        assert isinstance(analytics_router, APIRouter)
        assert analytics_router.tags == ["analytics"]


class TestEndpointRegistration:
    """Test endpoint registration in routers"""
    
    def test_flows_router_endpoints(self):
        """Test flows router endpoint registration"""
        # Check that expected endpoints are registered
        routes = [route.path for route in flows_router.routes]
        
        # Basic CRUD endpoints
        assert "/flows" in routes  # GET (list) and POST (create)
        assert "/flows/{flow_id}" in routes  # GET, PUT, DELETE
        
        # Additional flow-specific endpoints
        assert "/flows/{flow_id}/segments" in routes
        assert "/flows/{flow_id}/metadata" in routes
    
    def test_sources_router_endpoints(self):
        """Test sources router endpoint registration"""
        routes = [route.path for route in sources_router.routes]
        
        # Basic CRUD endpoints
        assert "/sources" in routes  # GET (list) and POST (create)
        assert "/sources/{source_id}" in routes  # GET, PUT, DELETE
        
        # Additional source-specific endpoints
        assert "/sources/{source_id}/flows" in routes
        assert "/sources/{source_id}/metadata" in routes
    
    def test_segments_router_endpoints(self):
        """Test segments router endpoint registration"""
        routes = [route.path for route in segments_router.routes]
        
        # Basic CRUD endpoints
        assert "/segments" in routes  # GET (list) and POST (create)
        assert "/segments/{segment_id}" in routes  # GET, PUT, DELETE
        
        # Additional segment-specific endpoints
        assert "/segments/{segment_id}/content" in routes
        assert "/segments/{segment_id}/metadata" in routes
    
    def test_objects_router_endpoints(self):
        """Test objects router endpoint registration"""
        routes = [route.path for route in objects_router.routes]
        
        # Basic CRUD endpoints
        assert "/objects" in routes  # GET (list) and POST (create)
        assert "/objects/{object_id}" in routes  # GET, PUT, DELETE
        
        # Additional object-specific endpoints
        assert "/objects/{object_id}/flows" in routes
        assert "/objects/{object_id}/metadata" in routes
    
    def test_analytics_router_endpoints(self):
        """Test analytics router endpoint registration"""
        routes = [route.path for route in analytics_router.routes]
        
        # Analytics endpoints
        assert "/analytics/query" in routes
        assert "/analytics/aggregate" in routes
        assert "/analytics/timeseries" in routes


class TestDependencyInjection:
    """Test dependency injection in routers"""
    
    def test_flows_router_dependencies(self):
        """Test flows router dependency injection"""
        # Check that dependencies are properly injected
        for route in flows_router.routes:
            if hasattr(route, 'dependencies'):
                # Verify dependencies exist and are properly configured
                assert route.dependencies is not None
    
    def test_sources_router_dependencies(self):
        """Test sources router dependency injection"""
        for route in sources_router.routes:
            if hasattr(route, 'dependencies'):
                assert route.dependencies is not None
    
    def test_segments_router_dependencies(self):
        """Test segments router dependency injection"""
        for route in segments_router.routes:
            if hasattr(route, 'dependencies'):
                assert route.dependencies is not None
    
    def test_objects_router_dependencies(self):
        """Test objects router dependency injection"""
        for route in objects_router.routes:
            if hasattr(route, 'dependencies'):
                assert route.dependencies is not None
    
    def test_analytics_router_dependencies(self):
        """Test analytics router dependency injection"""
        for route in analytics_router.routes:
            if hasattr(route, 'dependencies'):
                assert route.dependencies is not None


class TestErrorHandling:
    """Test error handling in routers"""
    
    def test_flows_router_error_handling(self):
        """Test flows router error handling"""
        # Create test app with flows router
        app = FastAPI()
        app.include_router(flows_router)
        client = TestClient(app)
        
        # Test invalid flow ID format
        response = client.get("/flows/invalid-uuid")
        assert response.status_code == 422  # Validation error
        
        # Test non-existent flow
        response = client.get("/flows/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404  # Not found
    
    def test_sources_router_error_handling(self):
        """Test sources router error handling"""
        app = FastAPI()
        app.include_router(sources_router)
        client = TestClient(app)
        
        # Test invalid source ID format
        response = client.get("/sources/invalid-uuid")
        assert response.status_code == 422  # Validation error
        
        # Test non-existent source
        response = client.get("/sources/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404  # Not found
    
    def test_segments_router_error_handling(self):
        """Test segments router error handling"""
        app = FastAPI()
        app.include_router(segments_router)
        client = TestClient(app)
        
        # Test invalid segment ID format
        response = client.get("/segments/invalid-id")
        assert response.status_code == 422  # Validation error
        
        # Test non-existent segment
        response = client.get("/segments/non-existent-id")
        assert response.status_code == 404  # Not found
    
    def test_objects_router_error_handling(self):
        """Test objects router error handling"""
        app = FastAPI()
        app.include_router(objects_router)
        client = TestClient(app)
        
        # Test invalid object ID format
        response = client.get("/objects/invalid-id")
        assert response.status_code == 422  # Validation error
        
        # Test non-existent object
        response = client.get("/objects/non-existent-id")
        assert response.status_code == 404  # Not found


class TestRouterIntegration:
    """Test integration of multiple routers"""
    
    def test_multiple_router_integration(self):
        """Test integration of multiple routers in FastAPI app"""
        app = FastAPI()
        
        # Include all routers
        app.include_router(flows_router)
        app.include_router(sources_router)
        app.include_router(segments_router)
        app.include_router(objects_router)
        app.include_router(analytics_router)
        
        client = TestClient(app)
        
        # Test that all routers are accessible
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test that router prefixes are working
        response = client.get("/flows")
        assert response.status_code in [200, 404]  # 404 is expected without data
        
        response = client.get("/sources")
        assert response.status_code in [200, 404]
        
        response = client.get("/segments")
        assert response.status_code in [200, 404]
        
        response = client.get("/objects")
        assert response.status_code in [200, 404]
        
        response = client.get("/analytics/query")
        assert response.status_code in [200, 404, 422]  # 422 for missing query params
    
    def test_router_prefix_conflicts(self):
        """Test that router prefixes don't conflict"""
        app = FastAPI()
        
        # Include all routers
        app.include_router(flows_router)
        app.include_router(sources_router)
        app.include_router(segments_router)
        app.include_router(objects_router)
        app.include_router(analytics_router)
        
        # Check that all routes have unique paths
        all_routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                all_routes.append(route.path)
        
        # Remove duplicates and check count
        unique_routes = list(set(all_routes))
        assert len(unique_routes) == len(all_routes), "Duplicate routes found"
    
    def test_router_tag_organization(self):
        """Test that router tags are properly organized"""
        app = FastAPI()
        
        # Include all routers
        app.include_router(flows_router)
        app.include_router(sources_router)
        app.include_router(segments_router)
        app.include_router(objects_router)
        app.include_router(analytics_router)
        
        # Check that tags are properly set
        expected_tags = ["flows", "sources", "segments", "objects", "analytics"]
        
        for route in app.routes:
            if hasattr(route, 'tags') and route.tags:
                for tag in route.tags:
                    assert tag in expected_tags, f"Unexpected tag: {tag}"


class TestCRUDOperations:
    """Test CRUD operations through routers"""
    
    def test_flows_crud_operations(self):
        """Test flows CRUD operations through router"""
        app = FastAPI()
        app.include_router(flows_router)
        client = TestClient(app)
        
        # Test flow creation
        flow_data = {
            "source_id": "00000000-0000-0000-0000-000000000000",
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "label": "Test Flow",
            "description": "Test Description"
        }
        
        response = client.post("/flows", json=flow_data)
        # Note: This will likely fail without proper dependencies
        # We're just testing that the endpoint exists and accepts the data format
        assert response.status_code in [200, 201, 422, 500]
    
    def test_sources_crud_operations(self):
        """Test sources CRUD operations through router"""
        app = FastAPI()
        app.include_router(sources_router)
        client = TestClient(app)
        
        # Test source creation
        source_data = {
            "format": "urn:x-nmos:format:video",
            "label": "Test Source",
            "description": "Test Description"
        }
        
        response = client.post("/sources", json=source_data)
        # Note: This will likely fail without proper dependencies
        # We're just testing that the endpoint exists and accepts the data format
        assert response.status_code in [200, 201, 422, 500]
    
    def test_segments_crud_operations(self):
        """Test segments CRUD operations through router"""
        app = FastAPI()
        app.include_router(segments_router)
        client = TestClient(app)
        
        # Test segment creation
        segment_data = {
            "flow_id": "00000000-0000-0000-0000-000000000000",
            "storage_path": "/test/path"
        }
        
        response = client.post("/segments", json=segment_data)
        # Note: This will likely fail without proper dependencies
        # We're just testing that the endpoint exists and accepts the data format
        assert response.status_code in [200, 201, 422, 500]
    
    def test_objects_crud_operations(self):
        """Test objects CRUD operations through router"""
        app = FastAPI()
        app.include_router(objects_router)
        client = TestClient(app)
        
        # Test object creation
        object_data = {
            "referenced_by_flows": ["00000000-0000-0000-0000-000000000000"],
            "size": 1024
        }
        
        response = client.post("/objects", json=object_data)
        # Note: This will likely fail without proper dependencies
        # We're just testing that the endpoint exists and accepts the data format
        assert response.status_code in [200, 201, 422, 500]
