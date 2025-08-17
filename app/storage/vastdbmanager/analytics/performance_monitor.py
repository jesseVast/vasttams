"""Performance monitoring and system health for VastDBManager"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_type: str
    table_name: str
    execution_time: float
    rows_returned: int
    splits_used: int
    subsplits_used: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class PerformanceMonitor:
    """Monitors query performance and system health"""
    
    def __init__(self):
        """Initialize performance monitor"""
        self.query_metrics: List[QueryMetrics] = []
        self.max_metrics_history = 1000
        self.slow_query_threshold = 5.0  # seconds
    
    def record_query(self, query_type: str, table_name: str, execution_time: float,
                     rows_returned: int, splits_used: int, subsplits_used: int,
                     success: bool, error_message: Optional[str] = None):
        """Record query performance metrics"""
        try:
            metric = QueryMetrics(
                query_type=query_type,
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=rows_returned,
                splits_used=splits_used,
                subsplits_used=subsplits_used,
                timestamp=datetime.now(),
                success=success,
                error_message=error_message
            )
            
            self.query_metrics.append(metric)
            
            # Maintain history size
            if len(self.query_metrics) > self.max_metrics_history:
                self.query_metrics.pop(0)
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning("Slow query detected: %s on %s took %.2fs", 
                             query_type, table_name, execution_time)
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Recorded %s query on %s: %.3fs, %d rows", 
                           query_type, table_name, execution_time, rows_returned)
                        
        except Exception as e:
            logger.error("Error recording query metrics: %s", e)
    
    def get_performance_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary for the specified time window"""
        try:
            cutoff_time = datetime.now() - time_window
            recent_metrics = [
                m for m in self.query_metrics 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"message": "No metrics available for the specified time window"}
            
            # Calculate statistics
            total_queries = len(recent_metrics)
            successful_queries = len([m for m in recent_metrics if m.success])
            failed_queries = total_queries - successful_queries
            
            execution_times = [m.execution_time for m in recent_metrics if m.success]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            max_execution_time = max(execution_times) if execution_times else 0
            
            # Query type breakdown
            query_types = {}
            for metric in recent_metrics:
                query_type = metric.query_type
                if query_type not in query_types:
                    query_types[query_type] = {"count": 0, "avg_time": 0, "total_rows": 0}
                
                query_types[query_type]["count"] += 1
                if metric.success:
                    query_types[query_type]["total_rows"] += metric.rows_returned
            
            # Calculate average time per query type
            for query_type, stats in query_types.items():
                type_metrics = [m for m in recent_metrics if m.query_type == query_type and m.success]
                if type_metrics:
                    stats["avg_time"] = sum(m.execution_time for m in type_metrics) / len(type_metrics)
            
            return {
                "time_window_hours": time_window.total_seconds() / 3600,
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "failed_queries": failed_queries,
                "success_rate": (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                "avg_execution_time": avg_execution_time,
                "max_execution_time": max_execution_time,
                "query_types": query_types,
                "total_rows_processed": sum(m.rows_returned for m in recent_metrics if m.success)
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return {"error": str(e)}
    
    def get_slow_queries(self, threshold: float = 5.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of slow queries above threshold"""
        try:
            slow_queries = [
                m for m in self.query_metrics 
                if m.execution_time > threshold
            ]
            
            # Sort by execution time (slowest first)
            slow_queries.sort(key=lambda x: x.execution_time, reverse=True)
            
            # Return limited results
            return [
                {
                    "query_type": m.query_type,
                    "table_name": m.table_name,
                    "execution_time": m.execution_time,
                    "rows_returned": m.rows_returned,
                    "timestamp": m.timestamp.isoformat(),
                    "success": m.success
                }
                for m in slow_queries[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    def get_table_performance(self, table_name: str, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance metrics for a specific table"""
        try:
            cutoff_time = datetime.now() - time_window
            table_metrics = [
                m for m in self.query_metrics 
                if m.table_name == table_name and m.timestamp >= cutoff_time
            ]
            
            if not table_metrics:
                return {"message": f"No metrics available for table {table_name}"}
            
            # Calculate table-specific statistics
            total_queries = len(table_metrics)
            successful_queries = len([m for m in table_metrics if m.success])
            
            execution_times = [m.execution_time for m in table_metrics if m.success]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            total_rows = sum(m.rows_returned for m in table_metrics if m.success)
            
            return {
                "table_name": table_name,
                "time_window_hours": time_window.total_seconds() / 3600,
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                "avg_execution_time": avg_execution_time,
                "total_rows_processed": total_rows,
                "avg_rows_per_query": total_rows / successful_queries if successful_queries > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting table performance for {table_name}: {e}")
            return {"error": str(e)}
    
    def clear_metrics(self):
        """Clear all stored metrics"""
        self.query_metrics.clear()
        logger.info("Cleared all performance metrics")
    
    def export_metrics(self) -> List[Dict[str, Any]]:
        """Export all metrics for external analysis"""
        try:
            return [
                {
                    "query_type": m.query_type,
                    "table_name": m.table_name,
                    "execution_time": m.execution_time,
                    "rows_returned": m.rows_returned,
                    "splits_used": m.splits_used,
                    "subsplits_used": m.subsplits_used,
                    "timestamp": m.timestamp.isoformat(),
                    "success": m.success,
                    "error_message": m.error_message
                }
                for m in self.query_metrics
            ]
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return []
