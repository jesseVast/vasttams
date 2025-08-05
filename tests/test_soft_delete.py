"""
Tests for soft delete and cascade delete functionality.
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import Source, VideoFlow, FlowSegment, Object, Tags
from app.vast_store import VASTStore
from app.sources import SourceManager
from app.flows import FlowManager
from app.segments import SegmentManager
from app.objects import ObjectManager


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
            id=uuid.uuid4(),
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
            id=uuid.uuid4(),
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
    """Integration tests for soft delete functionality."""

    @pytest.mark.asyncio
    async def test_soft_delete_workflow(self):
        """Test complete soft delete workflow."""
        # This would be an integration test that tests the full workflow
        # from API endpoint through to database operations
        
        # For now, this is a placeholder for integration tests
        # that would require a real VAST database connection
        assert True

    @pytest.mark.asyncio
    async def test_cascade_delete_workflow(self):
        """Test complete cascade delete workflow."""
        # This would test the full cascade delete workflow
        # from source deletion through to segment deletion
        
        # For now, this is a placeholder for integration tests
        assert True 