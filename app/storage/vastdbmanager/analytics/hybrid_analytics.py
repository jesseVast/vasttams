"""Hybrid analytics combining VAST filtering with DuckDB processing"""

import logging
import time
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import duckdb
from pyarrow import Table

logger = logging.getLogger(__name__)


class HybridAnalytics:
    """Combines VAST filtering with DuckDB analytics processing"""
    
    def __init__(self, cache_manager):
        """Initialize hybrid analytics with cache manager"""
        self.cache_manager = cache_manager
        self.duck_conn = None
        self._initialize_duckdb()
    
    def _initialize_duckdb(self):
        """Initialize DuckDB connection"""
        try:
            self.duck_conn = duckdb.connect()
            logger.info("Initialized DuckDB connection for hybrid analytics")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            self.duck_conn = None
    
    def _ensure_duckdb_connection(self):
        """Ensure DuckDB connection is available"""
        if self.duck_conn is None:
            self._initialize_duckdb()
        return self.duck_conn is not None
    
    def calculate_moving_average_hybrid(self, table: Table, config, value_column: str,
                                       time_column: str, window_size: str = "1 hour",
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None,
                                       predicates: str = "") -> List[Dict[str, Any]]:
        """
        Calculate moving average using VAST filtering + DuckDB processing
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to calculate average for
            time_column: Time column for windowing
            window_size: Window size (e.g., "1 hour", "30 minutes")
            start_time: Start time for analysis
            end_time: End time for analysis
            predicates: Additional VAST predicates
            
        Returns:
            List of moving average results
        """
        try:
            if not self._ensure_duckdb_connection():
                raise RuntimeError("DuckDB connection not available")
            
            # Build VAST filter combining time range and predicates
            vast_filter = self._build_vast_time_filter(time_column, start_time, end_time, predicates)
            
            # Extract data from VAST using efficient filtering
            logger.info(f"Extracting data from VAST table {table.name} with filter: {vast_filter}")
            
            # Select only necessary columns for efficiency
            columns = [time_column, value_column]
            vast_query = table.select(columns)
            
            if vast_filter:
                vast_query = vast_query.filter(vast_filter)
            
            # Execute VAST query with splits optimization
            vast_result = vast_query.collect()
            
            if vast_result.num_rows == 0:
                logger.info("No data returned from VAST query")
                return []
            
            # Convert to DuckDB for analytics processing
            logger.info(f"Processing {vast_result.num_rows} rows with DuckDB")
            
            # Create temporary table in DuckDB
            temp_table_name = f"temp_{table.name}_{int(time.time())}"
            
            # Convert VAST result to DuckDB
            self.duck_conn.execute(f"CREATE TABLE {temp_table_name} AS SELECT * FROM vast_result")
            
            # Calculate moving average using DuckDB's advanced window functions
            window_sql = self._build_window_sql(window_size)
            
            analytics_query = f"""
                SELECT 
                    {window_sql} as window_start,
                    AVG({value_column}) as moving_avg,
                    COUNT(*) as sample_count,
                    MIN({value_column}) as min_value,
                    MAX({value_column}) as max_value,
                    STDDEV({value_column}) as std_dev
                FROM {temp_table_name}
                GROUP BY window_start
                ORDER BY window_start
            """
            
            result = self.duck_conn.execute(analytics_query).arrow()
            
            # Clean up temporary table
            self.duck_conn.execute(f"DROP TABLE {temp_table_name}")
            
            # Convert to Python list
            analytics_result = result.to_pylist()
            
            logger.info(f"Calculated moving average for {value_column} with {window_size} windows: {len(analytics_result)} windows")
            return analytics_result
            
        except Exception as e:
            logger.error(f"Error in hybrid moving average calculation: {e}")
            raise
    
    def calculate_percentiles_hybrid(self, table: Table, config, value_column: str,
                                    percentiles: List[float] = [25, 50, 75, 90, 95, 99],
                                    predicates: str = "") -> Dict[str, float]:
        """
        Calculate percentiles using VAST filtering + DuckDB processing
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to calculate percentiles for
            percentiles: List of percentiles to calculate
            predicates: VAST filter predicates
            
        Returns:
            Dictionary of percentile values
        """
        try:
            if not self._ensure_duckdb_connection():
                raise RuntimeError("DuckDB connection not available")
            
            # Extract data from VAST
            logger.info(f"Extracting data from VAST table {table.name} for percentile calculation")
            
            vast_query = table.select([value_column])
            if predicates:
                vast_query = vast_query.filter(predicates)
            
            vast_result = vast_query.collect()
            
            if vast_result.num_rows == 0:
                logger.info("No data returned from VAST query")
                return {}
            
            # Process with DuckDB
            temp_table_name = f"temp_percentiles_{int(time.time())}"
            self.duck_conn.execute(f"CREATE TABLE {temp_table_name} AS SELECT * FROM vast_result")
            
            # Calculate percentiles using DuckDB's PERCENTILE_CONT function
            percentile_columns = []
            for p in percentiles:
                percentile_columns.append(f"PERCENTILE_CONT({p/100}) WITHIN GROUP (ORDER BY {value_column}) as p{p}")
            
            analytics_query = f"""
                SELECT 
                    {', '.join(percentile_columns)},
                    COUNT(*) as total_count,
                    AVG({value_column}) as mean_value,
                    STDDEV({value_column}) as std_dev
                FROM {temp_table_name}
            """
            
            result = self.duck_conn.execute(analytics_query).arrow()
            
            # Clean up
            self.duck_conn.execute(f"DROP TABLE {temp_table_name}")
            
            # Extract results
            if result.num_rows > 0:
                row = result.to_pylist()[0]
                percentiles_dict = {}
                
                for p in percentiles:
                    key = f"p{p}"
                    if key in row:
                        percentiles_dict[key] = row[key]
                
                # Add additional statistics
                percentiles_dict.update({
                    "total_count": row.get("total_count", 0),
                    "mean_value": row.get("mean_value", 0),
                    "std_dev": row.get("std_dev", 0)
                })
                
                logger.info(f"Calculated {len(percentiles_dict)} percentiles for {value_column}")
                return percentiles_dict
            
            return {}
            
        except Exception as e:
            logger.error(f"Error in hybrid percentile calculation: {e}")
            raise
    
    def calculate_correlation_hybrid(self, table: Table, config, column1: str, column2: str,
                                    predicates: str = "") -> Dict[str, float]:
        """
        Calculate correlation using VAST filtering + DuckDB processing
        
        Args:
            table: VAST table
            config: QueryConfig
            column1: First column for correlation
            column2: Second column for correlation
            predicates: VAST filter predicates
            
        Returns:
            Correlation analysis results
        """
        try:
            if not self._ensure_duckdb_connection():
                raise RuntimeError("DuckDB connection not available")
            
            # Extract data from VAST
            logger.info(f"Extracting data from VAST table {table.name} for correlation analysis")
            
            vast_query = table.select([column1, column2])
            if predicates:
                vast_query = vast_query.filter(predicates)
            
            vast_result = vast_query.collect()
            
            if vast_result.num_rows == 0:
                logger.info("No data returned from VAST query")
                return {"correlation": 0, "sample_count": 0}
            
            # Process with DuckDB
            temp_table_name = f"temp_correlation_{int(time.time())}"
            self.duck_conn.execute(f"CREATE TABLE {temp_table_name} AS SELECT * FROM vast_result")
            
            # Calculate correlation using DuckDB's CORR function
            analytics_query = f"""
                SELECT 
                    CORR({column1}, {column2}) as correlation,
                    COUNT(*) as sample_count,
                    AVG({column1}) as avg_col1,
                    AVG({column2}) as avg_col2,
                    STDDEV({column1}) as std_col1,
                    STDDEV({column2}) as std_col2
                FROM {temp_table_name}
                WHERE {column1} IS NOT NULL AND {column2} IS NOT NULL
            """
            
            result = self.duck_conn.execute(analytics_query).arrow()
            
            # Clean up
            self.duck_conn.execute(f"DROP TABLE {temp_table_name}")
            
            # Extract results
            if result.num_rows > 0:
                row = result.to_pylist()[0]
                
                correlation_result = {
                    "correlation": row.get("correlation", 0) or 0,
                    "sample_count": row.get("sample_count", 0),
                    "avg_col1": row.get("avg_col1", 0),
                    "avg_col2": row.get("avg_col2", 0),
                    "std_col1": row.get("std_col1", 0),
                    "std_col2": row.get("std_col2", 0)
                }
                
                logger.info(f"Calculated correlation between {column1} and {column2}: {correlation_result['correlation']:.4f}")
                return correlation_result
            
            return {"correlation": 0, "sample_count": 0}
            
        except Exception as e:
            logger.error(f"Error in hybrid correlation calculation: {e}")
            raise
    
    def _build_vast_time_filter(self, time_column: str, start_time: Optional[datetime],
                                end_time: Optional[datetime], predicates: str) -> str:
        """Build VAST time filter combining time range and predicates"""
        filter_parts = []
        
        # Add time range filter
        if start_time and end_time:
            time_filter = f"{time_column} BETWEEN '{start_time}' AND '{end_time}'"
            filter_parts.append(time_filter)
        elif start_time:
            time_filter = f"{time_column} >= '{start_time}'"
            filter_parts.append(time_filter)
        elif end_time:
            time_filter = f"{time_column} <= '{end_time}'"
            filter_parts.append(time_filter)
        
        # Add additional predicates
        if predicates:
            filter_parts.append(predicates)
        
        if filter_parts:
            return " AND ".join(filter_parts)
        return ""
    
    def _build_window_sql(self, window_size: str) -> str:
        """Build DuckDB window function SQL"""
        # Convert window size to DuckDB format
        if "hour" in window_size:
            return f"DATE_TRUNC('hour', {time_column})"
        elif "minute" in window_size:
            return f"DATE_TRUNC('minute', {time_column})"
        elif "day" in window_size:
            return f"DATE_TRUNC('day', {time_column})"
        elif "week" in window_size:
            return f"DATE_TRUNC('week', {time_column})"
        elif "month" in window_size:
            return f"DATE_TRUNC('month', {time_column})"
        else:
            return f"DATE_TRUNC('hour', {time_column})"  # Default to hour
    
    def close(self):
        """Close DuckDB connection"""
        if self.duck_conn:
            self.duck_conn.close()
            self.duck_conn = None
            logger.info("Closed DuckDB connection")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.close()
