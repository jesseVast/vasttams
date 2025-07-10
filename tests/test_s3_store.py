import pytest
from unittest.mock import MagicMock, patch
from app.s3_store import S3Store
from app.models import FlowSegment
import uuid
from tests.test_settings import get_test_settings

@pytest.fixture
def s3_store():
    settings = get_test_settings()
    return S3Store(
        endpoint_url=settings.s3_endpoint_url,
        access_key_id=settings.s3_access_key_id,
        secret_access_key=settings.s3_secret_access_key,
        bucket_name=settings.s3_bucket_name,
        use_ssl=settings.s3_use_ssl
    )

@pytest.mark.asyncio
async def test_ensure_bucket_exists(s3_store):
    # Should not raise
    s3_store._ensure_bucket_exists()

@pytest.mark.asyncio
async def test_store_and_get_flow_segment(s3_store):
    flow_id = str(uuid.uuid4())
    segment = FlowSegment(object_id="obj1", timerange="[0:0_10:0)")
    data = b"testdata"
    s3_store.s3_client.put_object = MagicMock(return_value={})
    s3_store.s3_client.get_object = MagicMock(return_value={"Body": MagicMock(read=MagicMock(return_value=data))})
    # Store
    result = await s3_store.store_flow_segment(flow_id, segment, data, "video/mp4")
    assert result
    # Get
    result_data = await s3_store.get_flow_segment_data(flow_id, segment.object_id, segment.timerange)
    assert result_data == data

@pytest.mark.asyncio
async def test_generate_presigned_url(s3_store):
    flow_id = str(uuid.uuid4())
    object_id = "obj1"
    timerange = "[0:0_10:0)"
    s3_store.s3_client.generate_presigned_url = MagicMock(return_value="http://presigned.url")
    url = await s3_store.generate_presigned_url(flow_id, object_id, timerange, operation="get_object")
    assert url == "http://presigned.url"

@pytest.mark.asyncio
async def test_delete_flow_segment(s3_store):
    flow_id = str(uuid.uuid4())
    object_id = "obj1"
    timerange = "[0:0_10:0)"
    s3_store.s3_client.delete_object = MagicMock(return_value={})
    result = await s3_store.delete_flow_segment(flow_id, object_id, timerange)
    assert result

@pytest.mark.asyncio
async def test_error_handling(s3_store):
    # Simulate error in put_object
    s3_store.s3_client.put_object = MagicMock(side_effect=Exception("fail"))
    flow_id = str(uuid.uuid4())
    segment = FlowSegment(object_id="obj1", timerange="[0:0_10:0)")
    data = b"testdata"
    result = await s3_store.store_flow_segment(flow_id, segment, data, "video/mp4")
    assert not result 