import pytest
import httpx
import uuid
from datetime import datetime
import json
from tests.test_settings import get_test_settings

BASE_URL = "http://localhost:8000"
pytestmark = pytest.mark.asyncio

async def test_full_integration_flow():
    """
    Comprehensive integration test for TAMS API:
    - Create source
    - Create flow
    - Create segment
    - Create object
    - Retrieve and validate all entities
    - Delete all entities and confirm deletion
    """
    async with httpx.AsyncClient() as client:
        # 1. Create Source
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Integration Source",
            "description": "Integration test source",
            "created_by": "integration-test"
        }
        resp = await client.post(f"{BASE_URL}/sources", json=source_data)
        assert resp.status_code == 201
        created_source = resp.json()
        assert created_source["id"] == source_id

        # 2. Create Flow
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "label": "Integration Flow",
            "frame_width": 1280,
            "frame_height": 720,
            "frame_rate": "25/1",
            "created_by": "integration-test"
        }
        resp = await client.post(f"{BASE_URL}/flows", json=flow_data)
        assert resp.status_code == 201
        created_flow = resp.json()
        assert created_flow["id"] == flow_id

        # 3. Create Object
        object_id = str(uuid.uuid4())
        object_data = {
            "object_id": object_id,
            "flow_references": [],
            "size": 1234,
            "created": datetime.now().isoformat()
        }
        resp = await client.post(f"{BASE_URL}/objects", json=object_data)
        assert resp.status_code == 201
        created_object = resp.json()
        assert created_object["object_id"] == object_id

        # 4. Create Segment (simulate file upload)
        segment_data = {
            "object_id": object_id,
            "timerange": "[0:0_10:0)"
        }
        files = {
            "file": ("test.mp4", b"dummydata", "video/mp4"),
            "segment": (None, json.dumps(segment_data), "application/json")
        }
        resp = await client.post(f"{BASE_URL}/flows/{flow_id}/segments", files=files)
        assert resp.status_code in (200, 201)
        created_segment = resp.json()
        assert created_segment["object_id"] == object_id

        # 5. Retrieve and validate all entities
        resp = await client.get(f"{BASE_URL}/sources/{source_id}")
        assert resp.status_code == 200
        resp = await client.get(f"{BASE_URL}/flows/{flow_id}")
        assert resp.status_code == 200
        resp = await client.get(f"{BASE_URL}/objects/{object_id}")
        assert resp.status_code == 200
        resp = await client.get(f"{BASE_URL}/flows/{flow_id}/segments")
        assert resp.status_code == 200
        segments = resp.json()
        assert any(seg["object_id"] == object_id for seg in segments)

        # 6. Delete segment
        resp = await client.delete(f"{BASE_URL}/flows/{flow_id}/segments")
        assert resp.status_code == 200

        # 7. Delete object
        resp = await client.delete(f"{BASE_URL}/objects/{object_id}")
        assert resp.status_code in (200, 204, 404)  # Accept 404 if already deleted

        # 8. Delete flow
        resp = await client.delete(f"{BASE_URL}/flows/{flow_id}")
        assert resp.status_code == 200

        # 9. Delete source
        resp = await client.delete(f"{BASE_URL}/sources/{source_id}")
        assert resp.status_code == 200 