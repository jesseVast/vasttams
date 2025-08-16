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
                elif operator == 'or':
                    # Handle OR operations
                    if isinstance(value, (list, tuple)):
                        # Convert to Ibis OR expression
                        if len(value) >= 2:
                            # Generic OR for multiple values
                            converted_values = [self._convert_timestamp_value(v) for v in value]
                            return column_ref.isin(converted_values)
                        else:
                            logger.warning(f"Invalid 'or' value for column {column}: {value}")
                            return None
                    else:
                        logger.warning(f"Invalid 'or' value for column {column}: {value}")
                        return None
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
    
    def convert_ibis_predicate_to_vast(self, ibis_predicate: Any) -> Optional[Dict[str, Any]]:
        """
        Convert Ibis predicate objects to VAST-compatible dictionary format.
        
        This method handles the conversion of Ibis predicates (including Deferred types)
        to a format that can be used by VAST queries.
        
        Args:
            ibis_predicate: Ibis predicate object (can be Deferred, BinaryOp, etc.)
            
        Returns:
            VAST-compatible predicate dictionary or None if conversion fails
        """
        if ibis_predicate is None:
            return None
            
        try:
            # Convert to string first to avoid Deferred object issues
            predicate_str = str(ibis_predicate)
            
            # Parse the string representation to extract predicates
            return self._parse_predicate_string(predicate_str)
                
        except Exception as e:
            logger.warning(f"Failed to convert Ibis predicate {ibis_predicate}: {e}")
            return None
    
    def _parse_predicate_string(self, predicate_str: str) -> Optional[Dict[str, Any]]:
        """Parse predicate string representation to extract column conditions"""
        try:
            # Handle common patterns in Ibis predicate strings
            
            # Handle AND operations: (left & right) - check this first
            if ' & ' in predicate_str:
                # Handle nested parentheses in AND operations
                # Example: ((_.id == 'test-id') & (_.format == 'video'))
                if predicate_str.startswith('((') and predicate_str.endswith('))'):
                    # Remove outer double parentheses
                    inner_str = predicate_str[2:-2]
                    if ' & ' in inner_str:
                        left_part = inner_str.split(' & ')[0]
                        right_part = inner_str.split(' & ')[1]
                        
                        # Try to parse each part
                        left_pred = self._parse_predicate_string(left_part)
                        right_pred = self._parse_predicate_string(right_part)
                        
                        if left_pred and right_pred:
                            # Combine both predicates
                            combined = left_pred.copy()
                            combined.update(right_pred)
                            return combined
                        elif left_pred:
                            return left_pred
                        elif right_pred:
                            return right_pred
                else:
                    # Standard AND operation
                    left_part = predicate_str.split(' & ')[0]
                    right_part = predicate_str.split(' & ')[1]
                    
                    # Try to parse each part
                    left_pred = self._parse_predicate_string(left_part)
                    right_pred = self._parse_predicate_string(right_part)
                    
                    if left_pred and right_pred:
                        # Combine both predicates
                        combined = left_pred.copy()
                        combined.update(right_pred)
                        return combined
                    elif left_pred:
                        return left_pred
                    elif right_pred:
                        return right_pred
            
            # Handle OR operations: (left | right) - check this second
            elif ' | ' in predicate_str:
                # For OR operations, extract the first valid predicate
                left_part = predicate_str.split(' | ')[0]
                right_part = predicate_str.split(' | ')[1]
                
                left_pred = self._parse_predicate_string(left_part)
                if left_pred:
                    return left_pred
                
                right_pred = self._parse_predicate_string(right_part)
                if right_pred:
                    return right_pred
            
            # Handle isnull(): _.column.isnull()
            elif '.isnull()' in predicate_str:
                column = predicate_str.split('.isnull()')[0]
                if column.startswith('_.'):
                    column = column[2:]  # Remove _.
                elif column.startswith('(_.'):
                    column = column[3:-1]  # Remove (_. and )
                return {column: None}
            
            # Handle notnull(): _.column.notnull()
            elif '.notnull()' in predicate_str:
                column = predicate_str.split('.notnull()')[0]
                if column.startswith('_.'):
                    column = column[2:]  # Remove _.
                elif column.startswith('(_.'):
                    column = column[3:-1]  # Remove (_. and )
                return {column: {'is_not_null': True}}
            
            # Simple equality: (_.column == value) - check this last
            elif ' == ' in predicate_str:
                parts = predicate_str.split(' == ')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # Extract column name from left side - handle extra parentheses
                    if left.startswith('(_.') and left.endswith(')'):
                        column = left[3:-1]  # Remove (_. and )
                    elif left.startswith('_.'):
                        column = left[2:]  # Remove _.
                    else:
                        # Try to find column name in the left part
                        if '_.' in left:
                            column_start = left.find('_.') + 2
                            column_end = left.find(')', column_start)
                            if column_end == -1:
                                column_end = len(left)
                            column = left[column_start:column_end]
                        else:
                            logger.debug(f"Could not extract column name from left part: {left}")
                            return None
                    
                    # Clean up right side value - handle extra parentheses and quotes
                    if right.startswith("'") and right.endswith("'"):
                        value = right[1:-1]  # Remove quotes
                    elif right.endswith(')'):
                        # Remove trailing parentheses
                        value_str = right.rstrip(')')
                        if value_str == 'False':
                            value = False
                        elif value_str == 'True':
                            value = True
                        elif value_str == 'None':
                            value = None
                        elif value_str.startswith("'") and value_str.endswith("'"):
                            value = value_str[1:-1]  # Remove quotes
                        else:
                            # Try to convert to appropriate type
                            try:
                                value = int(value_str)
                            except ValueError:
                                try:
                                    value = float(value_str)
                                except ValueError:
                                    value = value_str
                    else:
                        # Handle values without trailing parentheses
                        if right == 'False':
                            value = False
                        elif right == 'True':
                            value = True
                        elif right == 'None':
                            value = None
                        elif right.startswith("'") and right.endswith("'"):
                            value = right[1:-1]  # Remove quotes
                        else:
                            # Try to convert to appropriate type
                            try:
                                value = int(right)
                            except ValueError:
                                try:
                                    value = float(right)
                                except ValueError:
                                    value = right
                    
                    logger.debug(f"Extracted column: {column}, value: {value}")
                    return {column: value}
            
            # If we can't parse it, return None
            logger.debug(f"Could not parse predicate string: {predicate_str}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse predicate string '{predicate_str}': {e}")
            return None
