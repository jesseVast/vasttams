#!/usr/bin/env python3
"""
Service Layer Tests for Analytics Service

Tests analytics/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime, timezone

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.analytics.service import AnalyticsService
from vasttams.analytics.models import AnalyticsSummary


class TestAnalyticsService:
    """Test AnalyticsService business logic"""
    
    def test_parse_sql_result_columnar_format(self):
        """Test parsing SQL result in columnar format"""
        service = AnalyticsService(Mock())
        
        # Columnar format (dict with column arrays)
        result = {
            'data': {
                'total_sources': [5],
                'total_flows': [10],
                'total_segments': [20]
            }
        }
        
        parsed = service._parse_sql_result(result)
        assert isinstance(parsed, dict)
        assert parsed['total_sources'] == 5
        assert parsed['total_flows'] == 10
    
    def test_parse_sql_result_list_format(self):
        """Test parsing SQL result in list format"""
        service = AnalyticsService(Mock())
        
        # List format
        result = {
            'data': [
                {'total_sources': 5, 'total_flows': 10}
            ]
        }
        
        parsed = service._parse_sql_result(result)
        assert isinstance(parsed, dict)
        assert parsed['total_sources'] == 5
    
    def test_parse_sql_result_empty(self):
        """Test parsing empty SQL result"""
        service = AnalyticsService(Mock())
        
        result = {'data': {}}
        parsed = service._parse_sql_result(result)
        assert parsed is None
        
        result = {'data': []}
        parsed = service._parse_sql_result(result)
        assert parsed is None
    
    @pytest.mark.asyncio
    async def test_get_summary_success(self):
        """Test get_summary with successful SQL result"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        # Mock SQL execution result
        mock_result = {
            'data': {
                'total_sources': [5],
                'total_flows': [10],
                'total_segments': [20],
                'total_objects': [15],
                'total_storage_bytes': [1000000],
                'avg_size_bytes': [66666.67],
                'min_size_bytes': [1000],
                'max_size_bytes': [100000],
                'object_count_with_size': [15],
                'video_flows': [8],
                'audio_flows': [2],
                'image_flows': [0],
                'data_flows': [0],
                'multi_flows': [0],
                'earliest_source_created': ['2024-01-01T00:00:00Z'],
                'latest_source_created': ['2024-12-31T23:59:59Z'],
                'earliest_flow_created': ['2024-01-01T00:00:00Z'],
                'latest_flow_created': ['2024-12-31T23:59:59Z'],
                'earliest_segment_created': ['2024-01-01T00:00:00Z'],
                'latest_segment_created': ['2024-12-31T23:59:59Z'],
                'earliest_object_created': ['2024-01-01T00:00:00Z'],
                'latest_object_created': ['2024-12-31T23:59:59Z']
            }
        }
        mock_db.execute_sql = Mock(return_value=mock_result)
        
        service = AnalyticsService(mock_db)
        summary = await service.get_summary()
        
        assert isinstance(summary, AnalyticsSummary)
        assert summary.counts.total_sources == 5
        assert summary.counts.total_flows == 10
        assert summary.storage.total_size_bytes == 1000000
    
    @pytest.mark.asyncio
    async def test_get_summary_empty_result(self):
        """Test get_summary with empty SQL result"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = AnalyticsService(mock_db)
        summary = await service.get_summary()
        
        assert isinstance(summary, AnalyticsSummary)
        assert summary.counts.total_sources == 0
        assert summary.counts.total_flows == 0
    
    @pytest.mark.asyncio
    async def test_get_summary_exception_handling(self):
        """Test get_summary handles exceptions gracefully"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(side_effect=Exception("Database error"))
        
        service = AnalyticsService(mock_db)
        summary = await service.get_summary()
        
        # Should return empty summary on error
        assert isinstance(summary, AnalyticsSummary)
        assert summary.counts.total_sources == 0
    
    @pytest.mark.asyncio
    async def test_get_source_analytics(self):
        """Test get_source_analytics"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {'id': 'source1', 'label': 'Source 1', 'flow_count': 2, 'segment_count': 5, 'total_size_bytes': 100000}
            ]
        })
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_source_analytics()
        
        assert isinstance(analytics, list)
        if analytics:
            assert analytics[0].source_id == 'source1'
    
    @pytest.mark.asyncio
    async def test_get_flow_analytics(self):
        """Test get_flow_analytics"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {'id': 'flow1', 'source_id': 'source1', 'segment_count': 3, 'total_size_bytes': 50000, 'format': 'urn:x-nmos:format:video'}
            ]
        })
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_flow_analytics()
        
        assert isinstance(analytics, list)
        if analytics:
            assert analytics[0].flow_id == 'flow1'
    
    def test_parse_sql_result_list_of_arrays(self):
        """Test _parse_sql_result with list of arrays format"""
        service = AnalyticsService(Mock())
        
        result = {
            'data': [[5, 10, 20]],
            'columns': ['total_sources', 'total_flows', 'total_segments']
        }
        
        parsed = service._parse_sql_result(result)
        assert isinstance(parsed, dict)
        assert parsed['total_sources'] == 5
        assert parsed['total_flows'] == 10
    
    def test_parse_sql_result_list_of_dicts(self):
        """Test _parse_sql_result with list of dicts format"""
        service = AnalyticsService(Mock())
        
        result = {
            'data': [
                {'Total_Sources': 5, 'Total_Flows': 10}
            ]
        }
        
        parsed = service._parse_sql_result(result)
        assert isinstance(parsed, dict)
        assert parsed['total_sources'] == 5
        assert parsed['total_flows'] == 10
    
    def test_parse_sql_result_multiple_rows(self):
        """Test _parse_sql_result with multiple rows returns list"""
        service = AnalyticsService(Mock())
        
        result = {
            'data': [
                {'id': 'source1', 'count': 5},
                {'id': 'source2', 'count': 10}
            ]
        }
        
        parsed = service._parse_sql_result(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
    
    def test_parse_sql_result_no_data_key(self):
        """Test _parse_sql_result with no data key"""
        service = AnalyticsService(Mock())
        
        result = {}
        parsed = service._parse_sql_result(result)
        assert parsed is None
    
    def test_parse_sql_result_none_result(self):
        """Test _parse_sql_result with None result"""
        service = AnalyticsService(Mock())
        
        parsed = service._parse_sql_result(None)
        assert parsed is None
    
    def test_parse_datetime_iso_format(self):
        """Test _parse_datetime with ISO format"""
        service = AnalyticsService(Mock())
        
        dt = service._parse_datetime("2024-01-01T00:00:00Z")
        assert dt is not None
        assert isinstance(dt, datetime)
    
    def test_parse_datetime_datetime_object(self):
        """Test _parse_datetime with datetime object"""
        service = AnalyticsService(Mock())
        
        now = datetime.now(timezone.utc)
        dt = service._parse_datetime(now)
        assert dt == now
    
    def test_parse_datetime_none(self):
        """Test _parse_datetime with None"""
        service = AnalyticsService(Mock())
        
        dt = service._parse_datetime(None)
        assert dt is None
    
    def test_parse_datetime_invalid_format(self):
        """Test _parse_datetime with invalid format"""
        service = AnalyticsService(Mock())
        
        dt = service._parse_datetime("invalid-date")
        assert dt is None
    
    def test_calculate_duration_from_timeranges(self):
        """Test _calculate_duration_from_timeranges"""
        service = AnalyticsService(Mock())
        
        timerange_starts = ["0:0", "10:0", "20:0"]
        timerange_ends = ["10:0", "20:0", "30:0"]
        
        duration = service._calculate_duration_from_timeranges(timerange_starts, timerange_ends)
        
        assert duration is not None
        assert duration == 30.0  # Max (30) - Min (0)
    
    def test_calculate_duration_from_timeranges_empty(self):
        """Test _calculate_duration_from_timeranges with empty lists"""
        service = AnalyticsService(Mock())
        
        duration = service._calculate_duration_from_timeranges([], [])
        assert duration is None
    
    def test_calculate_duration_from_timeranges_invalid_format(self):
        """Test _calculate_duration_from_timeranges with invalid format"""
        service = AnalyticsService(Mock())
        
        duration = service._calculate_duration_from_timeranges(["invalid"], ["invalid"])
        assert duration is None
    
    @pytest.mark.asyncio
    async def test_get_summary_with_null_values(self):
        """Test get_summary handles null values correctly"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'total_sources': [5],
                'total_flows': [10],
                'total_segments': [20],
                'total_objects': [15],
                'total_storage_bytes': [1000000],
                'avg_size_bytes': [66666.67],
                'min_size_bytes': [None],
                'max_size_bytes': [None],
                'object_count_with_size': [15],
                'video_flows': [8],
                'audio_flows': [2],
                'image_flows': [0],
                'data_flows': [0],
                'multi_flows': [0],
                'earliest_source_created': [None],
                'latest_source_created': [None],
                'earliest_flow_created': [None],
                'latest_flow_created': [None],
                'earliest_segment_created': [None],
                'latest_segment_created': [None],
                'earliest_object_created': [None],
                'latest_object_created': [None]
            }
        })
        
        service = AnalyticsService(mock_db)
        summary = await service.get_summary()
        
        assert isinstance(summary, AnalyticsSummary)
        assert summary.storage.min_size_bytes is None
        assert summary.storage.max_size_bytes is None
    
    @pytest.mark.asyncio
    async def test_get_source_analytics_empty(self):
        """Test get_source_analytics with empty result"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': []})
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_source_analytics()
        
        assert isinstance(analytics, list)
        assert len(analytics) == 0
    
    @pytest.mark.asyncio
    async def test_get_source_analytics_multiple_sources(self):
        """Test get_source_analytics with multiple sources"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {'id': 'source1', 'label': 'Source 1', 'flow_count': 2, 'segment_count': 5, 'total_size_bytes': 100000},
                {'id': 'source2', 'label': 'Source 2', 'flow_count': 3, 'segment_count': 8, 'total_size_bytes': 200000}
            ]
        })
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_source_analytics()
        
        assert len(analytics) == 2
        assert analytics[0].source_id == 'source1'
        assert analytics[1].source_id == 'source2'
    
    @pytest.mark.asyncio
    async def test_get_source_analytics_exception(self):
        """Test get_source_analytics handles exceptions"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(side_effect=Exception("Database error"))
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_source_analytics()
        
        assert isinstance(analytics, list)
        assert len(analytics) == 0
    
    @pytest.mark.asyncio
    async def test_get_flow_analytics_empty(self):
        """Test get_flow_analytics with empty result"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': []})
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_flow_analytics()
        
        assert isinstance(analytics, list)
        assert len(analytics) == 0
    
    @pytest.mark.asyncio
    async def test_get_flow_analytics_with_duration(self):
        """Test get_flow_analytics with duration calculation"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {
                    'id': 'flow1',
                    'source_id': 'source1',
                    'segment_count': 3,
                    'total_duration_seconds': 120.5,
                    'total_size_bytes': 50000,
                    'format': 'urn:x-nmos:format:video',
                    'label': 'Test Flow',
                    'created': '2024-01-01T00:00:00Z'
                }
            ]
        })
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_flow_analytics()
        
        assert len(analytics) == 1
        assert analytics[0].total_duration_seconds == 120.5
    
    @pytest.mark.asyncio
    async def test_get_flow_analytics_exception(self):
        """Test get_flow_analytics handles exceptions"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(side_effect=Exception("Database error"))
        
        service = AnalyticsService(mock_db)
        analytics = await service.get_flow_analytics()
        
        assert isinstance(analytics, list)
        assert len(analytics) == 0

