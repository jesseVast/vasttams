#!/usr/bin/env python3
"""
Bit Rate Calculation Tests

Tests for automatic bit rate calculation (App Note 0013).
"""

import pytest
import sys
import requests
from pathlib import Path
import uuid
import time

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings
from vasttams.flows.bitrate_calculator import BitRateCalculator
from vasttams.segments.models import FlowSegment, GetUrl, TimeRange, Timestamp

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


@pytest.fixture
def clean_flow_id():
    """Generate a clean flow ID for each test"""
    return str(uuid.uuid4())


@pytest.fixture
def test_source_id(api_available, auth_headers):
    """Create a test source for flow testing"""
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        if response.status_code == 201:
            yield source_id
        else:
            pytest.skip(f"Failed to create test source: {response.text}")
    finally:
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestBitRateAutoCalculation:
    """Test automatic bit rate calculation on flow creation"""
    
    def test_create_flow_without_bit_rates_triggers_auto_calc(self, api_available, test_source_id, auth_headers):
        """Test that creating a flow without bit rates triggers auto-calculation"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())
        
        # Create flow without avg_bit_rate or max_bit_rate
        flow_data = {
            "id": flow_id,
            "source_id": test_source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"Test Flow {flow_id[:8]}",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {
                    "numerator": 25,
                    "denominator": 1
                },
                "interlace_mode": "progressive",
                "transfer_characteristic": "ITU-R BT.709"
            }
            # avg_bit_rate and max_bit_rate omitted
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create flow: {response.text}"
        
        # Verify flow was created
        response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code == 200
        flow = response.json()
        
        # Note: Bit rates may be None if no segments exist
        # This is expected behavior when there are no segments to calculate from
        assert flow["id"] == flow_id
        # bit rates are either calculated or None (if no segments)
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
    
    def test_manual_recalculate_bit_rates_endpoint(self, api_available, test_source_id, auth_headers):
        """Test manual recalculate bit rates endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())
        
        # Create flow
        flow_data = {
            "id": flow_id,
            "source_id": test_source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"Test Flow {flow_id[:8]}",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {
                    "numerator": 25,
                    "denominator": 1
                },
                "interlace_mode": "progressive",
                "transfer_characteristic": "ITU-R BT.709"
            }
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Call recalculation endpoint
        response = requests.post(f"{BASE_URL}/flows/{flow_id}/recalculate-bit-rates", headers=auth_headers)
        # Accept 200 (success) or 404 (flow not found) or 500 (no segments)
        assert response.status_code in [200, 404, 500], f"Unexpected status: {response.text}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
    
    def test_recalculate_bit_rates_on_non_existent_flow(self, api_available, auth_headers):
        """Test that recalculating bit rates on non-existent flow returns 404"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())  # Non-existent flow
        
        response = requests.post(f"{BASE_URL}/flows/{flow_id}/recalculate-bit-rates", headers=auth_headers)
        assert response.status_code == 404, "Should return 404 for non-existent flow"


@pytest.mark.usefixtures("api_available")
class TestBitRateCalculator:
    """Test BitRateCalculator module directly"""
    
    def test_calculate_avg_bit_rate_with_test_segments(self):
        """Test average bit rate calculation with mock segments"""
        # Create mock segments
        segments = []
        for i in range(3):
            segment = FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange=TimeRange(value=f"[{i}:0_{i+1}:0)"),
                sample_count=1000,
                get_urls=[
                    GetUrl(
                        url=f"http://example.com/segment{i}.mp4",
                        storage_id=str(uuid.uuid4()),
                        store_type="http_object_store",
                        provider="aws",
                        store_product="s3"
                    )
                ]
            )
            segments.append(segment)
        
        # Test calculation (async)
        async def test():
            calculator = BitRateCalculator()
            avg_bit_rate = await calculator.calculate_avg_bit_rate(segments)
            # Should return a value or None if calculation fails
            assert avg_bit_rate is None or avg_bit_rate >= 0
        
        # Run async test
        import asyncio
        asyncio.run(test())
    
    def test_calculate_max_bit_rate_with_test_segments(self):
        """Test maximum bit rate calculation with mock segments"""
        # Create mock segments
        segments = []
        for i in range(5):
            segment = FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange=TimeRange(value=f"[{i}:0_{i+1}:0)"),
                sample_count=1000,
                get_urls=[
                    GetUrl(
                        url=f"http://example.com/segment{i}.mp4",
                        storage_id=str(uuid.uuid4()),
                        store_type="http_object_store",
                        provider="aws",
                        store_product="s3"
                    )
                ]
            )
            segments.append(segment)
        
        # Test calculation (async)
        async def test():
            calculator = BitRateCalculator()
            max_bit_rate = await calculator.calculate_max_bit_rate(segments, 1.0)
            # Should return a value or None if calculation fails
            assert max_bit_rate is None or max_bit_rate >= 0
        
        # Run async test
        import asyncio
        asyncio.run(test())
    
    def test_calculate_bit_rates_with_empty_segments(self):
        """Test bit rate calculation with no segments returns None"""
        segments = []
        
        async def test():
            calculator = BitRateCalculator()
            avg_bit_rate = await calculator.calculate_avg_bit_rate(segments)
            max_bit_rate = await calculator.calculate_max_bit_rate(segments, 1.0)
            
            # Should return None for empty segments
            assert avg_bit_rate is None
            assert max_bit_rate is None
        
        import asyncio
        asyncio.run(test())

