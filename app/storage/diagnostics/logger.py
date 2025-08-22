"""
Diagnostics Logger for TAMS Storage System

Provides human-readable logging for diagnostic test results with structured
line-by-line output for easy debugging and monitoring.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum


class DiagnosticLevel(Enum):
    """Diagnostic severity levels"""
    INFO = "INFO"
    SUCCESS = "SUCCESS" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DiagnosticsLogger:
    """Human-readable diagnostics logger"""
    
    def __init__(self, log_file: str = "logs/diagnostics.log"):
        """Initialize diagnostics logger"""
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger("diagnostics")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create file handler for diagnostics
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter for human-readable output
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_test_start(self, test_name: str, description: str = ""):
        """Log the start of a diagnostic test"""
        msg = f"TEST_START | {test_name}"
        if description:
            msg += f" | {description}"
        self.logger.info(msg)
    
    def log_test_result(self, test_name: str, success: bool, duration_ms: float, 
                       details: Optional[Dict[str, Any]] = None):
        """Log the result of a diagnostic test"""
        status = "PASS" if success else "FAIL"
        level = DiagnosticLevel.SUCCESS if success else DiagnosticLevel.ERROR
        
        msg = f"TEST_RESULT | {test_name} | {status} | {duration_ms:.2f}ms"
        
        if details:
            detail_parts = []
            for key, value in details.items():
                if isinstance(value, (int, float)):
                    detail_parts.append(f"{key}={value}")
                elif isinstance(value, str):
                    detail_parts.append(f"{key}='{value}'")
                elif isinstance(value, list):
                    detail_parts.append(f"{key}={len(value)} items")
                else:
                    detail_parts.append(f"{key}={str(value)}")
            
            if detail_parts:
                msg += f" | {', '.join(detail_parts)}"
        
        self._log_with_level(level, msg)
    
    def log_health_check(self, component: str, status: str, response_time_ms: float, 
                        message: str = ""):
        """Log a health check result"""
        level = self._get_level_from_status(status)
        msg = f"HEALTH_CHECK | {component} | {status.upper()} | {response_time_ms:.2f}ms"
        if message:
            msg += f" | {message}"
        self._log_with_level(level, msg)
    
    def log_compliance_result(self, model_name: str, compliance_percentage: float, 
                            compliance_level: str, issues_count: int = 0, 
                            critical_issues: int = 0):
        """Log TAMS compliance validation result"""
        level = DiagnosticLevel.SUCCESS if compliance_percentage == 100 else \
                DiagnosticLevel.WARNING if compliance_percentage >= 80 else \
                DiagnosticLevel.ERROR
        
        msg = f"COMPLIANCE | {model_name} | {compliance_percentage:.1f}% | {compliance_level.upper()}"
        if issues_count > 0:
            msg += f" | issues={issues_count}, critical={critical_issues}"
        
        self._log_with_level(level, msg)
    
    def log_connection_test(self, test_name: str, status: str, response_time_ms: float, 
                           message: str = ""):
        """Log connection test result"""
        level = self._get_level_from_status(status)
        msg = f"CONNECTION | {test_name} | {status.upper()} | {response_time_ms:.2f}ms"
        if message:
            msg += f" | {message}"
        self._log_with_level(level, msg)
    
    def log_performance_benchmark(self, benchmark_name: str, status: str, 
                                 execution_time_ms: float, throughput: Optional[float] = None):
        """Log performance benchmark result"""
        level = self._get_level_from_status(status)
        msg = f"PERFORMANCE | {benchmark_name} | {status.upper()} | {execution_time_ms:.2f}ms"
        if throughput is not None:
            msg += f" | throughput={throughput:.2f} ops/sec"
        self._log_with_level(level, msg)
    
    def log_issue_detected(self, category: str, severity: str, title: str, 
                          description: str = ""):
        """Log a detected issue"""
        level = DiagnosticLevel.CRITICAL if severity == "critical" else \
                DiagnosticLevel.ERROR if severity == "high" else \
                DiagnosticLevel.WARNING if severity == "medium" else \
                DiagnosticLevel.INFO
        
        msg = f"ISSUE | {category.upper()} | {severity.upper()} | {title}"
        if description:
            msg += f" | {description}"
        self._log_with_level(level, msg)
    
    def log_troubleshooting_session(self, session_id: str, overall_health: str, 
                                   issues_count: int, duration_ms: float):
        """Log troubleshooting session summary"""
        level = DiagnosticLevel.SUCCESS if overall_health == "healthy" else \
                DiagnosticLevel.WARNING if overall_health in ["warning", "minor_issues"] else \
                DiagnosticLevel.ERROR
        
        msg = f"TROUBLESHOOT | {session_id} | {overall_health.upper()} | {issues_count} issues | {duration_ms:.2f}ms"
        self._log_with_level(level, msg)
    
    def log_system_event(self, event_type: str, message: str, 
                        level: DiagnosticLevel = DiagnosticLevel.INFO):
        """Log a general system event"""
        msg = f"SYSTEM | {event_type.upper()} | {message}"
        self._log_with_level(level, msg)
    
    def log_session_start(self, session_type: str = "diagnostic"):
        """Log the start of a diagnostic session"""
        msg = f"SESSION_START | {session_type.upper()} | Starting diagnostic session"
        self.logger.info(msg)
    
    def log_session_end(self, session_type: str, success_rate: float, duration_seconds: float):
        """Log the end of a diagnostic session"""
        level = DiagnosticLevel.SUCCESS if success_rate == 100 else \
                DiagnosticLevel.WARNING if success_rate >= 80 else \
                DiagnosticLevel.ERROR
        
        msg = f"SESSION_END | {session_type.upper()} | {success_rate:.1f}% success | {duration_seconds:.2f}s"
        self._log_with_level(level, msg)
    
    def log_separator(self, title: str = ""):
        """Log a visual separator for readability"""
        separator = "=" * 80
        if title:
            title_line = f" {title} ".center(80, "=")
            self.logger.info(title_line)
        else:
            self.logger.info(separator)
    
    def _get_level_from_status(self, status: str) -> DiagnosticLevel:
        """Convert status string to diagnostic level"""
        status_lower = status.lower()
        if status_lower in ["connected", "healthy", "excellent", "good", "compliant"]:
            return DiagnosticLevel.SUCCESS
        elif status_lower in ["warning", "acceptable", "minor_issues"]:
            return DiagnosticLevel.WARNING
        elif status_lower in ["error", "critical", "poor", "major_issues", "non_compliant"]:
            return DiagnosticLevel.ERROR
        elif status_lower in ["disconnected", "timeout", "unknown"]:
            return DiagnosticLevel.WARNING
        else:
            return DiagnosticLevel.INFO
    
    def _log_with_level(self, level: DiagnosticLevel, message: str):
        """Log message with appropriate level"""
        if level == DiagnosticLevel.SUCCESS:
            self.logger.info(message)
        elif level == DiagnosticLevel.WARNING:
            self.logger.warning(message)
        elif level == DiagnosticLevel.ERROR:
            self.logger.error(message)
        elif level == DiagnosticLevel.CRITICAL:
            self.logger.critical(message)
        else:
            self.logger.info(message)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about the current log file"""
        if not self.log_file.exists():
            return {"exists": False, "lines": 0, "size_bytes": 0}
        
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
        
        stats = {
            "exists": True,
            "lines": len(lines),
            "size_bytes": self.log_file.stat().st_size,
            "last_modified": datetime.fromtimestamp(self.log_file.stat().st_mtime).isoformat()
        }
        
        # Count different types of entries
        test_results = [line for line in lines if "TEST_RESULT" in line]
        health_checks = [line for line in lines if "HEALTH_CHECK" in line]
        compliance_checks = [line for line in lines if "COMPLIANCE" in line]
        issues = [line for line in lines if "ISSUE" in line]
        
        stats.update({
            "test_results": len(test_results),
            "health_checks": len(health_checks),
            "compliance_checks": len(compliance_checks), 
            "issues_detected": len(issues)
        })
        
        return stats
    
    def tail_log(self, lines: int = 20) -> List[str]:
        """Get the last N lines from the log file"""
        if not self.log_file.exists():
            return []
        
        with open(self.log_file, 'r') as f:
            all_lines = f.readlines()
        
        return [line.strip() for line in all_lines[-lines:]]


# Global diagnostics logger instance
_diagnostics_logger = None

def get_diagnostics_logger() -> DiagnosticsLogger:
    """Get the global diagnostics logger instance"""
    global _diagnostics_logger
    if _diagnostics_logger is None:
        _diagnostics_logger = DiagnosticsLogger()
    return _diagnostics_logger


def log_diagnostic_event(event_type: str, message: str, **kwargs):
    """Convenience function to log diagnostic events"""
    logger = get_diagnostics_logger()
    
    if event_type == "test_start":
        logger.log_test_start(kwargs.get("test_name", ""), message)
    elif event_type == "test_result":
        logger.log_test_result(
            kwargs.get("test_name", ""),
            kwargs.get("success", False),
            kwargs.get("duration_ms", 0),
            kwargs.get("details")
        )
    elif event_type == "health_check":
        logger.log_health_check(
            kwargs.get("component", ""),
            kwargs.get("status", "unknown"),
            kwargs.get("response_time_ms", 0),
            message
        )
    elif event_type == "compliance":
        logger.log_compliance_result(
            kwargs.get("model_name", ""),
            kwargs.get("compliance_percentage", 0),
            kwargs.get("compliance_level", "unknown"),
            kwargs.get("issues_count", 0),
            kwargs.get("critical_issues", 0)
        )
    elif event_type == "connection":
        logger.log_connection_test(
            kwargs.get("test_name", ""),
            kwargs.get("status", "unknown"),
            kwargs.get("response_time_ms", 0),
            message
        )
    elif event_type == "performance":
        logger.log_performance_benchmark(
            kwargs.get("benchmark_name", ""),
            kwargs.get("status", "unknown"),
            kwargs.get("execution_time_ms", 0),
            kwargs.get("throughput")
        )
    elif event_type == "issue":
        logger.log_issue_detected(
            kwargs.get("category", "general"),
            kwargs.get("severity", "medium"),
            kwargs.get("title", ""),
            message
        )
    elif event_type == "session_start":
        logger.log_session_start(kwargs.get("session_type", "diagnostic"))
    elif event_type == "session_end":
        logger.log_session_end(
            kwargs.get("session_type", "diagnostic"),
            kwargs.get("success_rate", 0),
            kwargs.get("duration_seconds", 0)
        )
    else:
        logger.log_system_event(event_type, message)
