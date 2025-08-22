"""
Common Test Helpers

This module provides utility functions and helpers that can be used
across all test modules to reduce code duplication and improve consistency.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import pytest
from unittest.mock import MagicMock, patch

from app.models.models import Source, VideoFlow, FlowSegment, Object


class TestDataFactory:
    """Factory class for creating test data objects"""
    
    @staticmethod
    def create_source(
        name: str = "Test Source",
        description: str = "Test Description",
        source_type: str = "urn:x-nmos:format:video",
        location: str = "Test Location",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Source:
        """Create a test Source object"""
        return Source(
            id=uuid.uuid4(),
            format=source_type,
            label=name,
            description=description,
            created_by="test-user",
            updated_by="test-user",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc)
        )
    
    @staticmethod
    def create_flow(
        name: str = "Test Flow",
        description: str = "Test Description",
        source_id: Optional[uuid.UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VideoFlow:
        """Create a test VideoFlow object"""
        if source_id is None:
            source_id = uuid.uuid4()
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        if end_time is None:
            end_time = start_time + timedelta(hours=1)
        
        return VideoFlow(
            id=uuid.uuid4(),
            source_id=source_id,
            format="urn:x-nmos:format:video",
            codec="video/mp4",
            label=name,
            description=description,
            created_by="test-user",
            updated_by="test-user",
            created=start_time,
            metadata_updated=end_time,
            segments_updated=end_time,
            metadata_version="1.0",
            generation=0,
            frame_width=1920,
            frame_height=1080,
            frame_rate="25:1"
        )
    
    @staticmethod
    def create_segment(
        flow_id: Optional[uuid.UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        media_type: str = "video",
        storage_path: str = "/test/path",
        metadata: Optional[Dict[str, Any]] = None
    ) -> FlowSegment:
        """Create a test FlowSegment object"""
        if flow_id is None:
            flow_id = uuid.uuid4()
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        if end_time is None:
            end_time = start_time + timedelta(minutes=5)
        
        # Convert time range to TAMS format
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        timerange = f"[{start_ts}:0_{end_ts}:0]"
        
        return FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange=timerange,
            storage_path=storage_path
        )
    
    @staticmethod
    def create_object(
        name: str = "Test Object",
        description: str = "Test Description",
        object_type: str = "person",
        bounding_box: List[float] = None,
        confidence: float = 0.95,
        metadata: Optional[Dict[str, Any]] = None,
        referenced_by_flows: Optional[List[str]] = None
    ) -> Object:
        """Create a test Object object"""
        if referenced_by_flows is None:
            referenced_by_flows = [str(uuid.uuid4())]
        elif len(referenced_by_flows) == 0:
            # Object model requires at least one referenced flow
            referenced_by_flows = [str(uuid.uuid4())]
        
        return Object(
            id=str(uuid.uuid4()),
            referenced_by_flows=referenced_by_flows,
            first_referenced_by_flow=referenced_by_flows[0] if referenced_by_flows else None,
            size=1024,
            created=datetime.now(timezone.utc)
        )


class MockHelper:
    """Helper class for common mocking operations"""
    
    @staticmethod
    def mock_config_settings(**kwargs):
        """Create a mock config settings object"""
        mock_settings = MagicMock()
        for key, value in kwargs.items():
            setattr(mock_settings, key, value)
        return mock_settings
    
    @staticmethod
    def mock_database_connection():
        """Create a mock database connection"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value = MagicMock()
        mock_conn.fetchone.return_value = None
        mock_conn.fetchall.return_value = []
        return mock_conn
    
    @staticmethod
    def mock_s3_client():
        """Create a mock S3 client"""
        mock_client = MagicMock()
        mock_client.upload_file.return_value = None
        mock_client.download_file.return_value = None
        mock_client.delete_object.return_value = {'ResponseMetadata': {'HTTPStatusCode': 204}}
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_client.head_object.return_value = {'ContentLength': 1024}
        return mock_client
    
    @staticmethod
    def mock_vast_connection():
        """Create a mock VAST database connection"""
        mock_conn = MagicMock()
        mock_conn.table.return_value = MagicMock()
        mock_conn.list_tables.return_value = []
        return mock_conn


class AssertionHelper:
    """Helper class for common assertion operations"""
    
    @staticmethod
    def assert_model_fields(model, expected_fields: Dict[str, Any]):
        """Assert that a model has the expected field values"""
        for field_name, expected_value in expected_fields.items():
            if hasattr(model, field_name):
                actual_value = getattr(model, field_name)
                assert actual_value == expected_value, \
                    f"Field {field_name}: expected {expected_value}, got {actual_value}"
            else:
                pytest.fail(f"Model does not have field: {field_name}")
    
    @staticmethod
    def assert_model_created(model, id_field: str = "id"):
        """Assert that a model was created with required fields"""
        assert model is not None, "Model should not be None"
        assert hasattr(model, id_field), f"Model should have {id_field} field"
        assert getattr(model, id_field) is not None, f"{id_field} should not be None"
        
        # Check timestamps
        if hasattr(model, 'created'):
            assert model.created is not None, "created should not be None"
        if hasattr(model, 'updated'):
            assert model.updated is not None, "updated should not be None"
    
    @staticmethod
    def assert_list_response(response_list: List[Any], expected_count: int = None):
        """Assert that a list response is valid"""
        assert isinstance(response_list, list), "Response should be a list"
        if expected_count is not None:
            assert len(response_list) == expected_count, \
                f"Expected {expected_count} items, got {len(response_list)}"
    
    @staticmethod
    def assert_error_response(response, expected_status: int, expected_message: str = None):
        """Assert that an error response is valid"""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}"
        
        if expected_message:
            response_data = response.json()
            if 'detail' in response_data:
                assert expected_message in str(response_data['detail']), \
                    f"Expected message '{expected_message}' not found in response"
            elif 'message' in response_data:
                assert expected_message in str(response_data['message']), \
                    f"Expected message '{expected_message}' not found in response"


class TestSetupHelper:
    """Helper class for test setup and teardown operations"""
    
    @staticmethod
    def setup_test_environment():
        """Setup common test environment variables"""
        import os
        os.environ['TESTING'] = 'true'
        os.environ['ENVIRONMENT'] = 'test'
    
    @staticmethod
    def cleanup_test_environment():
        """Cleanup test environment variables"""
        import os
        if 'TESTING' in os.environ:
            del os.environ['TESTING']
        if 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
    
    @staticmethod
    def create_test_data_batch(count: int, factory_method, **kwargs) -> List[Any]:
        """Create a batch of test data objects"""
        return [factory_method(**kwargs) for _ in range(count)]
    
    @staticmethod
    def cleanup_test_data(data_objects: List[Any], delete_method):
        """Cleanup test data using the provided delete method"""
        for obj in data_objects:
            if hasattr(obj, 'id'):
                delete_method(obj.id)


# Global instances for easy import
test_data_factory = TestDataFactory()
mock_helper = MockHelper()
assertion_helper = AssertionHelper()
test_setup_helper = TestSetupHelper()
