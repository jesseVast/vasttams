"""TAMS-specific logging configuration and structured logging"""

import logging
import logging.config
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys
from app.core.config import get_settings


class TAMSStructuredFormatter(logging.Formatter):
    """Structured formatter for TAMS logging with JSON output"""
    
    def __init__(self, include_timestamp: bool = True, include_level: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if self.include_timestamp:
            log_entry["timestamp"] = datetime.utcnow().isoformat()
        
        if self.include_level:
            log_entry["level"] = record.levelname
        
        # Add extra fields if present
        if hasattr(record, 'tams_compliance_data'):
            log_entry["tams_compliance"] = record.tams_compliance_data
        
        if hasattr(record, 'error_details'):
            log_entry["error_details"] = record.error_details
        
        if hasattr(record, 'user_context'):
            log_entry["user_context"] = record.user_context
        
        if hasattr(record, 'api_context'):
            log_entry["api_context"] = record.api_context
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, default=str)


class TAMSComplianceFilter(logging.Filter):
    """Filter for TAMS compliance-related log messages"""
    
    def __init__(self, name: str = "", compliance_only: bool = False):
        super().__init__(name)
        self.compliance_only = compliance_only
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on compliance criteria"""
        if self.compliance_only:
            # Only show compliance-related messages
            return (
                hasattr(record, 'tams_compliance_data') or
                'tams' in record.name.lower() or
                'compliance' in record.getMessage().lower()
            )
        return True


class TAMSLoggingConfig:
    """Configuration for TAMS-specific logging"""
    
    def __init__(self):
        self.settings = get_settings()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
    
    def setup_logging(self):
        """Setup TAMS logging configuration"""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "tams_structured": {
                    "()": TAMSStructuredFormatter,
                    "include_timestamp": True,
                    "include_level": True
                },
                "tams_simple": {
                    "()": TAMSStructuredFormatter,
                    "include_timestamp": False,
                    "include_level": False
                },
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "filters": {
                "tams_compliance": {
                    "()": TAMSComplianceFilter,
                    "compliance_only": False
                },
                "tams_compliance_only": {
                    "()": TAMSComplianceFilter,
                    "compliance_only": True
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "tams_structured",
                    "stream": sys.stdout,
                    "filters": ["tams_compliance"]
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "tams_structured",
                    "filename": str(self.log_dir / "tams.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "filters": ["tams_compliance"]
                },
                "compliance_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "tams_structured",
                    "filename": str(self.log_dir / "tams_compliance.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "filters": ["tams_compliance_only"]
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "tams_structured",
                    "filename": str(self.log_dir / "tams_errors.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5
                }
            },
            "loggers": {
                "": {  # Root logger
                    "level": "INFO",
                    "handlers": ["console", "file"]
                },
                "app": {  # Application logger
                    "level": "DEBUG",
                    "handlers": ["console", "file", "error_file"],
                    "propagate": False
                },
                "app.api": {  # API logger
                    "level": "INFO",
                    "handlers": ["console", "file", "error_file"],
                    "propagate": False
                },
                "app.storage": {  # Storage logger
                    "level": "INFO",
                    "handlers": ["console", "file", "error_file"],
                    "propagate": False
                },
                "tams.compliance": {  # TAMS compliance logger
                    "level": "INFO",
                    "handlers": ["console", "compliance_file", "error_file"],
                    "propagate": False
                },
                "tams.validation": {  # TAMS validation logger
                    "level": "INFO",
                    "handlers": ["console", "compliance_file", "error_file"],
                    "propagate": False
                },
                "tams.storage": {  # TAMS storage logger
                    "level": "INFO",
                    "handlers": ["console", "file", "error_file"],
                    "propagate": False
                }
            }
        }
        
        # Apply configuration
        logging.config.dictConfig(config)
        
        # Set log levels based on settings
        if self.settings.debug:
            logging.getLogger("app").setLevel(logging.DEBUG)
        
        if self.settings.tams_audit_logging:
            logging.getLogger("tams.compliance").setLevel(logging.INFO)
        else:
            logging.getLogger("tams.compliance").setLevel(logging.WARNING)
        
        # Log configuration setup
        logger = logging.getLogger("app.core.tams_logging")
        logger.info("TAMS logging configuration initialized", extra={
            "tams_compliance_data": {
                "feature": "logging_setup",
                "compliance_level": "full"
            }
        })


def get_tams_logger(name: str) -> logging.Logger:
    """Get a TAMS-specific logger"""
    return logging.getLogger(f"tams.{name}")


def log_tams_compliance_event(
    logger: logging.Logger,
    event_type: str,
    compliance_status: str,
    details: Optional[Dict[str, Any]] = None,
    severity: str = "info"
):
    """Log a TAMS compliance event with structured data"""
    extra_data = {
        "tams_compliance_data": {
            "event_type": event_type,
            "compliance_status": compliance_status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
    }
    
    if severity.lower() == "error":
        logger.error(f"TAMS Compliance Event: {event_type} - {compliance_status}", extra=extra_data)
    elif severity.lower() == "warning":
        logger.warning(f"TAMS Compliance Event: {event_type} - {compliance_status}", extra=extra_data)
    elif severity.lower() == "debug":
        logger.debug(f"TAMS Compliance Event: {event_type} - {compliance_status}", extra=extra_data)
    else:
        logger.info(f"TAMS Compliance Event: {event_type} - {compliance_status}", extra=extra_data)


def log_tams_validation_result(
    logger: logging.Logger,
    field_path: str,
    validation_result: bool,
    validation_rule: str,
    details: Optional[Dict[str, Any]] = None
):
    """Log a TAMS validation result"""
    status = "PASSED" if validation_result else "FAILED"
    level = "info" if validation_result else "warning"
    
    extra_data = {
        "tams_compliance_data": {
            "event_type": "field_validation",
            "field_path": field_path,
            "validation_result": validation_result,
            "validation_rule": validation_rule,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
    }
    
    if level == "warning":
        logger.warning(f"TAMS Validation: {field_path} - {status} ({validation_rule})", extra=extra_data)
    else:
        logger.info(f"TAMS Validation: {field_path} - {status} ({validation_rule})", extra=extra_data)


def log_tams_api_request(
    logger: logging.Logger,
    endpoint: str,
    method: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log a TAMS API request"""
    extra_data = {
        "api_context": {
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
    }
    
    logger.info(f"TAMS API Request: {method} {endpoint}", extra=extra_data)


def log_tams_storage_operation(
    logger: logging.Logger,
    operation: str,
    storage_backend_id: str,
    entity_type: str,
    entity_id: str,
    success: bool,
    details: Optional[Dict[str, Any]] = None
):
    """Log a TAMS storage operation"""
    status = "SUCCESS" if success else "FAILED"
    level = "info" if success else "error"
    
    extra_data = {
        "tams_compliance_data": {
            "event_type": "storage_operation",
            "operation": operation,
            "storage_backend_id": storage_backend_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
    }
    
    if level == "error":
        logger.error(f"TAMS Storage Operation: {operation} - {status}", extra=extra_data)
    else:
        logger.info(f"TAMS Storage Operation: {operation} - {status}", extra=extra_data)


# Initialize logging when module is imported
_tams_logging_config = TAMSLoggingConfig()
_tams_logging_config.setup_logging()
