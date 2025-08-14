"""Advanced aggregation analytics for VastDBManager"""

import logging
from typing import List, Dict, Any, Optional, Union
from pyarrow import Table

logger = logging.getLogger(__name__)


class AggregationAnalytics:
    """Advanced aggregation analytics and statistical functions"""
    
    def __init__(self, cache_manager):
        """Initialize aggregation analytics with cache manager"""
        self.cache_manager = cache_manager
    
    def calculate_percentiles(self, table: Table, config, value_column: str,
                             percentiles: List[float] = [25, 50, 75, 90, 95, 99],
                             predicates: str = "") -> Dict[str, float]:
        """
        Calculate percentiles for a numeric column
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to calculate percentiles for
            percentiles: List of percentiles to calculate
            predicates: Optional filter predicates
            
        Returns:
            Dictionary of percentile values
        """
        try:
            # Build percentile query using VAST window functions
            percentile_columns = []
            for p in percentiles:
                percentile_columns.append(f"PERCENTILE({value_column}, {p/100}) as p{p}")
            
            query = table.select(percentile_columns)
            
            if predicates:
                query = query.filter(predicates)
            
            result = query.collect().to_pylist()
            
            if not result:
                return {}
            
            # Extract percentile values
            percentiles_dict = {}
            for p in percentiles:
                key = f"p{p}"
                if key in result[0]:
                    percentiles_dict[f"p{p}"] = result[0][key]
            
            logger.info(f"Calculated {len(percentiles_dict)} percentiles for {value_column}")
            return percentiles_dict
            
        except Exception as e:
            logger.error(f"Error calculating percentiles: {e}")
            raise
    
    def calculate_correlation(self, table: Table, config, column1: str, column2: str,
                             predicates: str = "") -> Dict[str, float]:
        """
        Calculate correlation between two numeric columns
        
        Args:
            table: VAST table
            config: QueryConfig
            column1: First column for correlation
            column2: Second column for correlation
            predicates: Optional filter predicates
            
        Returns:
            Correlation analysis results
        """
        try:
            # Calculate correlation using statistical functions
            correlation_columns = [
                f"AVG({column1}) as avg_col1",
                f"AVG({column2}) as avg_col2",
                f"AVG({column1} * {column2}) as avg_product",
                f"STDDEV({column1}) as std_col1",
                f"STDDEV({column2}) as std_col2",
                f"COUNT(*) as sample_count"
            ]
            
            query = table.select(correlation_columns)
            
            if predicates:
                query = query.filter(predicates)
            
            result = query.collect().to_pylist()
            
            if not result:
                return {"correlation": 0, "sample_count": 0}
            
            stats = result[0]
            
            # Calculate correlation coefficient
            if stats['std_col1'] and stats['std_col2'] and stats['sample_count'] > 1:
                covariance = stats['avg_product'] - (stats['avg_col1'] * stats['avg_col2'])
                correlation = covariance / (stats['std_col1'] * stats['std_col2'])
            else:
                correlation = 0
            
            logger.info(f"Calculated correlation between {column1} and {column2}: {correlation:.4f}")
            
            return {
                "correlation": correlation,
                "sample_count": stats['sample_count'],
                "covariance": stats['avg_product'] - (stats['avg_col1'] * stats['avg_col2']) if stats['std_col1'] and stats['std_col2'] else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            raise
    
    def calculate_distribution(self, table: Table, config, value_column: str,
                              num_bins: int = 10, predicates: str = "") -> List[Dict[str, Any]]:
        """
        Calculate histogram distribution for a numeric column
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to analyze distribution for
            num_bins: Number of histogram bins
            predicates: Optional filter predicates
            
        Returns:
            List of histogram bin data
        """
        try:
            # First get min/max values to calculate bin boundaries
            bounds_query = table.select([
                f"MIN({value_column}) as min_val",
                f"MAX({value_column}) as max_val",
                f"COUNT(*) as total_count"
            ])
            
            if predicates:
                bounds_query = bounds_query.filter(predicates)
            
            bounds_result = bounds_query.collect().to_pylist()
            
            if not bounds_result or not bounds_result[0]['min_val']:
                return []
            
            min_val = bounds_result[0]['min_val']
            max_val = bounds_result[0]['max_val']
            total_count = bounds_result[0]['total_count']
            
            if min_val == max_val:
                return [{"bin": 0, "range": f"{min_val}", "count": total_count, "percentage": 100.0}]
            
            # Calculate bin width
            bin_width = (max_val - min_val) / num_bins
            
            # Build histogram query using CASE statements
            case_parts = []
            for i in range(num_bins):
                bin_start = min_val + (i * bin_width)
                bin_end = min_val + ((i + 1) * bin_width)
                
                if i == num_bins - 1:  # Last bin includes the max value
                    case_parts.append(f"WHEN {value_column} >= {bin_start} THEN {i}")
                else:
                    case_parts.append(f"WHEN {value_column} >= {bin_start} AND {value_column} < {bin_end} THEN {i}")
            
            case_statement = f"CASE {' '.join(case_parts)} ELSE {num_bins} END"
            
            histogram_columns = [
                f"{case_statement} as bin",
                f"COUNT(*) as count"
            ]
            
            histogram_query = table.select(histogram_columns)
            
            if predicates:
                histogram_query = histogram_query.filter(predicates)
            
            histogram_query = histogram_query.group_by("bin").order_by("bin")
            histogram_result = histogram_query.collect().to_pylist()
            
            # Format results
            distribution = []
            for bin_data in histogram_result:
                bin_num = bin_data['bin']
                if bin_num < num_bins:
                    bin_start = min_val + (bin_num * bin_width)
                    bin_end = min_val + ((bin_num + 1) * bin_width)
                    
                    distribution.append({
                        "bin": int(bin_num),
                        "range": f"{bin_start:.2f} - {bin_end:.2f}",
                        "count": bin_data['count'],
                        "percentage": (bin_data['count'] / total_count * 100) if total_count > 0 else 0
                    })
            
            logger.info(f"Calculated distribution for {value_column} with {num_bins} bins")
            return distribution
            
        except Exception as e:
            logger.error(f"Error calculating distribution: {e}")
            raise
    
    def calculate_top_values(self, table: Table, config, value_column: str,
                            group_by_column: str, top_n: int = 10,
                            predicates: str = "") -> List[Dict[str, Any]]:
        """
        Calculate top N values by group
        
        Args:
            table: VAST table
            config: QueryConfig
            value_column: Column to aggregate
            group_by_column: Column to group by
            top_n: Number of top values to return
            predicates: Optional filter predicates
            
        Returns:
            List of top values by group
        """
        try:
            # Build top values query
            top_columns = [
                group_by_column,
                f"COUNT(*) as count",
                f"AVG({value_column}) as avg_value",
                f"MIN({value_column}) as min_value",
                f"MAX({value_column}) as max_value"
            ]
            
            query = table.select(top_columns)
            
            if predicates:
                query = query.filter(predicates)
            
            query = query.group_by(group_by_column).order_by("count", ascending=False).limit(top_n)
            result = query.collect().to_pylist()
            
            logger.info(f"Calculated top {len(result)} values for {value_column} grouped by {group_by_column}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating top values: {e}")
            raise
