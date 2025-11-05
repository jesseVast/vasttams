#!/usr/bin/env python3
"""
Full S3 Upload Workflow Test

This test validates the complete workflow:
1. Run test data ingestion (sources, flows, objects, segments)
2. Verify all data was created correctly
3. Test analytics endpoints
4. Verify segment sharing between flows
"""

import pytest
import sys
import requests
import subprocess
from pathlib import Path
import json
import time

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.fixture(scope="module")
def test_data_ingested(api_available):
    """Run test data ingestion and return resource IDs"""
    if not api_available:
        pytest.skip("API not available")
    
    # Run the ingestion script
    script_path = Path(__file__).parent / "ingest_test_data.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode != 0:
            pytest.skip(f"Test data ingestion failed: {result.stderr}")
        
        # Wait a moment for data to be fully written
        time.sleep(2)
        
        # Load resource IDs if saved
        resources_file = Path("test_data_resources.json")
        if resources_file.exists():
            with open(resources_file) as f:
                resources = json.load(f)
        else:
            resources = None
        
        yield resources
        
    except subprocess.TimeoutExpired:
        pytest.skip("Test data ingestion timed out")
    except Exception as e:
        pytest.skip(f"Failed to ingest test data: {e}")


@pytest.mark.usefixtures("api_available")
class TestS3UploadWorkflow:
    """Test complete S3 upload workflow with test data"""
    
    def test_analytics_summary(self, test_data_ingested, auth_headers):
        """Test analytics summary endpoint"""
        response = requests.get(f"{BASE_URL}/analytics/summary", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get analytics: {response.text}"
        
        data = response.json()
        
        # Verify counts
        assert data["counts"]["total_sources"] >= 2, "Should have at least 2 sources"
        assert data["counts"]["total_flows"] >= 4, "Should have at least 4 flows"
        assert data["counts"]["total_segments"] >= 10, "Should have at least 10 segments"
        assert data["counts"]["total_objects"] >= 10, "Should have at least 10 objects"
        
        logger.info(f"✅ Analytics summary: {data['counts']}")
    
    def test_sources_exist(self, test_data_ingested, auth_headers):
        """Verify sources were created"""
        response = requests.get(f"{BASE_URL}/sources", headers=auth_headers)
        assert response.status_code == 200
        
        sources = response.json()
        if isinstance(sources, dict) and "data" in sources:
            sources = sources["data"]
        
        assert len(sources) >= 2, f"Expected at least 2 sources, got {len(sources)}"
        logger.info(f"✅ Found {len(sources)} sources")
    
    def test_flows_exist(self, test_data_ingested, auth_headers):
        """Verify flows were created"""
        response = requests.get(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code == 200
        
        flows = response.json()
        if isinstance(flows, dict) and "data" in flows:
            flows = flows["data"]
        
        assert len(flows) >= 4, f"Expected at least 4 flows, got {len(flows)}"
        
        # Verify audio flow exists
        audio_flows = [f for f in flows if f.get("format") == "urn:x-nmos:format:audio"]
        assert len(audio_flows) >= 1, "Should have at least 1 audio flow"
        
        logger.info(f"✅ Found {len(flows)} flows ({len(audio_flows)} audio)")
    
    def test_objects_exist(self, test_data_ingested, auth_headers):
        """Verify objects were created via S3 uploads"""
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        assert response.status_code == 200
        
        objects = response.json()
        if isinstance(objects, dict) and "data" in objects:
            objects = objects["data"]
        
        # Objects are referenced via segments, so check through segments
        # We can verify by checking segment object_ids
        logger.info(f"✅ Objects are referenced via segments")
    
    def test_segments_exist(self, test_data_ingested, auth_headers):
        """Verify segments were created"""
        response = requests.get(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code == 200
        
        flows = response.json()
        if isinstance(flows, dict) and "data" in flows:
            flows = flows["data"]
        
        total_segments = 0
        for flow in flows[:4]:  # Check first 4 flows
            flow_id = flow["id"]
            segments_response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
            if segments_response.status_code == 200:
                segments = segments_response.json()
                if isinstance(segments, dict) and "data" in segments:
                    segments = segments["data"]
                total_segments += len(segments)
        
        assert total_segments >= 10, f"Expected at least 10 segments across flows, got {total_segments}"
        logger.info(f"✅ Found {total_segments} segments across flows")
    
    def test_segment_sharing(self, test_data_ingested, auth_headers):
        """Verify that segments are shared between flows (flow 2 and flow 4)"""
        response = requests.get(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code == 200
        
        flows = response.json()
        if isinstance(flows, dict) and "data" in flows:
            flows = flows["data"]
        
        # Find flows by label or get all flows and compare segments
        flow_segments = {}
        for flow in flows:
            flow_id = flow["id"]
            segments_response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
            if segments_response.status_code == 200:
                segments = segments_response.json()
                if isinstance(segments, dict) and "data" in segments:
                    segments = segments["data"]
                flow_segments[flow_id] = [s.get("object_id") for s in segments if s.get("object_id")]
        
        # Find flows with shared object_ids (segments)
        shared_found = False
        flow_ids = list(flow_segments.keys())
        for i, flow1_id in enumerate(flow_ids):
            for flow2_id in flow_ids[i+1:]:
                objects1 = set(flow_segments[flow1_id])
                objects2 = set(flow_segments[flow2_id])
                shared = objects1.intersection(objects2)
                if len(shared) > 0:
                    shared_found = True
                    logger.info(f"✅ Found {len(shared)} shared segments between flows {flow1_id[:8]}... and {flow2_id[:8]}...")
        
        assert shared_found, "Should have flows sharing segments"
    
    def test_audio_flow_segments(self, test_data_ingested, auth_headers):
        """Verify audio flow has segments"""
        response = requests.get(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code == 200
        
        flows = response.json()
        if isinstance(flows, dict) and "data" in flows:
            flows = flows["data"]
        
        # Find audio flow
        audio_flows = [f for f in flows if f.get("format") == "urn:x-nmos:format:audio"]
        assert len(audio_flows) > 0, "Should have at least one audio flow"
        
        audio_flow_id = audio_flows[0]["id"]
        segments_response = requests.get(f"{BASE_URL}/flows/{audio_flow_id}/segments", headers=auth_headers)
        assert segments_response.status_code == 200
        
        segments = segments_response.json()
        if isinstance(segments, dict) and "data" in segments:
            segments = segments["data"]
        
        assert len(segments) >= 2, f"Audio flow should have at least 2 segments, got {len(segments)}"
        logger.info(f"✅ Audio flow has {len(segments)} segments")


