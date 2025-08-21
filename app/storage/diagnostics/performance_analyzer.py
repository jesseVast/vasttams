"""
Performance Analyzer for TAMS Storage Systems

Analyzes query performance, system performance, and identifies bottlenecks
in the storage layer with detailed metrics and recommendations.
"""

import logging
import time
import asyncio
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceStatus(Enum):
    """Performance status levels"""
    EXCELLENT = "excellent"
    GOOD = "good" 
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QueryMetric:
    """Individual query performance metric"""
    query_type: str
    table_name: str
    execution_time_ms: float
    rows_returned: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceBenchmark:
    """Performance benchmark result"""
    benchmark_name: str
    status: PerformanceStatus
    execution_time_ms: float
    throughput: Optional[float] = None  # operations per second
    memory_usage_mb: Optional[float] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass 
class PerformanceReport:
    """Comprehensive performance analysis report"""
    overall_status: PerformanceStatus
    benchmarks: List[PerformanceBenchmark]
    query_metrics: List[QueryMetric]
    performance_score: float
    bottlenecks: List[str]
    recommendations: List[str]
    timestamp: datetime
    summary: str


class PerformanceAnalyzer:
    """Analyze query and system performance"""
    
    def __init__(self):
        """Initialize performance analyzer"""
        self.logger = logging.getLogger(__name__)
        self.query_history: List[QueryMetric] = []
        self.benchmark_history: List[PerformanceBenchmark] = []
        self.max_history = 1000
        
        # Performance thresholds (in milliseconds)
        self.thresholds = {
            "excellent": 100,    # < 100ms
            "good": 500,         # < 500ms  
            "acceptable": 1000,  # < 1s
            "poor": 5000,        # < 5s
            "critical": float('inf')  # >= 5s
        }
    
    async def analyze_performance(self, include_benchmarks: bool = True) -> PerformanceReport:
        """
        Run comprehensive performance analysis
        
        Args:
            include_benchmarks: Include performance benchmarking tests
            
        Returns:
            PerformanceReport with detailed analysis
        """
        start_time = time.time()
        benchmarks = []
        query_metrics = []
        
        try:
            self.logger.info("Starting performance analysis")
            
            # Core performance tests
            analysis_tasks = [
                self._analyze_query_performance(),
                self._analyze_connection_performance(),
            ]
            
            if include_benchmarks:
                analysis_tasks.extend([
                    self._run_database_benchmarks(),
                    self._run_storage_benchmarks(),
                ])
            
            # Run analysis in parallel
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    benchmarks.append(PerformanceBenchmark(
                        benchmark_name="analysis_error",
                        status=PerformanceStatus.CRITICAL,
                        execution_time_ms=0,
                        message=f"Analysis failed: {str(result)}"
                    ))
                elif isinstance(result, dict):
                    if "benchmarks" in result:
                        benchmarks.extend(result["benchmarks"])
                    if "metrics" in result:
                        query_metrics.extend(result["metrics"])
                elif isinstance(result, list):
                    # Assume it's a list of benchmarks
                    benchmarks.extend(result)
            
            # Calculate overall performance
            report = self._generate_performance_report(benchmarks, query_metrics)
            
            # Store in history
            self._update_performance_history(benchmarks, query_metrics)
            
            total_time = (time.time() - start_time) * 1000
            self.logger.info(f"Performance analysis completed in {total_time:.2f}ms - Score: {report.performance_score:.1f}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            error_benchmark = PerformanceBenchmark(
                benchmark_name="performance_analysis",
                status=PerformanceStatus.CRITICAL,
                execution_time_ms=(time.time() - start_time) * 1000,
                message=f"Performance analysis failed: {str(e)}"
            )
            return PerformanceReport(
                overall_status=PerformanceStatus.CRITICAL,
                benchmarks=[error_benchmark],
                query_metrics=[],
                performance_score=0.0,
                bottlenecks=["Analysis failure"],
                recommendations=["Check system logs", "Verify system health"],
                timestamp=datetime.utcnow(),
                summary="Performance analysis failed due to internal error"
            )
    
    async def _analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze database query performance"""
        start_time = time.time()
        benchmarks = []
        metrics = []
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store:
                return {
                    "benchmarks": [PerformanceBenchmark(
                        benchmark_name="query_performance",
                        status=PerformanceStatus.CRITICAL,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        message="VAST store not available for query analysis"
                    )],
                    "metrics": []
                }
            
            # Test different query types
            query_tests = [
                ("list_tables", self._test_list_tables_performance, store),
                ("simple_select", self._test_simple_select_performance, store),
                ("filtered_query", self._test_filtered_query_performance, store),
            ]
            
            for test_name, test_func, store_param in query_tests:
                test_start = time.time()
                try:
                    result = await test_func(store_param)
                    test_time = (time.time() - test_start) * 1000
                    
                    # Create metric
                    metric = QueryMetric(
                        query_type=test_name,
                        table_name=result.get("table", "N/A"),
                        execution_time_ms=test_time,
                        rows_returned=result.get("rows", 0),
                        timestamp=datetime.utcnow(),
                        success=True,
                        details=result
                    )
                    metrics.append(metric)
                    
                    # Create benchmark
                    status = self._get_performance_status(test_time)
                    benchmarks.append(PerformanceBenchmark(
                        benchmark_name=f"query_{test_name}",
                        status=status,
                        execution_time_ms=test_time,
                        message=f"Query {test_name}: {test_time:.2f}ms, {result.get('rows', 0)} rows",
                        details=result
                    ))
                    
                except Exception as e:
                    test_time = (time.time() - test_start) * 1000
                    metrics.append(QueryMetric(
                        query_type=test_name,
                        table_name="error",
                        execution_time_ms=test_time,
                        rows_returned=0,
                        timestamp=datetime.utcnow(),
                        success=False,
                        error_message=str(e)
                    ))
                    
                    benchmarks.append(PerformanceBenchmark(
                        benchmark_name=f"query_{test_name}",
                        status=PerformanceStatus.CRITICAL,
                        execution_time_ms=test_time,
                        message=f"Query {test_name} failed: {str(e)}"
                    ))
            
            return {"benchmarks": benchmarks, "metrics": metrics}
            
        except Exception as e:
            return {
                "benchmarks": [PerformanceBenchmark(
                    benchmark_name="query_performance",
                    status=PerformanceStatus.CRITICAL,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    message=f"Query performance analysis failed: {str(e)}"
                )],
                "metrics": []
            }
    
    async def _test_list_tables_performance(self, store) -> Dict[str, Any]:
        """Test list tables performance"""
        tables = store.db_manager.list_tables()
        return {"table": "system", "rows": len(tables), "tables": tables}
    
    async def _test_simple_select_performance(self, store) -> Dict[str, Any]:
        """Test simple select query performance"""
        tables = store.db_manager.list_tables()
        if "sources" in tables:
            result = await store.db_manager.data_operations.query_with_predicates(
                "sources", {}, limit=5
            )
            return {"table": "sources", "rows": len(result) if result else 0}
        else:
            return {"table": "none", "rows": 0, "message": "No sources table found"}
    
    async def _test_filtered_query_performance(self, store) -> Dict[str, Any]:
        """Test filtered query performance"""
        tables = store.db_manager.list_tables()
        if "sources" in tables:
            result = await store.db_manager.data_operations.query_with_predicates(
                "sources", {"format": ["urn:x-nmos:format:video"]}, limit=5
            )
            return {"table": "sources", "rows": len(result) if result else 0, "filter": "format=video"}
        else:
            return {"table": "none", "rows": 0, "message": "No sources table found"}
    
    async def _analyze_connection_performance(self) -> List[PerformanceBenchmark]:
        """Analyze connection performance"""
        benchmarks = []
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store:
                return [PerformanceBenchmark(
                    benchmark_name="connection_performance",
                    status=PerformanceStatus.CRITICAL,
                    execution_time_ms=0,
                    message="Store not available for connection analysis"
                )]
            
            # Test VAST connection performance
            vast_start = time.time()
            is_connected = store.db_manager.connection_manager.is_connected()
            vast_time = (time.time() - vast_start) * 1000
            
            vast_status = self._get_performance_status(vast_time)
            benchmarks.append(PerformanceBenchmark(
                benchmark_name="vast_connection_check",
                status=vast_status,
                execution_time_ms=vast_time,
                message=f"VAST connection check: {vast_time:.2f}ms, connected: {is_connected}",
                details={"connected": is_connected}
            ))
            
            # Test S3 connection performance if available
            if store.s3_store:
                s3_start = time.time()
                try:
                    bucket_exists = await store.s3_store.bucket_exists()
                    s3_time = (time.time() - s3_start) * 1000
                    
                    s3_status = self._get_performance_status(s3_time)
                    benchmarks.append(PerformanceBenchmark(
                        benchmark_name="s3_connection_check",
                        status=s3_status,
                        execution_time_ms=s3_time,
                        message=f"S3 connection check: {s3_time:.2f}ms, bucket exists: {bucket_exists}",
                        details={"bucket_exists": bucket_exists}
                    ))
                except Exception as e:
                    s3_time = (time.time() - s3_start) * 1000
                    benchmarks.append(PerformanceBenchmark(
                        benchmark_name="s3_connection_check",
                        status=PerformanceStatus.CRITICAL,
                        execution_time_ms=s3_time,
                        message=f"S3 connection check failed: {str(e)}"
                    ))
            
            return benchmarks
            
        except Exception as e:
            return [PerformanceBenchmark(
                benchmark_name="connection_performance",
                status=PerformanceStatus.CRITICAL,
                execution_time_ms=0,
                message=f"Connection performance analysis failed: {str(e)}"
            )]
    
    async def _run_database_benchmarks(self) -> List[PerformanceBenchmark]:
        """Run database performance benchmarks"""
        benchmarks = []
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store:
                return [PerformanceBenchmark(
                    benchmark_name="database_benchmarks",
                    status=PerformanceStatus.CRITICAL,
                    execution_time_ms=0,
                    message="Store not available for database benchmarks"
                )]
            
            # Benchmark 1: Table operations
            table_start = time.time()
            tables = store.db_manager.list_tables()
            table_time = (time.time() - table_start) * 1000
            
            table_status = self._get_performance_status(table_time)
            benchmarks.append(PerformanceBenchmark(
                benchmark_name="table_operations",
                status=table_status,
                execution_time_ms=table_time,
                throughput=len(tables) / (table_time / 1000) if table_time > 0 else 0,
                message=f"Table operations: {table_time:.2f}ms for {len(tables)} tables"
            ))
            
            # Benchmark 2: Cache performance (if available)
            if hasattr(store.db_manager, 'cache_manager'):
                cache_start = time.time()
                cache_stats = {}
                for table in tables[:3]:  # Test first 3 tables
                    stats = store.db_manager.cache_manager.get_table_stats(table)
                    cache_stats[table] = stats
                cache_time = (time.time() - cache_start) * 1000
                
                cache_status = self._get_performance_status(cache_time)
                benchmarks.append(PerformanceBenchmark(
                    benchmark_name="cache_operations",
                    status=cache_status,
                    execution_time_ms=cache_time,
                    throughput=len(cache_stats) / (cache_time / 1000) if cache_time > 0 else 0,
                    message=f"Cache operations: {cache_time:.2f}ms for {len(cache_stats)} lookups"
                ))
            
            return benchmarks
            
        except Exception as e:
            return [PerformanceBenchmark(
                benchmark_name="database_benchmarks",
                status=PerformanceStatus.CRITICAL,
                execution_time_ms=0,
                message=f"Database benchmarks failed: {str(e)}"
            )]
    
    async def _run_storage_benchmarks(self) -> List[PerformanceBenchmark]:
        """Run storage performance benchmarks"""
        benchmarks = []
        
        try:
            from ...core.dependencies import get_vast_store
            
            store = get_vast_store()
            if not store or not store.s3_store:
                return [PerformanceBenchmark(
                    benchmark_name="storage_benchmarks",
                    status=PerformanceStatus.CRITICAL,
                    execution_time_ms=0,
                    message="S3 store not available for storage benchmarks"
                )]
            
            s3_store = store.s3_store
            
            # Benchmark 1: S3 list operations
            list_start = time.time()
            try:
                objects = await s3_store.list_objects(max_keys=10)
                list_time = (time.time() - list_start) * 1000
                object_count = len(objects) if objects else 0
                
                list_status = self._get_performance_status(list_time)
                benchmarks.append(PerformanceBenchmark(
                    benchmark_name="s3_list_operations",
                    status=list_status,
                    execution_time_ms=list_time,
                    throughput=object_count / (list_time / 1000) if list_time > 0 else 0,
                    message=f"S3 list operations: {list_time:.2f}ms for {object_count} objects"
                ))
            except Exception as e:
                list_time = (time.time() - list_start) * 1000
                benchmarks.append(PerformanceBenchmark(
                    benchmark_name="s3_list_operations",
                    status=PerformanceStatus.CRITICAL,
                    execution_time_ms=list_time,
                    message=f"S3 list operations failed: {str(e)}"
                ))
            
            # Benchmark 2: S3 bucket operations
            bucket_start = time.time()
            try:
                bucket_exists = await s3_store.bucket_exists()
                bucket_time = (time.time() - bucket_start) * 1000
                
                bucket_status = self._get_performance_status(bucket_time)
                benchmarks.append(PerformanceBenchmark(
                    benchmark_name="s3_bucket_operations",
                    status=bucket_status,
                    execution_time_ms=bucket_time,
                    message=f"S3 bucket operations: {bucket_time:.2f}ms, exists: {bucket_exists}"
                ))
            except Exception as e:
                bucket_time = (time.time() - bucket_start) * 1000
                benchmarks.append(PerformanceBenchmark(
                    benchmark_name="s3_bucket_operations",
                    status=PerformanceStatus.CRITICAL,
                    execution_time_ms=bucket_time,
                    message=f"S3 bucket operations failed: {str(e)}"
                ))
            
            return benchmarks
            
        except Exception as e:
            return [PerformanceBenchmark(
                benchmark_name="storage_benchmarks",
                status=PerformanceStatus.CRITICAL,
                execution_time_ms=0,
                message=f"Storage benchmarks failed: {str(e)}"
            )]
    
    def _get_performance_status(self, execution_time_ms: float) -> PerformanceStatus:
        """Determine performance status based on execution time"""
        if execution_time_ms < self.thresholds["excellent"]:
            return PerformanceStatus.EXCELLENT
        elif execution_time_ms < self.thresholds["good"]:
            return PerformanceStatus.GOOD
        elif execution_time_ms < self.thresholds["acceptable"]:
            return PerformanceStatus.ACCEPTABLE
        elif execution_time_ms < self.thresholds["poor"]:
            return PerformanceStatus.POOR
        else:
            return PerformanceStatus.CRITICAL
    
    def _generate_performance_report(self, benchmarks: List[PerformanceBenchmark], 
                                   metrics: List[QueryMetric]) -> PerformanceReport:
        """Generate comprehensive performance report"""
        if not benchmarks:
            return PerformanceReport(
                overall_status=PerformanceStatus.CRITICAL,
                benchmarks=[],
                query_metrics=metrics,
                performance_score=0.0,
                bottlenecks=["No performance data available"],
                recommendations=["Run performance benchmarks"],
                timestamp=datetime.utcnow(),
                summary="No performance data available"
            )
        
        # Calculate performance score
        status_scores = {
            PerformanceStatus.EXCELLENT: 100,
            PerformanceStatus.GOOD: 80,
            PerformanceStatus.ACCEPTABLE: 60,
            PerformanceStatus.POOR: 40,
            PerformanceStatus.CRITICAL: 0
        }
        
        total_score = sum(status_scores[benchmark.status] for benchmark in benchmarks)
        performance_score = total_score / len(benchmarks) if benchmarks else 0
        
        # Determine overall status
        critical_count = sum(1 for b in benchmarks if b.status == PerformanceStatus.CRITICAL)
        poor_count = sum(1 for b in benchmarks if b.status == PerformanceStatus.POOR)
        
        if critical_count > 0:
            overall_status = PerformanceStatus.CRITICAL
        elif poor_count > 0:
            overall_status = PerformanceStatus.POOR
        elif performance_score >= 90:
            overall_status = PerformanceStatus.EXCELLENT
        elif performance_score >= 70:
            overall_status = PerformanceStatus.GOOD
        else:
            overall_status = PerformanceStatus.ACCEPTABLE
        
        # Identify bottlenecks
        bottlenecks = []
        slow_benchmarks = [b for b in benchmarks if b.status in [PerformanceStatus.POOR, PerformanceStatus.CRITICAL]]
        for benchmark in slow_benchmarks:
            bottlenecks.append(f"{benchmark.benchmark_name}: {benchmark.execution_time_ms:.2f}ms")
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(benchmarks, metrics, overall_status)
        
        # Generate summary
        if overall_status == PerformanceStatus.EXCELLENT:
            summary = f"Excellent performance: {performance_score:.1f}/100"
        elif overall_status == PerformanceStatus.GOOD:
            summary = f"Good performance: {performance_score:.1f}/100"
        elif overall_status == PerformanceStatus.ACCEPTABLE:
            summary = f"Acceptable performance: {performance_score:.1f}/100"
        else:
            summary = f"Performance issues detected: {performance_score:.1f}/100, {len(bottlenecks)} bottlenecks"
        
        return PerformanceReport(
            overall_status=overall_status,
            benchmarks=benchmarks,
            query_metrics=metrics,
            performance_score=performance_score,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            timestamp=datetime.utcnow(),
            summary=summary
        )
    
    def _generate_performance_recommendations(self, benchmarks: List[PerformanceBenchmark], 
                                            metrics: List[QueryMetric], 
                                            overall_status: PerformanceStatus) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Analyze slow operations
        slow_benchmarks = [b for b in benchmarks if b.status in [PerformanceStatus.POOR, PerformanceStatus.CRITICAL]]
        
        for benchmark in slow_benchmarks:
            if "query" in benchmark.benchmark_name:
                recommendations.extend([
                    f"Optimize {benchmark.benchmark_name} performance (currently {benchmark.execution_time_ms:.2f}ms)",
                    "Consider adding database indexes for frequently queried columns",
                    "Review query complexity and data volume"
                ])
            elif "connection" in benchmark.benchmark_name:
                recommendations.extend([
                    f"Improve {benchmark.benchmark_name} performance",
                    "Check network latency and bandwidth",
                    "Verify database/storage server performance"
                ])
            elif "s3" in benchmark.benchmark_name:
                recommendations.extend([
                    f"Optimize S3 storage performance",
                    "Check S3 server performance and network connectivity", 
                    "Consider S3 configuration optimization"
                ])
        
        # General recommendations based on overall status
        if overall_status in [PerformanceStatus.POOR, PerformanceStatus.CRITICAL]:
            recommendations.extend([
                "Investigate system resource usage (CPU, memory, disk I/O)",
                "Check for concurrent operations that may cause contention",
                "Consider upgrading hardware resources",
                "Review application configuration for performance optimizations"
            ])
        
        # Failed query recommendations
        failed_queries = [m for m in metrics if not m.success]
        if failed_queries:
            recommendations.extend([
                f"Fix {len(failed_queries)} failed queries",
                "Review query syntax and database schema",
                "Check database connectivity and permissions"
            ])
        
        return recommendations if recommendations else ["Performance is optimal - no recommendations needed"]
    
    def _update_performance_history(self, benchmarks: List[PerformanceBenchmark], 
                                  metrics: List[QueryMetric]):
        """Update performance history"""
        # Add to benchmark history
        self.benchmark_history.extend(benchmarks)
        if len(self.benchmark_history) > self.max_history:
            self.benchmark_history = self.benchmark_history[-self.max_history:]
        
        # Add to query history
        self.query_history.extend(metrics)
        if len(self.query_history) > self.max_history:
            self.query_history = self.query_history[-self.max_history:]
    
    def get_performance_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trend analysis"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter recent benchmarks
        recent_benchmarks = [b for b in self.benchmark_history if b.timestamp >= cutoff_time]
        recent_metrics = [m for m in self.query_history if m.timestamp >= cutoff_time]
        
        if not recent_benchmarks and not recent_metrics:
            return {"trend": "no_data", "message": "No recent performance data available"}
        
        # Calculate trends
        trend_data = {
            "period_hours": hours,
            "benchmark_count": len(recent_benchmarks),
            "query_count": len(recent_metrics),
            "average_performance_score": 0,
            "trend": "stable"
        }
        
        if recent_benchmarks:
            # Calculate average performance scores
            status_scores = {
                PerformanceStatus.EXCELLENT: 100,
                PerformanceStatus.GOOD: 80,
                PerformanceStatus.ACCEPTABLE: 60,
                PerformanceStatus.POOR: 40,
                PerformanceStatus.CRITICAL: 0
            }
            
            scores = [status_scores[b.status] for b in recent_benchmarks]
            trend_data["average_performance_score"] = statistics.mean(scores)
            
            # Calculate trend
            if len(scores) >= 2:
                recent_score = statistics.mean(scores[-5:]) if len(scores) >= 5 else scores[-1]
                older_score = statistics.mean(scores[:5]) if len(scores) >= 5 else scores[0]
                
                if recent_score > older_score + 10:
                    trend_data["trend"] = "improving"
                elif recent_score < older_score - 10:
                    trend_data["trend"] = "degrading"
                else:
                    trend_data["trend"] = "stable"
        
        if recent_metrics:
            # Add query performance trends
            successful_queries = [m for m in recent_metrics if m.success]
            if successful_queries:
                avg_query_time = statistics.mean([m.execution_time_ms for m in successful_queries])
                trend_data["average_query_time_ms"] = avg_query_time
                trend_data["query_success_rate"] = len(successful_queries) / len(recent_metrics)
        
        return trend_data
