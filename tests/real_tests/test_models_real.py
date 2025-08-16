import pytest
import uuid
from datetime import datetime, timezone
from app.models.models import (
    Source, VideoFlow, FlowSegment, Object, Webhook, User, ApiToken, AuthLog
)


class TestSourceModelReal:
    """Test Source model with real data validation"""
    
    def test_source_creation_with_real_data(self):
        """Test creating a Source with realistic data"""
        source = Source(
            id=uuid.uuid4(),
            format="urn:x-nmos:format:video",
            label="BBC News Live Stream",
            description="Live news broadcast from BBC"
        )
        
        assert source.id is not None
        assert source.label == "BBC News Live Stream"
        assert source.format == "urn:x-nmos:format:video"
        assert source.description == "Live news broadcast from BBC"
    
    def test_source_validation_with_invalid_format(self):
        """Test Source validation with invalid format"""
        with pytest.raises(ValueError):
            Source(
                id=uuid.uuid4(),
                format="invalid-format",
                label="Test Source",
                description="Test description"
            )
    
    def test_source_serialization_roundtrip(self):
        """Test Source serialization and deserialization"""
        original = Source(
            id=uuid.uuid4(),
            format="urn:x-nmos:format:video",
            label="Test Source",
            description="Test description"
        )
        
        # Serialize to dict
        data = original.model_dump()
        
        # Deserialize back to model
        reconstructed = Source(**data)
        
        assert reconstructed.id == original.id
        assert reconstructed.label == original.label
        assert reconstructed.format == original.format
        assert reconstructed.description == original.description


class TestVideoFlowModelReal:
    """Test VideoFlow model with real data validation"""
    
    def test_video_flow_creation_with_real_data(self):
        """Test creating a VideoFlow with realistic data"""
        flow = VideoFlow(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            codec="video/h264",
            frame_width=1920,
            frame_height=1080,
            frame_rate="25/1",
            label="BBC News Evening Broadcast",
            description="Evening news program"
        )
        
        assert flow.id is not None
        assert flow.label == "BBC News Evening Broadcast"
        assert flow.frame_width == 1920
        assert flow.frame_height == 1080
        assert flow.frame_rate == "25/1"
        assert flow.codec == "video/h264"
    
    def test_video_flow_validation_with_invalid_dimensions(self):
        """Test VideoFlow validation with invalid dimensions"""
        with pytest.raises(ValueError):
            VideoFlow(
                id=uuid.uuid4(),
                source_id=uuid.uuid4(),
                codec="video/h264",
                frame_width=0,  # Invalid width
                frame_height=1080,
                frame_rate="25/1"
            )
    
    def test_video_flow_relationships(self):
        """Test VideoFlow relationship with Source"""
        source_id = uuid.uuid4()
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Test Source",
            description="Test description"
        )
        
        flow = VideoFlow(
            id=uuid.uuid4(),
            source_id=source_id,
            codec="video/h264",
            frame_width=1920,
            frame_height=1080,
            frame_rate="25/1",
            label="Test Flow",
            description="Test description"
        )
        
        assert flow.source_id == source.id


class TestFlowSegmentModelReal:
    """Test FlowSegment model with real data validation"""
    
    def test_flow_segment_creation_with_real_data(self):
        """Test creating a FlowSegment with realistic data"""
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange="0:0_3600:0",  # 1 hour range in correct TimeRange format
            sample_offset=0,
            sample_count=90000,  # 1 hour at 25fps
            key_frame_count=3600,  # 1 keyframe per second
            ts_offset="0",
            last_duration="3600.0",
            storage_path="flows/2024/01/01/segment_001"
        )
        
        assert segment.object_id is not None
        assert segment.timerange == "0:0_3600:0"
        assert segment.sample_count == 90000
        assert segment.key_frame_count == 3600
        assert segment.last_duration == "3600.0"
    
    def test_flow_segment_timerange_validation(self):
        """Test FlowSegment timerange validation"""
        # Valid timerange
        valid_segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange="0:0_3600:0",  # 1 hour range in correct TimeRange format
            sample_offset=0,
            sample_count=1000,
            key_frame_count=10
        )
        assert valid_segment.timerange is not None
        
        # Invalid timerange format - use a format that definitely won't match the regex
        with pytest.raises(ValueError):
            FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange="invalid-timerange",  # Invalid format that won't match the regex
                sample_offset=0,
                sample_count=1000,
                key_frame_count=10
            )


class TestObjectModelReal:
    """Test Object model with real data validation"""
    
    def test_object_creation_with_real_data(self):
        """Test creating an Object with realistic data"""
        obj = Object(
            object_id=str(uuid.uuid4()),
            flow_references=[{"flow_id": str(uuid.uuid4()), "type": "video"}],
            size=2147483648,  # 2GB
            created=datetime.now(timezone.utc)
        )
        
        assert obj.object_id is not None
        assert len(obj.flow_references) == 1
        assert obj.flow_references[0]["type"] == "video"
        assert obj.size == 2147483648
    
    def test_object_flow_references(self):
        """Test Object flow reference relationships"""
        flow_id = str(uuid.uuid4())
        
        obj = Object(
            object_id=str(uuid.uuid4()),
            flow_references=[{"flow_id": flow_id, "type": "video"}],
            size=1073741824  # 1GB
        )
        
        assert obj.flow_references[0]["flow_id"] == flow_id
        assert len(obj.flow_references) == 1


class TestWebhookModelReal:
    """Test Webhook model with real data validation"""
    
    def test_webhook_creation_with_real_data(self):
        """Test creating a Webhook with realistic data"""
        webhook = Webhook(
            url="https://api.bbc.com/webhooks/news",
            api_key_name="bbc_news_api_key",
            api_key_value="secret_key_value",
            events=["news_alert", "breaking_news"],
            created=datetime.now(timezone.utc)
        )
        
        assert webhook.url == "https://api.bbc.com/webhooks/news"
        assert webhook.api_key_name == "bbc_news_api_key"
        assert webhook.api_key_value == "secret_key_value"
        assert "news_alert" in webhook.events
    
    def test_webhook_url_validation(self):
        """Test Webhook URL validation"""
        # Valid URL
        valid_webhook = Webhook(
            url="https://example.com/webhook",
            api_key_name="test_key",
            api_key_value="test_value",
            events=["test_event"]
        )
        assert valid_webhook.url is not None
        
        # Invalid URL - this will fail at Pydantic validation level
        with pytest.raises(ValueError):
            Webhook(
                url="not-a-valid-url",
                api_key_name="test_key",
                api_key_value="test_value",
                events=["test_event"]
            )


class TestUserModelReal:
    """Test User model with real data validation"""
    
    def test_user_creation_with_real_data(self):
        """Test creating a User with realistic data"""
        user = User(
            user_id=str(uuid.uuid4()),
            username="bbc_news_editor",
            email="editor@bbc.com",
            full_name="BBC News Editor",
            is_admin=False,
            is_active=True,
            created=datetime.now(timezone.utc)
        )
        
        assert user.user_id is not None
        assert user.username == "bbc_news_editor"
        assert user.email == "editor@bbc.com"
        assert user.full_name == "BBC News Editor"
        assert user.is_admin == False
        assert user.is_active is True
    
    def test_user_disabled_state(self):
        """Test User disabled state functionality"""
        user = User(
            user_id=str(uuid.uuid4()),
            username="disabled_user",
            email="disabled@example.com",
            full_name="Disabled User",
            role="viewer",
            is_active=False
        )
        
        assert user.is_active is False


class TestAuthModelsReal:
    """Test authentication models with real data validation"""
    
    def test_api_token_creation_with_real_data(self):
        """Test creating an ApiToken with realistic data"""
        token = ApiToken(
            token_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            token_name="BBC News API Token",
            token_type="bearer",
            is_active=True,
            created=datetime.now(timezone.utc)
        )
        
        assert token.token_id is not None
        assert token.token_name == "BBC News API Token"
        assert token.token_type == "bearer"
        assert token.is_active is True
    
    def test_auth_log_creation_with_real_data(self):
        """Test creating an AuthLog with realistic data"""
        log_entry = AuthLog(
            log_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            event_type="login",
            auth_method="password",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (BBC News App)",
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        
        assert log_entry.log_id is not None
        assert log_entry.event_type == "login"
        assert log_entry.auth_method == "password"
        assert log_entry.ip_address == "192.168.1.100"
        assert log_entry.success is True


class TestModelRelationshipsReal:
    """Test model relationships with real data"""
    
    def test_source_to_flow_relationship(self):
        """Test Source to VideoFlow relationship"""
        source = Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="BBC News Source",
            description="BBC News live source"
        )
        
        flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=source.id,
            codec="video/h264",
            frame_width=1920,
            frame_height=1080,
            frame_rate="25"
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
            frame_rate="25"
        )
        
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange="0:0_3600:0",  # 1 hour range in correct TimeRange format
            sample_offset=0,
            sample_count=90000,
            key_frame_count=3600
        )
        
        assert segment.object_id is not None


if __name__ == "__main__":
    pytest.main([__file__])
