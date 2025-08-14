"""Predicate processing and VAST predicate objects for VastDBManager"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
import pyarrow as pa
from ibis import _

logger = logging.getLogger(__name__)


class PredicateBuilder:
    """Converts Python predicates to VAST-compatible Ibis predicate objects"""
    
    def build_vast_predicates(self, predicates: Dict[str, Any]) -> Optional[Any]:
        """
        Convert Python predicates to VAST-compatible Ibis predicate objects.
        
        Args:
            predicates: Dictionary of column predicates
                Example: {
                    'format': 'urn:x-nmos:format:video',
                    'bitrate': {'gte': 10000000},
                    'timestamp': {'between': [start_time, end_time]},
                    'tags': 'live'
                }
                
        Returns:
            VAST-compatible Ibis predicate object or None
        """
        if not predicates:
            return None
        
        try:
            # Build Ibis predicates
            ibis_predicates = []
            
            for column, condition in predicates.items():
                if isinstance(condition, dict):
                    # Complex condition (range, comparison, etc.)
                    predicate = self._build_complex_predicate(column, condition)
                    if predicate is not None:
                        ibis_predicates.append(predicate)
                else:
                    # Simple equality
                    predicate = self._build_simple_predicate(column, condition)
                    if predicate is not None:
                        ibis_predicates.append(predicate)
            
            # Combine all predicates with AND logic
            if ibis_predicates:
                if len(ibis_predicates) == 1:
                    return ibis_predicates[0]
                else:
                    # Combine multiple predicates with AND
                    result = ibis_predicates[0]
                    for predicate in ibis_predicates[1:]:
                        result = result & predicate
                    return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error building Ibis predicates: {e}")
            logger.warning("Falling back to unfiltered query")
            return None
    
    def _build_simple_predicate(self, column: str, value: Any) -> Optional[Any]:
        """Build simple equality predicate using Ibis"""
        try:
            if value is None:
                return getattr(_, column).isnull()
            else:
                return getattr(_, column) == self._convert_timestamp_value(value)
        except Exception as e:
            logger.warning(f"Failed to build simple predicate for {column}: {e}")
            return None
    
    def _build_complex_predicate(self, column: str, condition: Dict[str, Any]) -> Optional[Any]:
        """Build complex predicate with operators using Ibis"""
        try:
            column_ref = getattr(_, column)
            
            for operator, value in condition.items():
                if operator == 'eq':
                    return column_ref == self._convert_timestamp_value(value)
                elif operator == 'ne':
                    return column_ref != self._convert_timestamp_value(value)
                elif operator == 'gt':
                    return column_ref > self._convert_timestamp_value(value)
                elif operator == 'gte':
                    return column_ref >= self._convert_timestamp_value(value)
                elif operator == 'lt':
                    return column_ref < self._convert_timestamp_value(value)
                elif operator == 'lte':
                    return column_ref <= self._convert_timestamp_value(value)
                elif operator == 'between':
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        start, end = value
                        start_converted = self._convert_timestamp_value(start)
                        end_converted = self._convert_timestamp_value(end)
                        return (column_ref >= start_converted) & (column_ref <= end_converted)
                    else:
                        logger.warning(f"Invalid 'between' value for column {column}: {value}")
                        return None
                elif operator == 'in':
                    if isinstance(value, (list, tuple)):
                        converted_values = [self._convert_timestamp_value(v) for v in value]
                        return column_ref.isin(converted_values)
                    else:
                        logger.warning(f"Invalid 'in' value for column {column}: {value}")
                        return None
                elif operator == 'contains':
                    if isinstance(value, str):
                        return column_ref.contains(value)
                    else:
                        logger.warning(f"Invalid 'contains' value for column {column}: {value}")
                        return None
                elif operator == 'starts_with':
                    if isinstance(value, str):
                        return column_ref.startswith(value)
                    else:
                        logger.warning(f"Invalid 'starts_with' value for column {column}: {value}")
                        return None
                elif operator == 'is_null':
                    return column_ref.isnull()
                elif operator == 'is_not_null':
                    return column_ref.notnull()
                else:
                    logger.warning(f"Unsupported operator '{operator}' for column {column}")
                    return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to build complex predicate for {column}: {e}")
            return None
    
    def _convert_timestamp_value(self, value: Any) -> Any:
        """Convert Python datetime to VAST-compatible timestamp if needed"""
        if isinstance(value, datetime):
            # For VAST with PyArrow timestamps, use datetime objects directly
            # This enables optimal VAST timestamp comparisons and indexing
            return value
        return value
