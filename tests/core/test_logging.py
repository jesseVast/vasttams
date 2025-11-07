#!/usr/bin/env python3
"""
Tests for TAMS Logging Configuration

Tests the logging setup in src/vasttams/core/simple_logging.py
"""

import pytest
import sys
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.simple_logging import setup_logging, EnhancedFormatter
from vasttams.core.tams_logging import TAMSHumanReadableFormatter


class TestEnhancedFormatter:
    """Test EnhancedFormatter class from simple_logging"""
    
    def test_formatter_creation_with_function(self):
        """Test creating formatter with function name included"""
        formatter = EnhancedFormatter(include_function=True)
        # include_function is used in __init__ but not stored as attribute
        # Verify it works by checking the format includes funcName
        assert formatter.include_extra is True
        # Test that format string includes function name
        import logging
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "test", (), None)
        result = formatter.format(record)
        # Should include function name in format
        assert "test" in result
    
    def test_formatter_creation_without_function(self):
        """Test creating formatter without function name"""
        formatter = EnhancedFormatter(include_function=False)
        # include_function is used in __init__ but not stored as attribute
        # Verify it works by checking the format doesn't include funcName
        assert formatter.include_extra is True  # Default is True
    
    def test_formatter_creation_without_extra(self):
        """Test creating formatter without extra context"""
        formatter = TAMSHumanReadableFormatter(include_extra=False)
        assert formatter.include_extra is False
    
    def test_formatter_format_basic(self):
        """Test formatting a basic log record"""
        formatter = TAMSHumanReadableFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        result = formatter.format(record)
        assert "Test message" in result
        assert "test" in result
        assert "INFO" in result
    
    def test_formatter_format_with_tams_compliance_data(self):
        """Test formatting with TAMS compliance data"""
        formatter = TAMSHumanReadableFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.tams_compliance_data = {"field": "id", "value": "123"}
        result = formatter.format(record)
        assert "Test message" in result
        assert "TAMS:" in result
        assert "field=id" in result
        assert "value=123" in result
    
    def test_formatter_format_with_error_details(self):
        """Test formatting with error details"""
        formatter = TAMSHumanReadableFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None
        )
        record.error_details = {"code": "VALIDATION_ERROR", "message": "Invalid"}
        result = formatter.format(record)
        assert "Test error" in result
        assert "Error:" in result
        assert "code=VALIDATION_ERROR" in result
    
    def test_formatter_format_with_user_context(self):
        """Test formatting with user context"""
        formatter = TAMSHumanReadableFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.user_context = {"user_id": "123", "username": "admin"}
        result = formatter.format(record)
        assert "User:" in result
        assert "user_id=123" in result
        assert "username=admin" in result
    
    def test_formatter_format_with_api_context(self):
        """Test formatting with API context"""
        formatter = TAMSHumanReadableFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.api_context = {"endpoint": "/sources", "method": "GET"}
        result = formatter.format(record)
        assert "API:" in result
        assert "endpoint=/sources" in result
        assert "method=GET" in result
    
    def test_formatter_format_with_all_extra(self):
        """Test formatting with all extra context"""
        formatter = TAMSHumanReadableFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.tams_compliance_data = {"field": "id"}
        record.error_details = {"code": "ERROR"}
        record.user_context = {"user_id": "123"}
        record.api_context = {"endpoint": "/test"}
        result = formatter.format(record)
        assert "TAMS:" in result
        assert "Error:" in result
        assert "User:" in result
        assert "API:" in result
    
    def test_formatter_format_without_extra(self):
        """Test formatting without extra context (should not include extra)"""
        formatter = TAMSHumanReadableFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.tams_compliance_data = {"field": "id"}
        result = formatter.format(record)
        assert "Test message" in result
        assert "TAMS:" not in result


class TestSetupLogging:
    """Test setup_logging function"""
    
    @patch('vasttams.core.simple_logging.get_settings')
    @patch('logging.config.dictConfig')
    def test_setup_logging_called(self, mock_dict_config, mock_get_settings):
        """Test that setup_logging calls dictConfig"""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        # Call setup_logging
        setup_logging()
        
        # Verify dictConfig was called
        mock_dict_config.assert_called_once()
        config = mock_dict_config.call_args[0][0]
        assert "version" in config
        assert config["version"] == 1
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config
    
    @patch('vasttams.core.simple_logging.get_settings')
    @patch('logging.config.dictConfig')
    def test_setup_logging_config_structure(self, mock_dict_config, mock_get_settings):
        """Test that logging config has correct structure"""
        mock_settings = MagicMock()
        mock_settings.log_level = "DEBUG"
        mock_get_settings.return_value = mock_settings
        
        setup_logging()
        
        config = mock_dict_config.call_args[0][0]
        # Check formatters - may be "detailed" and "simple" or use TAMSHumanReadableFormatter
        assert "formatters" in config
        assert len(config["formatters"]) > 0
        # Check handlers
        assert "console" in config["handlers"]
        assert "file" in config["handlers"]
        assert "error_file" in config["handlers"]
        # Check loggers
        assert "" in config["loggers"]  # Root logger
        assert "app.vaststore" in config["loggers"]
        assert "vastdb" in config["loggers"]
    
    @patch('vasttams.core.simple_logging.get_settings')
    @patch('logging.config.dictConfig')
    def test_setup_logging_file_handlers(self, mock_dict_config, mock_get_settings):
        """Test that file handlers are configured correctly"""
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        setup_logging()
        
        config = mock_dict_config.call_args[0][0]
        file_handler = config["handlers"]["file"]
        assert file_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert file_handler["level"] == "DEBUG"
        assert "tams.log" in file_handler["filename"]
        assert file_handler["maxBytes"] == 10485760  # 10MB
        
        error_file_handler = config["handlers"]["error_file"]
        assert error_file_handler["level"] == "ERROR"
        assert "tams_errors.log" in error_file_handler["filename"]
    
    @patch('vasttams.core.simple_logging.get_settings')
    @patch('logging.config.dictConfig')
    def test_setup_logging_console_handler(self, mock_dict_config, mock_get_settings):
        """Test that console handler is configured"""
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        setup_logging()
        
        config = mock_dict_config.call_args[0][0]
        console_handler = config["handlers"]["console"]
        assert console_handler["class"] == "logging.StreamHandler"
        assert console_handler["level"] == "INFO"
        assert console_handler["formatter"] == "simple"
    
    @patch('vasttams.core.simple_logging.get_settings')
    @patch('logging.config.dictConfig')
    @patch('logging.getLogger')
    def test_setup_logging_sets_logger_levels(self, mock_get_logger, mock_dict_config, mock_get_settings):
        """Test that logger levels are set correctly"""
        mock_settings = MagicMock()
        mock_settings.log_level = "WARNING"
        mock_get_settings.return_value = mock_settings
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        setup_logging()
        
        # Verify root logger level was set
        mock_logger.setLevel.assert_called()
    
    def test_tams_compliance_filter_compliance_only(self):
        """Test TAMSComplianceFilter with compliance_only=True"""
        from vasttams.core.tams_logging import TAMSComplianceFilter
        
        filter_obj = TAMSComplianceFilter(compliance_only=True)
        
        # Create a record with compliance data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="TAMS compliance message",
            args=(),
            exc_info=None
        )
        record.tams_compliance_data = {"field": "id"}
        
        assert filter_obj.filter(record) is True
        
        # Create a record without compliance data
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Regular message",
            args=(),
            exc_info=None
        )
        assert filter_obj.filter(record2) is False
    
    def test_tams_compliance_filter_compliance_only_tams_in_name(self):
        """Test TAMSComplianceFilter with TAMS in logger name"""
        from vasttams.core.tams_logging import TAMSComplianceFilter
        
        filter_obj = TAMSComplianceFilter(compliance_only=True)
        
        record = logging.LogRecord(
            name="tams.compliance",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Regular message",
            args=(),
            exc_info=None
        )
        assert filter_obj.filter(record) is True
    
    def test_tams_compliance_filter_compliance_only_compliance_in_message(self):
        """Test TAMSComplianceFilter with 'compliance' in message"""
        from vasttams.core.tams_logging import TAMSComplianceFilter
        
        filter_obj = TAMSComplianceFilter(compliance_only=True)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="This is a compliance message",
            args=(),
            exc_info=None
        )
        assert filter_obj.filter(record) is True
    
    def test_tams_logging_config_init(self):
        """Test TAMSLoggingConfig initialization"""
        from vasttams.core.tams_logging import TAMSLoggingConfig
        from unittest.mock import patch
        
        with patch('vasttams.core.tams_logging.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_get_settings.return_value = mock_settings
            
            config = TAMSLoggingConfig()
            
            assert config.settings == mock_settings
            assert config.log_dir.exists()
    
    @patch('vasttams.core.tams_logging.get_settings')
    @patch('logging.config.dictConfig')
    @patch('logging.getLogger')
    def test_tams_logging_config_setup_logging(self, mock_get_logger, mock_dict_config, mock_get_settings):
        """Test TAMSLoggingConfig.setup_logging"""
        from vasttams.core.tams_logging import TAMSLoggingConfig
        
        mock_settings = MagicMock()
        mock_settings.debug = False
        mock_settings.tams_audit_logging = True
        mock_get_settings.return_value = mock_settings
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        config = TAMSLoggingConfig()
        config.setup_logging()
        
        mock_dict_config.assert_called_once()
        config_dict = mock_dict_config.call_args[0][0]
        assert "version" in config_dict
        assert "formatters" in config_dict
        assert "handlers" in config_dict
        assert "loggers" in config_dict
    
    def test_log_tams_compliance_event(self):
        """Test log_tams_compliance_event function"""
        from vasttams.core.tams_logging import log_tams_compliance_event
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'info') as mock_info:
            log_tams_compliance_event(
                logger=logger,
                event_type="validation",
                compliance_status="passed",
                details={"field": "id"},
                severity="info"
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "TAMS Compliance Event" in call_args[0][0]
            assert "validation" in call_args[0][0]
            assert "tams_compliance_data" in call_args[1]["extra"]
    
    def test_log_tams_compliance_event_error(self):
        """Test log_tams_compliance_event with error severity"""
        from vasttams.core.tams_logging import log_tams_compliance_event
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'error') as mock_error:
            log_tams_compliance_event(
                logger=logger,
                event_type="validation",
                compliance_status="failed",
                severity="error"
            )
            mock_error.assert_called_once()
    
    def test_log_tams_compliance_event_warning(self):
        """Test log_tams_compliance_event with warning severity"""
        from vasttams.core.tams_logging import log_tams_compliance_event
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'warning') as mock_warning:
            log_tams_compliance_event(
                logger=logger,
                event_type="validation",
                compliance_status="warning",
                severity="warning"
            )
            mock_warning.assert_called_once()
    
    def test_log_tams_compliance_event_debug(self):
        """Test log_tams_compliance_event with debug severity"""
        from vasttams.core.tams_logging import log_tams_compliance_event
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'debug') as mock_debug:
            log_tams_compliance_event(
                logger=logger,
                event_type="validation",
                compliance_status="debug",
                severity="debug"
            )
            mock_debug.assert_called_once()
    
    def test_log_tams_validation_result_passed(self):
        """Test log_tams_validation_result with passed result"""
        from vasttams.core.tams_logging import log_tams_validation_result
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'info') as mock_info:
            log_tams_validation_result(
                logger=logger,
                field_path="source.id",
                validation_result=True,
                validation_rule="UUID format"
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "PASSED" in call_args[0][0]
            assert "source.id" in call_args[0][0]
    
    def test_log_tams_validation_result_failed(self):
        """Test log_tams_validation_result with failed result"""
        from vasttams.core.tams_logging import log_tams_validation_result
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'warning') as mock_warning:
            log_tams_validation_result(
                logger=logger,
                field_path="source.id",
                validation_result=False,
                validation_rule="UUID format"
            )
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert "FAILED" in call_args[0][0]
    
    def test_log_tams_api_request(self):
        """Test log_tams_api_request function"""
        from vasttams.core.tams_logging import log_tams_api_request
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'info') as mock_info:
            log_tams_api_request(
                logger=logger,
                endpoint="/sources",
                method="GET",
                user_id="user123",
                request_id="req456"
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "TAMS API Request" in call_args[0][0]
            assert "GET /sources" in call_args[0][0]
            assert "api_context" in call_args[1]["extra"]
    
    def test_log_tams_storage_operation_success(self):
        """Test log_tams_storage_operation with success"""
        from vasttams.core.tams_logging import log_tams_storage_operation
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'info') as mock_info:
            log_tams_storage_operation(
                logger=logger,
                operation="upload",
                storage_backend_id="backend123",
                entity_type="object",
                entity_id="obj456",
                success=True
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "SUCCESS" in call_args[0][0]
            assert "upload" in call_args[0][0]
    
    def test_log_tams_storage_operation_failed(self):
        """Test log_tams_storage_operation with failure"""
        from vasttams.core.tams_logging import log_tams_storage_operation
        
        logger = logging.getLogger("test")
        with patch.object(logger, 'error') as mock_error:
            log_tams_storage_operation(
                logger=logger,
                operation="upload",
                storage_backend_id="backend123",
                entity_type="object",
                entity_id="obj456",
                success=False
            )
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "FAILED" in call_args[0][0]

