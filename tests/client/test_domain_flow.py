"""
Tests for TAMSFlow domain object.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from vasttamsclient.domain.flow import TAMSFlow
from vasttamsclient.domain.source import TAMSSource
from vasttamsclient.domain.segment import TAMSSegment
from vasttamsclient.exceptions import TAMSClientError


class TestTAMSFlowInit:
    """Tests for TAMSFlow initialization."""
    
    def test_init_new_flow_with_source_id(self, client):
        """Test creating a new flow with source_id."""
        flow = TAMSFlow(
            client,
            source_id="source-123",
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        assert flow.id is not None
        assert flow._data["source_id"] == "source-123"
        assert flow._data["format"] == "urn:x-nmos:format:video"
        assert flow._data["codec"] == "video/h264"
        assert flow._created is True
    
    def test_init_new_flow_with_source_object(self, client):
        """Test creating a new flow with TAMSSource object."""
        source = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
        flow = TAMSFlow(
            client,
            source=source,
            format="urn:x-nmos:format:video",
            codec="video/h264"
        )
        assert flow._data["source_id"] == "source-123"
        assert flow._created is True
    
    def test_init_existing_flow(self, client):
        """Test representing an existing flow."""
        flow_id = "flow-123"
        flow = TAMSFlow(
            client,
            id=flow_id,
            source_id="source-123",
            format="urn:x-nmos:format:video",
            codec="video/h264"
        )
        assert flow.id == flow_id
        assert flow._created is False
    
    def test_init_missing_format(self, client):
        """Test that format is required for new flow."""
        with pytest.raises(ValueError) as exc_info:
            TAMSFlow(client, source_id="source-123", codec="video/h264")
        assert "format and codec are required" in str(exc_info.value)
    
    def test_init_missing_codec(self, client):
        """Test that codec is required for new flow."""
        with pytest.raises(ValueError) as exc_info:
            TAMSFlow(client, source_id="source-123", format="urn:x-nmos:format:video")
        assert "format and codec are required" in str(exc_info.value)
    
    def test_init_missing_source(self, client):
        """Test that source or source_id is required for new flow."""
        with pytest.raises(ValueError) as exc_info:
            TAMSFlow(client, format="urn:x-nmos:format:video", codec="video/h264")
        assert "source or source_id is required" in str(exc_info.value)


class TestTAMSFlowProperties:
    """Tests for TAMSFlow properties."""
    
    def test_source_id_property(self, client):
        """Test source_id property."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        assert flow.source_id == "source-123"
    
    def test_format_property(self, client):
        """Test format property."""
        flow = TAMSFlow(client, id="flow-123", format="urn:x-nmos:format:video", codec="video/h264", source_id="source-123")
        flow._data["format"] = "urn:x-nmos:format:video"  # Set data for existing flow
        assert flow.format == "urn:x-nmos:format:video"
    
    def test_codec_property(self, client):
        """Test codec property."""
        flow = TAMSFlow(client, id="flow-123", codec="video/h264", format="urn:x-nmos:format:video", source_id="source-123")
        flow._data["codec"] = "video/h264"  # Set data for existing flow
        assert flow.codec == "video/h264"
    
    def test_label_property(self, client):
        """Test label property."""
        flow = TAMSFlow(client, id="flow-123", label="Test Flow", format="urn:x-nmos:format:video", codec="video/h264", source_id="source-123")
        flow._data["label"] = "Test Flow"  # Set data for existing flow
        assert flow.label == "Test Flow"
    
    def test_essence_parameters_property(self, client):
        """Test essence_parameters property."""
        essence_params = {"frame_width": 1920, "frame_height": 1080}
        flow = TAMSFlow(client, id="flow-123", essence_parameters=essence_params, format="urn:x-nmos:format:video", codec="video/h264", source_id="source-123")
        assert flow.essence_parameters == essence_params


class TestTAMSFlowCreation:
    """Tests for TAMSFlow creation."""
    
    @pytest.mark.asyncio
    async def test_ensure_created(self, client):
        """Test ensuring flow is created."""
        flow = TAMSFlow(
            client,
            source_id="source-123",
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        
        with patch('vasttamsclient.api.flows.create_flow', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": flow.id,
                "source_id": "source-123",
                "format": "urn:x-nmos:format:video",
                "codec": "video/h264",
                "label": "Test Flow",
                "created_at": "2025-01-01T00:00:00Z"
            }
            
            await flow._ensure_created()
            assert flow._created is False
            mock_create.assert_called_once()


class TestTAMSFlowSegmentOperations:
    """Tests for TAMSFlow segment operations."""
    
    @pytest.mark.asyncio
    async def test_add_segment_with_file_path(self, client, tmp_path):
        """Test adding a segment with file path."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        # Create a test file
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"fake video data")
        
        storage_result = {
            "media_objects": [{
                "object_id": "object-123",
                "put_url": {
                    "url": "https://s3.example.com/upload",
                    "content-type": "video/mp4"
                }
            }]
        }
        
        segment_result = {
            "id": "segment-123",
            "flow_id": "flow-123",
            "object_id": "object-123",
            "timerange": {"value": "[0:0_10:0)"}
        }
        
        with patch.object(flow, '_ensure_created', new_callable=AsyncMock):
            with patch('vasttamsclient.api.segments.allocate_storage', new_callable=AsyncMock) as mock_allocate:
                mock_allocate.return_value = storage_result
                with patch('vasttamsclient.api.segments.upload_to_storage', new_callable=AsyncMock):
                    with patch('vasttamsclient.api.segments.create_segment', new_callable=AsyncMock) as mock_create:
                        mock_create.return_value = segment_result
                        
                        segment = await flow.add_segment(
                            file_path=str(test_file),
                            timerange={"value": "[0:0_10:0)"}
                        )
                        assert isinstance(segment, TAMSSegment)
                        mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_segment_file_not_found(self, client):
        """Test adding segment with non-existent file."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch.object(flow, '_ensure_created', new_callable=AsyncMock):
            with patch('vasttamsclient.api.segments.allocate_storage', new_callable=AsyncMock) as mock_allocate:
                mock_allocate.return_value = {
                    "media_objects": [{
                        "object_id": "object-123",
                        "put_url": {"url": "https://s3.example.com/upload", "content-type": "video/mp4"}
                    }]
                }
                with pytest.raises(FileNotFoundError):
                    await flow.add_segment(file_path="/nonexistent/file.mp4")
    
    @pytest.mark.asyncio
    async def test_add_segment_no_file_or_s3(self, client):
        """Test adding segment without file_path or s3_object."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch.object(flow, '_ensure_created', new_callable=AsyncMock):
            with pytest.raises(ValueError) as exc_info:
                await flow.add_segment()
            assert "Either file_path or s3_object must be provided" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_segment(self, client):
        """Test getting a segment by object_id."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.segments.list_segments', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [{
                "id": "segment-123",
                "flow_id": "flow-123",
                "object_id": "object-123",
                "timerange": {"value": "[0:0_10:0)"}
            }]
            
            segment = await flow.get_segment("object-123")
            assert isinstance(segment, TAMSSegment)
            assert segment._data["object_id"] == "object-123"
    
    @pytest.mark.asyncio
    async def test_list_segments(self, client):
        """Test listing segments."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.segments.list_segments', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"id": "segment-1", "flow_id": "flow-123", "object_id": "object-1", "timerange": {"value": "[0:0_10:0)"}},
                {"id": "segment-2", "flow_id": "flow-123", "object_id": "object-2", "timerange": {"value": "[10:0_20:0)"}}
            ]
            
            segments = await flow.list_segments()
            assert len(segments) == 2
            assert all(isinstance(s, TAMSSegment) for s in segments)
    
    @pytest.mark.asyncio
    async def test_delete_segments(self, client):
        """Test deleting segments."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.segments.delete_segments', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None  # Synchronous deletion
            result = await flow.delete_segments(timerange={"value": "[0:0_10:0)"})
            
            assert result is None
            mock_delete.assert_called_once_with(client, "flow-123", {"timerange": {"value": "[0:0_10:0)"}})
    
    @pytest.mark.asyncio
    async def test_delete_segments_async(self, client):
        """Test deleting segments with async deletion request."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.segments.delete_segments', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {
                "id": "deletion-request-123",
                "status": "created",
                "location": "/flow-delete-requests/deletion-request-123"
            }
            result = await flow.delete_segments(timerange={"value": "[0:0_10:0)"})
            
            assert result is not None
            assert result["id"] == "deletion-request-123"
            assert result["status"] == "created"
            mock_delete.assert_called_once_with(client, "flow-123", {"timerange": {"value": "[0:0_10:0)"}})


class TestTAMSFlowCRUD:
    """Tests for TAMSFlow CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_refresh(self, client):
        """Test refreshing flow data."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.flows.get_flow', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": "flow-123",
                "label": "Updated Label",
                "essence_parameters": {"frame_width": 1920}
            }
            
            await flow.refresh()
            assert flow._data["label"] == "Updated Label"
            assert flow._data["essence_parameters"] == {"frame_width": 1920}
    
    @pytest.mark.asyncio
    async def test_update(self, client):
        """Test updating flow."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264", label="Old Label")
        
        with patch('vasttamsclient.api.flows.update_flow', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {
                "id": "flow-123",
                "label": "New Label"
            }
            
            await flow.update(label="New Label")
            assert flow._data["label"] == "New Label"
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete(self, client):
        """Test deleting flow."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.flows.delete_flow', new_callable=AsyncMock) as mock_delete:
            await flow.delete()
            mock_delete.assert_called_once_with(client, "flow-123")


class TestTAMSFlowTags:
    """Tests for TAMSFlow tag operations."""
    
    @pytest.mark.asyncio
    async def test_get_tags(self, client):
        """Test getting all tags."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.tags.get_tags', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"quality": "hd", "bitrate": "high"}
            
            tags = await flow.get_tags()
            assert tags == {"quality": "hd", "bitrate": "high"}
            mock_get.assert_called_once_with(client, "flow", "flow-123")
    
    @pytest.mark.asyncio
    async def test_set_tag(self, client):
        """Test setting a tag."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.tags.set_tag', new_callable=AsyncMock) as mock_set:
            await flow.set_tag("quality", "hd")
            mock_set.assert_called_once_with(client, "flow", "flow-123", "quality", "hd")
    
    @pytest.mark.asyncio
    async def test_delete_tag(self, client):
        """Test deleting a tag."""
        flow = TAMSFlow(client, id="flow-123", source_id="source-123", format="urn:x-nmos:format:video", codec="video/h264")
        
        with patch('vasttamsclient.api.tags.delete_tag', new_callable=AsyncMock) as mock_delete:
            await flow.delete_tag("quality")
            mock_delete.assert_called_once_with(client, "flow", "flow-123", "quality")

