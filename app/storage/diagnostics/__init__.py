"""
Storage Diagnostics Module for TAMS

This module provides comprehensive diagnostic capabilities for the storage layer,
including health monitoring, model validation, connection testing, and performance analysis.

Key Components:
- StorageHealthMonitor: System health checks and monitoring
- TAMSModelValidator: TAMS compliance validation for all models
- ConnectionTester: Database and S3 connectivity testing
- PerformanceAnalyzer: Query performance analysis and monitoring
- Troubleshooter: Automated issue detection and resolution suggestions

Usage:
    from app.storage.diagnostics import StorageHealthMonitor
    
    monitor = StorageHealthMonitor()
    health_status = await monitor.check_system_health()
"""

from .health_monitor import StorageHealthMonitor
from .model_validator import TAMSModelValidator
from .connection_tester import ConnectionTester
from .performance_analyzer import PerformanceAnalyzer
from .troubleshooter import StorageTroubleshooter
from .logger import DiagnosticsLogger, get_diagnostics_logger, log_diagnostic_event

__all__ = [
    "StorageHealthMonitor",
    "TAMSModelValidator", 
    "ConnectionTester",
    "PerformanceAnalyzer",
    "StorageTroubleshooter",
    "DiagnosticsLogger",
    "get_diagnostics_logger",
    "log_diagnostic_event"
]
