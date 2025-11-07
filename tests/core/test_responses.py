#!/usr/bin/env python3
"""
Tests for TAMS Response Models

Tests the response wrapper models in src/vasttams/common/responses.py
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.common.responses import (
    PagingInfo,
    ServiceResponse,
    SourcesResponse,
    FlowsResponse,
    WebhooksResponse,
    DeletionRequestsResponse
)
from vasttams.service.models import Service
from vasttams.sources.models import Source
from vasttams.service.webhooks import Webhook
from vasttams.service.deletion import DeletionRequestsList


class TestPagingInfo:
    """Test PagingInfo model"""
    
    def test_paging_info_creation_minimal(self):
        """Test creating PagingInfo with no fields"""
        paging = PagingInfo()
        assert paging.limit is None
        assert paging.next_key is None
    
    def test_paging_info_with_limit(self):
        """Test creating PagingInfo with limit"""
        paging = PagingInfo(limit=10)
        assert paging.limit == 10
        assert paging.next_key is None
    
    def test_paging_info_with_next_key(self):
        """Test creating PagingInfo with next_key"""
        paging = PagingInfo(next_key="abc123")
        assert paging.limit is None
        assert paging.next_key == "abc123"
    
    def test_paging_info_with_all_fields(self):
        """Test creating PagingInfo with all fields"""
        paging = PagingInfo(limit=20, next_key="xyz789")
        assert paging.limit == 20
        assert paging.next_key == "xyz789"
    
    def test_paging_info_whitespace_stripping(self):
        """Test that whitespace is stripped from string fields"""
        paging = PagingInfo(next_key="  abc123  ")
        assert paging.next_key == "abc123"


class TestServiceResponse:
    """Test ServiceResponse model"""
    
    def test_service_response_creation(self):
        """Test creating ServiceResponse with Service data"""
        service = Service(
            name="Test Service",
            service_version="1.0.0"
        )
        response = ServiceResponse(data=service)
        assert response.data == service
        assert response.data.name == "Test Service"
        assert response.data.service_version == "1.0.0"


class TestSourcesResponse:
    """Test SourcesResponse model"""
    
    def test_sources_response_creation_minimal(self):
        """Test creating SourcesResponse with just data"""
        sources = [
            Source(id="550e8400-e29b-41d4-a716-446655440000", format="urn:x-nmos:format:video")
        ]
        response = SourcesResponse(data=sources)
        assert len(response.data) == 1
        assert response.paging is None
    
    def test_sources_response_with_paging(self):
        """Test creating SourcesResponse with paging"""
        sources = [
            Source(id="550e8400-e29b-41d4-a716-446655440000", format="urn:x-nmos:format:video")
        ]
        paging = PagingInfo(limit=10, next_key="next")
        response = SourcesResponse(data=sources, paging=paging)
        assert len(response.data) == 1
        assert response.paging.limit == 10
        assert response.paging.next_key == "next"
    
    def test_sources_response_empty_list(self):
        """Test creating SourcesResponse with empty list"""
        response = SourcesResponse(data=[])
        assert len(response.data) == 0
        assert response.paging is None


class TestFlowsResponse:
    """Test FlowsResponse model"""
    
    def test_flows_response_creation_minimal(self):
        """Test creating FlowsResponse with just data"""
        from vasttams.flows.models import VideoFlow
        import uuid
        flows = [
            VideoFlow(
                id="550e8400-e29b-41d4-a716-446655440000",
                source_id=str(uuid.uuid4()),
                format="urn:x-nmos:format:video",
                codec="video/H264",
                essence_parameters={
                    "frame_width": 1920,
                    "frame_height": 1080,
                    "frame_rate": {"numerator": 25, "denominator": 1}
                }
            )
        ]
        response = FlowsResponse(data=flows)
        assert len(response.data) == 1
        assert response.paging is None
    
    def test_flows_response_with_paging(self):
        """Test creating FlowsResponse with paging"""
        from vasttams.flows.models import VideoFlow
        import uuid
        flows = [
            VideoFlow(
                id="550e8400-e29b-41d4-a716-446655440000",
                source_id=str(uuid.uuid4()),
                format="urn:x-nmos:format:video",
                codec="video/H264",
                essence_parameters={
                    "frame_width": 1920,
                    "frame_height": 1080,
                    "frame_rate": {"numerator": 25, "denominator": 1}
                }
            )
        ]
        paging = PagingInfo(limit=20)
        response = FlowsResponse(data=flows, paging=paging)
        assert len(response.data) == 1
        assert response.paging.limit == 20
    
    def test_flows_response_empty_list(self):
        """Test creating FlowsResponse with empty list"""
        response = FlowsResponse(data=[])
        assert len(response.data) == 0


class TestWebhooksResponse:
    """Test WebhooksResponse model"""
    
    def test_webhooks_response_creation(self):
        """Test creating WebhooksResponse"""
        webhooks = [
            Webhook(
                id="550e8400-e29b-41d4-a716-446655440000",
                url="https://example.com/webhook",
                api_key_name="X-API-Key",
                events=["flows/created"]
            )
        ]
        response = WebhooksResponse(data=webhooks)
        assert len(response.data) == 1
    
    def test_webhooks_response_empty_list(self):
        """Test creating WebhooksResponse with empty list"""
        response = WebhooksResponse(data=[])
        assert len(response.data) == 0


class TestDeletionRequestsResponse:
    """Test DeletionRequestsResponse model"""
    
    def test_deletion_requests_response_creation(self):
        """Test creating DeletionRequestsResponse"""
        deletion_requests = DeletionRequestsList(root=[])
        response = DeletionRequestsResponse(data=deletion_requests)
        assert response.data.root == []

