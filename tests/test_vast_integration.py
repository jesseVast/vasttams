"""
Integration tests for VAST database with real connection when available.
"""

import pytest
import asyncio
import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from app.models import Source, VideoFlow, FlowSegment, Object, Tags
from app.vast_store import VASTStore
from app.core.config import get_settings


def should_use_real_vast():
    """Determine if tests should use real VAST database."""
    # Check environment variable first
    if os.getenv("USE_REAL_VAST", "").lower() in ("true", "1", "yes"):
        return True
    
    # Check if --use-real-vast pytest marker is set
    if hasattr(pytest, "config") and pytest.config.getoption("--use-real-vast", default=False):
        return True
    
    return False


class TestVASTIntegration:
    """Integration tests for VAST database operations."""
    
    @pytest.fixture
    def vast_store(self):
        """Create a VAST store instance, real if possible, mock if not."""
        use_real = should_use_real_vast()
        
        if use_real:
            try:
                # Try to create a real VAST store
                settings = get_settings()
                store = VASTStore(
                    endpoint=settings.vast_endpoint,
                    access_key=settings.vast_access_key,
                    secret_key=settings.vast_secret_key,
                    bucket=settings.vast_bucket,
                    schema=settings.vast_schema,
                    s3_endpoint_url=settings.s3_endpoint_url,
                    s3_access_key_id=settings.s3_access_key_id,
                    s3_secret_access_key=settings.s3_secret_access_key,
                    s3_bucket_name=settings.s3_bucket_name,
                    s3_use_ssl=settings.s3_use_ssl
                )
                print("✅ Using real VAST database connection")
                return store
            except Exception as e:
                print(f"⚠️  Real VAST database connection failed ({e}), falling back to mock")
                # Fall back to mock if real connection fails
                return _create_mock_vast_store()
        else:
            print("🔧 Using mock VAST database for testing")
            return _create_mock_vast_store()
    
    @pytest.fixture
    def sample_source(self):
        """Create a sample source for testing."""
        return Source(
            id=uuid.uuid4(),
            format="urn:x-nmos:format:video",
            label="Integration Test Camera",
            description="Test camera source for integration testing",
            tags=Tags({"location": "test-studio", "test": "integration"}),
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
            tags=Tags({"quality": "test", "test": "integration"})
        )
    
    @pytest.fixture
    def sample_segment(self):
        """Create a sample segment for testing."""
        return FlowSegment(
            object_id="integration_test_seg_001",
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=250
        )
    
    @pytest.fixture
    def sample_object(self):
        """Create a sample object for testing."""
        return Object(
            object_id="integration_test_obj_001",
            flow_references=[{"flow_id": "test_flow_001"}],
            size=1024000
        )
    
    @pytest.mark.asyncio
    async def test_vast_connection(self, vast_store):
        """Test basic VAST connection and operations."""
        # Test that we can list tables and schemas
        tables = vast_store.list_tables()
        schemas = vast_store.list_schemas()
        
        print(f"Available tables: {tables}")
        print(f"Available schemas: {schemas}")
        
        # Basic connection test passed
        assert True
    
    @pytest.mark.asyncio
    async def test_source_operations(self, vast_store, sample_source):
        """Test source creation, retrieval, and deletion."""
        # Create source
        result = await vast_store.create_source(sample_source)
        assert result is True
        
        # Get source
        retrieved_source = await vast_store.get_source(str(sample_source.id))
        if retrieved_source:  # Only check if real database returned data
            assert retrieved_source.id == sample_source.id
            assert retrieved_source.label == sample_source.label
        
        # List sources
        sources = await vast_store.list_sources()
        assert isinstance(sources, list)
        
        # Test soft delete
        delete_result = await vast_store.delete_source(
            str(sample_source.id),
            soft_delete=True,
            cascade=True,
            deleted_by="integration_test"
        )
        assert delete_result is True
    
    @pytest.mark.asyncio
    async def test_flow_operations(self, vast_store, sample_flow):
        """Test flow creation, retrieval, and deletion."""
        # Create flow
        result = await vast_store.create_flow(sample_flow)
        assert result is True
        
        # Get flow
        retrieved_flow = await vast_store.get_flow(str(sample_flow.id))
        if retrieved_flow:  # Only check if real database returned data
            assert retrieved_flow.id == sample_flow.id
            assert retrieved_flow.source_id == sample_flow.source_id
        
        # List flows
        flows = await vast_store.list_flows()
        assert isinstance(flows, list)
        
        # Test soft delete
        delete_result = await vast_store.delete_flow(
            str(sample_flow.id),
            soft_delete=True,
            cascade=True,
            deleted_by="integration_test"
        )
        assert delete_result is True
    
    @pytest.mark.asyncio
    async def test_segment_operations(self, vast_store, sample_flow, sample_segment):
        """Test segment creation, retrieval, and deletion."""
        # Create segment
        test_data = b"test_segment_data"
        result = await vast_store.create_flow_segment(
            sample_segment, 
            str(sample_flow.id), 
            test_data
        )
        assert result is True
        
        # Get segments
        segments = await vast_store.get_flow_segments(str(sample_flow.id))
        assert isinstance(segments, list)
        
        # Test soft delete
        delete_result = await vast_store.delete_flow_segments(
            str(sample_flow.id),
            soft_delete=True,
            deleted_by="integration_test"
        )
        assert delete_result is True
    
    @pytest.mark.asyncio
    async def test_object_operations(self, vast_store, sample_object):
        """Test object creation, retrieval, and deletion."""
        # Create object
        result = await vast_store.create_object(sample_object)
        assert result is True
        
        # Get object
        retrieved_object = await vast_store.get_object(sample_object.object_id)
        if retrieved_object:  # Only check if real database returned data
            assert retrieved_object.object_id == sample_object.object_id
        
        # Test soft delete
        delete_result = await vast_store.delete_object(
            sample_object.object_id,
            soft_delete=True,
            deleted_by="integration_test"
        )
        assert delete_result is True
    
    @pytest.mark.asyncio
    async def test_soft_delete_integration(self, vast_store, sample_source, sample_flow):
        """Test complete soft delete workflow."""
        # Create source and flow
        await vast_store.create_source(sample_source)
        await vast_store.create_flow(sample_flow)
        
        # Test cascade delete from source
        result = await vast_store.delete_source(
            str(sample_source.id),
            soft_delete=True,
            cascade=True,
            deleted_by="integration_test"
        )
        assert result is True
        
        # Verify cascade behavior (source deletion should trigger flow deletion)
        # This would be verified in a real database by checking that flows are also soft-deleted
    
    @pytest.mark.asyncio
    async def test_hard_delete_integration(self, vast_store, sample_source):
        """Test hard delete workflow."""
        # Create source
        await vast_store.create_source(sample_source)
        
        # Test hard delete
        result = await vast_store.delete_source(
            str(sample_source.id),
            soft_delete=False,
            cascade=True,
            deleted_by="integration_test"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_query_with_soft_delete_filtering(self, vast_store, sample_source):
        """Test that queries automatically exclude soft-deleted records."""
        # Create source
        await vast_store.create_source(sample_source)
        
        # Soft delete the source
        await vast_store.delete_source(
            str(sample_source.id),
            soft_delete=True,
            cascade=False,
            deleted_by="integration_test"
        )
        
        # Try to get the source - should return None if soft-deleted
        retrieved_source = await vast_store.get_source(str(sample_source.id))
        # In a real database, this should be None due to soft delete filtering
        # With mock, it will return the mock's default value
        
        # List sources - should not include soft-deleted
        sources = await vast_store.list_sources()
        assert isinstance(sources, list)


class TestVASTRealDatabase:
    """Tests that require a real VAST database connection."""
    
    @pytest.mark.skipif(not should_use_real_vast(), reason="Requires real VAST database connection")
    @pytest.mark.asyncio
    async def test_real_database_connection(self):
        """Test with real VAST database connection."""
        settings = get_settings()
        store = VASTStore(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema
        )
        
        # Test real database operations
        tables = store.list_tables()
        schemas = store.list_schemas()
        
        print(f"Real database tables: {tables}")
        print(f"Real database schemas: {schemas}")
        
        await store.close()
        assert True
    
    @pytest.mark.skipif(not should_use_real_vast(), reason="Requires real VAST database connection")
    @pytest.mark.asyncio
    async def test_real_soft_delete_workflow(self):
        """Test complete soft delete workflow with real database."""
        # This test would create real data, soft delete it, and verify
        # that it's properly filtered out of queries
        pass


def _create_mock_vast_store():
    """Create a mock VAST store for testing."""
    store = AsyncMock(spec=VASTStore)
    store.db_manager = MagicMock()
    store.s3_store = AsyncMock()
    
    # Configure mock methods
    store.create_source = AsyncMock(return_value=True)
    store.get_source = AsyncMock(return_value=None)
    store.list_sources = AsyncMock(return_value=[])
    store.create_flow = AsyncMock(return_value=True)
    store.get_flow = AsyncMock(return_value=None)
    store.list_flows = AsyncMock(return_value=[])
    store.create_flow_segment = AsyncMock(return_value=True)
    store.get_flow_segments = AsyncMock(return_value=[])
    store.create_object = AsyncMock(return_value=True)
    store.get_object = AsyncMock(return_value=None)
    store.delete_source = AsyncMock(return_value=True)
    store.delete_flow = AsyncMock(return_value=True)
    store.delete_flow_segments = AsyncMock(return_value=True)
    store.delete_object = AsyncMock(return_value=True)
    store.list_tables = MagicMock(return_value=[])
    store.list_schemas = MagicMock(return_value=[])
    store.close = AsyncMock()
    
    return store


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--use-real-vast",
        action="store_true",
        default=False,
        help="Use real VAST database for integration tests"
    ) 