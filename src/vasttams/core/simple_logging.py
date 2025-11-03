"""Simplified, unified logging configuration for TAMS"""

import logging
import logging.config
from pathlib import Path
import sys
from .config import get_settings


class EnhancedFormatter(logging.Formatter):
    """Enhanced human-readable formatter with optional extra context"""
    
    def __init__(self, include_function: bool = True, include_extra: bool = True):
        # Enhanced format with debugging information
        if include_function:
            format_str = "%(asctime)s - %(name)s:%(lineno)d:%(funcName)s - %(levelname)s - %(message)s"
        else:
            format_str = "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
        
        super().__init__(fmt=format_str, datefmt='%Y-%m-%d %H:%M:%S')
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text with extra context"""
        # Get base formatted message
        base_message = super().format(record)
        
        if not self.include_extra:
            return base_message
        
        # Add extra context if present
        extra_parts = []
        
        if hasattr(record, 'tams_compliance_data'):
            compliance = record.tams_compliance_data
            if isinstance(compliance, dict):
                compliance_str = ", ".join(f"{k}={v}" for k, v in compliance.items())
                extra_parts.append(f"[TAMS: {compliance_str}]")
        
        if hasattr(record, 'error_details'):
            error_details = record.error_details
            if isinstance(error_details, dict):
                error_str = ", ".join(f"{k}={v}" for k, v in error_details.items())
                extra_parts.append(f"[Error: {error_str}]")
        
        if hasattr(record, 'user_context'):
            user_ctx = record.user_context
            if isinstance(user_ctx, dict):
                user_str = ", ".join(f"{k}={v}" for k, v in user_ctx.items())
                extra_parts.append(f"[User: {user_str}]")
        
        if hasattr(record, 'api_context'):
            api_ctx = record.api_context
            if isinstance(api_ctx, dict):
                api_str = ", ".join(f"{k}={v}" for k, v in api_ctx.items())
                extra_parts.append(f"[API: {api_str}]")
        
        # Add extra context to message
        if extra_parts:
            return f"{base_message} {' '.join(extra_parts)}"
        
        return base_message


def setup_logging():
    """Setup simple, unified logging configuration"""
    settings = get_settings()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Get log level from settings, with fallback
    log_level = settings.log_level.upper() if hasattr(settings, 'log_level') and settings.log_level else "INFO"
    
    # Simple, unified logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "()": EnhancedFormatter,
                "include_function": True,
                "include_extra": True
            },
            "simple": {
                "()": EnhancedFormatter,
                "include_function": False,
                "include_extra": False
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(log_dir / "tams.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(log_dir / "tams_errors.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 3
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console", "file", "error_file"]
            },
            "app.vaststore": {  # VAST store logger
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "vastdb": {  # VAST database logger
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            }
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Explicitly set level for root logger to ensure it's applied
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Set level for all existing loggers (submodules)
    # This ensures that loggers created before setup_logging() also get the correct level
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        try:
            logger_obj = logging.getLogger(logger_name)
            # Set level for vasttams submodules and loggers without explicit handlers
            if logger_name.startswith('vasttams.') or (isinstance(logger_obj, logging.Logger) and not logger_obj.handlers):
                logger_obj.setLevel(log_level)
        except Exception:
            # Skip any problematic loggers
            pass
    
    # Log configuration setup
    logger = logging.getLogger("app.core.logging")
    logger.info(f"Unified logging initialized - Debug: {settings.debug}, Level: {log_level}")


# Initialize logging when module is imported
setup_logging()
