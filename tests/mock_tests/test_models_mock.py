"""
Mock Tests for TAMS Models

This file tests the data models used throughout the TAMS application.
Tests focus on model validation, serialization, and basic functionality.
"""

import pytest
from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any

# Import models
from app.models.models import (
    Source, VideoFlow, FlowSegment, Object, 
    Webhook, User, ApiToken, AuthLog
)


class TestSourceModel:
    """Test Source model functionality"""
    
    def test_source_creation(self):
        """Test creating a Source instance"""
        source = Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="Test Video Source",
            description="Test source for video processing",
            created_by="test_user"
        )
        
        assert source.id is not None
        assert source.label == "Test Video Source"
        assert source.format == "urn:x-nmos:format:video"
        assert source.description == "Test source for video processing"
        assert source.created_by == "test_user"
        # created is optional, so it might be None
        assert source.created is None or isinstance(source.created, datetime)
    
    def test_source_validation(self):
        """Test Source model validation"""
        # Test required fields
        with pytest.raises(ValueError):
            Source()  # Should fail without required fields
        
        # Test valid source
        source = Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="Valid Source",
            created_by="user"
        )
        assert source is not None
    
    def test_source_serialization(self):
        """Test Source model serialization"""
        source = Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="Serializable Source",
            description="Test serialization",
            created_by="test_user"
        )
        
        # Test model_dump conversion (Pydantic v2)
        source_dict = source.model_dump()
        assert isinstance(source_dict, dict)
        assert source_dict["label"] == "Serializable Source"
        assert source_dict["format"] == "urn:x-nmos:format:video"


class TestVideoFlowModel:
    """Test VideoFlow model functionality"""
    
    def test_video_flow_creation(self):
        """Test creating a VideoFlow instance"""
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Video Flow",
            description="Test flow for video processing",
            created_by="test_user",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30:1"
        )
        
        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == "urn:x-nmos:format:video"
        assert flow.codec == "video/h264"
        assert flow.frame_width == 1920
        assert flow.frame_height == 1080
        assert flow.frame_rate == "30:1"
    
    def test_video_flow_validation(self):
        """Test VideoFlow model validation"""
        # Test with minimal required fields
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            codec="video/h264",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30:1"
        )
        assert flow is not None
        
        # Test frame dimensions
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            codec="video/h264",
            frame_width=1280,
            frame_height=720,
            frame_rate="30:1"
        )
        assert flow.frame_width == 1280
        assert flow.frame_height == 720


class TestFlowSegmentModel:
    """Test FlowSegment model functionality"""
    
    def test_flow_segment_creation(self):
        """Test creating a FlowSegment instance"""
        segment = FlowSegment(
            id=str(uuid.uuid4()),
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        
        assert segment.id is not None
        assert segment.timerange == "[0:0_10:0)"
        assert segment.sample_offset == 0
        assert segment.sample_count == 1000
        assert segment.key_frame_count == 10
    
    def test_flow_segment_timerange_validation(self):
        """Test FlowSegment timerange validation"""
        # Test valid timerange format
        valid_timeranges = [
            "[0:0_10:0)",
            "[10:0_20:0)",
            "[0:0_30:0)"
        ]
        
        for timerange in valid_timeranges:
            segment = FlowSegment(
                id=str(uuid.uuid4()),
                timerange=timerange,
                sample_offset=0,
                sample_count=1000,
                key_frame_count=10
            )
            assert segment.timerange == timerange


class TestObjectModel:
    """Test Object model functionality"""
    
    def test_object_creation(self):
        """Test creating an Object instance"""
        obj = Object(
            id=str(uuid.uuid4()),
            referenced_by_flows=[str(uuid.uuid4())],
            size=1024000,
            created=datetime.now(timezone.utc)
        )
        
        assert obj.id is not None
        assert len(obj.referenced_by_flows) == 1
        assert obj.size == 1024000
        assert obj.created is not None
    
    def test_object_flow_references(self):
        """Test Object flow references handling"""
        flow_id = str(uuid.uuid4())
        obj = Object(
            id=str(uuid.uuid4()),
            referenced_by_flows=[flow_id],
            size=1024000,
            created=datetime.now(timezone.utc)
        )
        
        assert flow_id in obj.referenced_by_flows
        assert obj.size == 1024000


class TestWebhookModel:
    """Test Webhook model functionality"""
    
    def test_webhook_creation(self):
        """Test creating a Webhook instance"""
        webhook = Webhook(
            url="https://webhook.example.com/callback",
            api_key_name="test-api-key",
            events=["flow.created", "segment.uploaded"],
            owner_id=str(uuid.uuid4())
        )
        
        assert webhook.url == "https://webhook.example.com/callback"
        assert webhook.api_key_name == "test-api-key"
        assert len(webhook.events) == 2
        assert webhook.owner_id is not None
    
    def test_webhook_url_validation(self):
        """Test Webhook URL validation"""
        # Test valid URLs
        valid_urls = [
            "https://webhook.example.com/callback",
            "http://localhost:8000/webhook",
            "https://api.example.com/webhooks/123"
        ]
        
        for url in valid_urls:
            webhook = Webhook(
                url=url,
                api_key_name="test-api-key",
                events=["test.event"],
                owner_id=str(uuid.uuid4())
            )
            assert webhook.url == url


class TestUserModel:
    """Test User model functionality"""
    
    def test_user_creation(self):
        """Test creating a User instance"""
        user = User(
            user_id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )
        
        assert user.user_id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True  # default value
    
    def test_user_disabled_state(self):
        """Test User disabled state"""
        disabled_user = User(
            user_id=str(uuid.uuid4()),
            username="disabled_user",
            email="disabled@example.com",
            full_name="Disabled User",
            is_active=False
        )
        
        assert disabled_user.is_active is False


class TestAuthModels:
    """Test authentication-related models"""
    
    def test_api_token_creation(self):
        """Test creating an ApiToken instance"""
        token = ApiToken(
            token_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            token_name="Test Token",
            token_type="bearer"
        )
        
        assert token.token_id is not None
        assert token.user_id is not None
        assert token.token_name == "Test Token"
        assert token.token_type == "bearer"
        assert token.is_active is True  # default value
    
    def test_auth_log_creation(self):
        """Test creating an AuthLog instance"""
        log_entry = AuthLog(
            log_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            event_type="login",
            auth_method="password",
            ip_address="192.168.1.1",
            user_agent="Test Browser",
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        
        assert log_entry.log_id is not None
        assert log_entry.user_id is not None
        assert log_entry.event_type == "login"
        assert log_entry.auth_method == "password"
        assert log_entry.ip_address == "192.168.1.1"
        assert log_entry.success is True


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_source_to_flow_relationship(self):
        """Test Source to VideoFlow relationship"""
        source = Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="Test Source",
            created_by="test_user"
        )
        
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=source.id,
            codec="video/h264",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30:1"
        )
        
        assert flow.source_id == source.id
    
    def test_flow_to_segment_relationship(self):
        """Test VideoFlow to FlowSegment relationship"""
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            codec="video/h264",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30:1"
        )
        
        segment = FlowSegment(
            id=str(uuid.uuid4()),
            timerange="[0:0_10:0)",
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        
        # Test that segment can reference flow
        assert segment.id is not None
        assert segment.timerange is not None


if __name__ == "__main__":
    pytest.main([__file__])
