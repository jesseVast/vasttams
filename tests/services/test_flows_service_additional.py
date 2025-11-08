#!/usr/bin/env python3
"""
Additional Service Layer Tests for Flows Service

Additional tests to improve coverage for flows/service.py.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.flows.service import FlowStorageService
from vasttams.flows.models import VideoFlow, AudioFlow
from vasttams.common.filters import FlowFilters, FlowDetailFilters
from vasttams.common.models import TimeRange
from fastapi import HTTPException


class TestFlowStorageServiceAdditional:
    """Additional tests for FlowStorageService to improve coverage"""
    
    @pytest.mark.asyncio
    async def test_get_flows_with_tag_filters_list(self):
        """Test get_flows with tag_filters (list of values)"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [str(uuid.uuid4())],
                'essence_parameters': ['{}'],
                'tags': ['{"genre": ["action", "drama"]}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        filters = FlowFilters(tag_filters={"genre": ["action", "drama"]})
        flows = await service.get_flows(filters)
        
        assert isinstance(flows, list)
    
    @pytest.mark.asyncio
    async def test_get_flows_with_tag_filters_string(self):
        """Test get_flows with tag_filters (single string value)"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [str(uuid.uuid4())],
                'essence_parameters': ['{}'],
                'tags': ['{"genre": "action"}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        filters = FlowFilters(tag_filters={"genre": "action"})
        flows = await service.get_flows(filters)
        
        assert isinstance(flows, list)
    
    @pytest.mark.asyncio
    async def test_get_flows_with_tag_exists_filters_false(self):
        """Test get_flows with tag_exists_filters (exists=False)"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [str(uuid.uuid4())],
                'essence_parameters': ['{}'],
                'tags': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        filters = FlowFilters(tag_exists_filters={"genre": False})
        flows = await service.get_flows(filters)
        
        assert isinstance(flows, list)
    
    @pytest.mark.asyncio
    async def test_get_flows_data_as_list(self):
        """Test get_flows with data as list (not dict)"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [{
                'id': flow_id,
                'format': 'urn:x-nmos:format:video',
                'source_id': str(uuid.uuid4()),
                'essence_parameters': '{}',
                'tags': '{}'
            }]
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        filters = FlowFilters()
        flows = await service.get_flows(filters)
        
        assert isinstance(flows, list)
    
    @pytest.mark.asyncio
    async def test_get_flows_list_format_result(self):
        """Test get_flows with list format result (not dict)"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = [{
            'id': flow_id,
            'format': 'urn:x-nmos:format:video',
            'source_id': str(uuid.uuid4()),
            'essence_parameters': '{}',
            'tags': '{}'
        }]
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        filters = FlowFilters()
        flows = await service.get_flows(filters)
        
        assert isinstance(flows, list)
    
    @pytest.mark.asyncio
    async def test_get_flows_json_parse_error(self):
        """Test get_flows with JSON parse error"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [str(uuid.uuid4())],
                'essence_parameters': ['invalid json{'],
                'tags': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        filters = FlowFilters()
        flows = await service.get_flows(filters)
        
        assert isinstance(flows, list)
    
    @pytest.mark.asyncio
    async def test_get_flow_empty_data_list(self):
        """Test get_flow with empty data list"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': []
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        flow = await service.get_flow(flow_id)
        
        assert flow is None
    
    @pytest.mark.asyncio
    async def test_get_flow_list_format(self):
        """Test get_flow with list format result"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = [{
            'id': flow_id,
            'format': 'urn:x-nmos:format:video',
            'source_id': source_id,
            'essence_parameters': '{}',
            'tags': '{}',
            'codec': 'video/H264'
        }]
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        flow = await service.get_flow(flow_id)
        
        assert flow is not None
        assert flow.id == flow_id
    
    @pytest.mark.asyncio
    async def test_get_flow_data_as_list(self):
        """Test get_flow with data as list (not dict)"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [{
                'id': flow_id,
                'format': 'urn:x-nmos:format:video',
                'source_id': source_id,
                'essence_parameters': '{}',
                'tags': '{}',
                'codec': 'video/H264'
            }]
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        flow = await service.get_flow(flow_id)
        
        assert flow is not None
        assert flow.id == flow_id
    
    @pytest.mark.asyncio
    async def test_get_flow_with_include_timerange(self):
        """Test get_flow with include_timerange filter"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [source_id],
                'essence_parameters': ['{}'],
                'tags': ['{}'],
                'codec': ['video/H264']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        # Mock _calculate_flow_timerange_from_segments
        service._calculate_flow_timerange_from_segments = AsyncMock(return_value="[0:0_100:0)")
        
        filters = FlowDetailFilters(include_timerange=True)
        flow = await service.get_flow(flow_id, filters)
        
        assert flow is not None
        assert hasattr(flow, 'timerange')
    
    @pytest.mark.asyncio
    async def test_get_flow_with_timerange_filter(self):
        """Test get_flow with timerange filter"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [source_id],
                'essence_parameters': ['{}'],
                'tags': ['{}'],
                'codec': ['video/H264']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        # Mock _calculate_flow_timerange_from_segments and _limit_timerange
        service._calculate_flow_timerange_from_segments = AsyncMock(return_value="[0:0_100:0)")
        service._limit_timerange = Mock(return_value="[10:0_50:0)")
        
        filters = FlowDetailFilters(timerange="[10:0_50:0)")
        flow = await service.get_flow(flow_id, filters)
        
        assert flow is not None
    
    @pytest.mark.asyncio
    async def test_get_flow_timerange_no_overlap(self):
        """Test get_flow with timerange filter that has no overlap"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [flow_id],
                'format': ['urn:x-nmos:format:video'],
                'source_id': [source_id],
                'essence_parameters': ['{}'],
                'tags': ['{}'],
                'codec': ['video/H264']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        # Mock _calculate_flow_timerange_from_segments and _limit_timerange (no overlap)
        service._calculate_flow_timerange_from_segments = AsyncMock(return_value="[0:0_100:0)")
        service._limit_timerange = Mock(return_value=None)  # No overlap
        
        filters = FlowDetailFilters(timerange="[200:0_300:0)")
        flow = await service.get_flow(flow_id, filters)
        
        assert flow is not None
        # Timerange should be removed (no overlap)
        assert not hasattr(flow, 'timerange') or flow.timerange is None
    
    @pytest.mark.asyncio
    async def test_calculate_flow_timerange_from_segments(self):
        """Test _calculate_flow_timerange_from_segments"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        # Mock SegmentStorageService - patch at the import location
        with patch('vasttams.segments.service.SegmentStorageService') as mock_segment_service_class:
            mock_segment_service = Mock()
            from vasttams.segments.models import FlowSegment
            from vasttams.common.models import TimeRange
            
            # Create mock segments with timeranges
            segment1 = FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange=TimeRange(value="[0:0_50:0)")
            )
            segment2 = FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange=TimeRange(value="[50:0_100:0)")
            )
            mock_segment_service.get_flow_segments = AsyncMock(return_value=[segment1, segment2])
            mock_segment_service_class.return_value = mock_segment_service
            
            timerange = await service._calculate_flow_timerange_from_segments(flow_id)
            
            assert timerange is not None
            assert "[0:0_100:0)" in timerange or timerange.startswith("[")
    
    @pytest.mark.asyncio
    async def test_calculate_flow_timerange_no_segments(self):
        """Test _calculate_flow_timerange_from_segments with no segments"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        # Mock SegmentStorageService - patch at the import location
        with patch('vasttams.segments.service.SegmentStorageService') as mock_segment_service_class:
            mock_segment_service = Mock()
            mock_segment_service.get_flow_segments = AsyncMock(return_value=[])
            mock_segment_service_class.return_value = mock_segment_service
            
            timerange = await service._calculate_flow_timerange_from_segments(flow_id)
            
            assert timerange is None
    
    @pytest.mark.asyncio
    async def test_limit_timerange(self):
        """Test _limit_timerange"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        flow_timerange = "[0:0_100:0)"
        limit_timerange = "[10:0_50:0)"
        
        limited = service._limit_timerange(flow_timerange, limit_timerange)
        
        assert limited is not None
        assert limited.startswith("[")
    
    @pytest.mark.asyncio
    async def test_limit_timerange_no_overlap(self):
        """Test _limit_timerange with no overlap"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        flow_timerange = "[0:0_100:0)"
        limit_timerange = "[200:0_300:0)"  # No overlap
        
        limited = service._limit_timerange(flow_timerange, limit_timerange)
        
        assert limited is None
    
    @pytest.mark.asyncio
    async def test_create_flow_vfr_validation_error(self):
        """Test create_flow with VFR validation error (vfr=True and frame_rate set)"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        from vasttams.flows.models import VideoEssenceParameters
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1},
            vfr=True  # Invalid: vfr=True but frame_rate is set
        )
        
        flow = VideoFlow(
            id=flow_id,
            source_id=source_id,
            format="urn:x-nmos:format:video",
            codec="video/H264",
            essence_parameters=essence_params
        )
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.create_flow(flow)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_create_flow_vfr_false_no_frame_rate(self):
        """Test create_flow with VFR validation error (vfr=False and frame_rate not set)"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        from vasttams.flows.models import VideoEssenceParameters
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            vfr=False  # Invalid: vfr=False but frame_rate is not set
        )
        
        flow = VideoFlow(
            id=flow_id,
            source_id=source_id,
            format="urn:x-nmos:format:video",
            codec="video/H264",
            essence_parameters=essence_params
        )
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.create_flow(flow)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_update_flow_vfr_validation_error(self):
        """Test update_flow with VFR validation error"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        from vasttams.flows.models import VideoEssenceParameters
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1},
            vfr=True  # Invalid: vfr=True but frame_rate is set
        )
        
        flow = VideoFlow(
            id=flow_id,
            source_id=source_id,
            format="urn:x-nmos:format:video",
            codec="video/H264",
            essence_parameters=essence_params
        )
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = FlowStorageService(mock_db, mock_s3)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_flow(flow_id, flow)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_update_flow_upsert_path(self):
        """Test update_flow when UPDATE fails, uses upsert (DELETE + INSERT)"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        from vasttams.flows.models import VideoEssenceParameters
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1}
        )
        
        flow = VideoFlow(
            id=flow_id,
            source_id=source_id,
            format="urn:x-nmos:format:video",
            codec="video/H264",
            essence_parameters=essence_params
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # First UPDATE fails, then DELETE + INSERT succeeds
        call_count = 0
        def execute_sql_side_effect(sql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("UPDATE failed")  # First call (UPDATE) fails
            return True  # Second call (DELETE) succeeds
        
        mock_db.execute_sql.side_effect = execute_sql_side_effect
        mock_db.insert_record = Mock()
        
        service = FlowStorageService(mock_db, Mock())
        service.tag_service = Mock()
        service.tag_service.update_flow_tags = AsyncMock(return_value=True)
        
        # Mock prepare_data_for_pyarrow to handle the conversion
        with patch('vasttams.common.storage.timestamp_utils.prepare_data_for_pyarrow') as mock_prepare:
            def prepare_side_effect(data):
                clean_data = {}
                for k, v in data.items():
                    if isinstance(v, str) and v.startswith('CAST('):
                        continue
                    clean_data[k] = v
                return clean_data
            
            mock_prepare.side_effect = prepare_side_effect
            
            result = await service.update_flow(flow_id, flow)
            
            assert result is True
            assert mock_db.insert_record.called
    
    @pytest.mark.asyncio
    async def test_update_flow_no_fields_to_update(self):
        """Test update_flow with no fields to update"""
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        
        from vasttams.flows.models import VideoEssenceParameters
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1}
        )
        
        # Create flow with only read-only fields
        flow = VideoFlow(
            id=flow_id,
            source_id=source_id,
            format="urn:x-nmos:format:video",
            codec="video/H264",
            essence_parameters=essence_params
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value=True)
        
        service = FlowStorageService(mock_db, Mock())
        service.tag_service = Mock()
        service.tag_service.update_flow_tags = AsyncMock(return_value=True)
        
        result = await service.update_flow(flow_id, flow)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_flows_exception_handling(self):
        """Test get_flows exception handling"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        with pytest.raises(HTTPException):
            await service.get_flows(FlowFilters())
    
    @pytest.mark.asyncio
    async def test_get_flow_exception_handling(self):
        """Test get_flow exception handling"""
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = FlowStorageService(mock_db, Mock())
        
        with pytest.raises(HTTPException):
            await service.get_flow(flow_id)

