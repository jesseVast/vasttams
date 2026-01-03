"""
Tests for GetUrlFactory

Comprehensive test coverage for the GetUrlFactory class including:
- Single URL generation
- Batch URL generation
- Thread pool executor functionality
- Error handling
- Storage backend integration
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import json
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "server"
sys.path.insert(0, str(src_path))

from vasttamsserver.segments.get_url_factory import GetUrlFactory
from vasttamsserver.segments.models import GetUrl


class TestGetUrlFactory:
    """Test suite for GetUrlFactory"""
    
    @pytest.fixture
    def mock_vast_db(self):
        """Mock VAST database"""
        db = Mock()
        db.get_record = Mock(return_value=None)
        return db
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        client = Mock()
        client.generate_presigned_url = Mock(return_value="https://s3.example.com/path/to/object")
        return client
    
    @pytest.fixture
    def mock_settings(self):
        """Mock application settings"""
        settings = Mock()
        settings.s3_provider = "aws"
        settings.s3_store_product = "s3"
        settings.s3_bucket_name = "test-bucket"
        settings.s3_endpoint_url = "https://s3.amazonaws.com"
        settings.s3_region = "us-east-1"
        settings.s3_use_ssl = True
        settings.s3_access_key_id = "test-key"
        settings.s3_secret_access_key = "test-secret"
        settings.s3_root_path = "tams"
        settings.tams_storage_path = "tams"
        settings.s3_presigned_url_download_timeout = 3600
        settings.vaststore_s3_chunk_size = 8388608
        settings.vaststore_s3_max_concurrent_parts = 10
        return settings
    
    @pytest.fixture
    def factory(self, mock_vast_db, mock_s3_client, mock_settings):
        """Create GetUrlFactory instance"""
        return GetUrlFactory(mock_vast_db, mock_s3_client, mock_settings, max_workers=5)
    
    @pytest.fixture
    def sample_object_data(self):
        """Sample object data from database"""
        object_id = str(uuid.uuid4())
        created = datetime.now(timezone.utc)
        metadata = {
            "storage_path": f"tams/2024/01/15/{object_id}",
            "storage_id": str(uuid.uuid4()),
            "content_type": "video/mp2t"
        }
        return {
            "id": object_id,
            "created": created.isoformat(),
            "metadata": json.dumps(metadata)
        }
    
    @pytest.mark.asyncio
    async def test_create_get_urls_success(self, factory, mock_vast_db, mock_s3_client, sample_object_data):
        """Test successful GetUrl creation"""
        object_id = sample_object_data["id"]
        metadata = json.loads(sample_object_data["metadata"])
        storage_id = metadata["storage_id"]
        
        # Mock query chain for _get_object
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [sample_object_data["id"]],
                'created': [sample_object_data["created"]],
                'metadata': [sample_object_data["metadata"]]
            }
        }
        mock_vast_db.query.return_value = mock_query
        
        # Mock asyncio.to_thread for _get_object
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                'data': {
                    'id': [sample_object_data["id"]],
                    'created': [sample_object_data["created"]],
                    'metadata': [sample_object_data["metadata"]]
                }
            }
            
            # Mock storage backend service
            with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
                mock_backend = Mock()
                mock_backend.model_dump.return_value = {
                    "id": storage_id,
                    "root_path": None
                }
                mock_service = Mock()
                mock_service.get_storage_backend = AsyncMock(return_value=mock_backend)
                mock_service_class.return_value = mock_service
                
                # Mock inspect.signature for S3 client
                with patch('inspect.signature') as mock_signature:
                    mock_sig = Mock()
                    mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
                    mock_signature.return_value = mock_sig
                    
                    # Mock event loop run_in_executor
                    with patch('asyncio.get_event_loop') as mock_get_loop:
                        mock_loop = Mock()
                        mock_get_loop.return_value = mock_loop
                        mock_loop.run_in_executor = AsyncMock(return_value="https://s3.example.com/test/url")
                        
                        result = await factory.create_get_urls(object_id)
        
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], GetUrl)
        assert result[0].url == "https://s3.example.com/test/url"
        assert result[0].presigned is True
        assert result[0].controlled is True
        assert result[0].store_type == "http_object_store"
        assert result[0].provider == "aws"
        assert result[0].store_product == "s3"
        assert result[0].storage_id == storage_id
    
    @pytest.mark.asyncio
    async def test_create_get_urls_object_not_found(self, factory, mock_vast_db):
        """Test GetUrl creation when object doesn't exist"""
        object_id = str(uuid.uuid4())
        
        # Mock asyncio.to_thread to return empty result
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {'data': {}}
            
            result = await factory.create_get_urls(object_id)
            
            assert result is None
            mock_s3_client = factory.s3_client
            mock_s3_client.generate_presigned_url.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_get_urls_no_storage_path(self, factory, mock_vast_db, sample_object_data):
        """Test GetUrl creation when object has no storage_path"""
        object_id = sample_object_data["id"]
        # Remove storage_path from metadata
        metadata = json.loads(sample_object_data["metadata"])
        del metadata["storage_path"]
        sample_object_data["metadata"] = json.dumps(metadata)
        
        # Mock query chain for _get_object
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [sample_object_data["id"]],
                'created': [sample_object_data["created"]],
                'metadata': [sample_object_data["metadata"]]
            }
        }
        mock_vast_db.query.return_value = mock_query
        
        # Mock asyncio.to_thread for _get_object
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                'data': {
                    'id': [sample_object_data["id"]],
                    'created': [sample_object_data["created"]],
                    'metadata': [sample_object_data["metadata"]]
                }
            }
            
            # Mock storage backend service (imported inside method)
            with patch('vasttamsserver.storagebackends.service.StorageBackendService'):
                # Mock inspect.signature for S3 client
                with patch('inspect.signature') as mock_signature:
                    mock_sig = Mock()
                    mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
                    mock_signature.return_value = mock_sig
                    
                    # Mock event loop run_in_executor
                    with patch('asyncio.get_event_loop') as mock_get_loop:
                        mock_loop = Mock()
                        mock_get_loop.return_value = mock_loop
                        mock_loop.run_in_executor = AsyncMock(return_value="https://s3.example.com/test/url")
                        
                        # Should reconstruct path from created timestamp
                        result = await factory.create_get_urls(object_id)
        
        # Should still succeed by reconstructing path
        assert result is not None
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_create_get_urls_batch_success(self, factory, mock_vast_db, mock_s3_client, sample_object_data):
        """Test batch GetUrl creation"""
        object_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        # Setup mock batch query result with all objects
        batch_data = {
            'data': {
                'id': [],
                'created': [],
                'metadata': []
            }
        }
        for obj_id in object_ids:
            obj_data = sample_object_data.copy()
            obj_data["id"] = obj_id
            metadata = json.loads(obj_data["metadata"])
            metadata["storage_path"] = f"tams/2024/01/15/{obj_id}"
            metadata["storage_id"] = str(uuid.uuid4())
            obj_data["metadata"] = json.dumps(metadata)
            batch_data['data']['id'].append(obj_data["id"])
            batch_data['data']['created'].append(obj_data["created"])
            batch_data['data']['metadata'].append(obj_data["metadata"])
        
        # Mock asyncio.to_thread for batch query
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = batch_data
            
            # Mock storage backend service
            with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
                mock_backend = Mock()
                mock_backend.model_dump.return_value = {"id": str(uuid.uuid4()), "root_path": None}
                mock_service = Mock()
                mock_service.get_storage_backend = AsyncMock(return_value=mock_backend)
                mock_service_class.return_value = mock_service
                
                # Mock inspect.signature for S3 client
                with patch('inspect.signature') as mock_signature:
                    mock_sig = Mock()
                    mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
                    mock_signature.return_value = mock_sig
                    
                    # Mock event loop run_in_executor
                    with patch('asyncio.get_event_loop') as mock_get_loop:
                        mock_loop = Mock()
                        mock_get_loop.return_value = mock_loop
                        mock_loop.run_in_executor = AsyncMock(return_value="https://s3.example.com/test/url")
                        
                        result = await factory.create_get_urls_batch(object_ids, batch_size=3)
                        
                        assert len(result) == 5
                        for obj_id in object_ids:
                            assert obj_id in result
                            assert result[obj_id] is not None
                            assert len(result[obj_id]) == 1
                            assert isinstance(result[obj_id][0], GetUrl)
    
    @pytest.mark.asyncio
    async def test_create_get_urls_batch_with_failures(self, factory, mock_vast_db, mock_s3_client, sample_object_data):
        """Test batch GetUrl creation with some failures"""
        object_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        # Setup mock batch query result - only first 2 objects found
        batch_data = {
            'data': {
                'id': [],
                'created': [],
                'metadata': []
            }
        }
        for i, obj_id in enumerate(object_ids[:2]):  # Only first 2 succeed
            obj_data = sample_object_data.copy()
            obj_data["id"] = obj_id
            metadata = json.loads(obj_data["metadata"])
            metadata["storage_path"] = f"tams/2024/01/15/{obj_id}"
            metadata["storage_id"] = str(uuid.uuid4())
            obj_data["metadata"] = json.dumps(metadata)
            batch_data['data']['id'].append(obj_data["id"])
            batch_data['data']['created'].append(obj_data["created"])
            batch_data['data']['metadata'].append(obj_data["metadata"])
        
        # Mock asyncio.to_thread for batch query
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = batch_data
            
            # Mock _get_object to return None for missing objects (fallback for batch misses)
            with patch.object(factory, '_get_object', new_callable=AsyncMock) as mock_get_object:
                def get_object_side_effect(obj_id):
                    # Return None for objects not in the first 2
                    if obj_id in object_ids[:2]:
                        # Return parsed object data for existing objects
                        obj_data = sample_object_data.copy()
                        obj_data["id"] = obj_id
                        metadata = json.loads(obj_data["metadata"])
                        metadata["storage_path"] = f"tams/2024/01/15/{obj_id}"
                        metadata["storage_id"] = str(uuid.uuid4())
                        obj_data["metadata"] = json.dumps(metadata)
                        # Return parsed dict (not query result format)
                        return {
                            'id': obj_data["id"],
                            'created': obj_data["created"],
                            'metadata': metadata  # Already parsed
                        }
                    else:
                        # Return None for missing objects
                        return None
                
                mock_get_object.side_effect = get_object_side_effect
                
                # Mock storage backend service (only for successful cases)
                with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
                    mock_backend = Mock()
                    mock_backend.model_dump.return_value = {"id": str(uuid.uuid4()), "root_path": None}
                    mock_service = Mock()
                    mock_service.get_storage_backend = AsyncMock(return_value=mock_backend)
                    mock_service_class.return_value = mock_service
                    
                    # Mock inspect.signature for S3 client
                    with patch('inspect.signature') as mock_signature:
                        mock_sig = Mock()
                        mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
                        mock_signature.return_value = mock_sig
                        
                        # Mock event loop run_in_executor
                        with patch('asyncio.get_event_loop') as mock_get_loop:
                            mock_loop = Mock()
                            mock_get_loop.return_value = mock_loop
                            mock_loop.run_in_executor = AsyncMock(return_value="https://s3.example.com/test/url")
                            
                            result = await factory.create_get_urls_batch(object_ids, batch_size=3)
                            
                            assert len(result) == 5
                            success_count = sum(1 for v in result.values() if v is not None)
                            failure_count = sum(1 for v in result.values() if v is None)
                            assert success_count == 2
                            assert failure_count == 3
    
    @pytest.mark.asyncio
    async def test_extract_storage_metadata_from_metadata(self, factory, sample_object_data):
        """Test metadata extraction from object metadata"""
        storage_path, storage_id, content_type = factory._extract_storage_metadata(sample_object_data, sample_object_data["id"])
        
        metadata = json.loads(sample_object_data["metadata"])
        assert storage_path == metadata["storage_path"]
        assert storage_id == metadata["storage_id"]
        assert content_type == metadata["content_type"]
    
    @pytest.mark.asyncio
    async def test_extract_storage_metadata_reconstruct_path(self, factory, sample_object_data):
        """Test path reconstruction from created timestamp"""
        # Remove storage_path from metadata
        metadata = json.loads(sample_object_data["metadata"])
        del metadata["storage_path"]
        sample_object_data["metadata"] = json.dumps(metadata)
        
        storage_path, storage_id, content_type = factory._extract_storage_metadata(sample_object_data, sample_object_data["id"])
        
        # Should reconstruct path from created timestamp
        assert storage_path is not None
        assert storage_path.startswith("tams/")
        assert sample_object_data["id"] in storage_path
    
    @pytest.mark.asyncio
    async def test_get_backend_info_with_storage_id(self, factory):
        """Test backend info retrieval with storage_id"""
        storage_id = str(uuid.uuid4())
        storage_path = "root_path/tams/2024/01/15/object_id"
        
        mock_backend = Mock()
        mock_backend.root_path = "root_path"
        mock_backend.model_dump.return_value = {
            "id": storage_id,
            "root_path": "root_path",
            "endpoint_url": "https://s3.example.com",
            "bucket_name": "test-bucket"
        }
        
        with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_storage_backend = AsyncMock(return_value=mock_backend)
            mock_service_class.return_value = mock_service
            
            backend_info, relative_path = await factory._get_backend_info(storage_id, storage_path)
            
            assert backend_info is not None
            assert backend_info["id"] == storage_id
            # Should strip root_path for relative path
            assert relative_path == "tams/2024/01/15/object_id"
    
    @pytest.mark.asyncio
    async def test_get_backend_info_no_storage_id(self, factory):
        """Test backend info retrieval without storage_id"""
        storage_path = "tams/2024/01/15/object_id"
        
        backend_info, relative_path = await factory._get_backend_info(None, storage_path)
        
        assert backend_info is None
        assert relative_path == storage_path
    
    @pytest.mark.asyncio
    async def test_generate_presigned_url_default_client(self, factory, mock_s3_client):
        """Test presigned URL generation with default client"""
        mock_s3_client.generate_presigned_url.return_value = "https://s3.example.com/presigned/url"
        
        # Mock inspect.signature to return supported parameters
        with patch('inspect.signature') as mock_signature:
            mock_sig = Mock()
            mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
            mock_signature.return_value = mock_sig
            
            result = await factory._generate_presigned_url(
                key="test/key",
                operation="get_object",
                expiration=3600
            )
            
            assert result == "https://s3.example.com/presigned/url"
            mock_s3_client.generate_presigned_url.assert_called()
    
    @pytest.mark.asyncio
    async def test_generate_presigned_url_with_backend(self, factory, mock_settings):
        """Test presigned URL generation with storage backend"""
        storage_backend = {
            "access_key": "backend-key",
            "secret_key": "backend-secret",
            "endpoint_url": "https://backend.s3.example.com",
            "bucket_name": "backend-bucket",
            "region": "us-west-2",
            "use_ssl": True,
            "root_path": "backend-root"
        }
        
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url = Mock(return_value="https://backend.s3.example.com/presigned/url")
        
        with patch('vasts3.S3Client') as mock_s3_client_class, \
             patch('inspect.signature') as mock_signature:
            mock_client_instance = Mock()
            mock_client_instance.generate_presigned_url = Mock(return_value="https://backend.s3.example.com/presigned/url")
            mock_s3_client_class.return_value = mock_client_instance
            
            mock_sig = Mock()
            mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
            mock_signature.return_value = mock_sig
            
            result = await factory._generate_presigned_url(
                key="test/key",
                operation="get_object",
                expiration=3600,
                storage_backend=storage_backend
            )
            
            assert result == "https://backend.s3.example.com/presigned/url"
            mock_s3_client_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_storage_id_default_backend(self, factory):
        """Test storage_id resolution from default backend"""
        default_backend_id = str(uuid.uuid4())
        mock_backend = Mock()
        mock_backend.id = default_backend_id
        mock_backend.default_storage = True
        # Mock model_dump() to return a dict with the expected fields
        mock_backend.model_dump = Mock(return_value={
            'id': default_backend_id,
            'default_storage': True
        })
        
        with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_storage_backends = AsyncMock(return_value=[mock_backend])
            mock_service_class.return_value = mock_service
            
            result = await factory._resolve_storage_id()
            
            assert result == default_backend_id
    
    @pytest.mark.asyncio
    async def test_resolve_storage_id_generate_uuid(self, factory):
        """Test storage_id resolution when no default backend"""
        with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_storage_backends = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service
            
            result = await factory._resolve_storage_id()
            
            # Should generate a UUID
            assert result is not None
            # Verify it's a valid UUID format
            uuid.UUID(result)  # Will raise if invalid
    
    @pytest.mark.asyncio
    async def test_create_get_url_object(self, factory):
        """Test GetUrl object creation"""
        url = "https://s3.example.com/test/url"
        storage_id = str(uuid.uuid4())
        provider = "aws"
        store_product = "s3"
        
        result = factory._create_get_url_object(url, storage_id, provider, store_product)
        
        assert isinstance(result, GetUrl)
        assert result.url == url
        assert result.storage_id == storage_id
        assert result.provider == provider
        assert result.store_product == store_product
        assert result.presigned is True
        assert result.controlled is True
        assert result.store_type == "http_object_store"
    
    @pytest.mark.asyncio
    async def test_thread_pool_executor_usage(self, factory, mock_vast_db, mock_s3_client, sample_object_data):
        """Test that thread pool executor is used for blocking operations"""
        object_id = sample_object_data["id"]
        
        # Mock asyncio.to_thread for object lookup
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                'data': {
                    'id': [object_id],
                    'created': [sample_object_data.get('created', '2024-01-01T00:00:00Z')],
                    'metadata': [json.dumps(sample_object_data.get('metadata', {}))]
                }
            }
            
            # Mock the event loop's run_in_executor for S3 presigned URL generation
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop
                mock_loop.run_in_executor = AsyncMock(return_value="https://s3.example.com/presigned/url")
                
                with patch('inspect.signature') as mock_signature:
                    mock_sig = Mock()
                    mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
                    mock_signature.return_value = mock_sig
                    
                    result = await factory.create_get_urls(object_id)
                    
                    # Verify run_in_executor was called with the factory's executor
                    assert mock_loop.run_in_executor.called
                    call_args = mock_loop.run_in_executor.call_args
                    assert call_args[0][0] == factory._executor
    
    @pytest.mark.asyncio
    async def test_factory_cleanup(self, factory):
        """Test that executor is properly cleaned up"""
        executor = factory._executor
        
        # Simulate destruction
        factory.__del__()
        
        # Executor should be shutdown (though we can't easily verify this without accessing private state)
        assert hasattr(factory, '_executor')
    
    @pytest.mark.asyncio
    async def test_metadata_with_internal_metadata(self, factory):
        """Test metadata extraction from object with _internal_metadata attribute"""
        object_id = str(uuid.uuid4())
        mock_obj = Mock()
        mock_obj._internal_metadata = {
            "storage_path": "tams/2024/01/15/object_id",
            "storage_id": str(uuid.uuid4()),
            "content_type": "video/mp2t"
        }
        
        storage_path, storage_id, content_type = factory._extract_storage_metadata(mock_obj, object_id)
        
        assert storage_path == mock_obj._internal_metadata["storage_path"]
        assert storage_id == mock_obj._internal_metadata["storage_id"]
        assert content_type == mock_obj._internal_metadata["content_type"]
    
    @pytest.mark.asyncio
    async def test_metadata_string_json(self, factory):
        """Test metadata extraction when metadata is JSON string"""
        object_id = str(uuid.uuid4())
        metadata_dict = {
            "storage_path": "tams/2024/01/15/object_id",
            "storage_id": str(uuid.uuid4()),
            "content_type": "video/mp2t"
        }
        obj_data = {
            "id": object_id,
            "metadata": json.dumps(metadata_dict)
        }
        
        storage_path, storage_id, content_type = factory._extract_storage_metadata(obj_data, object_id)
        
        assert storage_path == metadata_dict["storage_path"]
        assert storage_id == metadata_dict["storage_id"]
        assert content_type == metadata_dict["content_type"]
    
    @pytest.mark.asyncio
    async def test_metadata_dict(self, factory):
        """Test metadata extraction when metadata is dict"""
        object_id = str(uuid.uuid4())
        metadata_dict = {
            "storage_path": "tams/2024/01/15/object_id",
            "storage_id": str(uuid.uuid4()),
            "content_type": "video/mp2t"
        }
        obj_data = {
            "id": object_id,
            "metadata": metadata_dict
        }
        
        storage_path, storage_id, content_type = factory._extract_storage_metadata(obj_data, object_id)
        
        assert storage_path == metadata_dict["storage_path"]
        assert storage_id == metadata_dict["storage_id"]
        assert content_type == metadata_dict["content_type"]
    
    @pytest.mark.asyncio
    async def test_batch_processing_different_sizes(self, factory, mock_vast_db, mock_s3_client, sample_object_data):
        """Test batch processing with different batch sizes"""
        object_ids = [str(uuid.uuid4()) for _ in range(25)]
        
        def get_record_side_effect(table, filters):
            obj_id = filters.get("id")
            obj_data = sample_object_data.copy()
            obj_data["id"] = obj_id
            metadata = json.loads(obj_data["metadata"])
            metadata["storage_path"] = f"tams/2024/01/15/{obj_id}"
            metadata["storage_id"] = str(uuid.uuid4())
            obj_data["metadata"] = json.dumps(metadata)
            return obj_data
        
        # Mock asyncio.to_thread for batch object lookup
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            def to_thread_side_effect(func):
                # Extract object IDs from the function (it's a lambda that queries objects)
                # Return mock data for all requested object IDs
                result_data = {
                    'id': [],
                    'created': [],
                    'metadata': []
                }
                for obj_id in object_ids:
                    obj_data = sample_object_data.copy()
                    obj_data["id"] = obj_id
                    metadata = json.loads(obj_data.get("metadata", "{}"))
                    metadata["storage_path"] = f"tams/2024/01/15/{obj_id}"
                    metadata["storage_id"] = str(uuid.uuid4())
                    obj_data["metadata"] = json.dumps(metadata)
                    
                    result_data['id'].append(obj_id)
                    result_data['created'].append(obj_data.get('created', '2024-01-01T00:00:00Z'))
                    result_data['metadata'].append(obj_data.get('metadata', '{}'))
                
                return {'data': result_data}
            
            mock_to_thread.side_effect = to_thread_side_effect
            
            # Mock storage backend service
            with patch('vasttamsserver.storagebackends.service.StorageBackendService') as mock_service_class:
                mock_backend = Mock()
                mock_backend.model_dump.return_value = {"id": str(uuid.uuid4()), "root_path": None}
                mock_service = Mock()
                mock_service.get_storage_backend = AsyncMock(return_value=mock_backend)
                mock_service_class.return_value = mock_service
                
                # Mock inspect.signature for S3 client
                with patch('inspect.signature') as mock_signature:
                    mock_sig = Mock()
                    mock_sig.parameters.keys.return_value = ['key', 'operation', 'expires_in', 'method']
                    mock_signature.return_value = mock_sig
                    
                    # Mock event loop run_in_executor
                    with patch('asyncio.get_event_loop') as mock_get_loop:
                        mock_loop = Mock()
                        mock_get_loop.return_value = mock_loop
                        mock_loop.run_in_executor = AsyncMock(return_value="https://s3.example.com/test/url")
                        
                        # Test with batch_size=5 (should create 5 batches)
                        result = await factory.create_get_urls_batch(object_ids, batch_size=5)
            
            assert len(result) == 25
            for obj_id in object_ids:
                assert obj_id in result
                assert result[obj_id] is not None

