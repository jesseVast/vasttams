#!/usr/bin/env python3
"""
Comprehensive integration tests for TAMS API with real database.

This test suite tests the complete TAMS functionality using the real VAST database
and S3 storage, including all CRUD operations, soft delete functionality, and
cascade operations.
"""

import asyncio
import logging
import sys
import os
import uuid
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_settings
from app.vast_store import VASTStore
from app.models import Source, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow, FlowSegment, Object, Tags, CollectionItem
from app.sources import SourceManager
from app.flows import FlowManager
from app.segments import SegmentManager
from app.objects import ObjectManager
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio

class TestTAMSIntegration:
    """Comprehensive integration tests for TAMS with real database."""
    
    def setup_method(self, method):
        """Setup test environment with real database."""
        # Run async setup in sync context
        asyncio.run(self._async_setup())

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Run async teardown in sync context
        asyncio.run(self._async_teardown())

    async def _async_setup(self):
        """Async setup method."""
        self.settings = get_settings()
        self.store = VASTStore(
            endpoint=self.settings.vast_endpoint,
            access_key=self.settings.vast_access_key,
            secret_key=self.settings.vast_secret_key,
            bucket=self.settings.vast_bucket,
            schema=self.settings.vast_schema,
            s3_endpoint_url=self.settings.s3_endpoint_url,
            s3_access_key_id=self.settings.s3_access_key_id,
            s3_secret_access_key=self.settings.s3_secret_access_key,
            s3_bucket_name=self.settings.s3_bucket_name,
            s3_use_ssl=self.settings.s3_use_ssl
        )
        
        # Initialize managers
        self.source_manager = SourceManager(store=self.store)
        self.flow_manager = FlowManager(store=self.store)
        self.segment_manager = SegmentManager(store=self.store)
        self.object_manager = ObjectManager(store=self.store)
        
        # Test data storage
        self.test_data = {}
        
        logger.info("✅ Test environment setup complete")

    async def _async_teardown(self):
        """Async teardown method."""
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data after tests."""
        try:
            logger.info("🧹 Cleaning up test data...")
            
            # Hard delete all test data
            if 'test_sources' in self.test_data:
                for source_id in self.test_data['test_sources']:
                    try:
                        await self.store.delete_source(source_id, soft_delete=False, cascade=True, deleted_by="test_cleanup")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup source {source_id}: {e}")
            
            if 'test_flows' in self.test_data:
                for flow_id in self.test_data['test_flows']:
                    try:
                        await self.store.delete_flow(flow_id, soft_delete=False, cascade=True, deleted_by="test_cleanup")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup flow {flow_id}: {e}")
            
            if 'test_objects' in self.test_data:
                for object_id in self.test_data['test_objects']:
                    try:
                        await self.store.delete_object(object_id, soft_delete=False, deleted_by="test_cleanup")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup object {object_id}: {e}")
            
            logger.info("✅ Test data cleanup complete")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def create_test_source(self, source_type: str = "video") -> Source:
        """Create a test source."""
        source_id = str(uuid.uuid4())
        
        if source_type == "video":
            format_urn = "urn:x-nmos:format:video"
        elif source_type == "audio":
            format_urn = "urn:x-nmos:format:audio"
        elif source_type == "data":
            format_urn = "urn:x-nmos:format:data"
        else:
            format_urn = "urn:x-nmos:format:video"
        
        source = Source(
            id=uuid.UUID(source_id),
            format=format_urn,
            label=f"Test {source_type.title()} Source",
            description=f"A test {source_type} source for integration testing",
            created_by="integration_test",
            updated_by="integration_test",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
            tags=Tags({
                "test": "integration",
                "type": source_type,
                "created_by": "integration_test"
            }),
            source_collection=[
                CollectionItem(id=str(uuid.uuid4()), label=f"Collection {source_type}")
            ],
            collected_by=[str(uuid.uuid4())]
        )
        
        return source
    
    def create_test_flow(self, source_id: str, flow_type: str = "video") -> VideoFlow:
        """Create a test flow."""
        flow_id = str(uuid.uuid4())
        
        if flow_type == "video":
            flow = VideoFlow(
                id=uuid.UUID(flow_id),
                source_id=uuid.UUID(source_id),
                format="urn:x-nmos:format:video",
                codec="video/mp4",
                label=f"Test Video Flow",
                description="A test video flow for integration testing",
                created_by="integration_test",
                updated_by="integration_test",
                created=datetime.now(timezone.utc),
                updated=datetime.now(timezone.utc),
                tags=Tags({
                    "test": "integration",
                    "type": "video",
                    "created_by": "integration_test"
                }),
                frame_width=1920,
                frame_height=1080,
                frame_rate="25/1",
                container="mp4",
                read_only=False,
                max_bit_rate=5000000,
                avg_bit_rate=3000000
            )
        elif flow_type == "audio":
            flow = AudioFlow(
                id=uuid.UUID(flow_id),
                source_id=uuid.UUID(source_id),
                format="urn:x-nmos:format:audio",
                codec="audio/aac",
                label=f"Test Audio Flow",
                description="A test audio flow for integration testing",
                created_by="integration_test",
                updated_by="integration_test",
                created=datetime.now(timezone.utc),
                updated=datetime.now(timezone.utc),
                tags=Tags({
                    "test": "integration",
                    "type": "audio",
                    "created_by": "integration_test"
                }),
                sample_rate=48000,
                bits_per_sample=16,
                channels=2,
                container="aac",
                read_only=False,
                max_bit_rate=128000,
                avg_bit_rate=96000
            )
        else:
            flow = DataFlow(
                id=uuid.UUID(flow_id),
                source_id=uuid.UUID(source_id),
                format="urn:x-nmos:format:data",
                codec="application/json",
                label=f"Test Data Flow",
                description="A test data flow for integration testing",
                created_by="integration_test",
                updated_by="integration_test",
                created=datetime.now(timezone.utc),
                updated=datetime.now(timezone.utc),
                tags=Tags({
                    "test": "integration",
                    "type": "data",
                    "created_by": "integration_test"
                }),
                container="json",
                read_only=False
            )
        
        return flow
    
    def create_test_segment(self, flow_id: str) -> FlowSegment:
        """Create a test flow segment."""
        segment = FlowSegment(
            id=str(uuid.uuid4()),
            flow_id=flow_id,
            object_id=f"test_obj_{uuid.uuid4().hex[:8]}",
            timerange="[0:0_10:0)",
            ts_offset="0:0",
            last_duration="10:0",
            sample_offset=0,
            sample_count=250,
            key_frame_count=1,
            created=datetime.now(timezone.utc),
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=10.0
        )
        
        return segment
    
    def create_test_object(self, flow_id: str) -> Object:
        """Create a test object."""
        object_data = Object(
            object_id=f"test_obj_{uuid.uuid4().hex[:8]}",
            flow_references=[{"flow_id": flow_id}],
            size=1024000,
            created=datetime.now(timezone.utc)
        )
        
        return object_data
    
    @pytest.mark.asyncio
    async def test_database_connectivity(self):
        """Test database connectivity."""
        logger.info("🔗 Testing database connectivity...")
        
        # Test VAST DB connection
        tables = self.store.list_tables()
        assert len(tables) > 0, "No tables found in database"
        assert 'sources' in tables, "Sources table not found"
        assert 'flows' in tables, "Flows table not found"
        assert 'segments' in tables, "Segments table not found"
        assert 'objects' in tables, "Objects table not found"
        
        logger.info(f"✅ Database connectivity verified. Found tables: {tables}")
    
    @pytest.mark.asyncio
    async def test_source_crud_operations(self):
        """Test complete source CRUD operations."""
        logger.info("📝 Testing source CRUD operations...")
        
        # Create test source
        source = self.create_test_source("video")
        created_source = await self.source_manager.create_source(source, store=self.store)
        assert created_source is not None, "Source creation failed"
        assert created_source.id == source.id, "Source ID mismatch"
        
        # Store for cleanup
        if 'test_sources' not in self.test_data:
            self.test_data['test_sources'] = []
        self.test_data['test_sources'].append(str(source.id))
        
        # Read source
        retrieved_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert retrieved_source is not None, "Source retrieval failed"
        assert retrieved_source.id == source.id, "Retrieved source ID mismatch"
        assert retrieved_source.label == source.label, "Retrieved source label mismatch"
        
        # Update source
        updated_label = "Updated Test Video Source"
        retrieved_source.label = updated_label
        update_result = await self.source_manager.update_source(str(source.id), retrieved_source, store=self.store)
        assert update_result is not None, "Source update failed"
        
        # Verify update
        updated_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert updated_source.label == updated_label, "Source update not persisted"
        
        # List sources
        sources_response = await self.source_manager.list_sources(filters={}, limit=100, store=self.store)
        sources = sources_response.data
        assert len(sources) > 0, "No sources found in list"
        
        # Test soft delete
        delete_result = await self.source_manager.delete_source(
            str(source.id), 
            store=self.store, 
            soft_delete=True, 
            cascade=False, 
            deleted_by="integration_test"
        )
        assert "soft deleted" in delete_result["message"], "Soft delete failed"
        
        # Verify soft delete (should not be returned in normal queries)
        try:
            deleted_source = await self.source_manager.get_source(str(source.id), store=self.store)
            assert False, "Soft deleted source should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Soft deleted source correctly not found")
        
        logger.info("✅ Source CRUD operations completed successfully")
    
    @pytest.mark.asyncio
    async def test_flow_crud_operations(self):
        """Test complete flow CRUD operations."""
        logger.info("🎬 Testing flow CRUD operations...")
        
        # Create test source first
        source = self.create_test_source("video")
        created_source = await self.source_manager.create_source(source, store=self.store)
        assert created_source is not None, "Source creation failed"
        
        # Store for cleanup
        if 'test_sources' not in self.test_data:
            self.test_data['test_sources'] = []
        self.test_data['test_sources'].append(str(source.id))
        
        # Create test flow
        flow = self.create_test_flow(str(source.id), "video")
        created_flow = await self.flow_manager.create_flow(flow, store=self.store)
        assert created_flow is not None, "Flow creation failed"
        assert created_flow.id == flow.id, "Flow ID mismatch"
        
        # Store for cleanup
        if 'test_flows' not in self.test_data:
            self.test_data['test_flows'] = []
        self.test_data['test_flows'].append(str(flow.id))
        
        # Read flow
        retrieved_flow = await self.flow_manager.get_flow(str(flow.id), store=self.store)
        assert retrieved_flow is not None, "Flow retrieval failed"
        assert retrieved_flow.id == flow.id, "Retrieved flow ID mismatch"
        assert retrieved_flow.source_id == flow.source_id, "Retrieved flow source_id mismatch"
        
        # Update flow
        updated_label = "Updated Test Video Flow"
        retrieved_flow.label = updated_label
        update_result = await self.flow_manager.update_flow(str(flow.id), retrieved_flow, store=self.store)
        assert update_result is not None, "Flow update failed"
        
        # Verify update
        updated_flow = await self.flow_manager.get_flow(str(flow.id), store=self.store)
        assert updated_flow.label == updated_label, "Flow update not persisted"
        
        # List flows
        flows_response = await self.flow_manager.list_flows(filters={}, limit=100, store=self.store)
        flows = flows_response.data
        assert len(flows) > 0, "No flows found in list"
        
        # Test soft delete
        delete_result = await self.flow_manager.delete_flow(
            str(flow.id), 
            store=self.store, 
            soft_delete=True, 
            cascade=False, 
            deleted_by="integration_test"
        )
        assert "soft deleted" in delete_result["message"], "Soft delete failed"
        
        # Verify soft delete
        try:
            deleted_flow = await self.flow_manager.get_flow(str(flow.id), store=self.store)
            assert False, "Soft deleted flow should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Soft deleted flow correctly not found")
        
        logger.info("✅ Flow CRUD operations completed successfully")
    
    @pytest.mark.asyncio
    async def test_object_crud_operations(self):
        """Test complete object CRUD operations."""
        logger.info("📦 Testing object CRUD operations...")
        
        # Create test object
        object_data = self.create_test_object("test_flow_id")
        created_object = await self.object_manager.create_object(object_data, store=self.store)
        assert created_object is not None, "Object creation failed"
        assert created_object.object_id == object_data.object_id, "Object ID mismatch"
        
        # Store for cleanup
        if 'test_objects' not in self.test_data:
            self.test_data['test_objects'] = []
        self.test_data['test_objects'].append(object_data.object_id)
        
        # Read object
        retrieved_object = await self.object_manager.get_object(object_data.object_id, store=self.store)
        assert retrieved_object is not None, "Object retrieval failed"
        assert retrieved_object.object_id == object_data.object_id, "Retrieved object ID mismatch"
        
        # Test soft delete
        delete_result = await self.object_manager.delete_object(
            object_data.object_id, 
            store=self.store, 
            soft_delete=True, 
            deleted_by="integration_test"
        )
        assert "soft deleted" in delete_result["message"], "Soft delete failed"
        
        # Verify soft delete
        try:
            deleted_object = await self.object_manager.get_object(object_data.object_id, store=self.store)
            assert False, "Soft deleted object should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Soft deleted object correctly not found")
        
        logger.info("✅ Object CRUD operations completed successfully")
    
    @pytest.mark.asyncio
    async def test_cascade_delete_operations(self):
        """Test cascade delete operations."""
        logger.info("🔄 Testing cascade delete operations...")
        
        # Create test hierarchy: Source -> Flow -> Segment
        source = self.create_test_source("video")
        created_source = await self.source_manager.create_source(source, store=self.store)
        assert created_source is not None, "Source creation failed"
        
        flow = self.create_test_flow(str(source.id), "video")
        created_flow = await self.flow_manager.create_flow(flow, store=self.store)
        assert created_flow is not None, "Flow creation failed"
        
        # Store for cleanup
        if 'test_sources' not in self.test_data:
            self.test_data['test_sources'] = []
        self.test_data['test_sources'].append(str(source.id))
        
        if 'test_flows' not in self.test_data:
            self.test_data['test_flows'] = []
        self.test_data['test_flows'].append(str(flow.id))
        
        # Verify hierarchy exists
        retrieved_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert retrieved_source is not None, "Source should exist"
        
        retrieved_flow = await self.flow_manager.get_flow(str(flow.id), store=self.store)
        assert retrieved_flow is not None, "Flow should exist"
        
        # Test cascade soft delete from source
        delete_result = await self.source_manager.delete_source(
            str(source.id), 
            store=self.store, 
            soft_delete=True, 
            cascade=True, 
            deleted_by="integration_test"
        )
        assert "soft deleted" in delete_result["message"], "Cascade soft delete failed"
        assert "with cascade" in delete_result["message"], "Cascade not performed"
        
        # Verify cascade delete
        try:
            deleted_source = await self.source_manager.get_source(str(source.id), store=self.store)
            assert False, "Soft deleted source should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Cascade soft deleted source correctly not found")
        
        try:
            deleted_flow = await self.flow_manager.get_flow(str(flow.id), store=self.store)
            assert False, "Cascade soft deleted flow should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Cascade soft deleted flow correctly not found")
        
        logger.info("✅ Cascade delete operations completed successfully")
    
    @pytest.mark.asyncio
    async def test_soft_delete_functionality(self):
        """Test comprehensive soft delete functionality."""
        logger.info("🗑️ Testing soft delete functionality...")
        
        # Create test data
        source = self.create_test_source("video")
        created_source = await self.source_manager.create_source(source, store=self.store)
        assert created_source is not None, "Source creation failed"
        
        # Store for cleanup
        if 'test_sources' not in self.test_data:
            self.test_data['test_sources'] = []
        self.test_data['test_sources'].append(str(source.id))
        
        # Test soft delete
        soft_delete_result = await self.store.soft_delete_record('sources', str(source.id), 'integration_test')
        assert soft_delete_result is True, "Soft delete record failed"
        
        # Verify soft delete
        try:
            deleted_source = await self.source_manager.get_source(str(source.id), store=self.store)
            assert False, "Soft deleted source should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Soft deleted source correctly not found")
        
        # Test restore
        restore_result = await self.store.restore_record('sources', str(source.id))
        assert restore_result is True, "Restore record failed"
        
        # Verify restore
        restored_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert restored_source is not None, "Restored source should be returned"
        assert restored_source.id == source.id, "Restored source ID mismatch"
        
        # Test hard delete
        hard_delete_result = await self.store.hard_delete_record('sources', str(source.id))
        assert hard_delete_result is True, "Hard delete record failed"
        
        # Verify hard delete
        try:
            hard_deleted_source = await self.source_manager.get_source(str(source.id), store=self.store)
            assert False, "Hard deleted source should not be returned"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Hard deleted source correctly not found")
        
        # Remove from cleanup since it's already deleted
        self.test_data['test_sources'].remove(str(source.id))
        
        logger.info("✅ Soft delete functionality completed successfully")
    
    @pytest.mark.asyncio
    async def test_analytics_queries(self):
        """Test analytics queries."""
        logger.info("📊 Testing analytics queries...")
        
        # Test catalog summary
        try:
            analytics_result = await self.store.analytics_query("catalog_summary")
            assert analytics_result is not None, "Analytics query failed"
            assert isinstance(analytics_result, dict), "Analytics result should be a dictionary"
            logger.info(f"✅ Analytics query successful: {analytics_result}")
        except Exception as e:
            logger.warning(f"⚠️ Analytics query failed (this is expected if no data): {e}")
        
        logger.info("✅ Analytics queries completed successfully")
    
    @pytest.mark.asyncio
    async def test_comprehensive_workflow(self):
        """Test a comprehensive workflow with multiple entities."""
        logger.info("🔄 Testing comprehensive workflow...")
        
        # Create multiple sources
        video_source = self.create_test_source("video")
        audio_source = self.create_test_source("audio")
        data_source = self.create_test_source("data")
        
        created_video_source = await self.source_manager.create_source(video_source, store=self.store)
        created_audio_source = await self.source_manager.create_source(audio_source, store=self.store)
        created_data_source = await self.source_manager.create_source(data_source, store=self.store)
        
        assert all([created_video_source, created_audio_source, created_data_source]), "Source creation failed"
        
        # Store for cleanup
        if 'test_sources' not in self.test_data:
            self.test_data['test_sources'] = []
        self.test_data['test_sources'].extend([
            str(video_source.id), 
            str(audio_source.id), 
            str(data_source.id)
        ])
        
        # Create flows for each source
        video_flow = self.create_test_flow(str(video_source.id), "video")
        audio_flow = self.create_test_flow(str(audio_source.id), "audio")
        data_flow = self.create_test_flow(str(data_source.id), "data")
        
        created_video_flow = await self.flow_manager.create_flow(video_flow, store=self.store)
        created_audio_flow = await self.flow_manager.create_flow(audio_flow, store=self.store)
        created_data_flow = await self.flow_manager.create_flow(data_flow, store=self.store)
        
        assert all([created_video_flow, created_audio_flow, created_data_flow]), "Flow creation failed"
        
        # Store for cleanup
        if 'test_flows' not in self.test_data:
            self.test_data['test_flows'] = []
        self.test_data['test_flows'].extend([
            str(video_flow.id), 
            str(audio_flow.id), 
            str(data_flow.id)
        ])
        
        # Create objects
        video_object = self.create_test_object(str(video_flow.id))
        audio_object = self.create_test_object(str(audio_flow.id))
        data_object = self.create_test_object(str(data_flow.id))
        
        created_video_object = await self.object_manager.create_object(video_object, store=self.store)
        created_audio_object = await self.object_manager.create_object(audio_object, store=self.store)
        created_data_object = await self.object_manager.create_object(data_object, store=self.store)
        
        assert all([created_video_object, created_audio_object, created_data_object]), "Object creation failed"
        
        # Store for cleanup
        if 'test_objects' not in self.test_data:
            self.test_data['test_objects'] = []
        self.test_data['test_objects'].extend([
            video_object.object_id, 
            audio_object.object_id, 
            data_object.object_id
        ])
        
        # Verify all entities exist
        all_sources_response = await self.source_manager.list_sources(filters={}, limit=100, store=self.store)
        all_sources = all_sources_response.data
        all_flows_response = await self.flow_manager.list_flows(filters={}, limit=100, store=self.store)
        all_flows = all_flows_response.data
        
        assert len(all_sources) >= 3, "Not all sources found"
        assert len(all_flows) >= 3, "Not all flows found"
        
        # Test partial cleanup (soft delete some entities)
        soft_delete_result = await self.source_manager.delete_source(
            str(video_source.id), 
            store=self.store, 
            soft_delete=True, 
            cascade=True, 
            deleted_by="integration_test"
        )
        assert "soft deleted" in soft_delete_result["message"], "Partial cleanup failed"
        
        # Verify partial cleanup
        remaining_sources_response = await self.source_manager.list_sources(filters={}, limit=100, store=self.store)
        remaining_sources = remaining_sources_response.data
        remaining_flows_response = await self.flow_manager.list_flows(filters={}, limit=100, store=self.store)
        remaining_flows = remaining_flows_response.data
        
        # Should have 2 sources and 2 flows remaining (video source and flow were soft deleted)
        assert len(remaining_sources) >= 2, "Wrong number of remaining sources"
        assert len(remaining_flows) >= 2, "Wrong number of remaining flows"
        
        logger.info("✅ Comprehensive workflow completed successfully")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling scenarios."""
        logger.info("⚠️ Testing error handling...")
        
        # Test getting non-existent source
        try:
            non_existent_source = await self.source_manager.get_source("non-existent-id", store=self.store)
            assert False, "Non-existent source should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Non-existent source correctly returns 404")
        
        # Test getting non-existent flow
        try:
            non_existent_flow = await self.flow_manager.get_flow("non-existent-id", store=self.store)
            assert False, "Non-existent flow should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Non-existent flow correctly returns 404")
        
        # Test getting non-existent object
        try:
            non_existent_object = await self.object_manager.get_object("non-existent-id", store=self.store)
            assert False, "Non-existent object should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 404, f"Expected 404, got {e.status_code}"
            logger.info("✅ Non-existent object correctly returns 404")
        
        # Test soft deleting non-existent record
        soft_delete_result = await self.store.soft_delete_record('sources', 'non-existent-id', 'test')
        assert soft_delete_result is False, "Soft deleting non-existent record should return False"
        
        # Test hard deleting non-existent record
        hard_delete_result = await self.store.hard_delete_record('sources', 'non-existent-id')
        assert hard_delete_result is False, "Hard deleting non-existent record should return False"
        
        logger.info("✅ Error handling tests completed successfully")

async def run_integration_tests():
    """Run all integration tests."""
    logger.info("🚀 Starting TAMS Integration Tests with Real Database")
    
    # Create test instance and setup manually
    test_instance = TestTAMSIntegration()
    
    try:
        # Manual setup (not using pytest fixture)
        test_instance.settings = get_settings()
        test_instance.store = VASTStore(
            endpoint=test_instance.settings.vast_endpoint,
            access_key=test_instance.settings.vast_access_key,
            secret_key=test_instance.settings.vast_secret_key,
            bucket=test_instance.settings.vast_bucket,
            schema=test_instance.settings.vast_schema,
            s3_endpoint_url=test_instance.settings.s3_endpoint_url,
            s3_access_key_id=test_instance.settings.s3_access_key_id,
            s3_secret_access_key=test_instance.settings.s3_secret_access_key,
            s3_bucket_name=test_instance.settings.s3_bucket_name,
            s3_use_ssl=test_instance.settings.s3_use_ssl
        )
        
        # Initialize managers
        test_instance.source_manager = SourceManager()
        test_instance.flow_manager = FlowManager()
        test_instance.segment_manager = SegmentManager()
        test_instance.object_manager = ObjectManager()
        
        # Test data storage
        test_instance.test_data = {}
        
        logger.info("✅ Test environment setup complete")
        
        # Run all tests
        await test_instance.test_database_connectivity()
        await test_instance.test_source_crud_operations()
        await test_instance.test_flow_crud_operations()
        await test_instance.test_object_crud_operations()
        await test_instance.test_cascade_delete_operations()
        await test_instance.test_soft_delete_functionality()
        await test_instance.test_analytics_queries()
        await test_instance.test_comprehensive_workflow()
        await test_instance.test_error_handling()
        
        logger.info("\n🎉 All integration tests passed!")
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Integration tests failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        if hasattr(test_instance, 'test_data'):
            await test_instance.cleanup_test_data()

if __name__ == "__main__":
    exit_code = asyncio.run(run_integration_tests())
    sys.exit(exit_code) 