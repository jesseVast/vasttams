"""Advanced time-series analytics for VastDBManager"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from vastdb import Table

logger = logging.getLogger(__name__)


class TimeSeriesAnalytics:
    """Advanced time-series analytics and window functions"""
    
    def __init__(self, cache_manager):
        """Initialize time-series analytics with cache manager"""
        self.cache_manager = cache_manager
    
    def calculate_moving_average(self, table: Table, config, value_column: str, 
                                time_column: str, window_size: str = "1 hour",
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Calculate moving average over time windows
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to calculate average for
            time_column: Time column for windowing
            window_size: Window size (e.g., "1 hour", "30 minutes", "1 day")
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            List of moving average results
        """
        try:
            # Build time range filter
            time_filter = ""
            if start_time and end_time:
                time_filter = f"{time_column} BETWEEN '{start_time}' AND '{end_time}'"
            
            # Build moving average query using VAST window functions
            columns = [
                f"DATE_TRUNC('{self._parse_window_size(window_size)}', {time_column}) as window_start",
                f"AVG({value_column}) as moving_avg",
                f"COUNT(*) as sample_count"
            ]
            
            query = table.select(columns)
            
            if time_filter:
                query = query.filter(time_filter)
            
            query = query.group_by("window_start").order_by("window_start")
            
            # Execute with time-series optimization
            result = query.collect()
            
            logger.info(f"Calculated moving average for {value_column} with {window_size} windows")
            return result.to_pylist()
            
        except Exception as e:
            logger.error(f"Error calculating moving average: {e}")
            raise
    
    def detect_anomalies(self, table: Table, config, value_column: str, 
                         time_column: str, threshold: float = 2.0,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Detect anomalies using statistical methods
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to analyze for anomalies
            time_column: Time column
            threshold: Standard deviation threshold for anomaly detection
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            List of detected anomalies
        """
        try:
            # Build time range filter
            time_filter = ""
            if start_time and end_time:
                time_filter = f"{time_column} BETWEEN '{start_time}' AND '{end_time}'"
            
            # Calculate statistics for anomaly detection
            stats_columns = [
                f"AVG({value_column}) as mean_value",
                f"STDDEV({value_column}) as std_dev",
                f"MIN({value_column}) as min_value",
                f"MAX({value_column}) as max_value"
            ]
            
            stats_query = table.select(stats_columns)
            if time_filter:
                stats_query = stats_query.filter(time_filter)
            
            stats_result = stats_query.collect().to_pylist()
            
            if not stats_result:
                return []
            
            stats = stats_result[0]
            mean = stats['mean_value']
            std_dev = stats['std_dev']
            
            if not std_dev or std_dev == 0:
                logger.warning("Cannot detect anomalies: no variance in data")
                return []
            
            # Find anomalies beyond threshold
            anomaly_filter = f"({value_column} < {mean - threshold * std_dev} OR {value_column} > {mean + threshold * std_dev})"
            
            if time_filter:
                anomaly_filter = f"({time_filter}) AND ({anomaly_filter})"
            
            anomaly_columns = [
                time_column,
                value_column,
                f"({value_column} - {mean}) / {std_dev} as z_score"
            ]
            
            anomaly_query = table.select(anomaly_columns).filter(anomaly_filter).order_by(time_column)
            anomaly_result = anomaly_query.collect()
            
            logger.info(f"Detected {len(anomaly_result)} anomalies in {value_column}")
            return anomaly_result.to_pylist()
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            raise
    
    def calculate_trends(self, table: Table, config, value_column: str,
                         time_column: str, trend_period: str = "1 day",
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate trend analysis over time periods
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to analyze trends for
            time_column: Time column
            trend_period: Period for trend calculation
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            Trend analysis results
        """
        try:
            # Build time range filter
            time_filter = ""
            if start_time and end_time:
                time_filter = f"{time_column} BETWEEN '{start_time}' AND '{end_time}'"
            
            # Calculate trend using linear regression approximation
            trend_columns = [
                f"DATE_TRUNC('{self._parse_window_size(trend_period)}', {time_column}) as period",
                f"AVG({value_column}) as avg_value",
                f"COUNT(*) as sample_count"
            ]
            
            trend_query = table.select(trend_columns)
            if time_filter:
                trend_query = trend_query.filter(time_filter)
            
            trend_query = trend_query.group_by("period").order_by("period")
            trend_result = trend_query.collect().to_pylist()
            
            if len(trend_result) < 2:
                return {"trend": "insufficient_data", "slope": 0, "periods": len(trend_result)}
            
            # Calculate trend direction and slope
            first_period = trend_result[0]['avg_value']
            last_period = trend_result[-1]['avg_value']
            
            if first_period == last_period:
                trend = "stable"
                slope = 0
            elif last_period > first_period:
                trend = "increasing"
                slope = (last_period - first_period) / len(trend_result)
            else:
                trend = "decreasing"
                slope = (last_period - first_period) / len(trend_result)
            
            logger.info(f"Calculated trend for {value_column}: {trend} (slope: {slope:.4f})")
            
            return {
                "trend": trend,
                "slope": slope,
                "periods": len(trend_result),
                "first_value": first_period,
                "last_value": last_period,
                "change_percent": ((last_period - first_period) / first_period * 100) if first_period != 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            raise
    
    def _parse_window_size(self, window_size: str) -> str:
        """Parse window size string to VAST-compatible format"""
        # Convert common time units to VAST format
        if "hour" in window_size:
            return "hour"
        elif "minute" in window_size:
            return "minute"
        elif "day" in window_size:
            return "day"
        elif "week" in window_size:
            return "week"
        elif "month" in window_size:
            return "month"
        else:
            return "hour"  # Default to hour
