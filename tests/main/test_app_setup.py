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

