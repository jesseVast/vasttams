"""
Mock Tests for TAMS S3 Store

This file tests the S3 storage functionality with mocked dependencies.
Tests focus on S3 operations, error handling, and data management.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import uuid
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from app.storage.s3_store import S3Store
from app.models.models import FlowSegment


class TestS3StoreInitialization:
    """Test S3Store initialization and configuration"""
    
    @patch('app.storage.s3_store.S3Store._ensure_bucket_exists')
    def test_s3_store_creation(self, mock_ensure_bucket):
        """Test S3Store instance creation"""
        # Mock the bucket check to avoid real S3 calls
        mock_ensure_bucket.return_value = None
        
        store = S3Store(
            endpoint_url="http://test-endpoint",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
            use_ssl=False
        )
        
        assert store.endpoint_url == "http://test-endpoint"
        assert store.bucket_name == "test-bucket"
        assert store.access_key_id == "test-key"
        assert store.use_ssl is False
    
    @patch('app.storage.s3_store.S3Store._ensure_bucket_exists')
    def test_s3_store_with_ssl(self, mock_ensure_bucket):
        """Test S3Store creation with SSL enabled"""
        # Mock the bucket check to avoid real S3 calls
        mock_ensure_bucket.return_value = None
        
        store = S3Store(
            endpoint_url="https://test-endpoint",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
            use_ssl=True
        )
        
        assert store.use_ssl is True
    
    @patch('app.storage.s3_store.S3Store._ensure_bucket_exists')
    def test_s3_client_initialization(self, mock_ensure_bucket):
        """Test S3 client initialization"""
        # Mock the bucket check to avoid real S3 calls
        mock_ensure_bucket.return_value = None
        
        # Test that S3Store can be created
        store = S3Store(
            endpoint_url="http://test-endpoint",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
            use_ssl=False
        )
        
        # Verify the store was created with correct parameters
        assert store.endpoint_url == "http://test-endpoint"
        assert store.bucket_name == "test-bucket"
        assert store.access_key_id == "test-key"
        assert store.use_ssl is False


class TestS3StoreBucketOperations:
    """Test S3 bucket operations"""
    
    @pytest.fixture
    def mock_s3_store(self):
        """Create S3Store with mocked S3 client"""
        with patch('app.storage.s3_store.S3Store._ensure_bucket_exists') as mock_ensure_bucket:
            mock_ensure_bucket.return_value = None
            with patch('boto3.client') as mock_boto3:
                mock_s3_client = MagicMock()
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
    
    def test_bucket_exists_check(self, mock_s3_store):
        """Test checking if bucket exists"""
        # Mock successful bucket check
        mock_s3_store.s3_client.head_bucket.return_value = {}
        
        exists = mock_s3_store._ensure_bucket_exists()
        assert exists is None  # Method doesn't return anything on success
        
        # Verify head_bucket was called
        mock_s3_store.s3_client.head_bucket.assert_called_once_with(
            Bucket="test-bucket"
        )
    
    def test_bucket_creation_on_missing(self, mock_s3_store):
        """Test bucket creation when bucket doesn't exist"""
        # Mock bucket doesn't exist
        mock_s3_store.s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadBucket'
        )
        
        # Mock successful bucket creation
        mock_s3_store.s3_client.create_bucket.return_value = {}
        
        exists = mock_s3_store._ensure_bucket_exists()
        assert exists is None
        
        # Verify create_bucket was called
        mock_s3_store.s3_client.create_bucket.assert_called_once_with(
            Bucket="test-bucket"
        )
    
    def test_bucket_error_handling(self, mock_s3_store):
        """Test error handling during bucket operations"""
        # Mock unexpected error
        mock_s3_store.s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '500', 'Message': 'Internal Server Error'}}, 'HeadBucket'
        )
        
        # Should handle error gracefully
        with pytest.raises(ClientError):
            mock_s3_store._ensure_bucket_exists()


class TestS3StoreFlowSegmentOperations:
    """Test S3 flow segment operations"""
    
    @pytest.fixture
    def mock_s3_store(self):
        """Create S3Store with mocked S3 client"""
        with patch('app.storage.s3_store.S3Store._ensure_bucket_exists') as mock_ensure_bucket:
            mock_ensure_bucket.return_value = None
            with patch('boto3.client') as mock_boto3:
                mock_s3_client = MagicMock()
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
    
    @pytest.mark.asyncio
    async def test_store_flow_segment(self, mock_s3_store):
        """Test storing a flow segment"""
        # Mock successful S3 put operation
        mock_s3_store.s3_client.put_object.return_value = {}
        
        flow_id = str(uuid.uuid4())
        segment = FlowSegment(
            id=str(uuid.uuid4()),
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        data = b"test_segment_data"
        
        result = await mock_s3_store.store_flow_segment(flow_id, segment, data)
        assert result is True
        
        # Verify put_object was called
        mock_s3_store.s3_client.put_object.assert_called_once()
        call_args = mock_s3_store.s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == "test-bucket"
        assert call_args[1]['Body'] == data
    
    @pytest.mark.asyncio
    async def test_get_flow_segment_data(self, mock_s3_store):
        """Test retrieving flow segment data"""
        # Mock S3 get operation response
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = b"test_segment_data"
        mock_s3_store.s3_client.get_object.return_value = mock_response
        
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        result = await mock_s3_store.get_flow_segment_data(flow_id, segment_id, timerange)
        assert result == b"test_segment_data"
        
        # Verify get_object was called
        mock_s3_store.s3_client.get_object.assert_called_once()
        call_args = mock_s3_store.s3_client.get_object.call_args
        assert call_args[1]['Bucket'] == "test-bucket"
    
    @pytest.mark.asyncio
    async def test_delete_flow_segment(self, mock_s3_store):
        """Test deleting a flow segment"""
        # Mock successful S3 delete operation
        mock_s3_store.s3_client.delete_object.return_value = {}
        
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        result = await mock_s3_store.delete_flow_segment(flow_id, segment_id, timerange)
        assert result is True
        
        # Verify delete_object was called
        mock_s3_store.s3_client.delete_object.assert_called_once()
        call_args = mock_s3_store.s3_client.delete_object.call_args
        assert call_args[1]['Bucket'] == "test-bucket"


class TestS3StoreKeyGeneration:
    """Test S3 key generation for different operations"""
    
    @pytest.fixture
    def s3_store(self):
        """Create S3Store instance with mocked bucket check"""
        with patch('app.storage.s3_store.S3Store._ensure_bucket_exists') as mock_ensure_bucket:
            mock_ensure_bucket.return_value = None
            return S3Store(
                endpoint_url="http://test-endpoint",
                access_key_id="test-key",
                secret_access_key="test-secret",
                bucket_name="test-bucket",
                use_ssl=False
            )
    
    def test_segment_key_generation(self, s3_store):
        """Test flow segment key generation"""
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        key = s3_store.generate_segment_key(flow_id, segment_id, timerange)
        
        assert key is not None
        assert flow_id in key
        assert segment_id in key
        # The timerange is processed into date components, so we check for the flow_id and segment_id
        # The key format is: flow_id/year/month/day/segment_id
        assert "/" in key
        assert key.count("/") >= 3  # Should have at least 3 separators
    
    def test_presigned_url_generation(self, s3_store):
        """Test presigned URL generation"""
        flow_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        timerange = "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z"
        
        # Test that the method exists
        assert hasattr(s3_store, 'generate_presigned_url')
        assert callable(s3_store.generate_presigned_url)
    
    def test_object_presigned_url_generation(self, s3_store):
        """Test object presigned URL generation"""
        object_id = str(uuid.uuid4())
        
        # Test that the method exists
        assert hasattr(s3_store, 'generate_object_presigned_url')
        assert callable(s3_store.generate_object_presigned_url)


class TestS3StoreErrorHandling:
    """Test S3 error handling scenarios"""
    
    @pytest.fixture
    def mock_s3_store(self):
        """Create S3Store with mocked S3 client"""
        with patch('app.storage.s3_store.S3Store._ensure_bucket_exists') as mock_ensure_bucket:
            mock_ensure_bucket.return_value = None
            with patch('boto3.client') as mock_boto3:
                mock_s3_client = MagicMock()
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
    
    @pytest.mark.asyncio
    async def test_s3_client_error_handling(self, mock_s3_store):
        """Test handling of S3 client errors"""
        # Mock S3 client error
        mock_s3_store.s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': '500', 'Message': 'Internal Server Error'}}, 'PutObject'
        )
        
        flow_id = str(uuid.uuid4())
        segment = FlowSegment(
            id=str(uuid.uuid4()),
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        data = b"test_data"
        
        # Should handle error gracefully and return False
        result = await mock_s3_store.store_flow_segment(flow_id, segment, data)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_s3_store):
        """Test handling of network errors"""
        # Mock network error
        mock_s3_store.s3_client.put_object.side_effect = Exception("Network error")
        
        flow_id = str(uuid.uuid4())
        segment = FlowSegment(
            id=str(uuid.uuid4()),
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        data = b"test_data"
        
        # Should handle error gracefully and return False
        result = await mock_s3_store.store_flow_segment(flow_id, segment, data)
        assert result is False


class TestS3StoreConfiguration:
    """Test S3Store configuration options"""
    
    @patch('app.storage.s3_store.S3Store._ensure_bucket_exists')
    def test_s3_store_configuration(self, mock_ensure_bucket):
        """Test S3Store configuration"""
        # Mock the bucket check to avoid real S3 calls
        mock_ensure_bucket.return_value = None
        
        store = S3Store(
            endpoint_url="http://test-endpoint",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
            use_ssl=False
        )
        
        # Test that store has expected attributes
        assert store.endpoint_url == "http://test-endpoint"
        assert store.access_key_id == "test-key"
        assert store.secret_access_key == "test-secret"
        assert store.bucket_name == "test-bucket"
        assert store.use_ssl is False
        
        # Test that store has expected methods
        assert hasattr(store, 'generate_segment_key')
        assert hasattr(store, 'store_flow_segment')
        assert hasattr(store, 'get_flow_segment_data')
        assert hasattr(store, 'delete_flow_segment')


if __name__ == "__main__":
    pytest.main([__file__])
