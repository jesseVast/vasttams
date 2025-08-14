#!/usr/bin/env python3
"""
Test script for the new VAST store implementation using vastdbmanager
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from app.storage.vast_store import VASTStore
from app.models.models import Source, Flow, FlowSegment, Object, Tags, VideoFlow
from app.core.config import get_settings
from tests.test_settings import get_test_settings

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def store():
    settings = get_test_settings()
    store = VASTStore(
        endpoints=[settings.vast_endpoint],
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
    )
    yield store
    await store.close()

@pytest.mark.asyncio
async def test_source_crud(store):
    source_id = uuid.uuid4()
    source = Source(id=source_id, format="urn:x-nmos:format:video", label="UnitTest Source", created_by="unittest")
    assert await store.create_source(source)
    retrieved = await store.get_source(str(source_id))
    assert retrieved is not None
    assert retrieved.id == source_id
    retrieved.label = "Updated Label"
    assert await store.update_source(str(source_id), retrieved)
    updated = await store.get_source(str(source_id))
    assert updated.label == "Updated Label"
    assert await store.delete_source(str(source_id))
    assert await store.get_source(str(source_id)) is None

@pytest.mark.asyncio
async def test_flow_crud(store):
    # Create source first
    source_id = uuid.uuid4()
    source = Source(id=source_id, format="urn:x-nmos:format:video", label="FlowTest Source")
    await store.create_source(source)
    flow_id = uuid.uuid4()
    flow = VideoFlow(id=flow_id, source_id=source_id, format="urn:x-nmos:format:video", codec="video/mp4", frame_width=1920, frame_height=1080, frame_rate="25/1")
    assert await store.create_flow(flow)
    retrieved = await store.get_flow(str(flow_id))
    assert retrieved is not None
    assert retrieved.id == flow_id
    retrieved.label = "Updated Flow"
    assert await store.update_flow(str(flow_id), retrieved)
    updated = await store.get_flow(str(flow_id))
    assert updated.label == "Updated Flow"
    assert await store.delete_flow(str(flow_id))
    assert await store.get_flow(str(flow_id)) is None
    await store.delete_source(str(source_id))

@pytest.mark.asyncio
async def test_segment_crud(store):
    # Create source and flow first
    source_id = uuid.uuid4()
    await store.create_source(Source(id=source_id, format="urn:x-nmos:format:video", label="SegTest Source"))
    flow_id = uuid.uuid4()
    await store.create_flow(VideoFlow(id=flow_id, source_id=source_id, format="urn:x-nmos:format:video", codec="video/mp4", frame_width=1920, frame_height=1080, frame_rate="25/1"))
    segment = FlowSegment(object_id="obj1", timerange="[0:0_10:0)")
    # Simulate segment creation (media data is not tested here)
    assert await store.create_flow_segment(segment, str(flow_id), b"data", "video/mp4")
    segments = await store.get_flow_segments(str(flow_id))
    assert any(seg.object_id == "obj1" for seg in segments)
    assert await store.delete_flow_segments(str(flow_id))
    await store.delete_flow(str(flow_id))
    await store.delete_source(str(source_id))

@pytest.mark.asyncio
async def test_object_crud(store):
    obj = Object(object_id="obj-unit", flow_references=[], size=123, created=datetime.now())
    assert await store.create_object(obj)
    retrieved = await store.get_object("obj-unit")
    assert retrieved is not None
    assert retrieved.object_id == "obj-unit"
    # No update/delete implemented for objects in VASTStore, just test get

@pytest.mark.asyncio
async def test_analytics_and_stats(store):
    assert isinstance(await store.analytics_query("flow_usage"), dict)
    assert isinstance(await store.analytics_query("storage_usage"), dict)
    assert isinstance(await store.analytics_query("catalog_summary"), dict)
    for table in store.list_tables():
        assert isinstance(store.get_table_stats(table), dict)

@pytest.mark.asyncio
async def test_error_handling(store):
    # Try to get non-existent source/flow/object
    assert await store.get_source(str(uuid.uuid4())) is None
    assert await store.get_flow(str(uuid.uuid4())) is None
    assert await store.get_object("nonexistent") is None 