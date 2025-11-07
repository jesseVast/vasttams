#!/usr/bin/env python3
"""
Service Layer Tests for Objects Service

Tests objects/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
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

from vasttams.objects.service import ObjectStorageService
from vasttams.objects.models import Object


class TestObjectStorageService:
    """Test ObjectStorageService"""
    
    def test_init(self):
        """Test service initialization"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = ObjectStorageService(mock_db, mock_s3)
        assert service.vast_db == mock_db
        assert service.s3_client == mock_s3
    
    @pytest.mark.asyncio
    async def test_get_object_existing(self):
        """Test get_object with existing object"""
        object_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'first_referenced_by_flow': [flow_id],
                'timerange': ['0:0_100:0'],
                'size': [1000000],
                'metadata': ['{}'],
                'created': ['2024-01-01T00:00:00Z']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.id == object_id
    
    @pytest.mark.asyncio
    async def test_get_object_nonexistent(self):
        """Test get_object with non-existent object"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is None
    
    @pytest.mark.asyncio
    async def test_get_object_with_referenced_flows(self):
        """Test get_object computes referenced_by_flows dynamically"""
        object_id = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        flow_id2 = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'first_referenced_by_flow': [flow_id1],
                'timerange': ['0:0_100:0'],
                'size': [1000000],
                'metadata': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Mock referenced flows query
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'flow_id': [flow_id1, flow_id2]
            }
        })
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.id == object_id
        # referenced_by_flows should be computed from segments
        assert isinstance(obj.referenced_by_flows, list)
    
    @pytest.mark.asyncio
    async def test_create_object(self):
        """Test create_object"""
        object_id = str(uuid.uuid4())
        obj = Object(
            id=object_id,
            timerange={"value": "0:0_100:0"},
            size=1000000,
            referenced_by_flows=[]
        )
        
        mock_db = Mock()
        mock_db.insert_record = Mock()
        
        service = ObjectStorageService(mock_db, Mock())
        result = await service.create_object(obj)
        
        assert result is True
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_unreferenced_objects(self):
        """Test get_unreferenced_objects"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {'object_id': ['obj1', 'obj2']}})
        
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {'data': {'id': ['obj1', 'obj2', 'obj3']}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        unreferenced = await service.get_unreferenced_objects()
        
        assert isinstance(unreferenced, list)
        # obj3 should be unreferenced
        assert 'obj3' in unreferenced
    
    @pytest.mark.asyncio
    async def test_get_unreferenced_objects_with_exclude(self):
        """Test get_unreferenced_objects with exclude list"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {'object_id': ['obj1']}})
        
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {'data': {'id': ['obj1', 'obj2']}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        unreferenced = await service.get_unreferenced_objects(exclude_object_ids=['obj2'])
        
        assert 'obj2' not in unreferenced
    
    @pytest.mark.asyncio
    async def test_delete_unreferenced_objects(self):
        """Test delete_unreferenced_objects"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        # Mock delete_object to return True
        service.delete_object = AsyncMock(return_value=True)
        
        deleted_count = await service.delete_unreferenced_objects([object_id])
        
        assert deleted_count == 1
    
    @pytest.mark.asyncio
    async def test_delete_object(self):
        """Test delete_object"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        # Mock get_object to return None (object doesn't exist)
        service.get_object = AsyncMock(return_value=None)
        service.list_object_instances = AsyncMock(return_value=[])
        
        result = await service.delete_object(object_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_objects(self):
        """Test get_objects"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': ['obj1', 'obj2'],
                'timerange': ['0:0_100:0', '100:0_200:0'],
                'size': [1000000, 2000000],
                'metadata': ['{}', '{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
        assert len(objects) == 2
    
    @pytest.mark.asyncio
    async def test_create_object_instance(self):
        """Test create_object_instance"""
        object_id = str(uuid.uuid4())
        
        from vasttams.objects.models import ObjectInstance
        
        instance = ObjectInstance(
            label="test-instance",
            storage_id="test-storage",
            url="https://example.com/object",
            controlled=False
        )
        
        mock_db = Mock()
        mock_db.insert_record = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        # Mock get_object to return a valid object
        service.get_object = AsyncMock(return_value=Object(
            id=object_id,
            timerange={"value": "0:0_100:0"},
            size=1000000,
            referenced_by_flows=[]
        ))
        
        result = await service.create_object_instance(object_id, instance)
        
        assert result is True
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_object_instances(self):
        """Test list_object_instances"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'label': 'instance1',
                    'storage_id': 'storage1',
                    'url': 'https://example.com/obj1',
                    'controlled': False,
                    'metadata': {}
                }
            ]
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        # Mock get_object to return a valid object
        service.get_object = AsyncMock(return_value=Object(
            id=object_id,
            timerange={"value": "0:0_100:0"},
            size=1000000,
            referenced_by_flows=[]
        ))
        
        instances = await service.list_object_instances(object_id)
        
        assert isinstance(instances, list)
        assert len(instances) == 1
    
    def test_extract_storage_path_from_url(self):
        """Test _extract_storage_path_from_url"""
        service = ObjectStorageService(Mock(), Mock())
        
        # Test S3 URL
        url = "https://s3.amazonaws.com/bucket/path/to/object"
        path = service._extract_storage_path_from_url(url)
        assert path == "bucket/path/to/object"
        
        # Test URL with query params
        url = "https://example.com/path/to/object?param=value"
        path = service._extract_storage_path_from_url(url)
        assert path == "path/to/object"
    
    @pytest.mark.asyncio
    async def test_delete_object_instance(self):
        """Test delete_object_instance"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock get_object to return a valid object
        mock_get_query = Mock()
        mock_get_query.select.return_value = mock_get_query
        mock_get_query.where.return_value = mock_get_query
        mock_get_query.execute.return_value = {'data': {'id': [object_id], 'size': [1000000]}}
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        # Mock instance query (to get instance data before deletion)
        mock_instance_query = Mock()
        mock_instance_query.select.return_value = mock_instance_query
        mock_instance_query.where.return_value = mock_instance_query
        mock_instance_query.execute.return_value = {'data': {'label': ['test-instance'], 'storage_id': ['test-storage'], 'controlled': [False]}}
        
        # Mock delete query
        mock_delete_query = Mock()
        mock_delete_query.delete.return_value = mock_delete_query
        mock_delete_query.where.return_value = mock_delete_query
        mock_delete_query.execute.return_value = True
        
        def query_side_effect(table_name):
            if table_name == "objects":
                return mock_get_query
            elif table_name == "object_instances":
                return mock_instance_query
            return mock_delete_query
        
        mock_db.query.side_effect = query_side_effect
        
        service = ObjectStorageService(mock_db, Mock())
        
        # delete_object_instance requires label or storage_id parameter
        result = await service.delete_object_instance(object_id, label="test-instance")
        
        assert result is True

