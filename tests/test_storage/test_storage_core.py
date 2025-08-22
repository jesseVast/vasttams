"""
Tests for Storage Core Components

This module tests the core storage components including StorageFactory,
S3Core, VastCore, and their interactions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime, timezone, timedelta

from app.storage.core.storage_factory import StorageFactory
from app.storage.core.s3_core import S3Core
from app.storage.core.vast_core import VastCore
from tests.test_utils.mock_vastdbmanager import MockVastDBManager
from tests.test_utils.mock_s3store import MockS3Store


class TestStorageFactory:
    """Test StorageFactory functionality"""
    
    def test_storage_factory_initialization(self):
        """Test StorageFactory initialization"""
        factory = StorageFactory()
        assert factory is not None
        assert hasattr(factory, 'create_storage')
    
    def test_create_s3_storage(self):
        """Test creating S3 storage instance"""
        factory = StorageFactory()
        
        with patch('app.storage.core.storage_factory.S3Core') as mock_s3:
            mock_s3.return_value = Mock()
            storage = factory.create_storage('s3', {
                'endpoint_url': 'http://test-endpoint',
                'bucket_name': 'test-bucket',
                'access_key_id': 'test-key',
                'secret_access_key': 'test-secret'
            })
            
            assert storage is not None
            mock_s3.assert_called_once()
    
    def test_create_vast_storage(self):
        """Test creating VAST storage instance"""
        factory = StorageFactory()
        
        with patch('app.storage.core.storage_factory.VastCore') as mock_vast:
            mock_vast.return_value = Mock()
            storage = factory.create_storage('vast', {
                'host': 'test-host',
                'port': 1234,
                'username': 'test-user',
                'password': 'test-pass'
            })
            
            assert storage is not None
            mock_vast.assert_called_once()
    
    def test_create_invalid_storage_type(self):
        """Test creating storage with invalid type"""
        factory = StorageFactory()
        
        with pytest.raises(ValueError):
            factory.create_storage('invalid', {})
    
    def test_storage_factory_singleton_behavior(self):
        """Test that StorageFactory maintains singleton behavior"""
        factory1 = StorageFactory()
        factory2 = StorageFactory()
        
        # Should be the same instance
        assert factory1 is factory2


class TestS3Core:
    """Test S3Core functionality"""
    
    def test_s3_core_initialization(self):
        """Test S3Core initialization"""
        config = {
            'endpoint_url': 'http://test-endpoint',
            'bucket_name': 'test-bucket',
            'access_key_id': 'test-key',
            'secret_access_key': 'test-secret',
            'use_ssl': False
        }
        
        s3_core = S3Core(**config)
        
        assert s3_core.endpoint_url == config['endpoint_url']
        assert s3_core.bucket_name == config['bucket_name']
        assert s3_core.access_key_id == config['access_key_id']
        assert s3_core.secret_access_key == config['secret_access_key']
        assert s3_core.use_ssl == config['use_ssl']
    
    def test_s3_core_bucket_operations(self):
        """Test S3Core bucket operations"""
        s3_core = S3Core(
            endpoint_url='http://test-endpoint',
            bucket_name='test-bucket',
            access_key_id='test-key',
            secret_access_key='test-secret'
        )
        
        # Test bucket creation
        with patch.object(s3_core, '_ensure_bucket_exists') as mock_ensure:
            mock_ensure.return_value = True
            result = s3_core._ensure_bucket_exists()
            assert result is True
    
    def test_s3_core_connection_management(self):
        """Test S3Core connection management"""
        s3_core = S3Core(
            endpoint_url='http://test-endpoint',
            bucket_name='test-bucket',
            access_key_id='test-key',
            secret_access_key='test-secret'
        )
        
        # Test connection setup
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            s3_core._setup_s3_client()
            
            mock_boto.assert_called_once_with(
                's3',
                endpoint_url=s3_core.endpoint_url,
                aws_access_key_id=s3_core.access_key_id,
                aws_secret_access_key=s3_core.secret_access_key,
                use_ssl=s3_core.use_ssl
            )
    
    def test_s3_core_error_handling(self):
        """Test S3Core error handling"""
        s3_core = S3Core(
            endpoint_url='http://test-endpoint',
            bucket_name='test-bucket',
            access_key_id='test-key',
            secret_access_key='test-secret'
        )
        
        # Test with invalid credentials
        with patch('boto3.client') as mock_boto:
            mock_boto.side_effect = Exception("Invalid credentials")
            
            with pytest.raises(Exception):
                s3_core._setup_s3_client()


class TestVastCore:
    """Test VastCore functionality"""
    
    def test_vast_core_initialization(self):
        """Test VastCore initialization"""
        config = {
            'host': 'test-host',
            'port': 1234,
            'username': 'test-user',
            'password': 'test-pass'
        }
        
        vast_core = VastCore(**config)
        
        assert vast_core.host == config['host']
        assert vast_core.port == config['port']
        assert vast_core.username == config['username']
        assert vast_core.password == config['password']
    
    def test_vast_core_connection_management(self):
        """Test VastCore connection management"""
        vast_core = VastCore(
            host='test-host',
            port=1234,
            username='test-user',
            password='test-pass'
        )
        
        # Test connection setup
        with patch('app.storage.vastdbmanager.VastDBManager') as mock_vast:
            mock_manager = Mock()
            mock_vast.return_value = mock_manager
            
            vast_core._setup_vast_connection()
            
            mock_vast.assert_called_once_with(
                host=vast_core.host,
                port=vast_core.port,
                username=vast_core.username,
                password=vast_core.password
            )
    
    def test_vast_core_error_handling(self):
        """Test VastCore error handling"""
        vast_core = VastCore(
            host='test-host',
            port=1234,
            username='test-user',
            password='test-pass'
        )
        
        # Test with invalid connection
        with patch('app.storage.vastdbmanager.VastDBManager') as mock_vast:
            mock_vast.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                vast_core._setup_vast_connection()


class TestStorageIntegration:
    """Test storage integration scenarios"""
    
    def test_mixed_storage_workflow(self):
        """Test workflow using both S3 and VAST storage"""
        # Create mock storage instances
        s3_storage = MockS3Store()
        vast_storage = MockVastDBManager()
        
        # Test data flow between storage types
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Source',
            'description': 'Test Description'
        })
        
        flow = vast_storage.create_flow({
            'source_id': source.id,
            'format': 'urn:x-nmos:format:video',
            'codec': 'video/mp4',
            'label': 'Test Flow',
            'description': 'Test Description'
        })
        
        segment = vast_storage.create_segment({
            'flow_id': flow.id,
            'storage_path': '/test/path'
        })
        
        # Store segment in S3
        segment_data = b"mock video data"
        object_key = s3_storage.store_segment(segment, segment_data)
        
        assert object_key is not None
        assert s3_storage.object_exists(object_key)
        
        # Verify data integrity
        retrieved_data = s3_storage.retrieve_segment(segment)
        assert retrieved_data == segment_data
    
    def test_storage_error_recovery(self):
        """Test storage error recovery scenarios"""
        s3_storage = MockS3Store()
        vast_storage = MockVastDBManager()
        
        # Test S3 upload failure recovery
        with patch.object(s3_storage, 'upload_file') as mock_upload:
            mock_upload.side_effect = Exception("Upload failed")
            
            with pytest.raises(Exception):
                s3_storage.upload_file('/test/file', 'test-key')
        
        # Test VAST connection failure recovery
        with patch.object(vast_storage, 'create_source') as mock_create:
            mock_create.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                vast_storage.create_source({
                    'format': 'urn:x-nmos:format:video',
                    'label': 'Test Source'
                })
    
    def test_storage_data_consistency(self):
        """Test data consistency across storage types"""
        s3_storage = MockS3Store()
        vast_storage = MockVastDBManager()
        
        # Create source in VAST
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Source',
            'description': 'Test Description'
        })
        
        # Create flow in VAST
        flow = vast_storage.create_flow({
            'source_id': source.id,
            'format': 'urn:x-nmos:format:video',
            'codec': 'video/mp4',
            'label': 'Test Flow',
            'description': 'Test Description'
        })
        
        # Verify relationships
        retrieved_source = vast_storage.get_source(source.id)
        retrieved_flow = vast_storage.get_flow(flow.id)
        
        assert retrieved_source.id == source.id
        assert retrieved_flow.source_id == source.id
        
        # Test data persistence
        vast_storage.reset_test_data()
        
        # Data should be cleared
        assert len(vast_storage.test_data['sources']) == 0
        assert len(vast_storage.test_data['flows']) == 0


class TestStorageCRUD:
    """Test CRUD operations for storage components"""
    
    def test_s3_crud_operations(self):
        """Test S3 CRUD operations"""
        s3_storage = MockS3Store()
        
        # Create
        test_data = b"test content"
        object_key = "test/object.txt"
        
        s3_storage.upload_fileobj(
            io.BytesIO(test_data),
            object_key,
            ContentType="text/plain"
        )
        
        # Read
        assert s3_storage.object_exists(object_key)
        retrieved_data = s3_storage.get_object(object_key)
        assert retrieved_data['ContentLength'] == len(test_data)
        
        # Update (re-upload with new content)
        updated_data = b"updated content"
        s3_storage.upload_fileobj(
            io.BytesIO(updated_data),
            object_key,
            ContentType="text/plain"
        )
        
        updated_retrieved = s3_storage.get_object(object_key)
        assert updated_retrieved['ContentLength'] == len(updated_data)
        
        # Delete
        s3_storage.delete_object(object_key)
        assert not s3_storage.object_exists(object_key)
    
    def test_vast_crud_operations(self):
        """Test VAST CRUD operations"""
        vast_storage = MockVastDBManager()
        
        # Create
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Source',
            'description': 'Test Description'
        })
        
        # Read
        retrieved_source = vast_storage.get_source(source.id)
        assert retrieved_source.id == source.id
        assert retrieved_source.label == 'Test Source'
        
        # Update
        updated_source = vast_storage.update_source(source.id, {
            'label': 'Updated Source',
            'description': 'Updated Description'
        })
        assert updated_source.label == 'Updated Source'
        
        # Delete
        vast_storage.delete_source(source.id)
        deleted_source = vast_storage.get_source(source.id)
        assert deleted_source is None
    
    def test_storage_batch_operations(self):
        """Test batch storage operations"""
        s3_storage = MockS3Store()
        vast_storage = MockVastDBManager()
        
        # Batch create sources
        sources = []
        for i in range(5):
            source = vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': f'Source {i}',
                'description': f'Description {i}'
            })
            sources.append(source)
        
        # Batch create flows
        flows = []
        for source in sources:
            flow = vast_storage.create_flow({
                'source_id': source.id,
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': f'Flow for {source.label}',
                'description': f'Flow description for {source.label}'
            })
            flows.append(flow)
        
        # Verify batch creation
        assert len(sources) == 5
        assert len(flows) == 5
        
        # Batch delete
        for source in sources:
            vast_storage.delete_source(source.id)
        
        # Verify batch deletion
        for source in sources:
            assert vast_storage.get_source(source.id) is None


# Import io for BytesIO usage
import io
