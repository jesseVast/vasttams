"""
End-to-End Workflow Tests with Parameterized Storage

This module tests the complete TAMS workflow from source creation
through analytics, ensuring all components work together correctly.

Support for both mock and real storage backends via environment variable:
- TAMS_TEST_BACKEND=mock (default) - Use mock storage (fast, no external deps)
- TAMS_TEST_BACKEND=real - Use real storage from config.py (requires services)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime, timezone, timedelta
import json

from tests.test_utils.mock_vastdbmanager import MockVastDBManager
from tests.test_utils.mock_s3store import MockS3Store
from tests.test_utils.test_helpers import TestDataFactory
import os

# Simple storage backend configuration
USE_MOCK_STORAGE = os.getenv("TAMS_TEST_BACKEND", "mock") == "mock"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow scenarios"""
    
    def test_basic_media_workflow(self):
        """Test basic media workflow: Source -> Flow -> Segments -> Objects -> Analytics"""
        
        # EASY SWITCHING: Environment variable controls storage backend
        if USE_MOCK_STORAGE:
            # Use mock storage (fast, no external dependencies)
            vast_storage = MockVastDBManager()
            s3_storage = MockS3Store()
            print(f"Using MOCK storage for testing")
        else:
            # Use real storage (requires external services) 
            from app.storage.vastdbmanager import VastDBManager
            from app.storage.s3_store import S3Store
            from app.core.config import get_settings
            
            settings = get_settings()
            # VastDBManager expects endpoints as a parameter
            vast_storage = VastDBManager(endpoints=settings.vast_endpoint)
            s3_storage = S3Store(
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                bucket_name=settings.s3_bucket_name
            )
            print(f"Using REAL storage from config.py")
        
        # YOUR EXISTING TEST LOGIC STAYS EXACTLY THE SAME!
        # No changes needed below this point
        
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
        
        backend = "mock" if USE_MOCK_STORAGE else "real"
        print(f"✅ Test completed successfully with {backend} storage")
    
    def test_batch_operations(self):
        """Test batch operations with multiple sources and flows"""
        
        # Same easy switching pattern
        if USE_MOCK_STORAGE:
            vast_storage = MockVastDBManager()
            s3_storage = MockS3Store()
        else:
            from app.storage.vastdbmanager import VastDBManager
            from app.storage.s3_store import S3Store
            from app.core.config import get_settings
            
            settings = get_settings()
            vast_storage = VastDBManager(endpoints=settings.vast_endpoint)
            s3_storage = S3Store(
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                bucket_name=settings.s3_bucket_name
            )
        
        # Create multiple sources
        sources = []
        for i in range(3):
            source = vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': f'Test Camera {i}',
                'description': f'Test camera {i} for batch validation'
            })
            sources.append(source)
        
        assert len(sources) == 3
        
        # Create flows for each source
        flows = []
        for source in sources:
            flow = vast_storage.create_flow({
                'source_id': source.id,
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': f'Flow for {source.label}',
                'description': 'Batch flow test'
            })
            flows.append(flow)
        
        assert len(flows) == 3
        
        # Verify relationships
        for i, (source, flow) in enumerate(zip(sources, flows)):
            assert flow.source_id == source.id
            assert flow.format == source.format
        
        backend = "mock" if USE_MOCK_STORAGE else "real"
        print(f"✅ Batch test completed with {backend} storage")
    
    def test_data_integrity(self):
        """Test data integrity and retrieval"""
        
        # Same easy switching pattern
        if USE_MOCK_STORAGE:
            vast_storage = MockVastDBManager()
            s3_storage = MockS3Store()
        else:
            from app.storage.vastdbmanager import VastDBManager
            from app.storage.s3_store import S3Store
            from app.core.config import get_settings
            
            settings = get_settings()
            vast_storage = VastDBManager(endpoints=settings.vast_endpoint)
            s3_storage = S3Store(
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                bucket_name=settings.s3_bucket_name
            )
        
        # Create source and verify retrieval
        source = vast_storage.create_source({
            'format': 'urn:x-nmos:format:video',
            'label': 'Integrity Test Source',
            'description': 'Source for data integrity testing'
        })
        
        # Retrieve and verify
        retrieved_source = vast_storage.get_source(str(source.id))
        assert retrieved_source is not None
        assert retrieved_source.id == source.id
        assert retrieved_source.label == source.label
        
        # Create flow and verify retrieval
        flow = vast_storage.create_flow({
            'source_id': source.id,
            'format': 'urn:x-nmos:format:video',
            'codec': 'video/mp4',
            'label': 'Integrity Test Flow'
        })
        
        retrieved_flow = vast_storage.get_flow(str(flow.id))
        assert retrieved_flow is not None
        assert retrieved_flow.id == flow.id
        assert retrieved_flow.source_id == source.id
        
        backend = "mock" if USE_MOCK_STORAGE else "real"
        print(f"✅ Data integrity test completed with {backend} storage")
    
    def test_list_operations(self):
        """Test listing operations for all entity types"""
        
        # Same easy switching pattern
        if USE_MOCK_STORAGE:
            vast_storage = MockVastDBManager()
            s3_storage = MockS3Store()
        else:
            from app.storage.vastdbmanager import VastDBManager
            from app.storage.s3_store import S3Store
            from app.core.config import get_settings
            
            settings = get_settings()
            vast_storage = VastDBManager(endpoints=settings.vast_endpoint)
            s3_storage = S3Store(
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                bucket_name=settings.s3_bucket_name
            )
        
        # Create test data
        sources = []
        flows = []
        segments = []
        objects = []
        
        # Create sources
        for i in range(2):
            source = vast_storage.create_source({
                'format': 'urn:x-nmos:format:video',
                'label': f'List Test Source {i}'
            })
            sources.append(source)
        
        # Create flows
        for source in sources:
            flow = vast_storage.create_flow({
                'source_id': source.id,
                'format': 'urn:x-nmos:format:video',
                'codec': 'video/mp4',
                'label': f'List Test Flow for {source.label}'
            })
            flows.append(flow)
        
        # Create segments
        for flow in flows:
            segment = vast_storage.create_segment({
                'flow_id': flow.id,
                'storage_path': f'/test/list/{flow.id}/segment.mp4'
            })
            segments.append(segment)
        
        # Create objects
        for flow in flows:
            obj = vast_storage.create_object({
                'referenced_by_flows': [str(flow.id)],
                'size': 2048
            })
            objects.append(obj)
        
        # Test list operations
        all_sources = vast_storage.list_sources()
        assert len(all_sources) >= len(sources)
        
        all_flows = vast_storage.list_flows()
        assert len(all_flows) >= len(flows)
        
        all_segments = vast_storage.list_segments()
        assert len(all_segments) >= len(segments)
        
        all_objects = vast_storage.list_objects()
        assert len(all_objects) >= len(objects)
        
        backend = "mock" if USE_MOCK_STORAGE else "real"
        print(f"✅ List operations test completed with {backend} storage")


# Example usage functions
def run_mock_tests():
    """Run tests with mock storage only"""
    import os
    os.environ['TAMS_TEST_BACKEND'] = 'mock'
    pytest.main([__file__, "-v"])

def run_real_tests():
    """Run tests with real storage only"""
    import os
    os.environ['TAMS_TEST_BACKEND'] = 'real'
    pytest.main([__file__, "-v"])

def run_all_tests():
    """Run tests with current backend setting"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        backend = sys.argv[1]
        if backend == "mock":
            run_mock_tests()
        elif backend == "real":
            run_real_tests()
        else:
            run_all_tests()
    else:
        run_all_tests()
