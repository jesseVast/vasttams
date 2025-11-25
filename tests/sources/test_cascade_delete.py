#!/usr/bin/env python3
"""
Tests for source cascade deletion fix.

Tests that source deletion properly uses segment service for cleanup.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.sources.service import SourceStorageService
from fastapi import HTTPException


class TestSourceCascadeDelete:
    """Test source cascade deletion"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock SourceStorageService"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = SourceStorageService(mock_db, mock_s3)
        return service
    
    @pytest.mark.asyncio
    async def test_cascade_delete_uses_segment_service(self, mock_service):
        """Test that cascade delete uses segment service instead of raw SQL"""
        source_id = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        flow_id2 = str(uuid.uuid4())
        
        # Mock flow query result
        mock_flows_result = {
            'data': {
                'id': [flow_id1, flow_id2]
            }
        }
        mock_service.vast_db.query.return_value.select.return_value.where.return_value.execute = Mock(
            return_value=mock_flows_result
        )
        
        # Mock segment service
        with patch('vasttamsserver.sources.service.SegmentStorageService') as mock_segment_service_class:
            mock_segment_service = Mock()
            mock_segment_service.delete_flow_segments = AsyncMock(return_value=True)
            mock_segment_service_class.return_value = mock_segment_service
            
            # Mock settings
            with patch('vasttamsserver.sources.service.get_settings') as mock_get_settings:
                mock_settings = Mock()
                mock_get_settings.return_value = mock_settings
                
                # Mock S3 client
                with patch('vasttamsserver.sources.service.get_s3_client') as mock_get_s3:
                    mock_s3_client = Mock()
                    mock_get_s3.return_value = mock_s3_client
                    
                    # Mock flow deletion
                    mock_service.vast_db.query.return_value.delete.return_value.where.return_value.execute = Mock(
                        return_value=True
                    )
                    
                    result = await mock_service._cascade_delete_flows(source_id)
                    
                    assert result is True
                    # Verify segment service was used (not raw SQL)
                    assert mock_segment_service.delete_flow_segments.call_count == 2
                    # Verify it was called for each flow
                    assert mock_segment_service.delete_flow_segments.call_args_list[0][0][0] == flow_id1
                    assert mock_segment_service.delete_flow_segments.call_args_list[1][0][0] == flow_id2
    
    @pytest.mark.asyncio
    async def test_cascade_delete_no_flows(self, mock_service):
        """Test cascade delete when source has no flows"""
        source_id = str(uuid.uuid4())
        
        # Mock empty flow query result
        mock_flows_result = {
            'data': {
                'id': []
            }
        }
        mock_service.vast_db.query.return_value.select.return_value.where.return_value.execute = Mock(
            return_value=mock_flows_result
        )
        
        result = await mock_service._cascade_delete_flows(source_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cascade_delete_handles_segment_service_error(self, mock_service):
        """Test that cascade delete continues even if segment deletion fails for one flow"""
        source_id = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        flow_id2 = str(uuid.uuid4())
        
        # Mock flow query result
        mock_flows_result = {
            'data': {
                'id': [flow_id1, flow_id2]
            }
        }
        mock_service.vast_db.query.return_value.select.return_value.where.return_value.execute = Mock(
            return_value=mock_flows_result
        )
        
        # Mock segment service with one failure
        with patch('vasttamsserver.sources.service.SegmentStorageService') as mock_segment_service_class:
            mock_segment_service = Mock()
            mock_segment_service.delete_flow_segments = AsyncMock(side_effect=[
                Exception("Segment deletion failed"),
                True  # Second one succeeds
            ])
            mock_segment_service_class.return_value = mock_segment_service
            
            with patch('vasttamsserver.sources.service.get_settings'):
                with patch('vasttamsserver.sources.service.get_s3_client') as mock_get_s3:
                    mock_s3_client = Mock()
                    mock_get_s3.return_value = mock_s3_client
                    
                    mock_service.vast_db.query.return_value.delete.return_value.where.return_value.execute = Mock(
                        return_value=True
                    )
                    
                    # Should not raise exception, should continue
                    result = await mock_service._cascade_delete_flows(source_id)
                    
                    # Should still return True (flows were deleted)
                    assert result is True
                    # Both flows should have been attempted
                    assert mock_segment_service.delete_flow_segments.call_count == 2

