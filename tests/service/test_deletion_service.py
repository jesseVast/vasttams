"""
Unit tests for deletion request service
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.service.deletion_service import DeletionRequestService
from vasttamsserver.common.models import TimeRange


@pytest.fixture
def mock_vast_db():
    """Create a mock VAST database"""
    db = MagicMock()
    db.get_qualified_table_name = lambda table: f"test_{table}"
    db.execute_sql = MagicMock(return_value=None)
    return db


@pytest.fixture
def deletion_service(mock_vast_db):
    """Create a deletion service instance"""
    return DeletionRequestService(mock_vast_db)


class TestDeletionRequestService:
    """Test DeletionRequestService"""
    
    @pytest.mark.asyncio
    async def test_create_deletion_request(self, deletion_service, mock_vast_db):
        """Test creating a deletion request"""
        flow_id = str(uuid.uuid4())
        timerange = TimeRange(value="[0:0_100:0)")
        
        # Mock execute_sql to simulate successful insert
        mock_vast_db.execute_sql.return_value = None
        
        request = await deletion_service.create_deletion_request(
            flow_id=flow_id,
            timerange_to_delete=timerange,
            delete_flow=False,
            created_by="test_user"
        )
        
        assert request.id is not None
        assert request.flow_id == flow_id
        assert request.timerange_to_delete == timerange
        assert request.delete_flow is False
        assert request.status == "created"
        assert request.created_by == "test_user"
        assert request.error is None
        
        # Verify execute_sql was called
        assert mock_vast_db.execute_sql.called
    
    @pytest.mark.asyncio
    async def test_get_deletion_request(self, deletion_service, mock_vast_db):
        """Test getting a deletion request"""
        request_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        # Mock database result
        mock_vast_db.execute_sql.return_value = {
            'data': {
                'id': [request_id],
                'flow_id': [flow_id],
                'timerange_to_delete': ['[0:0_100:0)'],
                'delete_flow': [False],
                'status': ['created'],
                'timerange_remaining': ['[0:0_100:0)'],
                'created': ['2024-01-01T00:00:00'],
                'created_by': ['test_user'],
                'updated': ['2024-01-01T00:00:00'],
                'expiry': ['2024-01-08T00:00:00'],
                'error': [None]
            }
        }
        
        request = await deletion_service.get_deletion_request(request_id)
        
        assert request is not None
        assert request.id == request_id
        assert request.flow_id == flow_id
        assert request.status == 'created'
    
    @pytest.mark.asyncio
    async def test_get_deletion_request_not_found(self, deletion_service, mock_vast_db):
        """Test getting a non-existent deletion request"""
        request_id = str(uuid.uuid4())
        
        # Mock empty result
        mock_vast_db.execute_sql.return_value = None
        
        request = await deletion_service.get_deletion_request(request_id)
        
        assert request is None
    
    @pytest.mark.asyncio
    async def test_update_deletion_request_status(self, deletion_service, mock_vast_db):
        """Test updating deletion request status"""
        request_id = str(uuid.uuid4())
        
        # Mock successful update
        mock_vast_db.execute_sql.return_value = None
        
        result = await deletion_service.update_deletion_request_status(
            request_id=request_id,
            status="started"
        )
        
        assert result is True
        assert mock_vast_db.execute_sql.called
    
    @pytest.mark.asyncio
    async def test_process_deletion_request_not_found(self, deletion_service, mock_vast_db):
        """Test processing a non-existent deletion request"""
        request_id = str(uuid.uuid4())
        
        # Mock get_deletion_request to return None
        with patch.object(deletion_service, 'get_deletion_request', return_value=None):
            mock_segment_service = AsyncMock()
            
            await deletion_service.process_deletion_request(
                request_id=request_id,
                segment_service=mock_segment_service
            )
            
            # Should update status to error
            assert mock_vast_db.execute_sql.called
    
    @pytest.mark.asyncio
    async def test_get_deletion_requests(self, deletion_service, mock_vast_db):
        """Test getting all deletion requests"""
        # Mock database result with multiple requests
        req1_id = str(uuid.uuid4())
        req2_id = str(uuid.uuid4())
        flow1_id = str(uuid.uuid4())
        flow2_id = str(uuid.uuid4())
        
        mock_vast_db.execute_sql.return_value = {
            'data': {
                'id': [req1_id, req2_id],
                'flow_id': [flow1_id, flow2_id],
                'timerange_to_delete': ['[0:0_100:0)', '[0:0_200:0)'],
                'delete_flow': [False, False],
                'status': ['created', 'started'],
                'timerange_remaining': ['[0:0_100:0)', '[0:0_200:0)'],
                'created': ['2024-01-01T00:00:00', '2024-01-01T01:00:00'],
                'created_by': ['user1', 'user2'],
                'updated': ['2024-01-01T00:00:00', '2024-01-01T01:00:00'],
                'expiry': ['2024-01-08T00:00:00', '2024-01-08T01:00:00'],
                'error': [None, None]
            }
        }
        
        requests = await deletion_service.get_deletion_requests()
        
        assert len(requests) == 2
        assert requests[0].id == req1_id
        assert requests[1].id == req2_id

