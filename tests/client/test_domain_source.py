"""
Tests for TAMSSource domain object.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from vasttamsclient.domain.source import TAMSSource
from vasttamsclient.domain.flow import TAMSFlow
from vasttamsclient.exceptions import TAMSClientError


class TestTAMSSourceInit:
    """Tests for TAMSSource initialization."""
    
    def test_init_new_source(self, client):
        """Test creating a new source."""
        source = TAMSSource(
            client,
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        assert source.id is not None
        assert source._data["format"] == "urn:x-nmos:format:video"
        assert source._data["label"] == "Test Source"
        assert source._created is True
    
    def test_init_new_source_with_id(self, client):
        """Test creating a source with explicit ID (treated as existing source)."""
        source_id = str(uuid.uuid4())
        source = TAMSSource(
            client,
            format="urn:x-nmos:format:video",
            id=source_id
        )
        assert source.id == source_id
        assert source._created is False  # When id is provided, it's treated as existing
    
    def test_init_existing_source(self, client):
        """Test representing an existing source."""
        source_id = "existing-source-123"
        source = TAMSSource(
            client,
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Existing Source"
        )
        assert source.id == source_id
        assert source._created is False
    
    def test_init_missing_format(self, client):
        """Test that format is required for new source."""
        with pytest.raises(ValueError) as exc_info:
            TAMSSource(client, label="Test")
        assert "format is required" in str(exc_info.value)


class TestTAMSSourceProperties:
    """Tests for TAMSSource properties."""
    
    def test_format_property(self, client):
        """Test format property."""
        source = TAMSSource(client, id="test", format="urn:x-nmos:format:video")
        assert source.format == "urn:x-nmos:format:video"
    
    def test_label_property(self, client):
        """Test label property."""
        source = TAMSSource(client, id="test", label="Test Source")
        assert source.label == "Test Source"
    
    def test_description_property(self, client):
        """Test description property."""
        source = TAMSSource(client, id="test", description="Test description")
        assert source.description == "Test description"


class TestTAMSSourceCreation:
    """Tests for TAMSSource creation."""
    
    @pytest.mark.asyncio
    async def test_ensure_created(self, client):
        """Test ensuring source is created."""
        source = TAMSSource(
            client,
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        
        with patch('vasttamsclient.api.sources.create_source', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": source.id,
                "format": "urn:x-nmos:format:video",
                "label": "Test Source",
                "created_at": "2025-01-01T00:00:00Z"
            }
            
            await source._ensure_created()
            assert source._created is False
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_created_already_created(self, client):
        """Test that _ensure_created doesn't recreate existing source."""
        source = TAMSSource(client, id="existing-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.sources.create_source', new_callable=AsyncMock) as mock_create:
            await source._ensure_created()
            mock_create.assert_not_called()


class TestTAMSSourceFlowOperations:
    """Tests for TAMSSource flow operations."""
    
    def test_tams_flow_factory(self, client):
        """Test TAMSFlow factory method."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        flow = source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        assert isinstance(flow, TAMSFlow)
        assert flow._data["format"] == "urn:x-nmos:format:video"
        assert flow._data["codec"] == "video/h264"
        assert flow._data["label"] == "Test Flow"
    
    @pytest.mark.asyncio
    async def test_add_flow(self, client):
        """Test adding a flow to a source."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        flow = TAMSFlow(
            client,
            source_id="source-123",  # Set source_id
            format="urn:x-nmos:format:video",
            codec="video/h264"
        )
        
        with patch.object(source, '_ensure_created', new_callable=AsyncMock):
            with patch.object(flow, '_ensure_created', new_callable=AsyncMock):
                result = await source.add_flow(flow)
                assert result == flow
                assert flow._data["source_id"] == "source-123"
                flow._ensure_created.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_flow(self, client):
        """Test getting a flow by ID."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        flow_data = {
            "id": "flow-123",
            "source_id": "source-123",
            "format": "urn:x-nmos:format:video",
            "codec": "video/h264"
        }
        
        with patch('vasttamsclient.api.flows.get_flow', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = flow_data
            
            flow = await source.get_flow("flow-123")
            assert isinstance(flow, TAMSFlow)
            assert flow.id == "flow-123"
            assert flow._data["source_id"] == "source-123"
            mock_get.assert_called_once_with(client, "flow-123")
    
    @pytest.mark.asyncio
    async def test_get_flow_not_found(self, client):
        """Test getting a non-existent flow."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.flows.get_flow', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            flow = await source.get_flow("nonexistent")
            assert flow is None
    
    @pytest.mark.asyncio
    async def test_list_flows(self, client):
        """Test listing flows for a source."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        flows_data = [
            {"id": "flow-1", "source_id": "source-123", "format": "urn:x-nmos:format:video", "codec": "video/h264"},
            {"id": "flow-2", "source_id": "source-123", "format": "urn:x-nmos:format:video", "codec": "video/h264"}
        ]
        
        with patch('vasttamsclient.api.flows.list_flows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = flows_data
            
            flows = await source.list_flows()
            assert len(flows) == 2
            assert all(isinstance(f, TAMSFlow) for f in flows)
            assert flows[0].id == "flow-1"
            assert flows[1].id == "flow-2"
            mock_list.assert_called_once_with(client, {"source_id": "source-123"})


class TestTAMSSourceCRUD:
    """Tests for TAMSSource CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_refresh(self, client):
        """Test refreshing source data."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.sources.get_source', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": "source-123",
                "format": "urn:x-nmos:format:video",
                "label": "Updated Label",
                "description": "Updated description"
            }
            
            await source.refresh()
            assert source._data["label"] == "Updated Label"
            assert source._data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_refresh_not_found(self, client):
        """Test refreshing non-existent source."""
        source = TAMSSource(client, id="nonexistent", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.sources.get_source', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(TAMSClientError) as exc_info:
                await source.refresh()
            assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update(self, client):
        """Test updating source."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video", label="Old Label")
        
        with patch('vasttamsclient.api.sources.update_source_label', new_callable=AsyncMock) as mock_update_label:
            with patch('vasttamsclient.api.sources.update_source_description', new_callable=AsyncMock) as mock_update_desc:
                with patch.object(source, 'refresh', new_callable=AsyncMock) as mock_refresh:
                    mock_refresh.return_value = None
                    
                    await source.update(label="New Label", description="New description")
                    assert source._data["label"] == "New Label"
                    assert source._data["description"] == "New description"
                    mock_update_label.assert_called_once_with(client, "source-123", "New Label")
                    mock_update_desc.assert_called_once_with(client, "source-123", "New description")
                    mock_refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete(self, client):
        """Test deleting source."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.sources.delete_source', new_callable=AsyncMock) as mock_delete:
            await source.delete()
            mock_delete.assert_called_once_with(client, "source-123", cascade=True)


class TestTAMSSourceTags:
    """Tests for TAMSSource tag operations."""
    
    @pytest.mark.asyncio
    async def test_get_tags(self, client):
        """Test getting all tags."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.tags.get_tags', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"location": "studio-a", "camera": "panasonic"}
            
            tags = await source.get_tags()
            assert tags == {"location": "studio-a", "camera": "panasonic"}
            mock_get.assert_called_once_with(client, "source", "source-123")
    
    @pytest.mark.asyncio
    async def test_get_tag(self, client):
        """Test getting a specific tag."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.tags.get_tag', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = "studio-a"
            
            value = await source.get_tag("location")
            assert value == "studio-a"
            mock_get.assert_called_once_with(client, "source", "source-123", "location")
    
    @pytest.mark.asyncio
    async def test_set_tag(self, client):
        """Test setting a tag."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.tags.set_tag', new_callable=AsyncMock) as mock_set:
            await source.set_tag("location", "studio-a")
            mock_set.assert_called_once_with(client, "source", "source-123", "location", "studio-a")
    
    @pytest.mark.asyncio
    async def test_delete_tag(self, client):
        """Test deleting a tag."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        
        with patch('vasttamsclient.api.tags.delete_tag', new_callable=AsyncMock) as mock_delete:
            await source.delete_tag("location")
            mock_delete.assert_called_once_with(client, "source", "source-123", "location")

