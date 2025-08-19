"""TAMS API Compliance Tests

This module contains comprehensive tests to ensure the application
fully complies with the TAMS API specification.
"""

import pytest
import uuid
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.models import (
    Object, Source, FlowSegment, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
    GetUrl, Webhook, WebhookPost, Service, StorageBackend, Tags, CollectionItem
)
from app.core.tams_errors import (
    TAMSErrorCode, TAMSErrorSeverity, TAMSComplianceError, TAMSValidationError,
    TAMSDataIntegrityError, TAMSStorageError
)
from app.core.tams_logging import get_tams_logger
from app.models.models import validate_tams_uuid, validate_tams_timestamp, validate_content_format, validate_mime_type


class TestTAMSCompliance:
    """Test TAMS API compliance for all models"""
    
    def setup_method(self):
        """Set up test data"""
        self.valid_uuid = str(uuid.uuid4())
        self.valid_uuid_2 = str(uuid.uuid4())
        self.valid_uuid_3 = str(uuid.uuid4())
        self.valid_video_format = "urn:x-nmos:format:video"
        self.valid_audio_format = "urn:x-nmos:format:audio"
        self.valid_data_format = "urn:x-nmos:format:data"
        self.valid_image_format = "urn:x-tam:format:image"
        self.valid_multi_format = "urn:x-nmos:format:multi"

    def test_object_model_tams_compliance(self):
        """Test Object model TAMS compliance"""
        # Test valid Object creation
        obj = Object(
            id=self.valid_uuid,
            referenced_by_flows=[self.valid_uuid_2],
            first_referenced_by_flow=self.valid_uuid_2,
            size=1024,
            created=datetime.now(timezone.utc)
        )
    
        assert obj.id == self.valid_uuid
        assert obj.referenced_by_flows == [self.valid_uuid_2]
        assert obj.first_referenced_by_flow == self.valid_uuid_2
        assert obj.size == 1024
        assert obj.created is not None
    
        # Test validation errors - expect Pydantic ValidationError, not ValueError
        with pytest.raises(ValidationError):
            Object(
                id="",
                referenced_by_flows=[self.valid_uuid_2]
            )
    
        with pytest.raises(ValidationError):
            Object(
                id=self.valid_uuid,
                referenced_by_flows=[]
            )
    
        with pytest.raises(ValidationError):
            Object(
                id=self.valid_uuid,
                referenced_by_flows=[self.valid_uuid_2],
                size=-1
            )

    def test_source_model_tams_compliance(self):
        """Test Source model TAMS compliance"""
        # Test valid Source creation
        source = Source(
            id=uuid.uuid4(),
            format=self.valid_video_format,
            label="Test Source",
            description="Test Description",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            tags=Tags({"test": "value"}),
            source_collection=[
                CollectionItem(id=uuid.uuid4(), label="Collection 1")
            ],
            collected_by=[uuid.uuid4()]
        )

        assert source.id is not None
        assert source.format == self.valid_video_format
        assert source.label == "Test Source"
        assert source.description == "Test Description"
        assert source.created_by == "test_user"
        assert source.updated_by == "test_user"
        assert source.created is not None
        assert source.updated is not None
        assert source.tags is not None
        assert source.source_collection is not None
        assert source.collected_by is not None

    def test_flow_segment_model_tams_compliance(self):
        """Test FlowSegment model TAMS compliance"""
        # Test valid FlowSegment creation
        segment = FlowSegment(
            id=self.valid_uuid,
            timerange="[0:0_10:0)",
            ts_offset="0:0",
            last_duration="0:0",
            sample_offset=0,
            sample_count=100,
            key_frame_count=5,
            storage_path="/path/to/segment"
        )
    
        assert segment.object_id == self.valid_uuid
        assert segment.timerange == "[0:0_10:0)"
        assert segment.storage_path == "/path/to/segment"
    
        # Test timerange validation - expect Pydantic ValidationError, not ValueError
        with pytest.raises(ValidationError):
            FlowSegment(
                object_id=self.valid_uuid,
                timerange=123  # Invalid type
            )

    def test_video_flow_model_tams_compliance(self):
        """Test VideoFlow model TAMS compliance"""
        # Test valid VideoFlow creation
        flow = VideoFlow(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            format=self.valid_video_format,
            codec="video/h264",
            label="Test Video Flow",
            description="Test Description",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            segments_updated=datetime.now(timezone.utc),
            metadata_version="1.0",
            generation=0,
            segment_duration={"numerator": 1, "denominator": 30},
            frame_width=1920,
            frame_height=1080,
            frame_rate="30:1",
            container="video/mp4"
        )

        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == self.valid_video_format
        assert flow.codec == "video/h264"
        assert flow.label == "Test Video Flow"
        assert flow.metadata_updated is not None
        assert flow.segments_updated is not None
        assert flow.metadata_version == "1.0"
        assert flow.generation == 0
        assert flow.segment_duration == {"numerator": 1, "denominator": 30}

    def test_audio_flow_model_tams_compliance(self):
        """Test AudioFlow model TAMS compliance"""
        # Test valid AudioFlow creation
        flow = AudioFlow(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            format=self.valid_audio_format,
            codec="audio/aac",
            label="Test Audio Flow",
            description="Test Description",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            segments_updated=datetime.now(timezone.utc),
            metadata_version="1.0",
            generation=0,
            segment_duration={"numerator": 1, "denominator": 30},
            sample_rate=48000,
            bits_per_sample=16,
            channels=2,
            container="audio/aac"
        )

        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == self.valid_audio_format
        assert flow.codec == "audio/aac"
        assert flow.label == "Test Audio Flow"
        assert flow.metadata_updated is not None
        assert flow.segments_updated is not None
        assert flow.metadata_version == "1.0"
        assert flow.generation == 0
        assert flow.segment_duration == {"numerator": 1, "denominator": 30}

    def test_data_flow_model_tams_compliance(self):
        """Test DataFlow model TAMS compliance"""
        # Test valid DataFlow creation
        flow = DataFlow(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            format=self.valid_data_format,
            codec="application/json",
            label="Test Data Flow",
            description="Test Description",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            segments_updated=datetime.now(timezone.utc),
            metadata_version="1.0",
            generation=0,
            segment_duration={"numerator": 1, "denominator": 1},
            container="application/json"
        )

        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == self.valid_data_format
        assert flow.codec == "application/json"
        assert flow.label == "Test Data Flow"
        assert flow.metadata_updated is not None
        assert flow.segments_updated is not None
        assert flow.metadata_version == "1.0"
        assert flow.generation == 0
        assert flow.segment_duration == {"numerator": 1, "denominator": 1}

    def test_image_flow_model_tams_compliance(self):
        """Test ImageFlow model TAMS compliance"""
        # Test valid ImageFlow creation
        flow = ImageFlow(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            format=self.valid_image_format,
            codec="image/jpeg",
            label="Test Image Flow",
            description="Test Description",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            segments_updated=datetime.now(timezone.utc),
            metadata_version="1.0",
            generation=0,
            segment_duration={"numerator": 1, "denominator": 1},
            frame_width=1920,
            frame_height=1080,
            container="image/jpeg"
        )

        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == self.valid_image_format
        assert flow.codec == "image/jpeg"
        assert flow.label == "Test Image Flow"
        assert flow.metadata_updated is not None
        assert flow.segments_updated is not None
        assert flow.metadata_version == "1.0"
        assert flow.generation == 0
        assert flow.segment_duration == {"numerator": 1, "denominator": 1}

    def test_multi_flow_model_tams_compliance(self):
        """Test MultiFlow model TAMS compliance"""
        # Test valid MultiFlow creation
        flow = MultiFlow(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            format=self.valid_multi_format,
            codec="multipart/mixed",
            label="Test Multi Flow",
            description="Test Description",
            created_by="test_user",
            updated_by="test_user",
            created=datetime.now(timezone.utc),
            metadata_updated=datetime.now(timezone.utc),
            segments_updated=datetime.now(timezone.utc),
            metadata_version="1.0",
            generation=0,
            segment_duration={"numerator": 1, "denominator": 30},
            flow_collection=[self.valid_uuid_2, self.valid_uuid_3],
            collected_by=[self.valid_uuid],
            container="multipart/mixed"
        )

        assert flow.id is not None
        assert flow.source_id is not None
        assert flow.format == self.valid_multi_format
        assert flow.codec == "multipart/mixed"
        assert flow.label == "Test Multi Flow"
        assert flow.metadata_updated is not None
        assert flow.segments_updated is not None
        assert flow.metadata_version == "1.0"
        assert flow.generation == 0
        assert flow.segment_duration == {"numerator": 1, "denominator": 30}
        assert flow.flow_collection == [self.valid_uuid_2, self.valid_uuid_3]
        assert flow.collected_by == [self.valid_uuid]

    def test_get_url_model_tams_compliance(self):
        """Test GetUrl model TAMS compliance"""
        # Test valid GetUrl creation
        get_url = GetUrl(
            store_type="http_object_store",
            provider="aws",
            region="us-east-1",
            availability_zone="us-east-1a",
            store_product="S3",
            url="https://example.com/segment.mp4",
            storage_id=self.valid_uuid,
            presigned=True,
            label="primary",
            controlled=True
        )
    
        assert get_url.store_type == "http_object_store"
        assert get_url.provider == "aws"
        assert get_url.region == "us-east-1"
        assert get_url.url == "https://example.com/segment.mp4"
        assert get_url.storage_id == self.valid_uuid
        assert get_url.presigned is True
        assert get_url.controlled is True
    
        # Test UUID validation - expect Pydantic ValidationError, not ValueError
        with pytest.raises(ValidationError):
            GetUrl(
                store_type="http_object_store",
                provider="aws",
                region="us-east-1",
                store_product="S3",
                url="https://example.com/segment.mp4",
                storage_id="invalid-uuid"
            )

    def test_webhook_model_tams_compliance(self):
        """Test Webhook model TAMS compliance"""
        # Test valid Webhook creation
        webhook = Webhook(
            url="https://example.com/webhook",
            api_key_name="X-API-Key",
            api_key_value="secret-key",
            events=["flow.created", "flow.updated"],
            flow_ids=[self.valid_uuid],
            source_ids=[self.valid_uuid_2],
            flow_collected_by_ids=[self.valid_uuid_3],
            source_collected_by_ids=[self.valid_uuid],
            accept_get_urls=["primary", "secondary"],
            accept_storage_ids=[self.valid_uuid_2],
            presigned=True,
            verbose_storage=True,
            owner_id="owner123",
            created_by="creator123",
            created=datetime.now(timezone.utc)
        )

        assert webhook.url == "https://example.com/webhook"
        assert webhook.api_key_name == "X-API-Key"
        assert webhook.api_key_value == "secret-key"
        assert webhook.events == ["flow.created", "flow.updated"]
        assert webhook.flow_ids == [self.valid_uuid]
        assert webhook.source_ids == [self.valid_uuid_2]
        assert webhook.presigned is True
        assert webhook.verbose_storage is True

    def test_webhook_post_model_tams_compliance(self):
        """Test WebhookPost model TAMS compliance"""
        # Test valid WebhookPost creation
        webhook_post = WebhookPost(
            url="https://example.com/webhook",
            api_key_name="X-API-Key",
            api_key_value="secret-key",
            events=["flow.created", "flow.updated"],
            flow_ids=[self.valid_uuid],
            source_ids=[self.valid_uuid_2],
            flow_collected_by_ids=[self.valid_uuid_3],
            source_collected_by_ids=[self.valid_uuid],
            accept_get_urls=["primary", "secondary"],
            accept_storage_ids=[self.valid_uuid_2],
            presigned=True,
            verbose_storage=True,
            owner_id="owner123",
            created_by="creator123"
        )

        assert webhook_post.url == "https://example.com/webhook"
        assert webhook_post.api_key_name == "X-API-Key"
        assert webhook_post.api_key_value == "secret-key"
        assert webhook_post.events == ["flow.created", "flow.updated"]

    def test_service_model_tams_compliance(self):
        """Test Service model TAMS compliance"""
        # Test valid Service creation
        service = Service(
            name="TAMS Service",
            description="Test TAMS Service",
            type="urn:x-tams:service:api",
            api_version="7.0",
            service_version="1.0.0",
            media_store={"type": "http_object_store"},
            event_stream_mechanisms=[
                {"name": "SSE", "description": "Server-Sent Events"}
            ]
        )

        assert service.name == "TAMS Service"
        assert service.type == "urn:x-tams:service:api"
        assert service.api_version == "7.0"
        assert service.service_version == "1.0.0"

    def test_storage_backend_model_tams_compliance(self):
        """Test StorageBackend model TAMS compliance"""
        # Test valid StorageBackend creation
        backend = StorageBackend(
            id=self.valid_uuid,
            store_type="http_object_store",
            provider="aws",
            store_product="S3",
            region="us-east-1",
            availability_zone="us-east-1a",
            label="Primary Storage",
            default_storage=True
        )
    
        assert backend.id == self.valid_uuid
        assert backend.store_type == "http_object_store"
        assert backend.provider == "aws"
        assert backend.store_product == "S3"
        assert backend.region == "us-east-1"
        assert backend.default_storage is True
    
        # Test UUID validation - expect Pydantic ValidationError, not ValueError
        with pytest.raises(ValidationError):
            StorageBackend(
                id="invalid-uuid",
                store_type="http_object_store",
                provider="aws",
                store_product="S3"
            )

    def test_tags_model_tams_compliance(self):
        """Test Tags model TAMS compliance"""
        # Test valid Tags creation
        tags_data = {
            "environment": "production",
            "version": "1.0.0",
            "owner": "team-a"
        }
        tags = Tags(tags_data)
    
        assert tags["environment"] == "production"
        assert tags["version"] == "1.0.0"
        assert tags["owner"] == "team-a"
        # Tags is a dict-like object, check if it has the expected items
        assert "environment" in tags
        assert "version" in tags
        assert "owner" in tags

    def test_collection_item_model_tams_compliance(self):
        """Test CollectionItem model TAMS compliance"""
        # Test valid CollectionItem creation
        item = CollectionItem(
            id=uuid.uuid4(),
            label="Test Collection"
        )

        assert item.id is not None
        assert item.label == "Test Collection"

    def test_tams_error_codes(self):
        """Test TAMSErrorCode enum"""
        assert TAMSErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert TAMSErrorCode.REFERENTIAL_INTEGRITY_VIOLATION == "REFERENTIAL_INTEGRITY_VIOLATION"
        assert TAMSErrorCode.STORAGE_OPERATION_FAILED == "STORAGE_OPERATION_FAILED"
        assert TAMSErrorCode.TAMS_COMPLIANCE_VIOLATION == "TAMS_COMPLIANCE_VIOLATION"

    def test_tams_error_severity(self):
        """Test TAMSErrorSeverity enum"""
        assert TAMSErrorSeverity.LOW == "low"
        assert TAMSErrorSeverity.MEDIUM == "medium"
        assert TAMSErrorSeverity.HIGH == "high"
        assert TAMSErrorSeverity.CRITICAL == "critical"

    def test_tams_compliance_error(self):
        """Test TAMSComplianceError creation"""
        error = TAMSComplianceError(
            message="Compliance violation detected",
            error_code=TAMSErrorCode.TAMS_COMPLIANCE_VIOLATION,
            severity=TAMSErrorSeverity.HIGH
        )

        assert error.message == "Compliance violation detected"
        assert error.error_code == TAMSErrorCode.TAMS_COMPLIANCE_VIOLATION
        assert error.severity == TAMSErrorSeverity.HIGH

    def test_tams_validation_error(self):
        """Test TAMSValidationError creation"""
        error = TAMSValidationError(
            message="Invalid field value",
            field_path="object.id",
            invalid_value="invalid-uuid",
            expected_format="Valid UUID format"
        )

        assert error.message == "Invalid field value"
        assert error.field_path == "object.id"
        assert error.error_code == TAMSErrorCode.VALIDATION_ERROR
        assert error.severity == TAMSErrorSeverity.MEDIUM

    def test_tams_data_integrity_error(self):
        """Test TAMSDataIntegrityError creation"""
        error = TAMSDataIntegrityError(
            message="Referential integrity violation",
            entity_type="Flow",
            entity_id="flow-123"
        )

        assert error.message == "Referential integrity violation"
        assert error.error_code == TAMSErrorCode.REFERENTIAL_INTEGRITY_VIOLATION
        assert error.severity == TAMSErrorSeverity.HIGH

    def test_tams_storage_error(self):
        """Test TAMSStorageError creation"""
        error = TAMSStorageError(
            message="Storage operation failed",
            storage_backend_id="backend-123",
            operation="upload"
        )

        assert error.message == "Storage operation failed"
        assert error.error_code == TAMSErrorCode.STORAGE_OPERATION_FAILED
        assert error.severity == TAMSErrorSeverity.HIGH

    def test_tams_logging(self):
        """Test TAMS logging functionality"""
        logger = get_tams_logger("test_logger")
        assert logger is not None
        assert "tams.test_logger" in logger.name


class TestTAMSValidationFunctions:
    """Test individual TAMS validation functions"""
    
    def test_validate_tams_uuid(self):
        """Test TAMS UUID validation"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        invalid_uuid = "invalid-uuid"
        
        # Validation functions return the input value if valid, raise ValueError if invalid
        assert validate_tams_uuid(valid_uuid) == valid_uuid
        with pytest.raises(ValueError):
            validate_tams_uuid(invalid_uuid)

    def test_validate_tams_timestamp(self):
        """Test TAMS timestamp validation"""
        valid_timestamp = "2023-01-01T00:00:00Z"
        invalid_timestamp = "invalid-timestamp"
        
        # Validation functions return the input value if valid, raise ValueError if invalid
        assert validate_tams_timestamp(valid_timestamp) == valid_timestamp
        with pytest.raises(ValueError):
            validate_tams_timestamp(invalid_timestamp)

    def test_validate_content_format(self):
        """Test content format validation"""
        valid_format = "urn:x-nmos:format:video"
        invalid_format = "invalid/format"
        
        # Validation functions return the input value if valid, raise ValueError if invalid
        assert validate_content_format(valid_format) == valid_format
        with pytest.raises(ValueError):
            validate_content_format(invalid_format)

    def test_validate_mime_type(self):
        """Test MIME type validation"""
        valid_mime = "application/json"
        invalid_mime = "invalid-mime"
        
        # Validation functions return the input value if valid, raise ValueError if invalid
        assert validate_mime_type(valid_mime) == valid_mime
        with pytest.raises(ValueError):
            validate_mime_type(invalid_mime)


if __name__ == "__main__":
    pytest.main([__file__])
