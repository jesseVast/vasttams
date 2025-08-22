"""
Connection Tester for TAMS Storage Systems

Tests and validates database connections, S3 storage connectivity,
and network connectivity with detailed diagnostics and benchmarking.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status enumeration"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ConnectionTest:
    """Individual connection test result"""
    test_name: str
    status: ConnectionStatus
    response_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ConnectionSuite:
    """Complete connection test suite result"""
    suite_name: str
    overall_status: ConnectionStatus
    tests: List[ConnectionTest]
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_response_time: float
    timestamp: datetime
    summary: str


class ConnectionTester:
    """Test and validate database and storage connections"""
    
    def __init__(self):
        """Initialize connection tester"""
        self.logger = logging.getLogger(__name__)
        self.test_history: List[ConnectionSuite] = []
        self.max_history = 50
        
    async def run_connectivity_suite(self, include_performance: bool = True) -> ConnectionSuite:
        """
        Run complete connectivity test suite
        
        Args:
            include_performance: Include performance benchmarking tests
            
        Returns:
            ConnectionSuite with all test results
        """
        start_time = time.time()
        tests = []
        
        try:
            self.logger.info("Starting connectivity test suite")
            
            # Core connectivity tests
            test_tasks = [
                self._test_vast_connection(),
                self._test_s3_connection(),
                self._test_network_connectivity(),
            ]
            
            if include_performance:
                test_tasks.extend([
                    self._test_vast_performance(),
                    self._test_s3_performance(),
                ])
            
            # Run tests in parallel
            test_results = await asyncio.gather(*test_tasks, return_exceptions=True)
            
            # Process results
            for result in test_results:
                if isinstance(result, Exception):
                    tests.append(ConnectionTest(
                        test_name="connection_test_error",
                        status=ConnectionStatus.ERROR,
                        response_time_ms=0,
                        message=f"Test failed: {str(result)}",
                        error=str(result)
                    ))
                elif isinstance(result, ConnectionTest):
                    tests.append(result)
                elif isinstance(result, list):
                    tests.extend(result)
            
            # Calculate suite results
            suite = self._calculate_suite_results("Complete Connectivity", tests)
            
            # Store in history
            self._update_test_history(suite)
            
            total_time = (time.time() - start_time) * 1000
            self.logger.info(f"Connectivity suite completed in {total_time:.2f}ms - Status: {suite.overall_status.value}")
            
            return suite
            
        except Exception as e:
            self.logger.error(f"Connectivity suite failed: {e}")
            error_test = ConnectionTest(
                test_name="connectivity_suite",
                status=ConnectionStatus.ERROR,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"Connectivity suite failed: {str(e)}",
                error=str(e)
            )
            return ConnectionSuite(
                suite_name="Complete Connectivity",
                overall_status=ConnectionStatus.ERROR,
                tests=[error_test],
                total_tests=1,
                passed_tests=0,
                failed_tests=1,
                average_response_time=error_test.response_time_ms,
                timestamp=datetime.utcnow(),
                summary="Connectivity suite failed due to internal error"
            )
    
    async def _test_vast_connection(self) -> ConnectionTest:
        """Test VAST database connectivity"""
        start_time = time.time()
        test_name = "vast_database_connection"
        
        try:
            # Import here to avoid circular dependencies
            from ...core.dependencies import get_vast_store, set_vast_store
            from ...core.config import get_settings
            from ...storage.vast_store import VASTStore
            
            settings = get_settings()
            
            # Try to get existing store, or create one for diagnostics
            try:
                store = get_vast_store()
            except Exception:
                # No store initialized, create one for diagnostics
                store = VASTStore(
                    endpoint=settings.vast_endpoint,
                    access_key=settings.vast_access_key,
                    secret_key=settings.vast_secret_key,
                    bucket=settings.vast_bucket,
                    schema=settings.vast_schema
                )
                set_vast_store(store)
            
            if not store:
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.DISCONNECTED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="VAST store could not be initialized",
                    details={"endpoint": settings.vast_endpoint}
                )
            
            # Test basic connection
            connection_manager = store.db_manager.connection_manager
            is_connected = connection_manager.is_connected()
            
            if not is_connected:
                # Try to connect
                connection_manager.connect()
                is_connected = connection_manager.is_connected()
            
            response_time = (time.time() - start_time) * 1000
            
            if is_connected:
                # Test basic operations
                tables = store.db_manager.list_tables()
                
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.CONNECTED,
                    response_time_ms=response_time,
                    message=f"VAST database connected successfully - {len(tables)} tables available",
                    details={
                        "endpoint": settings.vast_endpoint,
                        "bucket": settings.vast_bucket,
                        "schema": settings.vast_schema,
                        "table_count": len(tables),
                        "connection_manager": "active"
                    }
                )
            else:
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.DISCONNECTED,
                    response_time_ms=response_time,
                    message="Failed to connect to VAST database",
                    details={
                        "endpoint": settings.vast_endpoint,
                        "bucket": settings.vast_bucket,
                        "schema": settings.vast_schema
                    }
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTest(
                test_name=test_name,
                status=ConnectionStatus.ERROR,
                response_time_ms=response_time,
                message=f"VAST connection test failed: {str(e)}",
                error=str(e),
                details={"error_type": type(e).__name__}
            )
    
    async def _test_s3_connection(self) -> ConnectionTest:
        """Test S3 storage connectivity"""
        start_time = time.time()
        test_name = "s3_storage_connection"
        
        try:
            # Import here to avoid circular dependencies
            from ...core.dependencies import get_vast_store
            from ...core.config import get_settings
            
            settings = get_settings()
            store = get_vast_store()
            
            if not store or not store.s3_store:
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.DISCONNECTED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="S3 store not initialized",
                    details={"endpoint": settings.s3_endpoint_url}
                )
            
            # Test S3 connection
            s3_store = store.s3_store
            bucket_exists = await s3_store.bucket_exists()
            
            response_time = (time.time() - start_time) * 1000
            
            if bucket_exists:
                # Test basic operations
                try:
                    objects = await s3_store.list_objects(max_keys=1)
                    object_count = len(objects) if objects else 0
                    
                    return ConnectionTest(
                        test_name=test_name,
                        status=ConnectionStatus.CONNECTED,
                        response_time_ms=response_time,
                        message=f"S3 storage connected successfully - bucket accessible",
                        details={
                            "endpoint": settings.s3_endpoint_url,
                            "bucket": settings.s3_bucket_name,
                            "bucket_exists": True,
                            "ssl_enabled": settings.s3_use_ssl,
                            "test_object_count": object_count
                        }
                    )
                except Exception as list_error:
                    return ConnectionTest(
                        test_name=test_name,
                        status=ConnectionStatus.CONNECTED,
                        response_time_ms=response_time,
                        message=f"S3 bucket accessible but list operation failed",
                        details={
                            "endpoint": settings.s3_endpoint_url,
                            "bucket": settings.s3_bucket_name,
                            "bucket_exists": True,
                            "list_error": str(list_error)
                        }
                    )
            else:
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.DISCONNECTED,
                    response_time_ms=response_time,
                    message="S3 bucket not accessible",
                    details={
                        "endpoint": settings.s3_endpoint_url,
                        "bucket": settings.s3_bucket_name,
                        "bucket_exists": False
                    }
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTest(
                test_name=test_name,
                status=ConnectionStatus.ERROR,
                response_time_ms=response_time,
                message=f"S3 connection test failed: {str(e)}",
                error=str(e),
                details={"error_type": type(e).__name__}
            )
    
    async def _test_network_connectivity(self) -> List[ConnectionTest]:
        """Test network connectivity to various endpoints"""
        tests = []
        
        try:
            from ...core.config import get_settings
            import socket
            
            settings = get_settings()
            
            # Extract hostnames from endpoints
            endpoints_to_test = []
            
            # VAST endpoint
            if settings.vast_endpoint:
                vast_host = settings.vast_endpoint.replace("http://", "").replace("https://", "").split(":")[0]
                endpoints_to_test.append(("vast_host", vast_host, 80))
            
            # S3 endpoint
            if settings.s3_endpoint_url:
                s3_host = settings.s3_endpoint_url.replace("http://", "").replace("https://", "").split(":")[0]
                endpoints_to_test.append(("s3_host", s3_host, 80))
            
            # Test each endpoint
            for test_name, hostname, port in endpoints_to_test:
                start_time = time.time()
                
                try:
                    # Test DNS resolution
                    ip_address = socket.gethostbyname(hostname)
                    
                    # Test port connectivity
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5.0)  # 5 second timeout
                    result = sock.connect_ex((hostname, port))
                    sock.close()
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    if result == 0:
                        tests.append(ConnectionTest(
                            test_name=f"network_{test_name}",
                            status=ConnectionStatus.CONNECTED,
                            response_time_ms=response_time,
                            message=f"Network connectivity to {hostname} successful",
                            details={
                                "hostname": hostname,
                                "ip_address": ip_address,
                                "port": port,
                                "dns_resolution": "successful"
                            }
                        ))
                    else:
                        tests.append(ConnectionTest(
                            test_name=f"network_{test_name}",
                            status=ConnectionStatus.DISCONNECTED,
                            response_time_ms=response_time,
                            message=f"Network connectivity to {hostname}:{port} failed",
                            details={
                                "hostname": hostname,
                                "ip_address": ip_address,
                                "port": port,
                                "connection_result": result
                            }
                        ))
                        
                except socket.gaierror as e:
                    response_time = (time.time() - start_time) * 1000
                    tests.append(ConnectionTest(
                        test_name=f"network_{test_name}",
                        status=ConnectionStatus.ERROR,
                        response_time_ms=response_time,
                        message=f"DNS resolution failed for {hostname}",
                        error=str(e),
                        details={"hostname": hostname, "error_type": "dns_resolution"}
                    ))
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    tests.append(ConnectionTest(
                        test_name=f"network_{test_name}",
                        status=ConnectionStatus.ERROR,
                        response_time_ms=response_time,
                        message=f"Network test failed for {hostname}: {str(e)}",
                        error=str(e),
                        details={"hostname": hostname}
                    ))
            
            return tests
            
        except Exception as e:
            return [ConnectionTest(
                test_name="network_connectivity",
                status=ConnectionStatus.ERROR,
                response_time_ms=0,
                message=f"Network connectivity test failed: {str(e)}",
                error=str(e)
            )]
    
    async def _test_vast_performance(self) -> ConnectionTest:
        """Test VAST database performance"""
        start_time = time.time()
        test_name = "vast_performance"
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store:
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.DISCONNECTED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="VAST store not available for performance test"
                )
            
            # Test basic query performance
            perf_tests = []
            
            # Test 1: List tables
            table_start = time.time()
            tables = store.db_manager.list_tables()
            table_time = (time.time() - table_start) * 1000
            perf_tests.append(("list_tables", table_time, len(tables)))
            
            # Test 2: Simple query on sources table (if exists)
            if "sources" in tables:
                query_start = time.time()
                try:
                    result = await store.db_manager.data_operations.query_with_predicates(
                        "sources", {}, limit=1
                    )
                    query_time = (time.time() - query_start) * 1000
                    row_count = len(result) if result else 0
                    perf_tests.append(("simple_query", query_time, row_count))
                except Exception as query_error:
                    query_time = (time.time() - query_start) * 1000
                    perf_tests.append(("simple_query", query_time, f"Error: {str(query_error)}"))
            
            response_time = (time.time() - start_time) * 1000
            avg_query_time = sum(test[1] for test in perf_tests) / len(perf_tests) if perf_tests else 0
            
            # Determine performance status
            if avg_query_time > 5000:  # > 5 seconds
                status = ConnectionStatus.TIMEOUT
                message = f"VAST performance poor: avg {avg_query_time:.2f}ms"
            elif avg_query_time > 1000:  # > 1 second
                status = ConnectionStatus.CONNECTED
                message = f"VAST performance acceptable: avg {avg_query_time:.2f}ms"
            else:
                status = ConnectionStatus.CONNECTED
                message = f"VAST performance good: avg {avg_query_time:.2f}ms"
            
            return ConnectionTest(
                test_name=test_name,
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "performance_tests": perf_tests,
                    "average_query_time": avg_query_time,
                    "total_tests": len(perf_tests)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTest(
                test_name=test_name,
                status=ConnectionStatus.ERROR,
                response_time_ms=response_time,
                message=f"VAST performance test failed: {str(e)}",
                error=str(e)
            )
    
    async def _test_s3_performance(self) -> ConnectionTest:
        """Test S3 storage performance"""
        start_time = time.time()
        test_name = "s3_performance"
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store or not store.s3_store:
                return ConnectionTest(
                    test_name=test_name,
                    status=ConnectionStatus.DISCONNECTED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="S3 store not available for performance test"
                )
            
            s3_store = store.s3_store
            perf_tests = []
            
            # Test 1: Bucket existence check
            bucket_start = time.time()
            bucket_exists = await s3_store.bucket_exists()
            bucket_time = (time.time() - bucket_start) * 1000
            perf_tests.append(("bucket_check", bucket_time, bucket_exists))
            
            # Test 2: List objects (small sample)
            if bucket_exists:
                list_start = time.time()
                try:
                    objects = await s3_store.list_objects(max_keys=5)
                    list_time = (time.time() - list_start) * 1000
                    object_count = len(objects) if objects else 0
                    perf_tests.append(("list_objects", list_time, object_count))
                except Exception as list_error:
                    list_time = (time.time() - list_start) * 1000
                    perf_tests.append(("list_objects", list_time, f"Error: {str(list_error)}"))
            
            response_time = (time.time() - start_time) * 1000
            avg_operation_time = sum(test[1] for test in perf_tests) / len(perf_tests) if perf_tests else 0
            
            # Determine performance status
            if avg_operation_time > 3000:  # > 3 seconds
                status = ConnectionStatus.TIMEOUT
                message = f"S3 performance poor: avg {avg_operation_time:.2f}ms"
            elif avg_operation_time > 1000:  # > 1 second
                status = ConnectionStatus.CONNECTED
                message = f"S3 performance acceptable: avg {avg_operation_time:.2f}ms"
            else:
                status = ConnectionStatus.CONNECTED
                message = f"S3 performance good: avg {avg_operation_time:.2f}ms"
            
            return ConnectionTest(
                test_name=test_name,
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "performance_tests": perf_tests,
                    "average_operation_time": avg_operation_time,
                    "total_tests": len(perf_tests)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTest(
                test_name=test_name,
                status=ConnectionStatus.ERROR,
                response_time_ms=response_time,
                message=f"S3 performance test failed: {str(e)}",
                error=str(e)
            )
    
    def _calculate_suite_results(self, suite_name: str, tests: List[ConnectionTest]) -> ConnectionSuite:
        """Calculate overall suite results from individual tests"""
        if not tests:
            return ConnectionSuite(
                suite_name=suite_name,
                overall_status=ConnectionStatus.UNKNOWN,
                tests=[],
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                average_response_time=0.0,
                timestamp=datetime.utcnow(),
                summary="No tests performed"
            )
        
        # Count status types
        passed_count = sum(1 for test in tests if test.status == ConnectionStatus.CONNECTED)
        failed_count = len(tests) - passed_count
        
        # Calculate average response time
        total_response_time = sum(test.response_time_ms for test in tests)
        avg_response_time = total_response_time / len(tests)
        
        # Determine overall status
        error_count = sum(1 for test in tests if test.status == ConnectionStatus.ERROR)
        timeout_count = sum(1 for test in tests if test.status == ConnectionStatus.TIMEOUT)
        disconnected_count = sum(1 for test in tests if test.status == ConnectionStatus.DISCONNECTED)
        
        if error_count > 0:
            overall_status = ConnectionStatus.ERROR
        elif disconnected_count > 0:
            overall_status = ConnectionStatus.DISCONNECTED
        elif timeout_count > 0:
            overall_status = ConnectionStatus.TIMEOUT
        else:
            overall_status = ConnectionStatus.CONNECTED
        
        # Generate summary
        if overall_status == ConnectionStatus.CONNECTED:
            summary = f"All {len(tests)} connectivity tests passed"
        else:
            summary = f"{failed_count} of {len(tests)} connectivity tests failed"
        
        return ConnectionSuite(
            suite_name=suite_name,
            overall_status=overall_status,
            tests=tests,
            total_tests=len(tests),
            passed_tests=passed_count,
            failed_tests=failed_count,
            average_response_time=avg_response_time,
            timestamp=datetime.utcnow(),
            summary=summary
        )
    
    def _update_test_history(self, suite: ConnectionSuite):
        """Update test history"""
        self.test_history.append(suite)
        
        # Maintain history size
        if len(self.test_history) > self.max_history:
            self.test_history.pop(0)
    
    def get_connectivity_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get connectivity trend analysis"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_tests = [t for t in self.test_history if t.timestamp >= cutoff_time]
        
        if not recent_tests:
            return {"trend": "no_data", "message": "No recent connectivity data available"}
        
        # Analyze trend
        connected_count = sum(1 for t in recent_tests if t.overall_status == ConnectionStatus.CONNECTED)
        total_count = len(recent_tests)
        success_rate = connected_count / total_count if total_count else 0
        
        # Calculate trend
        if len(recent_tests) >= 2:
            recent_success = recent_tests[-1].overall_status == ConnectionStatus.CONNECTED
            older_success = recent_tests[-2].overall_status == ConnectionStatus.CONNECTED
            
            if recent_success and not older_success:
                trend = "improving"
            elif not recent_success and older_success:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "period_hours": hours,
            "total_tests": total_count,
            "success_rate": success_rate,
            "average_response_time": sum(t.average_response_time for t in recent_tests) / total_count if recent_tests else 0,
            "latest_status": recent_tests[-1].overall_status.value if recent_tests else "unknown"
        }
    
    async def diagnose_connection_issues(self) -> List[Dict[str, Any]]:
        """Diagnose connection issues and provide solutions"""
        issues = []
        
        try:
            # Run connectivity tests
            suite = await self.run_connectivity_suite(include_performance=False)
            
            # Analyze failed tests
            for test in suite.tests:
                if test.status != ConnectionStatus.CONNECTED:
                    suggestions = self._get_connection_suggestions(test)
                    issues.append({
                        "test_name": test.test_name,
                        "status": test.status.value,
                        "message": test.message,
                        "suggestions": suggestions,
                        "details": test.details,
                        "error": test.error
                    })
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Connection diagnosis failed: {e}")
            return [{
                "test_name": "diagnosis_error",
                "status": "error",
                "message": f"Connection diagnosis failed: {str(e)}",
                "suggestions": ["Check system logs", "Verify network connectivity", "Restart services"],
                "details": {"error": str(e)}
            }]
    
    def _get_connection_suggestions(self, test: ConnectionTest) -> List[str]:
        """Get specific suggestions for connection issues"""
        suggestions = []
        
        if "vast" in test.test_name.lower():
            suggestions.extend([
                "Verify VAST database server is running and accessible",
                "Check VAST endpoint URL in configuration",
                "Verify VAST credentials (access_key, secret_key)",
                "Check network connectivity to VAST server",
                "Review VAST database logs for errors",
                "Ensure VAST bucket and schema exist"
            ])
        elif "s3" in test.test_name.lower():
            suggestions.extend([
                "Verify S3 service is running and accessible",
                "Check S3 endpoint URL in configuration",
                "Verify S3 credentials (access_key_id, secret_access_key)",
                "Check network connectivity to S3 server",
                "Ensure S3 bucket exists and is accessible",
                "Verify S3 permissions for bucket operations"
            ])
        elif "network" in test.test_name.lower():
            suggestions.extend([
                "Check network connectivity to target host",
                "Verify DNS resolution is working",
                "Check firewall rules and port accessibility",
                "Verify target service is running on expected port",
                "Check network routing and proxy settings"
            ])
        elif "performance" in test.test_name.lower():
            suggestions.extend([
                "Check system resource usage (CPU, memory, disk)",
                "Monitor network latency and bandwidth",
                "Review database query performance",
                "Check for system bottlenecks",
                "Consider optimizing queries or increasing resources"
            ])
        else:
            suggestions.extend([
                "Check system logs for more details",
                "Verify service configuration",
                "Restart affected services",
                "Contact system administrator"
            ])
        
        return suggestions
