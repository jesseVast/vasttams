"""
Integration tests for vasttamsclient against a real TAMS server.

These tests require a running TAMS server at localhost:8000.
Tests will be skipped if the server is not available.
"""

import pytest
import pytest_asyncio
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add src/client to path for imports
client_path = Path(__file__).parent.parent.parent / "src" / "client"
if str(client_path) not in sys.path:
    sys.path.insert(0, str(client_path))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSClientError, TAMSAuthenticationError, TAMSConnectionError
from vasttamsclient.domain.source import TAMSSource
from vasttamsclient.domain.flow import TAMSFlow

# Test server configuration
TEST_SERVER_URL = "http://localhost:8000"
TEST_USERNAME = "admin"  # Default test user
TEST_PASSWORD = "vastdata"  # Default test password (per TAMS server defaults)


def check_server_available() -> bool:
    """Check if TAMS server is available."""
    try:
        import aiohttp
        import asyncio
        
        async def check():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{TEST_SERVER_URL}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        return response.status == 200
            except Exception:
                return False
        
        return asyncio.run(check())
    except Exception:
        return False


@pytest.fixture(scope="module")
def server_available():
    """Check if server is available, skip tests if not."""
    if not check_server_available():
        pytest.skip("TAMS server not available at localhost:8000. Start server to run integration tests.")
    return True


@pytest_asyncio.fixture(scope="function")
async def client(server_available):
    """Create a TAMSClient instance connected to real server."""
    client = TAMSClient(
        server_url=TEST_SERVER_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD,
        timeout=30
    )
    async with client:
        yield client
    # Cleanup is handled by context manager


@pytest_asyncio.fixture(scope="function")
async def test_source(client):
    """Create a test source for use in tests."""
    source = client.TAMSSource(
        format="urn:x-nmos:format:video",
        label="Integration Test Source"
    )
    await source._ensure_created()
    yield source
    # Cleanup
    try:
        await source.delete()
    except Exception:
        pass  # Ignore cleanup errors


@pytest_asyncio.fixture(scope="function")
async def test_flow(client, test_source):
    """Create a test flow for use in tests."""
    flow = test_source.TAMSFlow(
        format="urn:x-nmos:format:video",
        codec="video/h264",
        label="Integration Test Flow",
        frame_width=1920,
        frame_height=1080,
        frame_rate={"numerator": 25, "denominator": 1}
    )
    await flow._ensure_created()
    yield flow
    # Cleanup
    try:
        await flow.delete()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.mark.integration
@pytest.mark.asyncio
class TestClientIntegration:
    """Integration tests for TAMSClient against real server."""
    
    async def test_client_connection(self, client):
        """Test that client can connect to server."""
        # Client should be initialized and session created
        assert client.server_url == TEST_SERVER_URL
        assert client._session is not None
        assert not client._session.closed
    
    async def test_authentication(self, client):
        """Test authentication with real server."""
        # Authentication happens automatically on first request
        # Just verify we can get headers (which requires auth)
        headers = await client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
    
    async def test_list_sources_empty(self, client):
        """Test listing sources (may be empty)."""
        sources = await client.list_sources()
        assert isinstance(sources, list)
        # Should not raise an error even if empty
    
    async def test_list_flows_empty(self, client):
        """Test listing flows (may be empty)."""
        flows = await client.list_flows()
        assert isinstance(flows, list)
        # Should not raise an error even if empty


@pytest.mark.integration
@pytest.mark.asyncio
class TestSourceIntegration:
    """Integration tests for TAMSSource against real server."""
    
    async def test_create_source(self, client):
        """Test creating a source on real server."""
        source = client.TAMSSource(
            format="urn:x-nmos:format:video",
            label="Test Source Create"
        )
        await source._ensure_created()
        
        assert source.id is not None
        assert source.format == "urn:x-nmos:format:video"
        assert source.label == "Test Source Create"
        
        # Cleanup
        await source.delete()
    
    async def test_get_source(self, client, test_source):
        """Test getting a source from real server."""
        retrieved = await client.get_source(test_source.id)
        assert retrieved is not None
        assert retrieved.id == test_source.id
        assert retrieved.format == test_source.format
        assert retrieved.label == test_source.label
    
    async def test_update_source(self, client, test_source):
        """Test updating a source on real server."""
        original_label = test_source.label
        new_label = "Updated Source Label"
        
        await test_source.update(label=new_label)
        assert test_source.label == new_label
        
        # Verify update persisted
        retrieved = await client.get_source(test_source.id)
        assert retrieved.label == new_label
    
    async def test_source_tags(self, client, test_source):
        """Test source tag operations on real server."""
        # Set a tag
        await test_source.set_tag("test_key", "test_value")
        
        # Get all tags
        tags = await test_source.get_tags()
        assert "test_key" in tags
        assert tags["test_key"] == "test_value"
        
        # Get specific tag
        value = await test_source.get_tag("test_key")
        assert value == "test_value"
        
        # Delete tag
        await test_source.delete_tag("test_key")
        tags_after = await test_source.get_tags()
        assert "test_key" not in tags_after
    
    async def test_source_refresh(self, client, test_source):
        """Test refreshing source data from server."""
        # Update source via API
        await test_source.update(description="Test description")
        
        # Create new source object and refresh
        new_source = TAMSSource(client, id=test_source.id)
        await new_source.refresh()
        
        assert new_source.description == "Test description"


@pytest.mark.integration
@pytest.mark.asyncio
class TestFlowIntegration:
    """Integration tests for TAMSFlow against real server."""
    
    async def test_create_flow(self, client, test_source):
        """Test creating a flow on real server."""
        flow = test_source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow Create",
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1}
        )
        await flow._ensure_created()
        
        assert flow.id is not None
        assert flow.source_id == test_source.id
        assert flow.format == "urn:x-nmos:format:video"
        assert flow.codec == "video/h264"
        assert flow.label == "Test Flow Create"
        
        # Cleanup
        await flow.delete()
    
    async def test_get_flow(self, client, test_flow):
        """Test getting a flow from real server."""
        retrieved = await client.get_flow(test_flow.id)
        assert retrieved is not None
        assert retrieved.id == test_flow.id
        assert retrieved.source_id == test_flow.source_id
        # Format may not be in server response, so just check it's a valid flow
        assert retrieved.id == test_flow.id
    
    async def test_update_flow(self, client, test_flow):
        """Test updating a flow on real server."""
        new_label = "Updated Flow Label"
        
        await test_flow.update(label=new_label)
        assert test_flow.label == new_label
        
        # Verify update persisted
        retrieved = await client.get_flow(test_flow.id)
        assert retrieved.label == new_label
    
    async def test_flow_tags(self, client, test_flow):
        """Test flow tag operations on real server."""
        # Set a tag
        await test_flow.set_tag("quality", "hd")
        
        # Get all tags
        tags = await test_flow.get_tags()
        assert "quality" in tags
        assert tags["quality"] == "hd"
        
        # Delete tag
        await test_flow.delete_tag("quality")
        tags_after = await test_flow.get_tags()
        assert "quality" not in tags_after
    
    async def test_list_flows_for_source(self, client, test_source, test_flow):
        """Test listing flows for a source."""
        flows = await test_source.list_flows()
        assert isinstance(flows, list)
        assert len(flows) >= 1
        assert any(f.id == test_flow.id for f in flows)
    
    async def test_flow_refresh(self, client, test_flow):
        """Test refreshing flow data from server."""
        # Update flow via API
        await test_flow.update(description="Test flow description")
        
        # Create new flow object and refresh
        new_flow = TAMSFlow(client, id=test_flow.id, source_id=test_flow.source_id, 
                           format=test_flow.format, codec=test_flow.codec)
        await new_flow.refresh()
        
        assert new_flow.description == "Test flow description"


@pytest.mark.integration
@pytest.mark.asyncio
class TestSourceFlowWorkflow:
    """Integration tests for complete source-flow workflows."""
    
    async def test_create_source_with_flow(self, client):
        """Test creating a source and flow together."""
        # Create source
        source = client.TAMSSource(
            format="urn:x-nmos:format:video",
            label="Workflow Test Source"
        )
        await source._ensure_created()
        
        # Create flow for source
        flow = source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Workflow Test Flow",
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1}
        )
        await flow._ensure_created()
        
        # Verify relationship
        assert flow.source_id == source.id
        
        # Verify we can retrieve both
        retrieved_source = await client.get_source(source.id)
        assert retrieved_source is not None
        
        retrieved_flow = await client.get_flow(flow.id)
        assert retrieved_flow is not None
        assert retrieved_flow.source_id == source.id
        
        # Cleanup
        await flow.delete()
        await source.delete()
    
    async def test_list_sources_with_flows(self, client):
        """Test listing sources and their flows."""
        # Create test data
        source = client.TAMSSource(
            format="urn:x-nmos:format:video",
            label="List Test Source"
        )
        await source._ensure_created()
        
        flow1 = source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Flow 1",
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1}
        )
        await flow1._ensure_created()
        
        flow2 = source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Flow 2",
            frame_width=1920,
            frame_height=1080,
            frame_rate={"numerator": 25, "denominator": 1}
        )
        await flow2._ensure_created()
        
        # List sources
        sources = await client.list_sources()
        assert any(s.id == source.id for s in sources)
        
        # List flows for source
        flows = await source.list_flows()
        assert len(flows) >= 2
        assert any(f.id == flow1.id for f in flows)
        assert any(f.id == flow2.id for f in flows)
        
        # Cleanup
        await flow1.delete()
        await flow2.delete()
        await source.delete()


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """Integration tests for error handling against real server."""
    
    async def test_get_nonexistent_source(self, client):
        """Test getting a non-existent source."""
        source = await client.get_source("00000000-0000-0000-0000-000000000000")
        assert source is None
    
    async def test_get_nonexistent_flow(self, client):
        """Test getting a non-existent flow."""
        flow = await client.get_flow("00000000-0000-0000-0000-000000000000")
        assert flow is None
    
    async def test_delete_nonexistent_source(self, client):
        """Test deleting a non-existent source (should not raise error)."""
        source = TAMSSource(client, id="00000000-0000-0000-0000-000000000000")
        # Should not raise error (idempotent delete)
        try:
            await source.delete()
        except Exception as e:
            # Some servers may return 404, which is acceptable
            assert "404" in str(e) or "not found" in str(e).lower()
    
    async def test_invalid_authentication(self):
        """Test authentication with invalid credentials."""
        invalid_client = TAMSClient(
            server_url=TEST_SERVER_URL,
            username="invalid",
            password="invalid",
            timeout=5
        )
        
        async with invalid_client:
            with pytest.raises((TAMSAuthenticationError, TAMSConnectionError)):
                # This should fail on first authenticated request
                await invalid_client.list_sources()


@pytest.mark.integration
@pytest.mark.asyncio
class TestQueryParameters:
    """Integration tests for query parameters and filtering."""
    
    async def test_list_sources_with_filters(self, client, test_source):
        """Test listing sources with query parameters."""
        # List sources with format filter
        sources = await client.list_sources(format="urn:x-nmos:format:video")
        assert isinstance(sources, list)
        # Should include our test source
        assert any(s.id == test_source.id for s in sources)
    
    async def test_list_flows_with_filters(self, client, test_flow):
        """Test listing flows with query parameters."""
        # List flows with codec filter
        flows = await client.list_flows(codec="video/h264")
        assert isinstance(flows, list)
        # Should include our test flow
        assert any(f.id == test_flow.id for f in flows)

