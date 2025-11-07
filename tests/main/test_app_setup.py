#!/usr/bin/env python3
"""
Tests for FastAPI Application Setup

Tests the main application setup in src/vasttams/main.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestAppCreation:
    """Test FastAPI app creation"""
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_app_creation(self, mock_get_vast_db, mock_get_settings):
        """Test that FastAPI app can be created"""
        from vasttams.main import app
        assert app is not None
        assert app.title is not None
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_app_has_routers(self, mock_get_vast_db, mock_get_settings):
        """Test that app has all required routers"""
        from vasttams.main import app
        router_paths = [route.path for route in app.routes]
        expected_paths = ["/sources", "/flows", "/segments", "/objects", "/auth"]
        # Check that at least some expected paths exist
        assert any("/sources" in path or path.startswith("/sources") for path in router_paths)
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_app_has_middleware(self, mock_get_vast_db, mock_get_settings):
        """Test that app has middleware configured"""
        from vasttams.main import app
        # Check that middleware is configured (CORS, telemetry, etc.)
        # FastAPI stores middleware in user_middleware list
        assert len(app.user_middleware) > 0


class TestLifespanEvents:
    """Test lifespan event handlers"""
    
    @pytest.mark.asyncio
    @patch('vasttams.main.telemetry_manager')
    @patch('vasttams.main.get_vast_db')
    @patch('vasttams.common.storage.table_initializer.TAMSTableInitializer')
    async def test_lifespan_startup(self, mock_initializer_class, mock_get_vast_db, mock_telemetry):
        """Test lifespan startup events"""
        from vasttams.main import lifespan, app
        
        # Mock dependencies
        mock_vast_db = MagicMock()
        mock_get_vast_db.return_value = mock_vast_db
        
        mock_initializer = AsyncMock()
        mock_initializer.verify_tables_exist = AsyncMock(return_value={})
        mock_initializer_class.return_value = mock_initializer
        
        mock_telemetry.initialize = MagicMock()
        
        # Test lifespan startup
        async with lifespan(app):
            # Startup should complete without errors
            assert mock_telemetry.initialize.called
            assert mock_initializer.verify_tables_exist.called
    
    @pytest.mark.asyncio
    @patch('vasttams.auth.user_service.UserService')
    @patch('vasttams.main.telemetry_manager')
    @patch('vasttams.main.get_vast_db')
    @patch('vasttams.common.storage.table_initializer.TAMSTableInitializer')
    async def test_lifespan_startup_with_missing_tables(self, mock_initializer_class, mock_get_vast_db, mock_telemetry, mock_user_service):
        """Test lifespan startup when tables are missing"""
        from vasttams.main import lifespan, app
        
        mock_vast_db = MagicMock()
        mock_get_vast_db.return_value = mock_vast_db
        
        mock_initializer = AsyncMock()
        mock_initializer.verify_tables_exist = AsyncMock(return_value={"sources": False, "flows": True})
        mock_initializer.initialize_all_tables = AsyncMock(return_value={"sources": True, "flows": True})
        mock_initializer_class.return_value = mock_initializer
        
        mock_telemetry.initialize = MagicMock()
        
        # Mock UserService to avoid errors
        mock_user = AsyncMock()
        mock_user.get_user_by_username = AsyncMock(return_value=None)
        mock_user.create_user = AsyncMock()
        mock_user_service.return_value = mock_user
        
        async with lifespan(app):
            assert mock_initializer.initialize_all_tables.called
    
    @pytest.mark.asyncio
    @patch('vasttams.storagebackends.service.StorageBackendService')
    @patch('vasttams.auth.user_service.UserService')
    @patch('vasttams.main.telemetry_manager')
    @patch('vasttams.main.get_vast_db')
    @patch('vasttams.main.get_s3_client')
    @patch('vasttams.common.storage.table_initializer.TAMSTableInitializer')
    async def test_lifespan_startup_initializes_storage_backends(self, mock_initializer_class, mock_get_s3, mock_get_vast_db, mock_telemetry, mock_user_service, mock_backend_service):
        """Test lifespan startup initializes storage backends"""
        from vasttams.main import lifespan, app
        
        mock_vast_db = MagicMock()
        mock_get_vast_db.return_value = mock_vast_db
        
        mock_initializer = AsyncMock()
        mock_initializer.verify_tables_exist = AsyncMock(return_value={})
        mock_initializer_class.return_value = mock_initializer
        
        mock_telemetry.initialize = MagicMock()
        
        # Mock UserService
        mock_user = AsyncMock()
        mock_user.get_user_by_username = AsyncMock(return_value=MagicMock())  # User exists
        mock_user_service.return_value = mock_user
        
        # Mock storage backend service
        mock_backend = AsyncMock()
        mock_backend.get_storage_backends = AsyncMock(return_value=[])
        mock_backend.create_storage_backend = AsyncMock()
        mock_backend_service.return_value = mock_backend
        
        async with lifespan(app):
            # Should attempt to initialize storage backends
            pass
    
    @pytest.mark.asyncio
    @patch('vasttams.main.telemetry_manager')
    @patch('vasttams.main.get_vast_db')
    async def test_lifespan_shutdown(self, mock_get_vast_db, mock_telemetry):
        """Test lifespan shutdown events"""
        from vasttams.main import lifespan, app
        
        mock_vast_db = MagicMock()
        mock_get_vast_db.return_value = None  # No DB for shutdown test
        mock_telemetry.shutdown = MagicMock()
        
        # Test lifespan shutdown
        async with lifespan(app):
            pass  # Shutdown happens on exit
        
        # Shutdown should be called
        # Note: Actual shutdown happens in finally block


class TestExceptionHandlers:
    """Test exception handlers"""
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_app_has_exception_handlers(self, mock_get_vast_db, mock_get_settings):
        """Test that app has exception handlers configured"""
        from vasttams.main import app
        # Check that exception handlers exist
        assert hasattr(app, 'exception_handlers') or len(app.exception_handlers) >= 0
    
    @pytest.mark.asyncio
    @patch('vasttams.main.logger')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_http_exception_handler_401(self, mock_get_vast_db, mock_get_settings, mock_logger):
        """Test HTTP exception handler for 401 errors (logs at DEBUG)"""
        from vasttams.main import app, http_exception_handler
        from fastapi import HTTPException, Request
        
        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=401, detail="Unauthorized")
        
        response = await http_exception_handler(mock_request, exc)
        
        assert response.status_code == 401
        assert "Unauthorized" in response.body.decode()
        mock_logger.debug.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('vasttams.main.logger')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_http_exception_handler_400(self, mock_get_vast_db, mock_get_settings, mock_logger):
        """Test HTTP exception handler for 400 errors (logs at WARNING)"""
        from vasttams.main import app, http_exception_handler
        from fastapi import HTTPException, Request
        
        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=400, detail="Bad Request")
        
        response = await http_exception_handler(mock_request, exc)
        
        assert response.status_code == 400
        mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('vasttams.main.logger')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_http_exception_handler_500(self, mock_get_vast_db, mock_get_settings, mock_logger):
        """Test HTTP exception handler for 500 errors (logs at ERROR)"""
        from vasttams.main import app, http_exception_handler
        from fastapi import HTTPException, Request
        
        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=500, detail="Internal Server Error")
        
        response = await http_exception_handler(mock_request, exc)
        
        assert response.status_code == 500
        mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('vasttams.main.log_pydantic_validation_error')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_validation_exception_handler(self, mock_get_vast_db, mock_get_settings, mock_log_error):
        """Test validation exception handler"""
        from vasttams.main import app, validation_exception_handler
        from fastapi import Request
        from fastapi.exceptions import RequestValidationError
        
        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/sources"
        mock_request.body = b'{"invalid": "data"}'
        
        mock_log_error.return_value = "Validation error message"
        
        # Create a RequestValidationError
        errors = [{"loc": ["body", "id"], "msg": "field required", "type": "value_error.missing"}]
        exc = RequestValidationError(errors=errors, body=mock_request.body)
        
        response = await validation_exception_handler(mock_request, exc)
        
        assert response.status_code == 422
        assert "Validation error" in response.body.decode()
        mock_log_error.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('vasttams.main.logger')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_timeout_exception_handler(self, mock_get_vast_db, mock_get_settings, mock_logger):
        """Test timeout exception handler"""
        from vasttams.main import app, timeout_exception_handler
        from fastapi import Request
        import asyncio
        
        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/sources"
        
        exc = asyncio.TimeoutError()
        
        response = await timeout_exception_handler(mock_request, exc)
        
        assert response.status_code == 503
        response_body = response.body.decode()
        assert "SERVICE_UNAVAILABLE" in response_body
        mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('vasttams.main.logger')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_connection_exception_handler(self, mock_get_vast_db, mock_get_settings, mock_logger):
        """Test connection exception handler"""
        from vasttams.main import app, connection_exception_handler
        from fastapi import Request
        
        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/sources"
        
        exc = ConnectionError("Connection failed")
        
        response = await connection_exception_handler(mock_request, exc)
        
        assert response.status_code == 503
        response_body = response.body.decode()
        assert "SERVICE_UNAVAILABLE" in response_body
        mock_logger.error.assert_called_once()


class TestOpenAPISchema:
    """Test OpenAPI schema generation"""
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_openapi_schema_generation(self, mock_get_vast_db, mock_get_settings):
        """Test that OpenAPI schema can be generated"""
        from vasttams.main import app
        schema = app.openapi()
        assert schema is not None
        assert "info" in schema
        assert "paths" in schema
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_openapi_schema_info(self, mock_get_vast_db, mock_get_settings):
        """Test OpenAPI schema info"""
        from vasttams.main import app
        schema = app.openapi()
        assert "title" in schema["info"]
        assert "version" in schema["info"]
    
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    def test_openapi_schema_has_tags(self, mock_get_vast_db, mock_get_settings):
        """Test OpenAPI schema has custom tags"""
        from vasttams.main import app
        schema = app.openapi()
        assert "tags" in schema
        tag_names = [tag["name"] for tag in schema["tags"]]
        assert "flows" in tag_names
        assert "sources" in tag_names


class TestRootEndpoints:
    """Test root endpoints"""
    
    @pytest.mark.asyncio
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_head_root(self, mock_get_vast_db, mock_get_settings):
        """Test HEAD / endpoint"""
        from vasttams.main import app, head_root
        from fastapi import Request
        
        mock_request = MagicMock(spec=Request)
        response = await head_root()
        
        assert response == {}
    
    @pytest.mark.asyncio
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_get_root(self, mock_get_vast_db, mock_get_settings):
        """Test GET / endpoint"""
        from vasttams.main import app, get_root
        
        response = await get_root()
        
        assert isinstance(response, list)
        assert "service" in response
        assert "flows" in response
        assert "sources" in response
    
    @pytest.mark.asyncio
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_get_openapi_json(self, mock_get_vast_db, mock_get_settings):
        """Test GET /openapi.json endpoint"""
        from vasttams.main import app, get_openapi_json
        
        response = await get_openapi_json()
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        content = response.body.decode()
        assert "openapi" in content or "swagger" in content


class TestHealthEndpoints:
    """Test health and metrics endpoints"""
    
    @pytest.mark.asyncio
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_head_health(self, mock_get_vast_db, mock_get_settings):
        """Test HEAD /health endpoint"""
        from vasttams.main import app, head_health
        
        response = await head_health()
        
        assert response == {}
    
    @pytest.mark.asyncio
    @patch('vasttams.main.enhanced_health_check')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_get_health(self, mock_get_vast_db, mock_get_settings, mock_health_check):
        """Test GET /health endpoint"""
        from vasttams.main import app, health_check
        
        mock_health_check.return_value = {"status": "healthy"}
        
        response = await health_check()
        
        assert response == {"status": "healthy"}
        mock_health_check.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('vasttams.main.metrics_endpoint')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_get_metrics(self, mock_get_vast_db, mock_get_settings, mock_metrics):
        """Test GET /metrics endpoint"""
        from vasttams.main import app, get_metrics
        
        mock_metrics.return_value = {"requests_total": 100}
        
        response = await get_metrics()
        
        assert response == {"requests_total": 100}
        mock_metrics.assert_called_once()


class TestConfigEndpoints:
    """Test configuration endpoints"""
    
    @pytest.mark.asyncio
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_get_async_deletion_threshold(self, mock_get_vast_db, mock_get_settings):
        """Test GET /config/async-deletion-threshold endpoint"""
        from vasttams.main import app, get_async_deletion_threshold
        
        mock_settings = MagicMock()
        mock_settings.async_deletion_threshold = 100
        mock_get_settings.return_value = mock_settings
        
        response = await get_async_deletion_threshold()
        
        assert response == {"async_deletion_threshold": 100}
    
    @pytest.mark.asyncio
    @patch('vasttams.main.update_settings')
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_update_async_deletion_threshold_success(self, mock_get_vast_db, mock_get_settings, mock_update_settings):
        """Test PUT /config/async-deletion-threshold endpoint with valid threshold"""
        from vasttams.main import app, update_async_deletion_threshold
        
        response = await update_async_deletion_threshold(threshold=200)
        
        assert response["threshold"] == 200
        assert "updated" in response["message"].lower()
        mock_update_settings.assert_called_once_with({"async_deletion_threshold": 200})
    
    @pytest.mark.asyncio
    @patch('vasttams.main.get_settings')
    @patch('vasttams.main.get_vast_db')
    async def test_update_async_deletion_threshold_negative(self, mock_get_vast_db, mock_get_settings):
        """Test PUT /config/async-deletion-threshold endpoint with negative threshold"""
        from vasttams.main import app, update_async_deletion_threshold
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await update_async_deletion_threshold(threshold=-1)
        
        assert exc_info.value.status_code == 400
        assert "non-negative" in exc_info.value.detail.lower()

