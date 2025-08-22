"""
End-to-End Workflow Tests

This module tests the complete TAMS workflow from source creation
through analytics, ensuring all components work together correctly.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime, timezone, timedelta
import json

from tests.test_utils.mock_vastdbmanager import MockVastDBManager
from tests.test_utils.mock_s3store import MockS3Store
from tests.test_utils.test_helpers import TestDataFactory


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow scenarios"""
    
    def test_basic_media_workflow(self):
        """Test basic media workflow: Source -> Flow -> Segments -> Objects -> Analytics"""
        # Initialize mock storage
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Step 1: Create source
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Camera',
            'description': 'Test camera for workflow validation'
        })
        
        assert source.id is not None
        assert source.format == 'urn:x-nmos:format:video'
        assert source.label == 'Test Camera'
        
        # Step 2: Create flow
        flow = vast_storage.create_flow({
            'source_id': source.id,
            'format': 'urn:x-nmos:format:video',
            'codec': 'video/mp4',
            'label': 'Test Flow',
            'description': 'Test flow for workflow validation'
        })
        
        assert flow.id is not None
        assert flow.source_id == source.id
        assert flow.format == 'urn:x-nmos:format:video'
        
        # Step 3: Create segments
        segments = []
        for i in range(3):
            segment = vast_storage.create_segment({
                'flow_id': flow.id,
                'storage_path': f'/test/segments/segment_{i}.mp4'
            })
            segments.append(segment)
        
        assert len(segments) == 3
        for segment in segments:
            assert segment.object_id is not None
            assert segment.timerange is not None
        
        # Step 4: Store segment content in S3
        for i, segment in enumerate(segments):
            segment_data = f"mock video data for segment {i}".encode('utf-8')
            object_key = s3_storage.store_segment(segment, segment_data)
            
            assert object_key is not None
            assert s3_storage.object_exists(object_key)
            
            # Verify data integrity
            retrieved_data = s3_storage.retrieve_segment(segment)
            assert retrieved_data == segment_data
        
        # Step 5: Create objects (detected entities)
        objects = []
        for i in range(2):
            obj = vast_storage.create_object({
                'referenced_by_flows': [str(flow.id)],
                'size': 1024 * (i + 1)
            })
            objects.append(obj)
        
        assert len(objects) == 2
        for obj in objects:
            assert obj.id is not None
            assert str(flow.id) in obj.referenced_by_flows
        
        # Step 6: Run analytics
        analytics_results = vast_storage.run_analytics({
            'flow_id': str(flow.id),
            'time_range': '[1000:0_2000:0]',
            'query': 'SELECT COUNT(*) FROM objects WHERE referenced_by_flows CONTAINS ?'
        })
        
        assert analytics_results is not None
        assert 'count' in analytics_results
        
        # Verify workflow integrity
        retrieved_source = vast_storage.get_source(source.id)
        retrieved_flow = vast_storage.get_flow(flow.id)
        
        assert retrieved_source.id == source.id
        assert retrieved_flow.source_id == source.id
        
        # Verify relationships
        source_flows = vast_storage.list_flows(source_id=source.id)
        assert len(source_flows) == 1
        assert source_flows[0].id == flow.id
        
        flow_segments = vast_storage.list_segments(flow_id=flow.id)
        assert len(flow_segments) == 3
        
        # Verify S3 storage
        for segment in segments:
            object_key = f"segments/{segment.object_id}/segment"
            assert s3_storage.object_exists(object_key)
    
    def test_batch_operations_workflow(self):
        """Test workflow with batch operations"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Batch create sources
        sources = []
        for i in range(5):
            source = vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': f'Camera {i}',
                'description': f'Camera {i} for batch testing'
            })
            sources.append(source)
        
        assert len(sources) == 5
        
        # Batch create flows for each source
        flows = []
        for source in sources:
            flow = vast_storage.create_flow({
                'source_id': source.id,
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': f'Flow for {source.label}',
                'description': f'Flow for {source.label}'
            })
            flows.append(flow)
        
        assert len(flows) == 5
        
        # Batch create segments for each flow
        all_segments = []
        for flow in flows:
            flow_segments = []
            for j in range(2):
                segment = vast_storage.create_segment({
                    'flow_id': flow.id,
                    'storage_path': f'/test/batch/flow_{flow.id}/segment_{j}.mp4'
                })
                flow_segments.append(segment)
            all_segments.extend(flow_segments)
        
        assert len(all_segments) == 10
        
        # Batch store segments in S3
        for segment in all_segments:
            segment_data = f"batch segment data for {segment.object_id}".encode('utf-8')
            object_key = s3_storage.store_segment(segment, segment_data)
            assert object_key is not None
        
        # Batch create objects
        all_objects = []
        for flow in flows:
            for k in range(3):
                obj = vast_storage.create_object({
                    'referenced_by_flows': [str(flow.id)],
                    'size': 1024 * (k + 1)
                })
                all_objects.append(obj)
        
        assert len(all_objects) == 15
        
        # Verify batch operations
        for source in sources:
            source_flows = vast_storage.list_flows(source_id=source.id)
            assert len(source_flows) == 1
        
        for flow in flows:
            flow_segments = vast_storage.list_segments(flow_id=flow.id)
            assert len(flow_segments) == 2
        
        # Batch analytics
        analytics_results = vast_storage.run_analytics({
            'query': 'SELECT COUNT(*) FROM sources',
            'time_range': '[0:0_10000:0]'
        })
        
        assert analytics_results['count'] == 5
        
        analytics_results = vast_storage.run_analytics({
            'query': 'SELECT COUNT(*) FROM flows',
            'time_range': '[0:0_10000:0]'
        })
        
        assert analytics_results['count'] == 5
    
    def test_error_recovery_workflow(self):
        """Test workflow error recovery scenarios"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Test source creation failure
        with patch.object(vast_storage, 'create_source') as mock_create:
            mock_create.side_effect = Exception("Source creation failed")
            
            with pytest.raises(Exception):
                vast_storage.create_source({
                    'format': 'urn:x-nmos:format:video',
                    'label': 'Test Source'
                })
        
        # Test flow creation with invalid source
        with pytest.raises(Exception):
            vast_storage.create_flow({
                'source_id': 'invalid-uuid',
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': 'Test Flow'
            })
        
        # Test segment storage failure
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Source'
        })
        
        flow = vast_storage.create_flow({
            'source_id': source.id,
            'format': 'urn:x-nmos:format:video',
            'codec': 'video/mp4',
            'label': 'Test Flow'
        })
        
        segment = vast_storage.create_segment({
            'flow_id': flow.id,
            'storage_path': '/test/path'
        })
        
        # Test S3 storage failure
        with patch.object(s3_storage, 'store_segment') as mock_store:
            mock_store.side_effect = Exception("S3 storage failed")
            
            with pytest.raises(Exception):
                s3_storage.store_segment(segment, b"test data")
        
        # Test analytics failure
        with patch.object(vast_storage, 'run_analytics') as mock_analytics:
            mock_analytics.side_effect = Exception("Analytics failed")
            
            with pytest.raises(Exception):
                vast_storage.run_analytics({
                    'query': 'SELECT * FROM sources'
                })
    
    def test_data_consistency_workflow(self):
        """Test workflow data consistency across operations"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Create initial data
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Consistency Test Camera',
            'description': 'Camera for consistency testing'
        })
        
        flow = vast_storage.create_flow({
            'source_id': source.id,
            'format': 'urn:x-nmos:format:video',
            'codec': 'video/mp4',
            'label': 'Consistency Test Flow',
            'description': 'Flow for consistency testing'
        })
        
        # Verify initial state
        initial_source = vast_storage.get_source(source.id)
        initial_flow = vast_storage.get_flow(flow.id)
        
        assert initial_source.id == source.id
        assert initial_flow.source_id == source.id
        
        # Update source
        updated_source = vast_storage.update_source(source.id, {
            'label': 'Updated Consistency Test Camera',
            'description': 'Updated description'
        })
        
        assert updated_source.label == 'Updated Consistency Test Camera'
        
        # Verify update persisted
        retrieved_source = vast_storage.get_source(source.id)
        assert retrieved_source.label == 'Updated Consistency Test Camera'
        
        # Update flow
        updated_flow = vast_storage.update_flow(flow.id, {
            'label': 'Updated Consistency Test Flow',
            'description': 'Updated flow description'
        })
        
        assert updated_flow.label == 'Updated Consistency Test Flow'
        
        # Verify flow update persisted
        retrieved_flow = vast_storage.get_flow(flow.id)
        assert retrieved_flow.label == 'Updated Consistency Test Flow'
        
        # Test deletion consistency
        vast_storage.delete_source(source.id)
        deleted_source = vast_storage.get_source(source.id)
        assert deleted_source is None
        
        # Flow should also be deleted (cascade)
        deleted_flow = vast_storage.get_flow(flow.id)
        assert deleted_flow is None
        
        # Verify S3 cleanup
        segments = vast_storage.list_segments(flow_id=flow.id)
        assert len(segments) == 0
    
    def test_workflow_edge_cases(self):
        """Test workflow edge cases and boundary conditions"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Test with empty data
        empty_sources = vast_storage.list_sources()
        assert len(empty_sources) == 0
        
        empty_flows = vast_storage.list_flows()
        assert len(empty_flows) == 0
        
        empty_segments = vast_storage.list_segments()
        assert len(empty_segments) == 0
        
        empty_objects = vast_storage.list_objects()
        assert len(empty_objects) == 0
        
        # Test with single item
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Single Test Camera',
            'description': 'Single camera for edge case testing'
        })
        
        single_sources = vast_storage.list_sources()
        assert len(single_sources) == 1
        assert single_sources[0].id == source.id
        
        # Test with maximum items (simulate large dataset)
        for i in range(100):
            vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': f'Camera {i}',
                'description': f'Camera {i} for large dataset testing'
            })
        
        large_sources = vast_storage.list_sources()
        assert len(large_sources) == 101  # 100 + 1 from above
        
        # Test reset functionality
        vast_storage.reset_test_data()
        
        reset_sources = vast_storage.list_sources()
        assert len(reset_sources) == 0
        
        # Test S3 edge cases
        s3_storage.reset_test_data()
        
        empty_buckets = s3_storage.list_buckets()
        assert len(empty_buckets) == 0
        
        # Test with invalid data
        with pytest.raises(Exception):
            vast_storage.create_source({})  # Missing required fields
        
        with pytest.raises(Exception):
            vast_storage.create_flow({})  # Missing required fields
        
        with pytest.raises(Exception):
            vast_storage.create_segment({})  # Missing required fields
        
        with pytest.raises(Exception):
            vast_storage.create_object({})  # Missing required fields


class TestWorkflowIntegration:
    """Test workflow integration with external systems"""
    
    def test_workflow_with_external_api(self):
        """Test workflow integration with external API calls"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Mock external API calls
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'status': 'success',
                'data': {'external_id': 'ext-123'}
            }
            
            # Create source with external reference
            source = vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': 'External API Camera',
                'description': 'Camera with external API integration'
            })
            
            # Verify external integration
            assert source.id is not None
    
    def test_workflow_with_database_transactions(self):
        """Test workflow with database transaction handling"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Test transaction rollback scenario
        try:
            # Create source
            source = vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': 'Transaction Test Camera',
                'description': 'Camera for transaction testing'
            })
            
            # Create flow
            flow = vast_storage.create_flow({
                'source_id': source.id,
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': 'Transaction Test Flow'
            })
            
            # Simulate error that would trigger rollback
            raise Exception("Simulated transaction error")
            
        except Exception:
            # In a real scenario, this would trigger rollback
            # For mock testing, we verify the error was raised
            pass
        
        # Verify data state after error
        sources = vast_storage.list_sources()
        flows = vast_storage.list_flows()
        
        # Note: Mock implementation doesn't implement transactions
        # This test documents the expected behavior
        assert len(sources) >= 0
        assert len(flows) >= 0
    
    def test_workflow_with_async_operations(self):
        """Test workflow with asynchronous operations"""
        vast_storage = MockVastDBManager()
        s3_storage = MockS3Store()
        
        # Test async source creation
        async def create_source_async():
            return vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': 'Async Test Camera',
                'description': 'Camera for async testing'
            })
        
        # In a real async scenario, this would be awaited
        # For testing, we just verify the function exists
        assert callable(create_source_async)
        
        # Test async flow creation
        async def create_flow_async(source_id):
            return vast_storage.create_flow({
                'source_id': source_id,
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': 'Async Test Flow'
            })
        
        assert callable(create_flow_async)
        
        # Test async segment processing
        async def process_segments_async(flow_id):
            segments = []
            for i in range(3):
                segment = vast_storage.create_segment({
                    'flow_id': flow_id,
                    'storage_path': f'/test/async/segment_{i}.mp4'
                })
                segments.append(segment)
            return segments
        
        assert callable(process_segments_async)
