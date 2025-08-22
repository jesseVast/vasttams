"""
Storage Health Monitor for TAMS

Provides comprehensive health monitoring for storage systems including
VAST database, S3 storage, and overall system performance.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SystemHealth:
    """Overall system health summary"""
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    total_checks: int
    healthy_checks: int
    warning_checks: int
    critical_checks: int
    timestamp: datetime
    summary: str


class StorageHealthMonitor:
    """Comprehensive health monitoring for storage systems"""
    
    def __init__(self):
        """Initialize health monitor"""
        self.logger = logging.getLogger(__name__)
        self.last_check_time = None
        self.health_history: List[SystemHealth] = []
        self.max_history = 100
        
    async def check_system_health(self, include_detailed: bool = True) -> SystemHealth:
        """
        Run comprehensive system health check
        
        Args:
            include_detailed: Include detailed performance metrics
            
        Returns:
            SystemHealth object with overall status and individual check results
        """
        start_time = time.time()
        checks = []
        
        try:
            # Parallel health checks for better performance
            check_tasks = [
                self._check_vast_connection(),
                self._check_s3_connection(),
                self._check_log_health(),
                self._check_disk_space(),
            ]
            
            if include_detailed:
                check_tasks.extend([
                    self._check_table_integrity(),
                    self._check_performance_metrics(),
                ])
            
            # Run all checks in parallel
            check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
            
            # Process results
            for result in check_results:
                if isinstance(result, Exception):
                    checks.append(HealthCheckResult(
                        name="health_check_error",
                        status=HealthStatus.CRITICAL,
                        response_time_ms=0,
                        message=f"Health check failed: {str(result)}",
                        details={"exception": str(result)}
                    ))
                elif isinstance(result, HealthCheckResult):
                    checks.append(result)
                elif isinstance(result, list):
                    checks.extend(result)
            
            # Calculate overall health
            system_health = self._calculate_overall_health(checks)
            
            # Store in history
            self._update_health_history(system_health)
            self.last_check_time = datetime.utcnow()
            
            total_time = (time.time() - start_time) * 1000
            self.logger.info(f"System health check completed in {total_time:.2f}ms - Status: {system_health.overall_status.value}")
            
            return system_health
            
        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            error_check = HealthCheckResult(
                name="system_health_check",
                status=HealthStatus.CRITICAL,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"System health check failed: {str(e)}",
                details={"exception": str(e)}
            )
            return SystemHealth(
                overall_status=HealthStatus.CRITICAL,
                checks=[error_check],
                total_checks=1,
                healthy_checks=0,
                warning_checks=0,
                critical_checks=1,
                timestamp=datetime.utcnow(),
                summary="System health check failed due to internal error"
            )
    
    async def _check_vast_connection(self) -> HealthCheckResult:
        """Check VAST database connection health"""
        start_time = time.time()
        
        try:
            # Import here to avoid circular dependencies
            from ...core.dependencies import get_vast_store, set_vast_store
            from ...core.config import get_settings
            from ...storage.vast_store import VASTStore
            
            # Try to get existing store, or create one for diagnostics
            try:
                store = get_vast_store()
            except Exception:
                # No store initialized, create one for diagnostics
                settings = get_settings()
                store = VASTStore(
                    endpoint=settings.vast_endpoint,
                    access_key=settings.vast_access_key,
                    secret_key=settings.vast_secret_key,
                    bucket=settings.vast_bucket,
                    schema=settings.vast_schema
                )
                set_vast_store(store)
            
            if not store:
                return HealthCheckResult(
                    name="vast_connection",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="VAST store not initialized",
                    details={"error": "Store instance not found"}
                )
            
            # Test connection by listing tables
            tables = store.db_manager.list_tables()
            response_time = (time.time() - start_time) * 1000
            
            if len(tables) > 0:
                return HealthCheckResult(
                    name="vast_connection",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message=f"VAST database connected - {len(tables)} tables available",
                    details={"table_count": len(tables), "tables": tables[:5]}  # First 5 tables
                )
            else:
                return HealthCheckResult(
                    name="vast_connection",
                    status=HealthStatus.WARNING,
                    response_time_ms=response_time,
                    message="VAST database connected but no tables found",
                    details={"table_count": 0}
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="vast_connection",
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"VAST connection failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _check_s3_connection(self) -> HealthCheckResult:
        """Check S3 storage connection health"""
        start_time = time.time()
        
        try:
            # Import here to avoid circular dependencies
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store or not store.s3_store:
                return HealthCheckResult(
                    name="s3_connection",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="S3 store not initialized",
                    details={"error": "S3 store instance not found"}
                )
            
            # Test S3 connection by checking bucket
            bucket_exists = await store.s3_store.bucket_exists()
            response_time = (time.time() - start_time) * 1000
            
            if bucket_exists:
                return HealthCheckResult(
                    name="s3_connection",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message="S3 storage connected and bucket accessible",
                    details={"bucket_exists": True, "bucket_name": store.s3_store.bucket_name}
                )
            else:
                return HealthCheckResult(
                    name="s3_connection",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=response_time,
                    message="S3 storage connection failed - bucket not accessible",
                    details={"bucket_exists": False, "bucket_name": store.s3_store.bucket_name}
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="s3_connection",
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"S3 connection check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _check_log_health(self) -> HealthCheckResult:
        """Check logging system health"""
        start_time = time.time()
        
        try:
            from pathlib import Path
            
            log_dir = Path("logs")
            issues = []
            
            # Check if log directory exists
            if not log_dir.exists():
                issues.append("Log directory does not exist")
            
            # Check log files
            log_files = ["tams.log", "tams_errors.log"]
            existing_files = []
            
            for log_file in log_files:
                log_path = log_dir / log_file
                if log_path.exists():
                    existing_files.append(log_file)
                    # Check if file is writable
                    if not log_path.stat().st_size == 0:  # Not empty
                        # Check if file was written to recently (last 24 hours)
                        file_age = time.time() - log_path.stat().st_mtime
                        if file_age > 86400:  # 24 hours
                            issues.append(f"{log_file} not written to in 24+ hours")
                else:
                    issues.append(f"{log_file} does not exist")
            
            response_time = (time.time() - start_time) * 1000
            
            if not issues:
                return HealthCheckResult(
                    name="log_health",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message=f"Logging system healthy - {len(existing_files)} log files active",
                    details={"log_files": existing_files, "log_directory": str(log_dir)}
                )
            else:
                return HealthCheckResult(
                    name="log_health",
                    status=HealthStatus.WARNING,
                    response_time_ms=response_time,
                    message=f"Logging issues detected: {len(issues)} problems",
                    details={"issues": issues, "existing_files": existing_files}
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="log_health",
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"Log health check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space health"""
        start_time = time.time()
        
        try:
            import shutil
            from pathlib import Path
            
            # Check disk space for current directory and logs
            paths_to_check = [Path("."), Path("logs")]
            disk_info = {}
            
            for path in paths_to_check:
                if path.exists():
                    usage = shutil.disk_usage(path)
                    free_gb = usage.free / (1024**3)
                    total_gb = usage.total / (1024**3)
                    used_percent = ((usage.total - usage.free) / usage.total) * 100
                    
                    disk_info[str(path)] = {
                        "free_gb": round(free_gb, 2),
                        "total_gb": round(total_gb, 2),
                        "used_percent": round(used_percent, 2)
                    }
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on available space
            min_free_gb = min(info["free_gb"] for info in disk_info.values())
            max_used_percent = max(info["used_percent"] for info in disk_info.values())
            
            if min_free_gb < 1.0:  # Less than 1GB free
                status = HealthStatus.CRITICAL
                message = f"Critical disk space: {min_free_gb:.2f}GB free"
            elif max_used_percent > 90:  # More than 90% used
                status = HealthStatus.WARNING
                message = f"Low disk space: {max_used_percent:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space healthy: {min_free_gb:.2f}GB free"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=disk_info
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"Disk space check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _check_table_integrity(self) -> List[HealthCheckResult]:
        """Check database table integrity"""
        start_time = time.time()
        results = []
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store:
                return [HealthCheckResult(
                    name="table_integrity",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="Cannot check table integrity - store not available"
                )]
            
            # Check each main table
            tables_to_check = ["sources", "flows", "segments", "objects"]
            
            for table_name in tables_to_check:
                table_start = time.time()
                try:
                    # Get table statistics
                    stats = store.db_manager.cache_manager.get_table_stats(table_name)
                    table_time = (time.time() - table_start) * 1000
                    
                    if stats and stats.get('total_rows', 0) >= 0:
                        results.append(HealthCheckResult(
                            name=f"table_{table_name}",
                            status=HealthStatus.HEALTHY,
                            response_time_ms=table_time,
                            message=f"Table {table_name} accessible with {stats.get('total_rows', 0)} rows",
                            details={"table_name": table_name, "row_count": stats.get('total_rows', 0)}
                        ))
                    else:
                        results.append(HealthCheckResult(
                            name=f"table_{table_name}",
                            status=HealthStatus.WARNING,
                            response_time_ms=table_time,
                            message=f"Table {table_name} accessible but no statistics available",
                            details={"table_name": table_name}
                        ))
                        
                except Exception as e:
                    table_time = (time.time() - table_start) * 1000
                    results.append(HealthCheckResult(
                        name=f"table_{table_name}",
                        status=HealthStatus.CRITICAL,
                        response_time_ms=table_time,
                        message=f"Table {table_name} check failed: {str(e)}",
                        details={"table_name": table_name, "error": str(e)}
                    ))
            
            return results
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return [HealthCheckResult(
                name="table_integrity",
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"Table integrity check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )]
    
    async def _check_performance_metrics(self) -> HealthCheckResult:
        """Check system performance metrics"""
        start_time = time.time()
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store:
                return HealthCheckResult(
                    name="performance_metrics",
                    status=HealthStatus.WARNING,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="Cannot check performance - store not available"
                )
            
            # Get performance metrics if available
            performance_data = {}
            
            # Check if performance monitor exists
            if hasattr(store.db_manager, 'performance_monitor'):
                monitor = store.db_manager.performance_monitor
                
                # Get recent performance summary
                recent_summary = monitor.get_performance_summary(time_window=timedelta(hours=1))
                performance_data.update(recent_summary)
            
            response_time = (time.time() - start_time) * 1000
            
            # Analyze performance metrics
            if performance_data:
                avg_query_time = performance_data.get('avg_query_time', 0)
                slow_queries = performance_data.get('slow_queries', 0)
                
                if avg_query_time > 5000:  # > 5 seconds
                    status = HealthStatus.WARNING
                    message = f"Performance degraded: avg query time {avg_query_time:.2f}ms"
                elif slow_queries > 10:
                    status = HealthStatus.WARNING
                    message = f"Performance warning: {slow_queries} slow queries in last hour"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Performance healthy: avg query time {avg_query_time:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Performance monitoring data not available"
            
            return HealthCheckResult(
                name="performance_metrics",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=performance_data
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="performance_metrics",
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"Performance check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    def _calculate_overall_health(self, checks: List[HealthCheckResult]) -> SystemHealth:
        """Calculate overall system health from individual checks"""
        if not checks:
            return SystemHealth(
                overall_status=HealthStatus.UNKNOWN,
                checks=[],
                total_checks=0,
                healthy_checks=0,
                warning_checks=0,
                critical_checks=0,
                timestamp=datetime.utcnow(),
                summary="No health checks performed"
            )
        
        # Count status types
        healthy_count = sum(1 for check in checks if check.status == HealthStatus.HEALTHY)
        warning_count = sum(1 for check in checks if check.status == HealthStatus.WARNING)
        critical_count = sum(1 for check in checks if check.status == HealthStatus.CRITICAL)
        
        # Determine overall status
        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Generate summary
        if overall_status == HealthStatus.HEALTHY:
            summary = f"All {len(checks)} health checks passed"
        elif overall_status == HealthStatus.WARNING:
            summary = f"{warning_count} warnings out of {len(checks)} checks"
        else:
            summary = f"{critical_count} critical issues out of {len(checks)} checks"
        
        return SystemHealth(
            overall_status=overall_status,
            checks=checks,
            total_checks=len(checks),
            healthy_checks=healthy_count,
            warning_checks=warning_count,
            critical_checks=critical_count,
            timestamp=datetime.utcnow(),
            summary=summary
        )
    
    def _update_health_history(self, health: SystemHealth):
        """Update health check history"""
        self.health_history.append(health)
        
        # Maintain history size
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
    
    def get_health_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trend analysis for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_checks = [h for h in self.health_history if h.timestamp >= cutoff_time]
        
        if not recent_checks:
            return {"trend": "no_data", "message": "No recent health data available"}
        
        # Analyze trend
        healthy_count = sum(1 for h in recent_checks if h.overall_status == HealthStatus.HEALTHY)
        warning_count = sum(1 for h in recent_checks if h.overall_status == HealthStatus.WARNING)
        critical_count = sum(1 for h in recent_checks if h.overall_status == HealthStatus.CRITICAL)
        
        # Calculate trend
        if len(recent_checks) >= 2:
            recent_status = recent_checks[-1].overall_status
            older_status = recent_checks[-2].overall_status
            
            if recent_status.value == "healthy" and older_status.value != "healthy":
                trend = "improving"
            elif recent_status.value != "healthy" and older_status.value == "healthy":
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "period_hours": hours,
            "total_checks": len(recent_checks),
            "healthy_ratio": healthy_count / len(recent_checks) if recent_checks else 0,
            "warning_ratio": warning_count / len(recent_checks) if recent_checks else 0,
            "critical_ratio": critical_count / len(recent_checks) if recent_checks else 0,
            "latest_status": recent_checks[-1].overall_status.value if recent_checks else "unknown"
        }
    
    async def diagnose_issues(self) -> List[Dict[str, Any]]:
        """Automatically diagnose common issues and provide suggestions"""
        issues = []
        
        try:
            # Run health check
            health = await self.check_system_health(include_detailed=True)
            
            # Analyze critical and warning issues
            for check in health.checks:
                if check.status in [HealthStatus.CRITICAL, HealthStatus.WARNING]:
                    suggestions = self._get_issue_suggestions(check)
                    issues.append({
                        "check_name": check.name,
                        "status": check.status.value,
                        "message": check.message,
                        "suggestions": suggestions,
                        "details": check.details
                    })
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Issue diagnosis failed: {e}")
            return [{
                "check_name": "diagnosis_error",
                "status": "critical",
                "message": f"Issue diagnosis failed: {str(e)}",
                "suggestions": ["Check system logs", "Restart application", "Contact support"],
                "details": {"error": str(e)}
            }]
    
    def _get_issue_suggestions(self, check: HealthCheckResult) -> List[str]:
        """Get specific suggestions for resolving issues"""
        suggestions = []
        
        if check.name == "vast_connection":
            suggestions.extend([
                "Check VAST database server is running",
                "Verify network connectivity to VAST endpoint",
                "Check VAST credentials and permissions",
                "Review VAST server logs for errors"
            ])
        elif check.name == "s3_connection":
            suggestions.extend([
                "Check S3 endpoint is accessible",
                "Verify S3 credentials and permissions",
                "Check S3 bucket exists and is accessible",
                "Review S3 service status"
            ])
        elif check.name.startswith("table_"):
            suggestions.extend([
                "Check VAST database connection",
                "Verify table exists and is accessible",
                "Check table permissions",
                "Run table integrity check"
            ])
        elif check.name == "disk_space":
            suggestions.extend([
                "Free up disk space by removing old files",
                "Archive or compress old log files",
                "Check for large temporary files",
                "Monitor disk usage trends"
            ])
        elif check.name == "log_health":
            suggestions.extend([
                "Check log directory permissions",
                "Verify logging configuration",
                "Check disk space for log files",
                "Review application startup logs"
            ])
        elif check.name == "performance_metrics":
            suggestions.extend([
                "Check database query performance",
                "Review slow query logs",
                "Monitor system resource usage",
                "Consider optimizing queries or adding indexes"
            ])
        else:
            suggestions.extend([
                "Check system logs for more details",
                "Review application configuration",
                "Restart affected services",
                "Contact system administrator"
            ])
        
        return suggestions
