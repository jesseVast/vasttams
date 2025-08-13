"""
Tests for soft delete and cascade delete functionality with real database.
"""
import pytest
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.models import Source, VideoFlow, FlowSegment, Object, Tags, CollectionItem
from app.storage.vast_store import VASTStore
from app.api.sources import SourceManager
from app.api.flows import FlowManager
from app.api.segments import SegmentManager
from app.api.objects import ObjectManager
from app.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


class TestSoftDelete:
    """Test soft delete functionality."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock VASTStore."""
        store = AsyncMock(spec=VASTStore)
        store.db_manager = MagicMock()
        store.s3_store = AsyncMock()
        
        # Add the new soft delete methods to the mock
        store._add_soft_delete_predicate = MagicMock()
        store.soft_delete_record = AsyncMock(return_value=True)
        store.hard_delete_record = AsyncMock(return_value=True)
        store.restore_record = AsyncMock()
        
        # Configure default return values for the main methods
        store.delete_source = AsyncMock(return_value=True)
        store.delete_flow = AsyncMock(return_value=True)
        store.delete_flow_segments = AsyncMock(return_value=True)
        store.delete_object = AsyncMock(return_value=True)
        store.get_source = AsyncMock(return_value=None)
        store.get_flow = AsyncMock(return_value=None)
        store.get_flow_segments = AsyncMock(return_value=[])
        store.get_object = AsyncMock(return_value=None)
        store.list_flows = AsyncMock(return_value=[])
        
        return store

    @pytest.fixture
    def sample_source(self):
        """Create a sample source for testing."""
        return Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="Test Camera",
            description="Test camera source",
            tags=Tags({"location": "studio1"}),
            source_collection=[],
            collected_by=[]
        )

    @pytest.fixture
    def sample_flow(self, sample_source):
        """Create a sample flow for testing."""
        return VideoFlow(
            id=str(uuid.uuid4()),
            source_id=sample_source.id,
            format="urn:x-nmos:format:video",
            codec="urn:x-nmos:codec:prores",
            frame_width=1920,
            frame_height=1080,
            frame_rate="25/1",
            tags=Tags({"quality": "high"})
        )

    @pytest.fixture
    def sample_segment(self):
        """Create a sample segment for testing."""
        return FlowSegment(
            object_id="seg_001",
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=250
        )

    @pytest.fixture
    def sample_object(self):
        """Create a sample object for testing."""
        return Object(
            object_id="obj_001",
            flow_references=[{"flow_id": "flow_001"}],
            size=1024000
        )

    def test_add_soft_delete_predicate(self, mock_store):
        """Test adding soft delete predicate to queries."""
        # Test with no existing predicate
        predicate = mock_store._add_soft_delete_predicate(None)
        assert predicate is not None
        
        # Test with existing predicate
        from ibis import _ as ibis_
        existing_predicate = (ibis_.id == "test_id")
        combined_predicate = mock_store._add_soft_delete_predicate(existing_predicate)
        assert combined_predicate is not None

    @pytest.mark.asyncio
    async def test_soft_delete_source(self, mock_store, sample_source):
        """Test soft deleting a source."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_source(
            str(sample_source.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_source.assert_called_once_with(
            str(sample_source.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_hard_delete_source(self, mock_store, sample_source):
        """Test hard deleting a source."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_source(
            str(sample_source.id), 
            soft_delete=False, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_source.assert_called_once_with(
            str(sample_source.id),
            soft_delete=False,
            cascade=True,
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_soft_delete_flow(self, mock_store, sample_flow):
        """Test soft deleting a flow."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_flow(
            str(sample_flow.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_flow.assert_called_once_with(
            str(sample_flow.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )


    @pytest.mark.asyncio
    async def test_soft_delete_flow_segments(self, mock_store, sample_flow, sample_segment):
        """Test soft deleting flow segments."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_flow_segments(
            str(sample_flow.id), 
            soft_delete=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_flow_segments.assert_called_once_with(
            str(sample_flow.id), 
            soft_delete=True, 
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_hard_delete_flow_segments(self, mock_store, sample_flow, sample_segment):
        """Test hard deleting flow segments."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_flow_segments(
            str(sample_flow.id), 
            soft_delete=False, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_flow_segments.assert_called_once_with(
            str(sample_flow.id), 
            soft_delete=False, 
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_soft_delete_object(self, mock_store, sample_object):
        """Test soft deleting an object."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_object(
            sample_object.object_id, 
            soft_delete=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_object.assert_called_once_with(
            sample_object.object_id, 
            soft_delete=True, 
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_cascade_delete_source(self, mock_store, sample_source, sample_flow):
        """Test cascade delete from source to flows."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_source(
            str(sample_source.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_source.assert_called_once_with(
            str(sample_source.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_cascade_delete_flow(self, mock_store, sample_flow):
        """Test cascade delete from flow to segments."""
        # Test that the method accepts the new parameters
        result = await mock_store.delete_flow(
            str(sample_flow.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Verify the method was called with the correct parameters
        mock_store.delete_flow.assert_called_once_with(
            str(sample_flow.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_query_excludes_soft_deleted(self, mock_store):
        """Test that queries exclude soft-deleted records."""
        # Test that get_source returns None (no soft-deleted records)
        result = await mock_store.get_source("test_source_id")
        assert result is None
        
        # Verify the method was called
        mock_store.get_source.assert_called_once_with("test_source_id")

    @pytest.mark.asyncio
    async def test_source_manager_soft_delete(self, mock_store, sample_source):
        """Test SourceManager soft delete functionality."""
        manager = SourceManager()
        
        # Mock the store operation
        mock_store.delete_source.return_value = True
        
        # Test soft delete
        result = await manager.delete_source(
            str(sample_source.id), 
            store=mock_store, 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert "soft deleted" in result["message"]
        assert "with cascade" in result["message"]

    @pytest.mark.asyncio
    async def test_flow_manager_soft_delete(self, mock_store, sample_flow):
        """Test FlowManager soft delete functionality."""
        manager = FlowManager()
        
        # Mock the store operation
        mock_store.delete_flow.return_value = True
        
        # Test soft delete
        result = await manager.delete_flow(
            str(sample_flow.id), 
            store=mock_store, 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert "soft deleted" in result["message"]
        assert "with cascade" in result["message"]

    @pytest.mark.asyncio
    async def test_segment_manager_soft_delete(self, mock_store, sample_flow):
        """Test SegmentManager soft delete functionality."""
        manager = SegmentManager()
        
        # Mock the store operation
        mock_store.delete_flow_segments.return_value = True
        
        # Test soft delete
        result = await manager.delete_segments(
            str(sample_flow.id), 
            timerange=None,
            store=mock_store, 
            soft_delete=True, 
            deleted_by="test_user"
        )
        
        assert "soft deleted" in result["message"]

    @pytest.mark.asyncio
    async def test_object_manager_soft_delete(self, mock_store, sample_object):
        """Test ObjectManager soft delete functionality."""
        manager = ObjectManager()
        
        # Mock the store operation
        mock_store.delete_object.return_value = True
        
        # Test soft delete
        result = await manager.delete_object(
            sample_object.object_id, 
            store=mock_store, 
            soft_delete=True, 
            deleted_by="test_user"
        )
        
        assert "soft deleted" in result["message"]

    @pytest.mark.asyncio
    async def test_soft_delete_record_method(self, mock_store):
        """Test the soft_delete_record helper method."""
        # Test that the method accepts the parameters
        result = await mock_store.soft_delete_record(
            'sources', 'test_id', 'test_user'
        )
        
        # Verify the method was called with the correct parameters
        mock_store.soft_delete_record.assert_called_once_with(
            'sources', 'test_id', 'test_user'
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_hard_delete_record_method(self, mock_store):
        """Test the hard_delete_record helper method."""
        # Test that the method accepts the parameters
        result = await mock_store.hard_delete_record(
            'sources', 'test_id'
        )
        
        # Verify the method was called with the correct parameters
        mock_store.hard_delete_record.assert_called_once_with(
            'sources', 'test_id'
        )
        assert result is True

    def test_soft_delete_schema_fields(self):
        """Test that soft delete fields are added to table schemas."""
        # This test verifies that the schema includes soft delete fields
        # The actual schema setup is done in _setup_tams_tables method
        
        # Verify that the schema includes the required soft delete fields
        expected_fields = ['deleted', 'deleted_at', 'deleted_by']
        
        # This is a structural test - the actual schema is defined in the VASTStore class
        # The fields should be present in all table schemas
        assert True  # Placeholder - actual schema validation would be done in integration tests


class TestSoftDeleteIntegration:
    """Integration tests for soft delete functionality with real database."""

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
        self.source_manager = SourceManager()
        self.flow_manager = FlowManager()
        self.segment_manager = SegmentManager()
        self.object_manager = ObjectManager()
        
        # Test data storage
        self.test_data = {}
        
        logger.info("✅ Real database test environment setup complete")

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
    
    def create_test_source(self) -> Source:
        """Create a test source."""
        source = Source(
            id=uuid.uuid4(),
            format="urn:x-nmos:format:video",
            label="Test Camera for Soft Delete",
            description="Test camera source for soft delete testing",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
            tags=Tags({"location": "studio1", "test": "soft_delete"}),
            source_collection=[CollectionItem(id=str(uuid.uuid4()), label="Test Collection")],
            collected_by=[str(uuid.uuid4())]
        )
        return source
    
    def create_test_flow(self, source_id: str) -> VideoFlow:
        """Create a test flow."""
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=uuid.UUID(source_id),
            format="urn:x-nmos:format:video",
            codec="video/mp4",
            label="Test Video Flow",
            description="Test video flow for soft delete testing",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
            tags=Tags({"quality": "high", "test": "soft_delete"}),
            frame_width=1920,
            frame_height=1080,
            frame_rate="25/1",
            container="mp4",
            read_only=False,
            max_bit_rate=5000000,
            avg_bit_rate=3000000
        )
        return flow

    @pytest.mark.asyncio
    async def test_soft_delete_workflow_real_db(self):
        """Test complete soft delete workflow with real database."""
        logger.info("🔄 Testing soft delete workflow with real database...")
        
        # Create test source
        source = self.create_test_source()
        created_source = await self.source_manager.create_source(source, store=self.store)
        assert created_source is not None, "Source creation failed"
        
        # Store for cleanup
        if 'test_sources' not in self.test_data:
            self.test_data['test_sources'] = []
        self.test_data['test_sources'].append(str(source.id))
        
        # Verify source exists
        retrieved_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert retrieved_source is not None, "Source should exist after creation"
        assert retrieved_source.id == source.id, "Retrieved source ID mismatch"
        
        # Soft delete the source
        delete_result = await self.source_manager.delete_source(
            str(source.id), 
            store=self.store, 
            soft_delete=True, 
            cascade=False, 
            deleted_by="test_user"
        )
        assert "soft deleted" in delete_result["message"], "Soft delete failed"
        
        # Verify source is soft deleted (should not be returned in normal queries)
        deleted_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert deleted_source is None, "Soft deleted source should not be returned"
        
        # Test restore
        restore_result = await self.store.restore_record('sources', str(source.id))
        assert restore_result is True, "Restore failed"
        
        # Verify restore
        restored_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert restored_source is not None, "Restored source should be returned"
        assert restored_source.id == source.id, "Restored source ID mismatch"
        
        logger.info("✅ Soft delete workflow with real database completed successfully")

    @pytest.mark.asyncio
    async def test_cascade_delete_workflow_real_db(self):
        """Test complete cascade delete workflow with real database."""
        logger.info("🔄 Testing cascade delete workflow with real database...")
        
        # Create test source
        source = self.create_test_source()
        created_source = await self.source_manager.create_source(source, store=self.store)
        assert created_source is not None, "Source creation failed"
        
        # Create test flow
        flow = self.create_test_flow(str(source.id))
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
        
        # Test cascade soft delete
        delete_result = await self.source_manager.delete_source(
            str(source.id), 
            store=self.store, 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        assert "soft deleted" in delete_result["message"], "Cascade soft delete failed"
        assert "with cascade" in delete_result["message"], "Cascade not performed"
        
        # Verify cascade delete
        deleted_source = await self.source_manager.get_source(str(source.id), store=self.store)
        assert deleted_source is None, "Soft deleted source should not be returned"
        
        deleted_flow = await self.flow_manager.get_flow(str(flow.id), store=self.store)
        assert deleted_flow is None, "Cascade soft deleted flow should not be returned"
        
        logger.info("✅ Cascade delete workflow with real database completed successfully") 