#!/usr/bin/env python3
"""
Comprehensive Router Tests for Analytics

Tests all endpoints in analytics/router.py to achieve 100% coverage.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
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


@pytest.mark.usefixtures("api_available")
class TestAnalyticsRouter:
    """Test analytics router endpoints"""
    
    def test_get_analytics_summary(self, api_available, auth_headers):
        """Test GET /analytics/summary endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Verify summary structure
        assert isinstance(data, dict)
        # Should have counts or other analytics fields
        assert "counts" in data or "sources" in data or "flows" in data or "segments" in data
    
    def test_get_source_analytics(self, api_available, auth_headers):
        """Test GET /analytics/sources endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/analytics/sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_flow_analytics(self, api_available, auth_headers):
        """Test GET /analytics/flows endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/analytics/flows", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_analytics_requires_auth(self, api_available):
        """Test that analytics endpoints require authentication"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/analytics/summary")
        assert response.status_code == 401
        
        response = requests.get(f"{BASE_URL}/analytics/sources")
        assert response.status_code == 401
        
        response = requests.get(f"{BASE_URL}/analytics/flows")
        assert response.status_code == 401

