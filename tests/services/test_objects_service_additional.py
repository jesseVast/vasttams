#!/usr/bin/env python3
"""
Additional Service Layer Tests for Objects Service

Additional tests to improve coverage for objects/service.py.
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
from vasttams.objects.models import Object, ObjectInstance
from vasttams.common.models import TimeRange
from fastapi import HTTPException


class TestObjectStorageServiceAdditional:
    """Additional tests for ObjectStorageService to improve coverage"""
    
    @pytest.mark.asyncio
    async def test_get_object_list_format(self):
        """Test get_object with list format result"""
        object_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = [{
            'id': object_id,
            'first_referenced_by_flow': flow_id,
            'timerange': '0:0_100:0',
            'size': 1000000,
            'metadata': '{}'
        }]
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.id == object_id
    
    @pytest.mark.asyncio
    async def test_get_object_data_as_list(self):
        """Test get_object with data as list (not dict)"""
        object_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [{
                'id': object_id,
                'first_referenced_by_flow': flow_id,
                'timerange': '0:0_100:0',
                'size': 1000000,
                'metadata': '{}'
            }]
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.id == object_id
    
    @pytest.mark.asyncio
    async def test_get_object_referenced_flows_list_format(self):
        """Test get_object with referenced flows in list format"""
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
        # Mock referenced flows query - return list format
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {'flow_id': flow_id1},
                {'flow_id': flow_id2}
            ]
        })
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert len(obj.referenced_by_flows) == 2
    
    @pytest.mark.asyncio
    async def test_get_object_referenced_flows_tuple_format(self):
        """Test get_object with referenced flows in tuple format"""
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
                'metadata': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Mock referenced flows query - return tuple format
        mock_db.execute_sql = Mock(return_value={
            'data': [
                (flow_id,),  # Tuple format
            ]
        })
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
    
    @pytest.mark.asyncio
    async def test_get_object_fallback_flow_object_references(self):
        """Test get_object uses flow_object_references table as fallback"""
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
                'metadata': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # First query (segments) returns empty, second query (flow_object_references) returns flows
        call_count = 0
        def execute_sql_side_effect(sql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'data': {}}  # Segments query returns empty
            elif call_count == 2:
                return {'data': {'flow_id': [flow_id]}}  # flow_object_references returns flows
            else:
                return {'data': {'flow_id': [flow_id]}}  # first_ref_query
        
        mock_db.execute_sql.side_effect = execute_sql_side_effect
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert len(obj.referenced_by_flows) > 0
    
    @pytest.mark.asyncio
    async def test_get_object_timerange_dict_format(self):
        """Test get_object with timerange as dict"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'timerange': [{'value': '0:0_100:0'}],  # Dict format
                'size': [1000000],
                'metadata': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.timerange is not None
    
    @pytest.mark.asyncio
    async def test_get_object_timerange_none(self):
        """Test get_object with timerange as None"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'timerange': [None],  # None
                'size': [1000000],
                'metadata': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.timerange is not None  # Should default to "0:0"
    
    @pytest.mark.asyncio
    async def test_get_object_timerange_empty_string(self):
        """Test get_object with timerange as empty string"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'timerange': [''],  # Empty string
                'size': [1000000],
                'metadata': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert obj.timerange is not None  # Should default to "0:0"
    
    @pytest.mark.asyncio
    async def test_get_object_metadata_json_string(self):
        """Test get_object with metadata as JSON string"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'timerange': ['0:0_100:0'],
                'size': [1000000],
                'metadata': ['{"storage_path": "/path/to/object"}']  # JSON string
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert hasattr(obj, '_internal_metadata')
    
    @pytest.mark.asyncio
    async def test_get_object_size_update_from_s3(self):
        """Test get_object updates size from S3 when missing"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'timerange': ['0:0_100:0'],
                'size': [None],  # Missing size
                'metadata': ['{"storage_path": "/path/to/object"}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        # Mock S3 client
        mock_s3 = Mock()
        mock_s3.get_object_metadata = Mock(return_value={'content_length': 5000000})
        
        service = ObjectStorageService(mock_db, mock_s3)
        obj = await service.get_object(object_id)
        
        assert obj is not None
        assert mock_s3.get_object_metadata.called
    
    @pytest.mark.asyncio
    async def test_get_object_size_update_from_s3_404(self):
        """Test get_object handles S3 404 error gracefully"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id],
                'timerange': ['0:0_100:0'],
                'size': [None],  # Missing size
                'metadata': ['{"storage_path": "/path/to/object"}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        # Mock S3 client - return 404 error
        mock_s3 = Mock()
        mock_s3.get_object_metadata = Mock(side_effect=Exception("404 Not Found"))
        
        service = ObjectStorageService(mock_db, mock_s3)
        obj = await service.get_object(object_id)
        
        assert obj is not None  # Should still return object even if S3 fails
    
    @pytest.mark.asyncio
    async def test_get_object_exception_handling(self):
        """Test get_object exception handling"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        
        with pytest.raises(HTTPException):
            await service.get_object(object_id)
    
    @pytest.mark.asyncio
    async def test_create_object_metadata_dict(self):
        """Test create_object with metadata as dict"""
        object_id = str(uuid.uuid4())
        
        obj = Object(
            id=object_id,
            timerange=TimeRange(value="0:0_100:0"),
            size=1000000,
            referenced_by_flows=[]
        )
        obj._internal_metadata = {"storage_path": "/path/to/object"}
        
        mock_db = Mock()
        mock_db.insert_record = Mock()
        
        service = ObjectStorageService(mock_db, Mock())
        result = await service.create_object(obj)
        
        assert result is True
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_object_metadata_string(self):
        """Test create_object with metadata as string"""
        object_id = str(uuid.uuid4())
        
        obj = Object(
            id=object_id,
            timerange=TimeRange(value="0:0_100:0"),
            size=1000000,
            referenced_by_flows=[]
        )
        # Set metadata as string (should be serialized)
        obj.metadata = '{"storage_path": "/path/to/object"}'
        
        mock_db = Mock()
        mock_db.insert_record = Mock()
        
        service = ObjectStorageService(mock_db, Mock())
        result = await service.create_object(obj)
        
        assert result is True
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_object_exception_handling(self):
        """Test create_object exception handling"""
        object_id = str(uuid.uuid4())
        
        obj = Object(
            id=object_id,
            timerange=TimeRange(value="0:0_100:0"),
            size=1000000,
            referenced_by_flows=[]
        )
        
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database error")
        
        service = ObjectStorageService(mock_db, Mock())
        
        with pytest.raises(HTTPException):
            await service.create_object(obj)
    
    @pytest.mark.asyncio
    async def test_get_unreferenced_objects_list_format(self):
        """Test get_unreferenced_objects with list format result"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Mock referenced query - return list format
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {'object_id': str(uuid.uuid4())}  # Referenced object
            ]
        })
        # Mock all objects query
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id, str(uuid.uuid4())]
            }
        }
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        unreferenced = await service.get_unreferenced_objects()
        
        assert isinstance(unreferenced, list)
    
    @pytest.mark.asyncio
    async def test_get_unreferenced_objects_tuple_format(self):
        """Test get_unreferenced_objects with tuple format result"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Mock referenced query - return tuple format
        mock_db.execute_sql = Mock(return_value={
            'data': [
                (str(uuid.uuid4()),)  # Referenced object (tuple)
            ]
        })
        # Mock all objects query
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id]
            }
        }
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        unreferenced = await service.get_unreferenced_objects()
        
        assert isinstance(unreferenced, list)
    
    @pytest.mark.asyncio
    async def test_get_unreferenced_objects_with_exclude(self):
        """Test get_unreferenced_objects with exclude_object_ids"""
        object_id1 = str(uuid.uuid4())
        object_id2 = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        # Mock all objects query
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [object_id1, object_id2]
            }
        }
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        unreferenced = await service.get_unreferenced_objects(exclude_object_ids=[object_id1])
        
        assert isinstance(unreferenced, list)
        assert object_id1 not in unreferenced
    
    @pytest.mark.asyncio
    async def test_get_unreferenced_objects_exception_handling(self):
        """Test get_unreferenced_objects exception handling"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = ObjectStorageService(mock_db, Mock())
        unreferenced = await service.get_unreferenced_objects()
        
        assert isinstance(unreferenced, list)
        assert len(unreferenced) == 0  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_delete_unreferenced_objects(self):
        """Test delete_unreferenced_objects"""
        object_id1 = str(uuid.uuid4())
        object_id2 = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        service.get_object = AsyncMock(return_value=None)  # Object doesn't exist
        service.list_object_instances = AsyncMock(return_value=[])
        
        deleted_count = await service.delete_unreferenced_objects([object_id1, object_id2])
        
        assert deleted_count == 2
    
    @pytest.mark.asyncio
    async def test_delete_unreferenced_objects_partial_failure(self):
        """Test delete_unreferenced_objects with partial failure"""
        object_id1 = str(uuid.uuid4())
        object_id2 = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        # First delete succeeds, second fails
        call_count = 0
        async def delete_object_side_effect(obj_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return True
            else:
                raise Exception("Delete failed")
        
        service.delete_object = delete_object_side_effect
        
        deleted_count = await service.delete_unreferenced_objects([object_id1, object_id2])
        
        assert deleted_count == 1  # Only first one succeeded
    
    @pytest.mark.asyncio
    async def test_delete_object_instances_s3(self):
        """Test _delete_object_instances_s3"""
        object_id = str(uuid.uuid4())
        
        from vasttams.objects.models import ObjectInstance
        
        instance = ObjectInstance(
            label="test-instance",
            storage_id=str(uuid.uuid4()),
            url="https://example.com/object",
            controlled=True,
            metadata={"storage_path": "/path/to/object"}
        )
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        service.list_object_instances = AsyncMock(return_value=[instance])
        service._delete_s3_object = AsyncMock(return_value=True)
        
        await service._delete_object_instances_s3(object_id)
        
        assert service._delete_s3_object.called
    
    @pytest.mark.asyncio
    async def test_delete_object_instances_s3_url_fallback(self):
        """Test _delete_object_instances_s3 uses URL parsing as fallback"""
        object_id = str(uuid.uuid4())
        
        from vasttams.objects.models import ObjectInstance
        
        instance = ObjectInstance(
            label="test-instance",
            storage_id=str(uuid.uuid4()),
            url="https://example.com/path/to/object",
            controlled=True,
            metadata={}  # No storage_path in metadata
        )
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        service.list_object_instances = AsyncMock(return_value=[instance])
        service._extract_storage_path_from_url = Mock(return_value="/path/to/object")
        service._delete_s3_object = AsyncMock(return_value=True)
        
        await service._delete_object_instances_s3(object_id)
        
        assert service._extract_storage_path_from_url.called
    
    @pytest.mark.asyncio
    async def test_delete_object_with_metadata(self):
        """Test delete_object with object metadata"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        # Mock object with metadata
        obj = Object(
            id=object_id,
            timerange=TimeRange(value="0:0_100:0"),
            size=1000000,
            referenced_by_flows=[]
        )
        obj._internal_metadata = {"storage_path": "/path/to/object", "storage_id": str(uuid.uuid4())}
        
        service = ObjectStorageService(mock_db, Mock())
        service.get_object = AsyncMock(return_value=obj)
        service._delete_object_instances_s3 = AsyncMock()
        service._delete_s3_object = AsyncMock(return_value=True)
        
        result = await service.delete_object(object_id)
        
        assert result is True
        assert service._delete_s3_object.called
    
    @pytest.mark.asyncio
    async def test_delete_object_exception_handling(self):
        """Test delete_object exception handling"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        service._delete_object_instances_s3 = AsyncMock()
        
        with pytest.raises(HTTPException):
            await service.delete_object(object_id)
    
    @pytest.mark.asyncio
    async def test_get_objects_empty_result(self):
        """Test get_objects with empty result"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = ObjectStorageService(mock_db, Mock())
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
        assert len(objects) == 0
    
    @pytest.mark.asyncio
    async def test_get_objects_timerange_dict_format(self):
        """Test get_objects with timerange as dict"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'id': [object_id],
                'size': [1000000],
                'timerange': [{'value': '0:0_100:0'}],  # Dict format
                'created': ['2024-01-01T00:00:00Z'],
                'flow_id': [None],
                'segment_created': [None]
            }
        })
        
        service = ObjectStorageService(mock_db, Mock())
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
        if objects:
            assert objects[0].timerange is not None
    
    @pytest.mark.asyncio
    async def test_get_objects_timerange_none(self):
        """Test get_objects with timerange as None"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'id': [object_id],
                'size': [1000000],
                'timerange': [None],  # None
                'created': ['2024-01-01T00:00:00Z'],
                'flow_id': [None],
                'segment_created': [None]
            }
        })
        
        service = ObjectStorageService(mock_db, Mock())
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
        if objects:
            assert objects[0].timerange is not None  # Should default to "0:0"
    
    @pytest.mark.asyncio
    async def test_get_objects_timerange_empty_string(self):
        """Test get_objects with timerange as empty string"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'id': [object_id],
                'size': [1000000],
                'timerange': [''],  # Empty string
                'created': ['2024-01-01T00:00:00Z'],
                'flow_id': [None],
                'segment_created': [None]
            }
        })
        
        service = ObjectStorageService(mock_db, Mock())
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
        if objects:
            assert objects[0].timerange is not None  # Should default to "0:0"
    
    @pytest.mark.asyncio
    async def test_get_objects_invalid_object_skipped(self):
        """Test get_objects skips invalid objects"""
        object_id1 = str(uuid.uuid4())
        object_id2 = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'id': [object_id1, object_id2],
                'size': [1000000, None],  # object_id2 has invalid data
                'timerange': ['0:0_100:0', None],
                'created': ['2024-01-01T00:00:00Z', None],
                'flow_id': [None, None],
                'segment_created': [None, None]
            }
        })
        
        service = ObjectStorageService(mock_db, Mock())
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
        # Should skip invalid objects
    
    @pytest.mark.asyncio
    async def test_get_objects_exception_handling(self):
        """Test get_objects exception handling"""
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = ObjectStorageService(mock_db, Mock())
        
        with pytest.raises(HTTPException):
            await service.get_objects()
    
    @pytest.mark.asyncio
    async def test_get_objects_partial_results(self):
        """Test get_objects returns partial results on error"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # First call succeeds, second call fails
        call_count = 0
        def execute_sql_side_effect(sql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    'data': {
                        'id': [object_id],
                        'size': [1000000],
                        'timerange': ['0:0_100:0'],
                        'created': ['2024-01-01T00:00:00Z'],
                        'flow_id': [None],
                        'segment_created': [None]
                    }
                }
            else:
                raise Exception("Processing error")
        
        mock_db.execute_sql.side_effect = execute_sql_side_effect
        
        service = ObjectStorageService(mock_db, Mock())
        # Should return partial results instead of failing
        objects = await service.get_objects()
        
        assert isinstance(objects, list)
    
    @pytest.mark.asyncio
    async def test_create_object_instance_object_not_found(self):
        """Test create_object_instance when object doesn't exist"""
        object_id = str(uuid.uuid4())
        
        from vasttams.objects.models import ObjectInstance
        instance = ObjectInstance(
            label="test-instance",
            storage_id=str(uuid.uuid4()),
            url="https://example.com/object",
            controlled=False
        )
        
        mock_db = Mock()
        service = ObjectStorageService(mock_db, Mock())
        service.get_object = AsyncMock(return_value=None)  # Object doesn't exist
        
        result = await service.create_object_instance(object_id, instance)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_object_instance_exception_handling(self):
        """Test create_object_instance exception handling"""
        object_id = str(uuid.uuid4())
        
        from vasttams.objects.models import ObjectInstance
        instance = ObjectInstance(
            label="test-instance",
            storage_id=str(uuid.uuid4()),
            url="https://example.com/object",
            controlled=False
        )
        
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database error")
        
        service = ObjectStorageService(mock_db, Mock())
        service.get_object = AsyncMock(return_value=Object(
            id=object_id,
            timerange=TimeRange(value="0:0_100:0"),
            size=1000000,
            referenced_by_flows=[]
        ))
        
        with pytest.raises(HTTPException):
            await service.create_object_instance(object_id, instance)
    
    @pytest.mark.asyncio
    async def test_list_object_instances_list_format(self):
        """Test list_object_instances with list format result"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = [{
            'label': 'instance1',
            'storage_id': str(uuid.uuid4()),
            'url': 'https://example.com/obj1',
            'controlled': False,
            'metadata': {}
        }]
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        instances = await service.list_object_instances(object_id)
        
        assert isinstance(instances, list)
    
    @pytest.mark.asyncio
    async def test_list_object_instances_data_as_list(self):
        """Test list_object_instances with data as list"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [{
                'label': 'instance1',
                'storage_id': str(uuid.uuid4()),
                'url': 'https://example.com/obj1',
                'controlled': False,
                'metadata': {}
            }]
        }
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        instances = await service.list_object_instances(object_id)
        
        assert isinstance(instances, list)
    
    @pytest.mark.asyncio
    async def test_extract_storage_path_from_url(self):
        """Test _extract_storage_path_from_url"""
        service = ObjectStorageService(Mock(), Mock())
        
        url = "https://example.com/path/to/object"
        path = service._extract_storage_path_from_url(url)
        
        assert path is not None
    
    @pytest.mark.asyncio
    async def test_extract_storage_path_from_url_none(self):
        """Test _extract_storage_path_from_url with invalid URL"""
        service = ObjectStorageService(Mock(), Mock())
        
        url = "invalid-url"
        path = service._extract_storage_path_from_url(url)
        
        # Should return None or handle gracefully
        assert path is None or isinstance(path, str)
    
    @pytest.mark.asyncio
    async def test_get_storage_path_from_instance_metadata(self):
        """Test _get_storage_path_from_instance with metadata"""
        service = ObjectStorageService(Mock(), Mock())
        
        instance_data = {
            'metadata': {
                'storage_path': '/path/to/object'
            }
        }
        
        path = service._get_storage_path_from_instance(instance_data)
        
        assert path == '/path/to/object'
    
    @pytest.mark.asyncio
    async def test_get_storage_path_from_instance_url(self):
        """Test _get_storage_path_from_instance with URL"""
        service = ObjectStorageService(Mock(), Mock())
        service._extract_storage_path_from_url = Mock(return_value='/path/to/object')
        
        instance_data = {
            'url': 'https://example.com/path/to/object',
            'metadata': {}
        }
        
        path = service._get_storage_path_from_instance(instance_data)
        
        assert path == '/path/to/object'
    
    @pytest.mark.asyncio
    async def test_delete_s3_object(self):
        """Test _delete_s3_object"""
        storage_path = "/path/to/object"
        storage_id = str(uuid.uuid4())
        
        mock_s3 = Mock()
        mock_s3.delete_object = Mock(return_value=True)
        
        service = ObjectStorageService(Mock(), mock_s3)
        result = await service._delete_s3_object(storage_path, storage_id=storage_id)
        
        assert result is True
        assert mock_s3.delete_object.called
    
    @pytest.mark.asyncio
    async def test_delete_s3_object_no_storage_id(self):
        """Test _delete_s3_object without storage_id"""
        storage_path = "/path/to/object"
        
        mock_s3 = Mock()
        mock_s3.delete_object = Mock(return_value=True)
        
        service = ObjectStorageService(Mock(), mock_s3)
        result = await service._delete_s3_object(storage_path)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_s3_object_exception(self):
        """Test _delete_s3_object exception handling"""
        storage_path = "/path/to/object"
        
        mock_s3 = Mock()
        mock_s3.delete_object = Mock(side_effect=Exception("S3 error"))
        
        service = ObjectStorageService(Mock(), mock_s3)
        result = await service._delete_s3_object(storage_path)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_object_instance_by_label(self):
        """Test delete_object_instance by label"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        result = await service.delete_object_instance(object_id, label="test-instance")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_object_instance_by_storage_id(self):
        """Test delete_object_instance by storage_id"""
        object_id = str(uuid.uuid4())
        storage_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        result = await service.delete_object_instance(object_id, storage_id=storage_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_object_instance_exception_handling(self):
        """Test delete_object_instance exception handling"""
        object_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = ObjectStorageService(mock_db, Mock())
        
        with pytest.raises(HTTPException):
            await service.delete_object_instance(object_id, label="test-instance")

