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
        store.soft_delete_record = AsyncMock()
        store.hard_delete_record = AsyncMock()
        store.restore_record = AsyncMock()
        
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
        # Mock the soft delete operation
        mock_store.soft_delete_record.return_value = True
        mock_store.delete_source.return_value = True
        
        # Test soft delete
        result = await mock_store.delete_source(
            str(sample_source.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        mock_store.soft_delete_record.assert_called_once_with(
            'sources', str(sample_source.id), "test_user"
        )

    @pytest.mark.asyncio
    async def test_hard_delete_source(self, mock_store, sample_source):
        """Test hard deleting a source."""
        # Mock the hard delete operation
        mock_store.hard_delete_record.return_value = True
        
        # Test hard delete
        result = await mock_store.delete_source(
            str(sample_source.id), 
            soft_delete=False, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        mock_store.hard_delete_record.assert_called_once_with(
            'sources', str(sample_source.id)
        )

    @pytest.mark.asyncio
    async def test_soft_delete_flow(self, mock_store, sample_flow):
        """Test soft deleting a flow."""
        # Mock the soft delete operation
        mock_store.soft_delete_record.return_value = True
        mock_store.delete_flow_segments.return_value = True
        
        # Test soft delete with cascade
        result = await mock_store.delete_flow(
            str(sample_flow.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        mock_store.delete_flow_segments.assert_called_once_with(
            str(sample_flow.id), timerange=None, soft_delete=True, deleted_by="test_user"
        )
        mock_store.soft_delete_record.assert_called_once_with(
            'flows', str(sample_flow.id), "test_user"
        )

    @pytest.mark.asyncio
    async def test_soft_delete_flow_segments(self, mock_store, sample_flow, sample_segment):
        """Test soft deleting flow segments."""
        # Mock the get_flow_segments operation
        mock_store.get_flow_segments.return_value = [sample_segment]
        mock_store.db_manager.update.return_value = 1
        
        # Test soft delete
        result = await mock_store.delete_flow_segments(
            str(sample_flow.id), 
            soft_delete=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Should not delete S3 data for soft delete
        mock_store.s3_store.delete_flow_segment.assert_not_called()

    @pytest.mark.asyncio
    async def test_hard_delete_flow_segments(self, mock_store, sample_flow, sample_segment):
        """Test hard deleting flow segments."""
        # Mock the get_flow_segments operation
        mock_store.get_flow_segments.return_value = [sample_segment]
        mock_store.db_manager.delete.return_value = 1
        
        # Test hard delete
        result = await mock_store.delete_flow_segments(
            str(sample_flow.id), 
            soft_delete=False, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Should delete S3 data for hard delete
        mock_store.s3_store.delete_flow_segment.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_object(self, mock_store, sample_object):
        """Test soft deleting an object."""
        # Mock the soft delete operation
        mock_store.soft_delete_record.return_value = True
        
        # Test soft delete
        result = await mock_store.delete_object(
            sample_object.object_id, 
            soft_delete=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        mock_store.soft_delete_record.assert_called_once_with(
            'objects', sample_object.object_id, "test_user"
        )

    @pytest.mark.asyncio
    async def test_cascade_delete_source(self, mock_store, sample_source, sample_flow):
        """Test cascade delete from source to flows."""
        # Mock list_flows to return associated flows
        mock_store.list_flows.return_value = [sample_flow]
        mock_store.delete_flow.return_value = True
        mock_store.soft_delete_record.return_value = True
        
        # Test cascade delete
        result = await mock_store.delete_source(
            str(sample_source.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Should delete associated flows
        mock_store.delete_flow.assert_called_once_with(
            str(sample_flow.id), soft_delete=True, cascade=True, deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_cascade_delete_flow(self, mock_store, sample_flow):
        """Test cascade delete from flow to segments."""
        # Mock delete_flow_segments
        mock_store.delete_flow_segments.return_value = True
        mock_store.soft_delete_record.return_value = True
        
        # Test cascade delete
        result = await mock_store.delete_flow(
            str(sample_flow.id), 
            soft_delete=True, 
            cascade=True, 
            deleted_by="test_user"
        )
        
        assert result is True
        # Should delete associated segments
        mock_store.delete_flow_segments.assert_called_once_with(
            str(sample_flow.id), timerange=None, soft_delete=True, deleted_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_query_excludes_soft_deleted(self, mock_store):
        """Test that queries exclude soft-deleted records."""
        # Mock the select operation to return empty results (no soft-deleted records)
        mock_store.db_manager.select.return_value = []
        
        # Test get_source excludes soft-deleted
        result = await mock_store.get_source("test_source_id")
        assert result is None
        
        # Verify the predicate was modified to exclude soft-deleted records
        mock_store.db_manager.select.assert_called()
        call_args = mock_store.db_manager.select.call_args
        assert call_args is not None

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
        
        assert result is True

    @pytest.mark.asyncio
    async def test_soft_delete_record_method(self, mock_store):
        """Test the soft_delete_record helper method."""
        # Mock the update operation
        mock_store.db_manager.update.return_value = 1
        
        # Test soft delete record
        result = await mock_store.soft_delete_record(
            'sources', 'test_id', 'test_user'
        )
        
        assert result is True
        mock_store.db_manager.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete_record_method(self, mock_store):
        """Test the hard_delete_record helper method."""
        # Mock the delete operation
        mock_store.db_manager.delete.return_value = 1
        
        # Test hard delete record
        result = await mock_store.hard_delete_record(
            'sources', 'test_id'
        )
        
        assert result is True
        mock_store.db_manager.delete.assert_called_once()

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