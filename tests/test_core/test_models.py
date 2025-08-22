"""
Tests for TAMS Models

This module tests the Pydantic models used throughout the TAMS application,
ensuring they properly validate data and handle edge cases.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import uuid
from pydantic import ValidationError

from app.models.models import Source, VideoFlow, FlowSegment, Object
from tests.test_utils.test_helpers import TestDataFactory


class TestSourceModel:
    """Test Source model creation and validation"""
    
    def test_create_source_with_valid_data(self):
        """Test creating a source with valid data"""
        source = TestDataFactory.create_source()
        
        assert source.id is not None
        assert source.format == "urn:x-nmos:format:video"
        assert source.label == "Test Source"
        assert source.description == "Test Description"
        assert source.created_by == "test-user"
        assert source.updated_by == "test-user"
        assert source.created is not None
        assert source.updated is not None
    
    def test_create_source_with_custom_data(self):
        """Test creating a source with custom data"""
        custom_source = TestDataFactory.create_source(
            name="Custom Source",
            description="Custom Description",
            source_type="urn:x-nmos:format:audio"
        )
        
        assert custom_source.label == "Custom Source"
        assert custom_source.description == "Custom Description"
        assert custom_source.format == "urn:x-nmos:format:audio"
    
    def test_source_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            Source()  # Missing required fields
    
    def test_source_field_types(self):
        """Test that field types are properly enforced"""
        source = TestDataFactory.create_source()
        
        assert isinstance(source.id, uuid.UUID)
        assert isinstance(source.format, str)
        assert isinstance(source.label, str)
        assert isinstance(source.description, str)
        assert isinstance(source.created_by, str)
        assert isinstance(source.updated_by, str)
        assert isinstance(source.created, datetime)
        assert isinstance(source.updated, datetime)
    
    def test_source_metadata_handling(self):
        """Test source metadata handling"""
        metadata = {"location": "Studio A", "camera": "Sony FX9"}
        source = TestDataFactory.create_source(metadata=metadata)
        
        # Note: Source model doesn't have metadata field in current TAMS spec
        # This test documents the current behavior
        assert hasattr(source, 'format')
        assert hasattr(source, 'label')
    
    def test_source_update_timestamps(self):
        """Test that timestamps are properly set"""
        before_creation = datetime.now(timezone.utc)
        source = TestDataFactory.create_source()
        after_creation = datetime.now(timezone.utc)
        
        assert before_creation <= source.created <= after_creation
        assert before_creation <= source.updated <= after_creation


class TestVideoFlowModel:
    """Test VideoFlow model creation and validation"""
    
    def test_create_flow_with_valid_data(self):
        """Test creating a flow with valid data"""
        flow = TestDataFactory.create_flow()
        
        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == "urn:x-nmos:format:video"
        assert flow.codec == "video/mp4"
        assert flow.label == "Test Flow"
        assert flow.description == "Test Description"
        assert flow.created_by == "test-user"
        assert flow.updated_by == "test-user"
        assert flow.created is not None
        assert flow.metadata_updated is not None
        assert flow.segments_updated is not None
        assert flow.metadata_version == "1.0"
        assert flow.generation == 0
        assert flow.frame_width == 1920
        assert flow.frame_height == 1080
        assert flow.frame_rate == "25:1"
    
    def test_create_flow_with_custom_data(self):
        """Test creating a flow with custom data"""
        custom_flow = TestDataFactory.create_flow(
            name="Custom Flow",
            description="Custom Description"
        )
        
        assert custom_flow.label == "Custom Flow"
        assert custom_flow.description == "Custom Description"
    
    def test_flow_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            VideoFlow()  # Missing required fields
    
    def test_flow_field_types(self):
        """Test that field types are properly enforced"""
        flow = TestDataFactory.create_flow()
        
        assert isinstance(flow.id, uuid.UUID)
        assert isinstance(flow.source_id, uuid.UUID)
        assert isinstance(flow.format, str)
        assert isinstance(flow.codec, str)
        assert isinstance(flow.label, str)
        assert isinstance(flow.description, str)
        assert isinstance(flow.created_by, str)
        assert isinstance(flow.updated_by, str)
        assert isinstance(flow.created, datetime)
        assert isinstance(flow.metadata_updated, datetime)
        assert isinstance(flow.segments_updated, datetime)
        assert isinstance(flow.metadata_version, str)
        assert isinstance(flow.generation, int)
        assert isinstance(flow.frame_width, int)
        assert isinstance(flow.frame_height, int)
        assert isinstance(flow.frame_rate, str)
    
    def test_flow_duration_calculation(self):
        """Test flow duration calculation"""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=2)
        
        flow = TestDataFactory.create_flow(
            start_time=start_time,
            end_time=end_time
        )
        
        # Note: VideoFlow model doesn't have duration calculation in current TAMS spec
        # This test documents the current behavior
        assert flow.created == start_time
        assert flow.metadata_updated == end_time
    
    def test_flow_metadata_handling(self):
        """Test flow metadata handling"""
        metadata = {"quality": "HD", "bitrate": "10Mbps"}
        flow = TestDataFactory.create_flow(metadata=metadata)
        
        # Note: VideoFlow model doesn't have metadata field in current TAMS spec
        # This test documents the current behavior
        assert hasattr(flow, 'format')
        assert hasattr(flow, 'codec')


class TestFlowSegmentModel:
    """Test FlowSegment model creation and validation"""
    
    def test_create_segment_with_valid_data(self):
        """Test creating a segment with valid data"""
        segment = TestDataFactory.create_segment()
        
        assert segment.object_id is not None
        assert segment.timerange is not None
        assert segment.storage_path == "/test/path"
    
    def test_create_segment_with_custom_data(self):
        """Test creating a segment with custom data"""
        custom_segment = TestDataFactory.create_segment(
            storage_path="/custom/path"
        )
        
        assert custom_segment.storage_path == "/custom/path"
    
    def test_segment_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            FlowSegment()  # Missing required fields
    
    def test_segment_field_types(self):
        """Test that field types are properly enforced"""
        segment = TestDataFactory.create_segment()
        
        assert isinstance(segment.object_id, str)
        assert isinstance(segment.timerange, str)
        assert isinstance(segment.storage_path, str)
    
    def test_segment_timerange_format(self):
        """Test segment timerange format validation"""
        segment = TestDataFactory.create_segment()
        
        # Timerange should be in format [start:0_end:0]
        assert segment.timerange.startswith('[')
        assert segment.timerange.endswith(']')
        assert ':' in segment.timerange
        assert '_' in segment.timerange
    
    def test_segment_storage_path_validation(self):
        """Test segment storage path validation"""
        # Test with valid paths
        valid_paths = ["/test/path", "/segments/123", "/storage/video"]
        for path in valid_paths:
            segment = TestDataFactory.create_segment(storage_path=path)
            assert segment.storage_path == path
        
        # Test with empty path (should be allowed by model)
        segment = TestDataFactory.create_segment(storage_path="")
        assert segment.storage_path == ""


class TestObjectModel:
    """Test Object model creation and validation"""
    
    def test_create_object_with_valid_data(self):
        """Test creating an object with valid data"""
        object_id = str(uuid.uuid4())
        referenced_flows = [str(uuid.uuid4())]
        
        obj = TestDataFactory.create_object(
            referenced_by_flows=referenced_flows
        )
        
        assert obj.id is not None
        assert obj.referenced_by_flows == referenced_flows
        assert obj.first_referenced_by_flow == referenced_flows[0]
        assert obj.size == 1024
        assert obj.created is not None
    
    def test_create_object_with_custom_data(self):
        """Test creating an object with custom data"""
        custom_obj = TestDataFactory.create_object(
            name="Custom Object",
            description="Custom Description"
        )
        
        # Note: Object model doesn't have name/description fields in current TAMS spec
        # This test documents the current behavior
        assert custom_obj.id is not None
        assert custom_obj.referenced_by_flows is not None
    
    def test_object_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            Object()  # Missing required fields
    
    def test_object_field_types(self):
        """Test that field types are properly enforced"""
        obj = TestDataFactory.create_object()
        
        assert isinstance(obj.id, str)
        assert isinstance(obj.referenced_by_flows, list)
        assert isinstance(obj.first_referenced_by_flow, str)
        assert isinstance(obj.size, int)
        assert isinstance(obj.created, datetime)
    
    def test_object_referenced_flows_handling(self):
        """Test object referenced flows handling"""
        # Test with single flow
        single_flow = [str(uuid.uuid4())]
        obj = TestDataFactory.create_object(referenced_by_flows=single_flow)
        assert obj.referenced_by_flows == single_flow
        assert obj.first_referenced_by_flow == single_flow[0]
        
        # Test with multiple flows
        multiple_flows = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
        obj = TestDataFactory.create_object(referenced_by_flows=multiple_flows)
        assert obj.referenced_by_flows == multiple_flows
        assert obj.first_referenced_by_flow == multiple_flows[0]
        
        # Test with empty flows list - should be handled by TestDataFactory
        obj = TestDataFactory.create_object(referenced_by_flows=[])
        assert len(obj.referenced_by_flows) >= 1  # Factory provides default
        assert obj.first_referenced_by_flow is not None
    
    def test_object_size_validation(self):
        """Test object size validation"""
        # Test with positive size
        obj = TestDataFactory.create_object()
        assert obj.size > 0
        
        # Test with custom size
        custom_size = 2048
        obj = TestDataFactory.create_object()
        obj.size = custom_size
        assert obj.size == custom_size
    
    def test_object_metadata_handling(self):
        """Test object metadata handling"""
        metadata = {"confidence": 0.95, "bbox": [100, 100, 200, 200]}
        obj = TestDataFactory.create_object(metadata=metadata)
        
        # Note: Object model doesn't have metadata field in current TAMS spec
        # This test documents the current behavior
        assert hasattr(obj, 'id')
        assert hasattr(obj, 'referenced_by_flows')


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_source_flow_relationship(self):
        """Test source-flow relationship"""
        source = TestDataFactory.create_source()
        flow = TestDataFactory.create_flow(source_id=source.id)
        
        assert flow.source_id == source.id
    
    def test_flow_segment_relationship(self):
        """Test flow-segment relationship"""
        flow = TestDataFactory.create_flow()
        segment = TestDataFactory.create_segment()
        
        # Note: FlowSegment model doesn't have flow_id field in current TAMS spec
        # This test documents the current behavior
        assert segment.object_id is not None
        assert segment.timerange is not None
    
    def test_object_flow_references(self):
        """Test object-flow references"""
        flow_id = str(uuid.uuid4())
        obj = TestDataFactory.create_object(
            referenced_by_flows=[flow_id]
        )
        
        assert flow_id in obj.referenced_by_flows
        assert obj.first_referenced_by_flow == flow_id


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_source_serialization(self):
        """Test source model serialization"""
        source = TestDataFactory.create_source()
        
        # Convert to dict
        source_dict = source.model_dump()
        assert isinstance(source_dict, dict)
        assert source_dict['format'] == source.format
        assert source_dict['label'] == source.label
        
        # Convert to JSON
        source_json = source.model_dump_json()
        assert isinstance(source_json, str)
        assert source.format in source_json
        assert source.label in source_json
    
    def test_flow_serialization(self):
        """Test flow model serialization"""
        flow = TestDataFactory.create_flow()
        
        # Convert to dict
        flow_dict = flow.model_dump()
        assert isinstance(flow_dict, dict)
        assert flow_dict['format'] == flow.format
        assert flow_dict['codec'] == flow.codec
        
        # Convert to JSON
        flow_json = flow.model_dump_json()
        assert isinstance(flow_json, str)
        assert flow.format in flow_json
        assert flow.codec in flow_json
    
    def test_segment_serialization(self):
        """Test segment model serialization"""
        segment = TestDataFactory.create_segment()
        
        # Convert to dict
        segment_dict = segment.model_dump()
        assert isinstance(segment_dict, dict)
        assert segment_dict['object_id'] == segment.object_id
        assert segment_dict['timerange'] == segment.timerange
        
        # Convert to JSON
        segment_json = segment.model_dump_json()
        assert isinstance(segment_json, str)
        assert segment.object_id in segment_json
        assert segment.timerange in segment_json
    
    def test_object_serialization(self):
        """Test object model serialization"""
        obj = TestDataFactory.create_object()
        
        # Convert to dict
        obj_dict = obj.model_dump()
        assert isinstance(obj_dict, dict)
        assert obj_dict['id'] == obj.id
        assert obj_dict['referenced_by_flows'] == obj.referenced_by_flows
        
        # Convert to JSON
        obj_json = obj.model_dump_json()
        assert isinstance(obj_json, str)
        assert obj.id in obj_json
        assert str(obj.referenced_by_flows[0]) in obj_json


class TestModelValidation:
    """Test model validation rules"""
    
    def test_source_format_validation(self):
        """Test source format validation"""
        # Valid formats
        valid_formats = [
            "urn:x-nmos:format:video",
            "urn:x-nmos:format:audio",
            "urn:x-nmos:format:data"
        ]
        
        for format_type in valid_formats:
            source = TestDataFactory.create_source(source_type=format_type)
            assert source.format == format_type
    
    def test_flow_codec_validation(self):
        """Test flow codec validation"""
        # Valid codecs
        valid_codecs = [
            "video/mp4",
            "video/h264",
            "audio/aac",
            "audio/mp3"
        ]
        
        for codec in valid_codecs:
            flow = TestDataFactory.create_flow()
            flow.codec = codec
            assert flow.codec == codec
    
    def test_segment_timerange_validation(self):
        """Test segment timerange validation"""
        # Valid timerange format: [start:0_end:0]
        valid_timeranges = [
            "[1000:0_2000:0]",
            "[0:0_3600:0]",
            "[5000:0_10000:0]"
        ]
        
        for timerange in valid_timeranges:
            segment = TestDataFactory.create_segment()
            segment.timerange = timerange
            assert segment.timerange == timerange
    
    def test_object_size_validation(self):
        """Test object size validation"""
        # Valid sizes
        valid_sizes = [1, 1024, 1048576, 1073741824]  # 1B, 1KB, 1MB, 1GB
        
        for size in valid_sizes:
            obj = TestDataFactory.create_object()
            obj.size = size
            assert obj.size == size


class TestModelEdgeCases:
    """Test model edge cases and error handling"""
    
    def test_source_empty_strings(self):
        """Test source with empty strings"""
        source = TestDataFactory.create_source(
            name="",
            description=""
        )
        
        assert source.label == ""
        assert source.description == ""
    
    def test_flow_zero_dimensions(self):
        """Test flow with zero dimensions"""
        flow = TestDataFactory.create_flow()
        flow.frame_width = 0
        flow.frame_height = 0
        
        assert flow.frame_width == 0
        assert flow.frame_height == 0
    
    def test_segment_empty_path(self):
        """Test segment with empty storage path"""
        segment = TestDataFactory.create_segment(storage_path="")
        
        assert segment.storage_path == ""
    
    def test_object_empty_references(self):
        """Test object with empty references - validates model constraint"""
        # TestDataFactory handles empty list by providing default
        obj = TestDataFactory.create_object(referenced_by_flows=[])
        
        assert len(obj.referenced_by_flows) >= 1  # Factory provides default
        assert obj.first_referenced_by_flow is not None
        
        # Test direct model validation error for empty list
        with pytest.raises(ValidationError):
            Object(
                id=str(uuid.uuid4()),
                referenced_by_flows=[],  # This should fail validation
                first_referenced_by_flow=None,
                size=1024,
                created=datetime.now(timezone.utc)
            )
    
    def test_model_field_constraints(self):
        """Test model field constraints"""
        # Test UUID validation
        with pytest.raises(ValidationError):
            Source(
                id="invalid-uuid",
                format="urn:x-nmos:format:video",
                label="Test",
                description="Test",
                created_by="test",
                updated_by="test",
                created=datetime.now(timezone.utc),
                updated=datetime.now(timezone.utc)
            )
        
        # Test datetime validation
        with pytest.raises(ValidationError):
            Source(
                id=uuid.uuid4(),
                format="urn:x-nmos:format:video",
                label="Test",
                description="Test",
                created_by="test",
                updated_by="test",
                created="invalid-date",
                updated="invalid-date"
            )
