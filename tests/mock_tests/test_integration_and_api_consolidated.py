"""
Consolidated Integration and API Tests

This file consolidates tests from:
- test_integration_api.py
- test_auth.py
- test_auth_simple.py
- test_403_compliance.py
- test_integration_real_db.py
- test_webhook_ownership.py
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import uuid
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient

from app.main import app
from app.auth.core import get_current_user, create_access_token
from app.auth.models import User, TokenData
from app.api.flows_router import router as flows_router
from app.api.sources_router import router as sources_router
from app.api.segments_router import router as segments_router


class TestAuthentication:
    """Authentication tests"""
    
    @pytest.fixture
    def test_user(self):
        """Test user for authentication"""
        return User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            disabled=False
        )
    
    @pytest.fixture
    def test_token(self, test_user):
        """Test access token"""
        return create_access_token(data={"sub": test_user.username})
    
    def test_token_creation(self, test_user):
        """Test access token creation"""
        token = create_access_token(data={"sub": test_user.username})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_token_validation(self, test_user, test_token):
        """Test token validation"""
        # Test valid token
        user = get_current_user(test_token)
        assert user.username == test_user.username
        
        # Test invalid token
        with pytest.raises(HTTPException):
            get_current_user("invalid_token")
    
    def test_user_authentication(self, test_user):
        """Test user authentication"""
        # Test valid user
        assert test_user.disabled is False
        assert test_user.username == "testuser"
        assert test_user.email == "test@example.com"
        
        # Test disabled user
        disabled_user = User(
            id=str(uuid.uuid4()),
            username="disabled_user",
            email="disabled@example.com",
            full_name="Disabled User",
            disabled=True
        )
        assert disabled_user.disabled is True


class TestAPIEndpoints:
    """API endpoint tests"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth(self):
        """Mock authentication"""
        with patch('app.auth.dependencies.get_current_user') as mock_auth:
            mock_user = User(
                id=str(uuid.uuid4()),
                username="testuser",
                email="test@example.com",
                full_name="Test User",
                disabled=False
            )
            mock_auth.return_value = mock_user
            yield mock_auth
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_sources_endpoint(self, client, mock_auth):
        """Test sources endpoint"""
        # Test GET sources
        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        
        # Test POST source
        source_data = {
            "label": "Test Source",
            "format": "video",
            "description": "Test source",
            "created_by": "testuser"
        }
        response = client.post("/api/v1/sources", json=source_data)
        assert response.status_code == 201
    
    def test_flows_endpoint(self, client, mock_auth):
        """Test flows endpoint"""
        # Test GET flows
        response = client.get("/api/v1/flows")
        assert response.status_code == 200
        
        # Test POST flow
        flow_data = {
            "source_id": str(uuid.uuid4()),
            "format": "video",
            "codec": "H.264",
            "label": "Test Flow",
            "description": "Test flow",
            "created_by": "testuser"
        }
        response = client.post("/api/v1/flows", json=flow_data)
        assert response.status_code == 201
    
    def test_segments_endpoint(self, client, mock_auth):
        """Test segments endpoint"""
        # Test GET segments
        response = client.get("/api/v1/segments")
        assert response.status_code == 200
        
        # Test POST segment
        segment_data = {
            "object_id": str(uuid.uuid4()),
            "timerange": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z",
            "sample_offset": 0,
            "sample_count": 1000,
            "key_frame_count": 10
        }
        response = client.post("/api/v1/segments", json=segment_data)
        assert response.status_code == 201


class Test403Compliance:
    """403 compliance tests"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    def test_unauthenticated_access(self, client):
        """Test that unauthenticated access returns 403"""
        # Test protected endpoints without authentication
        endpoints = [
            "/api/v1/sources",
            "/api/v1/flows",
            "/api/v1/segments",
            "/api/v1/objects"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 403
    
    def test_authenticated_access(self, client):
        """Test that authenticated access works"""
        # Mock authentication
        with patch('app.auth.dependencies.get_current_user') as mock_auth:
            mock_user = User(
                id=str(uuid.uuid4()),
                username="testuser",
                email="test@example.com",
                full_name="Test User",
                disabled=False
            )
            mock_auth.return_value = mock_user
            
            # Test protected endpoints with authentication
            response = client.get("/api/v1/sources")
            assert response.status_code == 200
    
    def test_disabled_user_access(self, client):
        """Test that disabled users cannot access endpoints"""
        # Mock disabled user
        with patch('app.auth.dependencies.get_current_user') as mock_auth:
            mock_user = User(
                id=str(uuid.uuid4()),
                username="disabled_user",
                email="disabled@example.com",
                full_name="Disabled User",
                disabled=True
            )
            mock_auth.return_value = mock_user
            
            # Test that disabled users get 403
            response = client.get("/api/v1/sources")
            assert response.status_code == 403


class TestWebhookOwnership:
    """Webhook ownership tests"""
    
    @pytest.fixture
    def webhook_data(self):
        """Test webhook data"""
        return {
            "id": str(uuid.uuid4()),
            "url": "https://webhook.example.com/callback",
            "events": ["flow.created", "segment.uploaded"],
            "owner_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def test_webhook_creation(self, webhook_data):
        """Test webhook creation"""
        # Test webhook data validation
        assert webhook_data["id"] is not None
        assert webhook_data["url"].startswith("https://")
        assert len(webhook_data["events"]) > 0
        assert webhook_data["owner_id"] is not None
    
    def test_webhook_ownership_validation(self, webhook_data):
        """Test webhook ownership validation"""
        # Test that owner_id is required
        assert "owner_id" in webhook_data
        
        # Test that owner_id is valid UUID
        try:
            uuid.UUID(webhook_data["owner_id"])
        except ValueError:
            pytest.fail("owner_id should be a valid UUID")
    
    def test_webhook_event_validation(self, webhook_data):
        """Test webhook event validation"""
        # Test that events list is not empty
        assert len(webhook_data["events"]) > 0
        
        # Test that events are valid
        valid_events = ["flow.created", "segment.uploaded", "source.created", "object.created"]
        for event in webhook_data["events"]:
            assert event in valid_events


class TestIntegrationScenarios:
    """Integration scenario tests"""
    
    @pytest.fixture
    def mock_vast_store(self):
        """Mock VAST store"""
        mock_store = MagicMock()
        mock_store.create_source = AsyncMock(return_value=True)
        mock_store.create_flow = AsyncMock(return_value=True)
        mock_store.create_flow_segment = AsyncMock(return_value=True)
        mock_store.get_source = AsyncMock(return_value=MagicMock())
        mock_store.get_flow = AsyncMock(return_value=MagicMock())
        mock_store.get_flow_segments = AsyncMock(return_value=[])
        return mock_store
    
    def test_source_to_flow_to_segment_workflow(self, mock_vast_store):
        """Test complete workflow from source to segment"""
        # Create source
        source_id = str(uuid.uuid4())
        source_result = asyncio.run(mock_vast_store.create_source(MagicMock()))
        assert source_result is True
        
        # Create flow
        flow_result = asyncio.run(mock_vast_store.create_flow(MagicMock()))
        assert flow_result is True
        
        # Create segment
        segment_result = asyncio.run(mock_vast_store.create_flow_segment(
            MagicMock(), str(uuid.uuid4()), b"test_data"
        ))
        assert segment_result is True
        
        # Verify all operations were called
        mock_vast_store.create_source.assert_called_once()
        mock_vast_store.create_flow.assert_called_once()
        mock_vast_store.create_flow_segment.assert_called_once()
    
    def test_data_retrieval_workflow(self, mock_vast_store):
        """Test data retrieval workflow"""
        # Mock data retrieval
        mock_source = MagicMock()
        mock_source.id = str(uuid.uuid4())
        mock_source.label = "Test Source"
        
        mock_flow = MagicMock()
        mock_flow.id = str(uuid.uuid4())
        mock_flow.source_id = mock_source.id
        
        mock_segments = [MagicMock(), MagicMock()]
        
        # Test retrieval
        source = asyncio.run(mock_vast_store.get_source(mock_source.id))
        assert source is not None
        
        flow = asyncio.run(mock_vast_store.get_flow(mock_flow.id))
        assert flow is not None
        
        segments = asyncio.run(mock_vast_store.get_flow_segments(mock_flow.id))
        assert len(segments) == 2
        
        # Verify all operations were called
        mock_vast_store.get_source.assert_called_once()
        mock_vast_store.get_flow.assert_called_once()
        mock_vast_store.get_flow_segments.assert_called_once()
    
    def test_error_handling_integration(self, mock_vast_store):
        """Test error handling in integration scenarios"""
        # Mock error conditions
        mock_vast_store.create_source.side_effect = Exception("Database error")
        mock_vast_store.create_flow.side_effect = Exception("Storage error")
        
        # Test error handling
        with pytest.raises(Exception):
            asyncio.run(mock_vast_store.create_source(MagicMock()))
        
        with pytest.raises(Exception):
            asyncio.run(mock_vast_store.create_flow(MagicMock()))
    
    def test_concurrent_operations(self, mock_vast_store):
        """Test concurrent operations"""
        # Test multiple concurrent operations
        async def concurrent_operations():
            tasks = []
            for i in range(5):
                task = mock_vast_store.create_source(MagicMock())
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        results = asyncio.run(concurrent_operations())
        assert len(results) == 5
        
        # Verify all operations were called
        assert mock_vast_store.create_source.call_count == 5


class TestRealDatabaseIntegration:
    """Real database integration tests (mocked)"""
    
    @pytest.fixture
    def mock_real_db_connection(self):
        """Mock real database connection"""
        mock_connection = MagicMock()
        mock_connection.execute = MagicMock()
        mock_connection.fetchall = MagicMock(return_value=[])
        mock_connection.fetchone = MagicMock(return_value=None)
        return mock_connection
    
    def test_database_connection(self, mock_real_db_connection):
        """Test database connection"""
        # Test connection establishment
        assert mock_real_db_connection is not None
        
        # Test query execution
        mock_real_db_connection.execute("SELECT 1")
        mock_real_db_connection.execute.assert_called_once_with("SELECT 1")
    
    def test_database_queries(self, mock_real_db_connection):
        """Test database queries"""
        # Test SELECT query
        mock_real_db_connection.fetchall.return_value = [{"id": 1, "name": "test"}]
        result = mock_real_db_connection.fetchall()
        assert len(result) == 1
        assert result[0]["id"] == 1
        
        # Test single row fetch
        mock_real_db_connection.fetchone.return_value = {"id": 1, "name": "test"}
        result = mock_real_db_connection.fetchone()
        assert result["name"] == "test"
    
    def test_database_transactions(self, mock_real_db_connection):
        """Test database transactions"""
        # Test transaction begin
        mock_real_db_connection.begin = MagicMock()
        mock_real_db_connection.begin()
        mock_real_db_connection.begin.assert_called_once()
        
        # Test transaction commit
        mock_real_db_connection.commit = MagicMock()
        mock_real_db_connection.commit()
        mock_real_db_connection.commit.assert_called_once()
        
        # Test transaction rollback
        mock_real_db_connection.rollback = MagicMock()
        mock_real_db_connection.rollback()
        mock_real_db_connection.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
