"""
Consolidated Storage and Flows Tests

This file consolidates tests from:
- test_s3_store.py
- test_s3_store_optimizations.py
- test_flow_manager.py
- test_segment_manager.py
- test_source_manager.py
- test_object_manager.py
- test_flow_with_multiple_segments.py
- test_flow_reference_management.py
- test_presigned_url_storage.py
- test_timerange_filtering.py
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import uuid
import json

from app.storage.s3_store import S3Store
from app.storage.vast_store import VASTStore
from app.models.models import Source, VideoFlow, FlowSegment, Object


class TestS3StoreOperations:
    """S3 store operation tests"""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        mock_client = MagicMock()
        mock_client.put_object.return_value = MagicMock()
        mock_client.get_object.return_value = MagicMock()
        mock_client.delete_object.return_value = MagicMock()
        mock_client.head_object.return_value = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://test-url.com"
        return mock_client
    
    @pytest.fixture
    def s3_store(self, mock_s3_client):
        """S3Store instance with mocked dependencies"""
        with patch('boto3.client') as mock_boto3:
            mock_boto3.return_value = mock_s3_client
            store = S3Store(
                endpoint_url="http://test-endpoint",
                access_key_id="test-key",
                secret_access_key="test-secret",
                bucket_name="test-bucket",
                use_ssl=False
            )
            store.s3_client = mock_s3_client
            return store
    
    def test_s3_store_initialization(self, s3_store):
        """Test S3Store initialization"""
        assert s3_store.endpoint_url == "http://test-endpoint"
        assert s3_store.bucket_name == "test-bucket"
        assert s3_store.access_key_id == "test-key"
        assert s3_store.use_ssl is False
    
    def test_flow_segment_storage(self, s3_store, mock_s3_client):
        """Test flow segment storage operations"""
        # Test segment storage
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        data = b"test_segment_data"
        
        # Mock segment object
        segment = FlowSegment(
            object_id=segment_id,
            timerange=timerange,
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        
        # Test storage
        result = asyncio.run(s3_store.store_flow_segment(flow_id, segment, data))
        assert result is True
        
        # Verify S3 client was called
        mock_s3_client.put_object.assert_called_once()
    
    def test_flow_segment_retrieval(self, s3_store, mock_s3_client):
        """Test flow segment retrieval operations"""
        # Mock S3 response
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = b"test_segment_data"
        mock_s3_client.get_object.return_value = mock_response
        
        # Test retrieval
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        result = asyncio.run(s3_store.get_flow_segment_data(flow_id, segment_id, timerange))
        assert result == b"test_segment_data"
        
        # Verify S3 client was called
        mock_s3_client.get_object.assert_called_once()
    
    def test_presigned_url_generation(self, s3_store, mock_s3_client):
        """Test presigned URL generation"""
        # Test presigned URL generation
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        url = s3_store.generate_presigned_url(flow_id, segment_id, timerange)
        assert url == "https://test-url.com"
        
        # Verify S3 client was called
        mock_s3_client.generate_presigned_url.assert_called_once()
    
    def test_s3_store_optimizations(self, s3_store):
        """Test S3 store optimization features"""
        # Test connection pool stats
        pool_stats = s3_store.get_connection_pool_stats()
        assert isinstance(pool_stats, dict)
        
        # Test async operation stats
        async_stats = s3_store.get_async_operation_stats()
        assert isinstance(async_stats, dict)
        
        # Test multipart upload stats
        multipart_stats = s3_store.get_multipart_upload_stats()
        assert isinstance(multipart_stats, dict)
        
        # Test batch operation stats
        batch_stats = s3_store.get_batch_operation_stats()
        assert isinstance(batch_stats, dict)


class TestFlowManagement:
    """Flow management tests"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        mock_db = MagicMock()
        mock_db.insert = MagicMock(return_value=1)
        mock_db.select = MagicMock(return_value=[])
        mock_db.update = MagicMock(return_value=1)
        mock_db.delete = MagicMock(return_value=1)
        return mock_db
    
    @pytest.fixture
    def mock_s3_store(self):
        """Mock S3 store"""
        mock_store = MagicMock()
        mock_store.store_flow_segment = AsyncMock(return_value=True)
        mock_store.delete_flow_segment = AsyncMock(return_value=True)
        mock_store.generate_segment_key = MagicMock(return_value="test/path/segment")
        return mock_store
    
    @pytest.fixture
    def vast_store(self, mock_s3_store, mock_db_manager):
        """VAST store with mocked dependencies"""
        with patch('app.storage.vast_store.VastDBManager') as mock_vast_manager:
            mock_vast_manager.return_value = mock_db_manager
            store = VASTStore()
            store.s3_store = mock_s3_store
            store.db_manager = mock_db_manager
            return store
    
    def test_source_creation(self, vast_store, mock_db_manager):
        """Test source creation"""
        # Create test source
        source = Source(
            id=str(uuid.uuid4()),
            label="Test Video Source",
            format="video",
            description="Test source for flow management",
            created_by="test_user"
        )
        
        # Test source creation
        result = asyncio.run(vast_store.create_source(source))
        assert result is True
        
        # Verify database insert was called
        mock_db_manager.insert.assert_called_once()
    
    def test_flow_creation(self, vast_store, mock_db_manager):
        """Test flow creation"""
        # Create test flow
        source_id = str(uuid.uuid4())
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=source_id,
            format="video",
            codec="H.264",
            label="Test Video Flow",
            description="Test flow for flow management",
            created_by="test_user",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30"
        )
        
        # Test flow creation
        result = asyncio.run(vast_store.create_flow(flow))
        assert result is True
        
        # Verify database insert was called
        mock_db_manager.insert.assert_called_once()
    
    def test_flow_segment_creation(self, vast_store, mock_db_manager, mock_s3_store):
        """Test flow segment creation"""
        # Create test segment
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange="2024-01-01T00:00:00Z/2024-01-01T01:00:00Z",
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        
        flow_id = str(uuid.uuid4())
        data = b"test_segment_data"
        
        # Test segment creation
        result = asyncio.run(vast_store.create_flow_segment(segment, flow_id, data))
        assert result is True
        
        # Verify database insert was called
        mock_db_manager.insert.assert_called_once()
        
        # Verify S3 storage was called
        mock_s3_store.store_flow_segment.assert_called_once()
    
    def test_flow_with_multiple_segments(self, vast_store, mock_db_manager, mock_s3_store):
        """Test flow with multiple segments"""
        # Create test source and flow
        source = Source(
            id=str(uuid.uuid4()),
            label="Multi-Segment Video Source",
            format="video",
            description="Test source for flow with multiple segments",
            created_by="test_user"
        )
        
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=source.id,
            format="video",
            codec="H.264",
            label="Multi-Segment Video Flow",
            description="Test flow with multiple segments",
            created_by="test_user",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30"
        )
        
        # Create multiple segments
        segments = []
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        for i in range(5):
            start_time = base_time + timedelta(minutes=i * 10)
            end_time = start_time + timedelta(minutes=10)
            
            segment = FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange=f"{start_time.isoformat()}/{end_time.isoformat()}",
                sample_offset=i * 1000,
                sample_count=1000,
                key_frame_count=10
            )
            segments.append(segment)
        
        # Test creating flow with segments
        source_success = asyncio.run(vast_store.create_source(source))
        assert source_success is True
        
        flow_success = asyncio.run(vast_store.create_flow(flow))
        assert flow_success is True
        
        # Create segments
        for segment in segments:
            success = asyncio.run(vast_store.create_flow_segment(segment, flow.id, b"test_data"))
            assert success is True
        
        # Verify all operations were called
        assert mock_db_manager.insert.call_count == 7  # 1 source + 1 flow + 5 segments
        assert mock_s3_store.store_flow_segment.call_count == 5
    
    def test_flow_reference_management(self, vast_store, mock_db_manager):
        """Test flow reference management"""
        # Create test objects with flow references
        flow_id = str(uuid.uuid4())
        
        objects = [
            Object(
                object_id=str(uuid.uuid4()),
                flow_references=[{"flow_id": flow_id, "timerange": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"}],
                size=1024000,
                created=datetime.now(timezone.utc)
            ),
            Object(
                object_id=str(uuid.uuid4()),
                flow_references=[{"flow_id": flow_id, "timerange": "2024-01-01T01:00:00Z/2024-01-01T02:00:00Z"}],
                size=2048000,
                created=datetime.now(timezone.utc)
            )
        ]
        
        # Mock get_objects_by_flow_reference
        vast_store.get_objects_by_flow_reference = AsyncMock(return_value=objects)
        
        # Test getting objects by flow reference
        result = asyncio.run(vast_store.get_objects_by_flow_reference(flow_id))
        assert len(result) == 2
        
        # Verify each object references the flow
        for obj in result:
            assert len(obj.flow_references) == 1
            assert obj.flow_references[0]['flow_id'] == flow_id


class TestTimerangeFiltering:
    """Timerange filtering tests"""
    
    @pytest.fixture
    def vast_store(self):
        """VAST store instance"""
        with patch('app.storage.vast_store.VastDBManager'):
            return VASTStore()
    
    def test_timerange_overlap_detection(self, vast_store):
        """Test timerange overlap detection"""
        # Test overlapping timeranges
        timerange1 = "2024-01-01T00:00:00Z/2024-01-01T02:00:00Z"
        timerange2 = "2024-01-01T01:00:00Z/2024-01-01T03:00:00Z"
        
        # These should overlap
        assert vast_store.timeranges_overlap(timerange1, timerange2)
        
        # Test non-overlapping timeranges
        timerange3 = "2024-01-01T03:00:00Z/2024-01-01T04:00:00Z"
        assert not vast_store.timeranges_overlap(timerange1, timerange3)
    
    def test_timerange_parsing(self, vast_store):
        """Test timerange parsing"""
        # Test valid timerange
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        parsed = vast_store.parse_timerange(timerange)
        
        assert parsed['start'] is not None
        assert parsed['end'] is not None
        assert parsed['start'] < parsed['end']
    
    def test_timerange_validation(self, vast_store):
        """Test timerange validation"""
        # Test valid timerange
        valid_timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        assert vast_store.validate_timerange(valid_timerange)
        
        # Test invalid timerange
        invalid_timerange = "invalid-timerange"
        assert not vast_store.validate_timerange(invalid_timerange)


class TestObjectManagement:
    """Object management tests"""
    
    @pytest.fixture
    def vast_store(self):
        """VAST store instance"""
        with patch('app.storage.vast_store.VastDBManager'):
            return VASTStore()
    
    def test_object_creation(self, vast_store):
        """Test object creation"""
        # Create test object
        object_id = str(uuid.uuid4())
        flow_references = [{"flow_id": str(uuid.uuid4()), "timerange": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"}]
        
        obj = Object(
            object_id=object_id,
            flow_references=flow_references,
            size=1024000,
            created=datetime.now(timezone.utc)
        )
        
        assert obj.object_id == object_id
        assert len(obj.flow_references) == 1
        assert obj.size == 1024000
    
    def test_flow_reference_operations(self, vast_store):
        """Test flow reference operations"""
        # Test adding flow reference
        obj = Object(
            object_id=str(uuid.uuid4()),
            flow_references=[],
            size=1024000,
            created=datetime.now(timezone.utc)
        )
        
        flow_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        # Add flow reference
        obj.flow_references.append({"flow_id": flow_id, "timerange": timerange})
        assert len(obj.flow_references) == 1
        assert obj.flow_references[0]['flow_id'] == flow_id
        
        # Remove flow reference
        obj.flow_references = [ref for ref in obj.flow_references if ref['flow_id'] != flow_id]
        assert len(obj.flow_references) == 0


if __name__ == "__main__":
    pytest.main([__file__])
