#!/usr/bin/env python3
"""
Tests for TAMS Error Handling

Tests the error classes and handlers in src/vasttams/core/tams_errors.py
"""

import pytest
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.tams_errors import (
    TAMSErrorCode,
    TAMSErrorSeverity,
    TAMSComplianceError,
    TAMSValidationError,
    TAMSDataIntegrityError,
    TAMSStorageError,
    TAMSErrorHandler,
    get_tams_error_handler,
    handle_tams_error,
    log_tams_compliance_violation
)


class TestTAMSErrorCode:
    """Test TAMSErrorCode enum"""
    
    def test_error_codes_exist(self):
        """Test that all expected error codes exist"""
        assert TAMSErrorCode.INVALID_UUID_FORMAT == "INVALID_UUID_FORMAT"
        assert TAMSErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert TAMSErrorCode.UNAUTHORIZED_ACCESS == "UNAUTHORIZED_ACCESS"
        assert TAMSErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"
    
    def test_error_code_values(self):
        """Test error code string values"""
        assert isinstance(TAMSErrorCode.INVALID_UUID_FORMAT, str)
        assert TAMSErrorCode.INVALID_UUID_FORMAT.value == "INVALID_UUID_FORMAT"


class TestTAMSErrorSeverity:
    """Test TAMSErrorSeverity enum"""
    
    def test_severity_levels(self):
        """Test all severity levels exist"""
        assert TAMSErrorSeverity.LOW == "low"
        assert TAMSErrorSeverity.MEDIUM == "medium"
        assert TAMSErrorSeverity.HIGH == "high"
        assert TAMSErrorSeverity.CRITICAL == "critical"


class TestTAMSComplianceError:
    """Test TAMSComplianceError base class"""
    
    def test_compliance_error_creation(self):
        """Test creating a basic compliance error"""
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM
        )
        assert error.message == "Test error"
        assert error.error_code == TAMSErrorCode.VALIDATION_ERROR
        assert error.severity == TAMSErrorSeverity.MEDIUM
        assert error.details == {}
        assert error.field_path is None
        assert error.compliance_requirement is None
        assert isinstance(error.timestamp, datetime)
    
    def test_compliance_error_with_details(self):
        """Test creating compliance error with details"""
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.HIGH,
            details={"key": "value"},
            field_path="field.name",
            compliance_requirement="TAMS 8.0 Spec"
        )
        assert error.details == {"key": "value"}
        assert error.field_path == "field.name"
        assert error.compliance_requirement == "TAMS 8.0 Spec"
    
    def test_compliance_error_to_dict(self):
        """Test converting error to dictionary"""
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM,
            details={"key": "value"}
        )
        error_dict = error.to_dict()
        assert "error" in error_dict
        assert error_dict["error"]["code"] == "VALIDATION_ERROR"
        assert error_dict["error"]["message"] == "Test error"
        assert error_dict["error"]["severity"] == "medium"
        assert error_dict["error"]["details"] == {"key": "value"}
        assert "timestamp" in error_dict["error"]
    
    def test_compliance_error_inheritance(self):
        """Test that TAMSComplianceError is an Exception"""
        error = TAMSComplianceError(
            message="Test",
            error_code=TAMSErrorCode.VALIDATION_ERROR
        )
        assert isinstance(error, Exception)
        assert str(error) == "Test"


class TestTAMSValidationError:
    """Test TAMSValidationError class"""
    
    def test_validation_error_creation(self):
        """Test creating a validation error"""
        error = TAMSValidationError(
            message="Invalid value",
            field_path="source.id",
            invalid_value="not-a-uuid",
            expected_format="UUID"
        )
        assert error.message == "Invalid value"
        assert error.error_code == TAMSErrorCode.VALIDATION_ERROR
        assert error.severity == TAMSErrorSeverity.MEDIUM
        assert error.field_path == "source.id"
        assert error.details["invalid_value"] == "not-a-uuid"
        assert error.details["expected_format"] == "UUID"
        assert error.compliance_requirement == "TAMS API Specification - Field Validation"
    
    def test_validation_error_with_details(self):
        """Test validation error with additional details"""
        error = TAMSValidationError(
            message="Invalid value",
            field_path="source.id",
            invalid_value="bad",
            details={"extra": "info"}
        )
        assert error.details["invalid_value"] == "bad"
        assert error.details["extra"] == "info"


class TestTAMSDataIntegrityError:
    """Test TAMSDataIntegrityError class"""
    
    def test_data_integrity_error_creation(self):
        """Test creating a data integrity error"""
        error = TAMSDataIntegrityError(
            message="Referential integrity violation",
            entity_type="flow",
            entity_id="123"
        )
        assert error.message == "Referential integrity violation"
        assert error.error_code == TAMSErrorCode.REFERENTIAL_INTEGRITY_VIOLATION
        assert error.severity == TAMSErrorSeverity.HIGH
        assert error.details["entity_type"] == "flow"
        assert error.details["entity_id"] == "123"
        assert error.compliance_requirement == "TAMS API Specification - Data Integrity"


class TestTAMSStorageError:
    """Test TAMSStorageError class"""
    
    def test_storage_error_creation(self):
        """Test creating a storage error"""
        error = TAMSStorageError(
            message="Storage operation failed",
            storage_backend_id="backend-123",
            operation="upload"
        )
        assert error.message == "Storage operation failed"
        assert error.error_code == TAMSErrorCode.STORAGE_OPERATION_FAILED
        assert error.severity == TAMSErrorSeverity.HIGH
        assert error.details["storage_backend_id"] == "backend-123"
        assert error.details["operation"] == "upload"
        assert error.compliance_requirement == "TAMS API Specification - Storage Operations"


class TestTAMSErrorHandler:
    """Test TAMSErrorHandler class"""
    
    def test_error_handler_creation(self):
        """Test creating an error handler"""
        handler = TAMSErrorHandler()
        assert handler.logger is not None
        assert handler.error_counts == {}
        assert handler.compliance_violations == []
    
    def test_error_handler_with_custom_logger(self):
        """Test creating error handler with custom logger"""
        custom_logger = logging.getLogger("test")
        handler = TAMSErrorHandler(logger=custom_logger)
        assert handler.logger == custom_logger
    
    def test_handle_error(self):
        """Test handling an error"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM
        )
        result = handler.handle_error(error)
        assert result == error.to_dict()
        assert TAMSErrorCode.VALIDATION_ERROR in handler.error_counts
        assert handler.error_counts[TAMSErrorCode.VALIDATION_ERROR] == 1
    
    def test_handle_error_tracks_statistics(self):
        """Test that error handler tracks statistics"""
        handler = TAMSErrorHandler()
        error1 = TAMSComplianceError(
            message="Error 1",
            error_code=TAMSErrorCode.VALIDATION_ERROR
        )
        error2 = TAMSComplianceError(
            message="Error 2",
            error_code=TAMSErrorCode.VALIDATION_ERROR
        )
        handler.handle_error(error1)
        handler.handle_error(error2)
        assert handler.error_counts[TAMSErrorCode.VALIDATION_ERROR] == 2
    
    def test_handle_error_tracks_compliance_violations(self):
        """Test that high/critical errors are tracked as violations"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Critical error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.CRITICAL,
            details={"reason": "Test validation failure"}
        )
        handler.handle_error(error)
        assert len(handler.compliance_violations) == 1
        assert handler.compliance_violations[0]["error_code"] == "VALIDATION_ERROR"
        assert handler.compliance_violations[0]["severity"] == "critical"
    
    def test_get_error_statistics(self):
        """Test getting error statistics"""
        handler = TAMSErrorHandler()
        error1 = TAMSComplianceError(
            message="Error 1",
            error_code=TAMSErrorCode.VALIDATION_ERROR
        )
        error2 = TAMSComplianceError(
            message="Error 2",
            error_code=TAMSErrorCode.INTERNAL_ERROR
        )
        handler.handle_error(error1)
        handler.handle_error(error2)
        stats = handler.get_error_statistics()
        assert stats["total_errors"] == 2
        assert stats["error_counts"][TAMSErrorCode.VALIDATION_ERROR] == 1
        assert stats["error_counts"][TAMSErrorCode.INTERNAL_ERROR] == 1
    
    def test_get_compliance_report(self):
        """Test getting compliance violation report"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Critical error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.CRITICAL,
            details={"reason": "Test validation failure"}
        )
        handler.handle_error(error)
        report = handler.get_compliance_report()
        assert report["total_violations"] == 1
        assert "violations_by_severity" in report
        assert "violations_by_code" in report
        assert len(report["recent_violations"]) == 1


class TestGlobalErrorHandler:
    """Test global error handler functions"""
    
    def test_get_tams_error_handler(self):
        """Test getting global error handler"""
        handler1 = get_tams_error_handler()
        handler2 = get_tams_error_handler()
        # Should return the same instance
        assert handler1 is handler2
    
    def test_handle_tams_error(self):
        """Test global handle_tams_error function"""
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR
        )
        result = handle_tams_error(error)
        assert result == error.to_dict()
    
    def test_log_tams_compliance_violation(self):
        """Test log_tams_compliance_violation function"""
        log_tams_compliance_violation(
            message="Test violation",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM,
            details={"key": "value"}
        )
        # Should not raise an exception
        assert True
    
    def test_error_handler_logs_critical(self):
        """Test that error handler logs critical errors at critical level"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Critical error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.CRITICAL
        )
        with patch.object(handler.logger, 'critical') as mock_critical:
            handler.handle_error(error)
            mock_critical.assert_called_once()
    
    def test_error_handler_logs_high(self):
        """Test that error handler logs high severity errors at error level"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="High severity error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.HIGH
        )
        with patch.object(handler.logger, 'error') as mock_error:
            handler.handle_error(error)
            mock_error.assert_called_once()
    
    def test_error_handler_logs_medium(self):
        """Test that error handler logs medium severity errors at warning level"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Medium severity error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM
        )
        with patch.object(handler.logger, 'warning') as mock_warning:
            handler.handle_error(error)
            mock_warning.assert_called_once()
    
    def test_error_handler_logs_low(self):
        """Test that error handler logs low severity errors at info level"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Low severity error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.LOW
        )
        with patch.object(handler.logger, 'info') as mock_info:
            handler.handle_error(error)
            mock_info.assert_called_once()
    
    def test_error_handler_logs_with_field_path(self):
        """Test that error handler includes field_path in log message"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM,
            field_path="source.id"
        )
        with patch.object(handler.logger, 'warning') as mock_warning:
            handler.handle_error(error)
            call_args = mock_warning.call_args[0][0]
            assert "Field: source.id" in call_args
    
    def test_error_handler_logs_with_compliance_requirement(self):
        """Test that error handler includes compliance_requirement in log message"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Test error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM,
            compliance_requirement="TAMS 8.0 Spec"
        )
        with patch.object(handler.logger, 'warning') as mock_warning:
            handler.handle_error(error)
            call_args = mock_warning.call_args[0][0]
            assert "Requirement: TAMS 8.0 Spec" in call_args
    
    def test_error_handler_tracks_medium_severity_violations(self):
        """Test that medium severity errors are NOT tracked as violations"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Medium error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM
        )
        handler.handle_error(error)
        assert len(handler.compliance_violations) == 0
    
    def test_error_handler_tracks_low_severity_violations(self):
        """Test that low severity errors are NOT tracked as violations"""
        handler = TAMSErrorHandler()
        error = TAMSComplianceError(
            message="Low error",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.LOW
        )
        handler.handle_error(error)
        assert len(handler.compliance_violations) == 0
    
    def test_get_error_statistics_no_errors(self):
        """Test getting error statistics when no errors have been handled"""
        handler = TAMSErrorHandler()
        stats = handler.get_error_statistics()
        assert stats["total_errors"] == 0
        assert stats["error_counts"] == {}
        assert stats["compliance_violations_count"] == 0
        assert stats["last_compliance_violation"] is None
    
    def test_get_compliance_report_no_violations(self):
        """Test getting compliance report when no violations"""
        handler = TAMSErrorHandler()
        report = handler.get_compliance_report()
        assert report["total_violations"] == 0
        assert report["violations_by_severity"]["low"] == 0
        assert report["violations_by_severity"]["medium"] == 0
        assert report["violations_by_severity"]["high"] == 0
        assert report["violations_by_severity"]["critical"] == 0
        assert len(report["recent_violations"]) == 0
    
    def test_get_compliance_report_multiple_violations(self):
        """Test getting compliance report with multiple violations"""
        handler = TAMSErrorHandler()
        error1 = TAMSComplianceError(
            message="Error 1",
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.HIGH
        )
        error2 = TAMSComplianceError(
            message="Error 2",
            error_code=TAMSErrorCode.INTERNAL_ERROR,
            severity=TAMSErrorSeverity.CRITICAL
        )
        handler.handle_error(error1)
        handler.handle_error(error2)
        
        report = handler.get_compliance_report()
        assert report["total_violations"] == 2
        assert report["violations_by_severity"]["high"] == 1
        assert report["violations_by_severity"]["critical"] == 1
        assert len(report["recent_violations"]) == 2

