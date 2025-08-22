"""
Shared Mock VASTDBManager for Testing

This module provides a centralized mock implementation of the VastDBManager
that can be imported and used across all test modules to ensure consistency.
"""

from unittest.mock import MagicMock, AsyncMock
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pyarrow import Schema, field, Table
import pandas as pd

from app.models.models import VideoFlow, FlowSegment, Source, Object


class MockVastDBManager:
    """Mock implementation of VastDBManager for testing"""
    
    def __init__(self):
        """Initialize mock manager with test data"""
        self.test_data = {
            'sources': {},
            'flows': {},
            'segments': {},
            'objects': {}
        }
        self.connection_manager = MagicMock()
        self.cache_manager = MagicMock()
        self.performance_monitor = MagicMock()
        self.time_series_analytics = MagicMock()
        self.aggregation_analytics = MagicMock()
        self.hybrid_analytics = MagicMock()
        
        # Mock connection
        self.connection_manager.get_connection.return_value = MagicMock()
        self.connection_manager.get_bucket.return_value = "test-bucket"
        self.connection_manager.get_schema.return_value = "test-schema"
        
        # Setup mock methods
        self._setup_mock_methods()
    
    def _setup_mock_methods(self):
        """Setup all mock methods with realistic behavior"""
        # Source operations
        self.create_source = MagicMock(side_effect=self._mock_create_source)
        self.get_source = MagicMock(side_effect=self._mock_get_source)
        self.update_source = MagicMock(side_effect=self._mock_update_source)
        self.delete_source = MagicMock(side_effect=self._mock_delete_source)
        self.list_sources = MagicMock(side_effect=self._mock_list_sources)
        
        # Flow operations
        self.create_flow = MagicMock(side_effect=self._mock_create_flow)
        self.get_flow = MagicMock(side_effect=self._mock_get_flow)
        self.update_flow = MagicMock(side_effect=self._mock_update_flow)
        self.delete_flow = MagicMock(side_effect=self._mock_delete_flow)
        self.list_flows = MagicMock(side_effect=self._mock_list_flows)
        
        # Segment operations
        self.create_segment = MagicMock(side_effect=self._mock_create_segment)
        self.get_segment = MagicMock(side_effect=self._mock_get_segment)
        self.update_segment = MagicMock(side_effect=self._mock_update_segment)
        self.delete_segment = MagicMock(side_effect=self._mock_delete_segment)
        self.list_segments = MagicMock(side_effect=self._mock_list_segments)
        
        # Object operations
        self.create_object = MagicMock(side_effect=self._mock_create_object)
        self.get_object = MagicMock(side_effect=self._mock_get_object)
        self.update_object = MagicMock(side_effect=self._mock_update_object)
        self.delete_object = MagicMock(side_effect=self._mock_delete_object)
        self.list_objects = MagicMock(side_effect=self._mock_list_objects)
        
        # Analytics operations
        self.get_analytics = MagicMock(side_effect=self._mock_get_analytics)
        self.get_time_series = MagicMock(side_effect=self._mock_get_time_series)
        self.get_aggregations = MagicMock(side_effect=self._mock_get_aggregations)
    
    def _mock_create_source(self, source_data: Dict[str, Any]) -> Source:
        """Mock source creation"""
        source_id = uuid.uuid4()
        source = Source(
            id=source_id,
            format=source_data.get('format', 'urn:x-nmos:format:video'),
            label=source_data.get('label', 'Test Source'),
            description=source_data.get('description', 'Test Description'),
            created_by=source_data.get('created_by', 'test-user'),
            updated_by=source_data.get('updated_by', 'test-user'),
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc)
        )
        self.test_data['sources'][source_id] = source
        return source
    
    def _mock_get_source(self, source_id: str) -> Optional[Source]:
        """Mock source retrieval"""
        # Convert string ID to UUID if needed
        if isinstance(source_id, str):
            try:
                source_id = uuid.UUID(source_id)
            except ValueError:
                return None
        return self.test_data['sources'].get(source_id)
    
    def _mock_update_source(self, source_id: str, update_data: Dict[str, Any]) -> Optional[Source]:
        """Mock source update"""
        if isinstance(source_id, str):
            try:
                source_id = uuid.UUID(source_id)
            except ValueError:
                return None
        
        source = self.test_data['sources'].get(source_id)
        if source:
            for key, value in update_data.items():
                if hasattr(source, key):
                    setattr(source, key, value)
            source.updated = datetime.now(timezone.utc)
            return source
        return None
    
    def _mock_delete_source(self, source_id: str) -> bool:
        """Mock source deletion"""
        if isinstance(source_id, str):
            try:
                source_id = uuid.UUID(source_id)
            except ValueError:
                return False
        
        if source_id in self.test_data['sources']:
            del self.test_data['sources'][source_id]
            return True
        return False
    
    def _mock_list_sources(self, filters: Optional[Dict[str, Any]] = None) -> List[Source]:
        """Mock source listing"""
        sources = list(self.test_data['sources'].values())
        if filters:
            # Apply basic filtering
            if 'format' in filters:
                sources = [s for s in sources if s.format == filters['format']]
        return sources
    
    def _mock_create_flow(self, flow_data: Dict[str, Any]) -> VideoFlow:
        """Mock flow creation"""
        flow_id = uuid.uuid4()
        source_id = flow_data.get('source_id', uuid.uuid4())
        if isinstance(source_id, str):
            try:
                source_id = uuid.UUID(source_id)
            except ValueError:
                source_id = uuid.uuid4()
        
        flow = VideoFlow(
            id=flow_id,
            source_id=source_id,
            format=flow_data.get('format', 'urn:x-nmos:format:video'),
            codec=flow_data.get('codec', 'video/mp4'),
            label=flow_data.get('label', 'Test Flow'),
            description=flow_data.get('description', 'Test Description'),
            created_by=flow_data.get('created_by', 'test-user'),
            updated_by=flow_data.get('updated_by', 'test-user'),
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            segments_updated=datetime.now(timezone.utc),
            metadata_version="1.0",
            generation=0,
            frame_width=1920,
            frame_height=1080,
            frame_rate="25:1"
        )
        self.test_data['flows'][flow_id] = flow
        return flow
    
    def _mock_get_flow(self, flow_id: str) -> Optional[VideoFlow]:
        """Mock flow retrieval"""
        if isinstance(flow_id, str):
            try:
                flow_id = uuid.UUID(flow_id)
            except ValueError:
                return None
        return self.test_data['flows'].get(flow_id)
    
    def _mock_update_flow(self, flow_id: str, update_data: Dict[str, Any]) -> Optional[VideoFlow]:
        """Mock flow update"""
        if isinstance(flow_id, str):
            try:
                flow_id = uuid.UUID(flow_id)
            except ValueError:
                return None
        
        flow = self.test_data['flows'].get(flow_id)
        if flow:
            for key, value in update_data.items():
                if hasattr(flow, key):
                    setattr(flow, key, value)
            flow.metadata_updated = datetime.now(timezone.utc)
            return flow
        return None
    
    def _mock_delete_flow(self, flow_id: str) -> bool:
        """Mock flow deletion"""
        if isinstance(flow_id, str):
            try:
                flow_id = uuid.UUID(flow_id)
            except ValueError:
                return False
        
        if flow_id in self.test_data['flows']:
            del self.test_data['flows'][flow_id]
            return True
        return False
    
    def _mock_list_flows(self, filters: Optional[Dict[str, Any]] = None) -> List[VideoFlow]:
        """Mock flow listing"""
        flows = list(self.test_data['flows'].values())
        if filters:
            # Apply basic filtering
            if 'source_id' in filters:
                source_id = filters['source_id']
                if isinstance(source_id, str):
                    try:
                        source_id = uuid.UUID(source_id)
                    except ValueError:
                        return []
                flows = [f for f in flows if f.source_id == source_id]
        return flows
    
    def _mock_create_segment(self, segment_data: Dict[str, Any]) -> FlowSegment:
        """Mock segment creation"""
        segment_id = str(uuid.uuid4())
        flow_id = segment_data.get('flow_id', uuid.uuid4())
        if isinstance(flow_id, str):
            try:
                flow_id = uuid.UUID(flow_id)
            except ValueError:
                flow_id = uuid.uuid4()
        
        # Create TAMS-compliant timerange
        start_time = segment_data.get('start_time', datetime.now(timezone.utc))
        end_time = segment_data.get('end_time', start_time + timedelta(minutes=5))
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        timerange = f"[{start_ts}:0_{end_ts}:0]"
        
        segment = FlowSegment(
            object_id=segment_id,
            timerange=timerange,
            storage_path=segment_data.get('storage_path', '/test/path')
        )
        self.test_data['segments'][segment_id] = segment
        return segment
    
    def _mock_get_segment(self, segment_id: str) -> Optional[FlowSegment]:
        """Mock segment retrieval"""
        return self.test_data['segments'].get(segment_id)
    
    def _mock_update_segment(self, segment_id: str, update_data: Dict[str, Any]) -> Optional[FlowSegment]:
        """Mock segment update"""
        segment = self.test_data['segments'].get(segment_id)
        if segment:
            for key, value in update_data.items():
                if hasattr(segment, key):
                    setattr(segment, key, value)
            return segment
        return None
    
    def _mock_delete_segment(self, segment_id: str) -> bool:
        """Mock segment deletion"""
        if segment_id in self.test_data['segments']:
            del self.test_data['segments'][segment_id]
            return True
        return False
    
    def _mock_list_segments(self, filters: Optional[Dict[str, Any]] = None) -> List[FlowSegment]:
        """Mock segment listing"""
        segments = list(self.test_data['segments'].values())
        if filters:
            # Apply basic filtering
            if 'flow_id' in filters:
                # Note: FlowSegment doesn't have flow_id field in TAMS spec
                # This is a simplified mock for testing
                pass
        return segments
    
    def _mock_create_object(self, object_data: Dict[str, Any]) -> Object:
        """Mock object creation"""
        object_id = str(uuid.uuid4())
        referenced_by_flows = object_data.get('referenced_by_flows', [str(uuid.uuid4())])
        
        obj = Object(
            id=object_id,
            referenced_by_flows=referenced_by_flows,
            first_referenced_by_flow=referenced_by_flows[0] if referenced_by_flows else None,
            size=object_data.get('size', 1024),
            created=datetime.now(timezone.utc)
        )
        self.test_data['objects'][object_id] = obj
        return obj
    
    def _mock_get_object(self, object_id: str) -> Optional[Object]:
        """Mock object retrieval"""
        return self.test_data['objects'].get(object_id)
    
    def _mock_update_object(self, object_id: str, update_data: Dict[str, Any]) -> Optional[Object]:
        """Mock object update"""
        obj = self.test_data['objects'].get(object_id)
        if obj:
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            return obj
        return None
    
    def _mock_delete_object(self, object_id: str) -> bool:
        """Mock object deletion"""
        if object_id in self.test_data['objects']:
            del self.test_data['objects'][object_id]
            return True
        return False
    
    def _mock_list_objects(self, filters: Optional[Dict[str, Any]] = None) -> List[Object]:
        """Mock object listing"""
        objects = list(self.test_data['objects'].values())
        if filters:
            # Apply basic filtering
            if 'type' in filters:
                # Note: Object doesn't have type field in TAMS spec
                # This is a simplified mock for testing
                pass
        return objects
    
    def _mock_get_analytics(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock analytics query"""
        return {
            'total_sources': len(self.test_data['sources']),
            'total_flows': len(self.test_data['flows']),
            'total_segments': len(self.test_data['segments']),
            'total_objects': len(self.test_data['objects']),
            'query_params': query_params
        }
    
    def _mock_get_time_series(self, time_range: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock time series data"""
        return [
            {'timestamp': datetime.now(timezone.utc), 'value': 10},
            {'timestamp': datetime.now(timezone.utc) + timedelta(hours=1), 'value': 15},
            {'timestamp': datetime.now(timezone.utc) + timedelta(hours=2), 'value': 12}
        ]
    
    def _mock_get_aggregations(self, aggregation_params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock aggregation data"""
        return {
            'count_by_type': {
                'urn:x-nmos:format:video': len([s for s in self.test_data['sources'].values() if s.format == 'urn:x-nmos:format:video']),
                'urn:x-nmos:format:audio': len([s for s in self.test_data['sources'].values() if s.format == 'urn:x-nmos:format:audio'])
            },
            'total_duration': sum(
                (f.metadata_updated - f.created).total_seconds() 
                for f in self.test_data['flows'].values()
                if f.metadata_updated and f.created
            )
        }
    
    def reset_test_data(self):
        """Reset all test data to empty state"""
        self.test_data = {
            'sources': {},
            'flows': {},
            'segments': {},
            'objects': {}
        }
    
    def add_test_data(self, data_type: str, items: List[Any]):
        """Add test data of specified type"""
        if data_type in self.test_data:
            for item in items:
                if hasattr(item, 'id'):
                    self.test_data[data_type][item.id] = item


# Global mock instance for easy import
mock_vastdbmanager = MockVastDBManager()
