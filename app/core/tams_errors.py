"""TAMS-specific error handling and error codes"""

from typing import Dict, Any, Optional, List
from enum import Enum
import logging
from datetime import datetime


class TAMSErrorCode(str, Enum):
    """TAMS-specific error codes according to specification"""
    
    # Validation errors
    INVALID_UUID_FORMAT = "INVALID_UUID_FORMAT"
    INVALID_TIMESTAMP_FORMAT = "INVALID_TIMESTAMP_FORMAT"
    INVALID_CONTENT_FORMAT = "INVALID_CONTENT_FORMAT"
    INVALID_MIME_TYPE = "INVALID_MIME_TYPE"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
    INVALID_FLOW_COLLECTION = "INVALID_FLOW_COLLECTION"
    INVALID_SOURCE_COLLECTION = "INVALID_SOURCE_COLLECTION"
    
    # Data integrity errors
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"
    FIELD_TYPE_MISMATCH = "FIELD_TYPE_MISMATCH"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    REFERENTIAL_INTEGRITY_VIOLATION = "REFERENTIAL_INTEGRITY_VIOLATION"
    
    # Storage errors
    STORAGE_BACKEND_NOT_FOUND = "STORAGE_BACKEND_NOT_FOUND"
    STORAGE_OPERATION_FAILED = "STORAGE_OPERATION_FAILED"
    PRESIGNED_URL_GENERATION_FAILED = "PRESIGNED_URL_GENERATION_FAILED"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    FLOW_NOT_FOUND = "FLOW_NOT_FOUND"
    SEGMENT_NOT_FOUND = "SEGMENT_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    
    # Compliance errors
    TAMS_COMPLIANCE_VIOLATION = "TAMS_COMPLIANCE_VIOLATION"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    API_VERSION_MISMATCH = "API_VERSION_MISMATCH"
    
    # Authentication and authorization errors
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INVALID_API_KEY = "INVALID_API_KEY"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    # Rate limiting and throttling
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    THROTTLING_ACTIVE = "THROTTLING_ACTIVE"
    
    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class TAMSErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TAMSComplianceError(Exception):
    """Base exception for TAMS compliance violations"""
    
    def __init__(
        self,
        message: str,
        error_code: TAMSErrorCode,
        severity: TAMSErrorSeverity = TAMSErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        field_path: Optional[str] = None,
        compliance_requirement: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.details = details or {}
        self.field_path = field_path
        self.compliance_requirement = compliance_requirement
        self.timestamp = datetime.utcnow()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for API responses"""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "severity": self.severity.value,
                "timestamp": self.timestamp.isoformat(),
                "details": self.details,
                "field_path": self.field_path,
                "compliance_requirement": self.compliance_requirement
            }
        }


class TAMSValidationError(TAMSComplianceError):
    """Exception for TAMS validation errors"""
    
    def __init__(
        self,
        message: str,
        field_path: str,
        invalid_value: Any = None,
        expected_format: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=TAMSErrorCode.VALIDATION_ERROR,
            severity=TAMSErrorSeverity.MEDIUM,
            details={
                "invalid_value": str(invalid_value) if invalid_value is not None else None,
                "expected_format": expected_format,
                **(details or {})
            },
            field_path=field_path,
            compliance_requirement="TAMS API Specification - Field Validation"
        )


class TAMSDataIntegrityError(TAMSComplianceError):
    """Exception for TAMS data integrity errors"""
    
    def __init__(
        self,
        message: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=TAMSErrorCode.REFERENTIAL_INTEGRITY_VIOLATION,
            severity=TAMSErrorSeverity.HIGH,
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                **(details or {})
            },
            compliance_requirement="TAMS API Specification - Data Integrity"
        )


class TAMSStorageError(TAMSComplianceError):
    """Exception for TAMS storage-related errors"""
    
    def __init__(
        self,
        message: str,
        storage_backend_id: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=TAMSErrorCode.STORAGE_OPERATION_FAILED,
            severity=TAMSErrorSeverity.HIGH,
            details={
                "storage_backend_id": storage_backend_id,
                "operation": operation,
                **(details or {})
            },
            compliance_requirement="TAMS API Specification - Storage Operations"
        )


class TAMSErrorHandler:
    """Handler for TAMS-specific errors"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[TAMSErrorCode, int] = {}
        self.compliance_violations: List[Dict[str, Any]] = []
    
    def handle_error(self, error: TAMSComplianceError) -> Dict[str, Any]:
        """Handle a TAMS compliance error"""
        # Log the error
        self._log_error(error)
        
        # Track error statistics
        self._track_error(error)
        
        # Track compliance violations
        if error.severity in [TAMSErrorSeverity.HIGH, TAMSErrorSeverity.CRITICAL]:
            self._track_compliance_violation(error)
        
        # Return error response
        return error.to_dict()
    
    def _log_error(self, error: TAMSComplianceError):
        """Log the error with appropriate level"""
        log_message = f"TAMS Compliance Error: {error.error_code.value} - {error.message}"
        
        if error.field_path:
            log_message += f" (Field: {error.field_path})"
        
        if error.compliance_requirement:
            log_message += f" (Requirement: {error.compliance_requirement})"
        
        if error.severity == TAMSErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra={"error_details": error.details})
        elif error.severity == TAMSErrorSeverity.HIGH:
            self.logger.error(log_message, extra={"error_details": error.details})
        elif error.severity == TAMSErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={"error_details": error.details})
        else:
            self.logger.info(log_message, extra={"error_details": error.details})
    
    def _track_error(self, error: TAMSComplianceError):
        """Track error statistics"""
        self.error_counts[error.error_code] = self.error_counts.get(error.error_code, 0) + 1
    
    def _track_compliance_violation(self, error: TAMSComplianceError):
        """Track compliance violations for audit purposes"""
        violation = {
            "timestamp": error.timestamp.isoformat(),
            "error_code": error.error_code.value,
            "severity": error.severity.value,
            "message": error.message,
            "field_path": error.field_path,
            "compliance_requirement": error.compliance_requirement,
            "details": error.details
        }
        self.compliance_violations.append(violation)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts,
            "compliance_violations_count": len(self.compliance_violations),
            "last_compliance_violation": self.compliance_violations[-1] if self.compliance_violations else None
        }
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Get compliance violation report"""
        return {
            "total_violations": len(self.compliance_violations),
            "violations_by_severity": {
                severity.value: len([v for v in self.compliance_violations if v["severity"] == severity.value])
                for severity in TAMSErrorSeverity
            },
            "violations_by_code": {
                code.value: len([v for v in self.compliance_violations if v["error_code"] == code.value])
                for code in TAMSErrorCode
            },
            "recent_violations": self.compliance_violations[-10:] if self.compliance_violations else []
        }


# Global error handler instance
_tams_error_handler = None


def get_tams_error_handler() -> TAMSErrorHandler:
    """Get global TAMS error handler"""
    global _tams_error_handler
    if _tams_error_handler is None:
        _tams_error_handler = TAMSErrorHandler()
    return _tams_error_handler


def handle_tams_error(error: TAMSComplianceError) -> Dict[str, Any]:
    """Handle a TAMS compliance error using the global handler"""
    return get_tams_error_handler().handle_error(error)


def log_tams_compliance_violation(
    message: str,
    error_code: TAMSErrorCode,
    severity: TAMSErrorSeverity = TAMSErrorSeverity.MEDIUM,
    details: Optional[Dict[str, Any]] = None,
    field_path: Optional[str] = None,
    compliance_requirement: Optional[str] = None
):
    """Log a TAMS compliance violation"""
    error = TAMSComplianceError(
        message=message,
        error_code=error_code,
        severity=severity,
        details=details,
        field_path=field_path,
        compliance_requirement=compliance_requirement
    )
    handle_tams_error(error)
