"""
Simplified predicate builder for TAMS timerange queries and basic comparisons

This module provides a focused predicate builder that handles TAMS requirements:
- Timerange overlap queries for media segments
- Simple equality and range comparisons
- OR logic for combining multiple conditions
- Compound predicates with AND/OR combinations

The PredicateBuilder converts Python dictionaries to VAST-compatible Ibis predicate objects
that can be used in VAST database queries.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
import re
from ibis import _

logger = logging.getLogger(__name__)


class PredicateBuilder:
    """
    Simplified predicate builder for TAMS requirements.
    
    This class converts Python dictionary predicates to VAST-compatible Ibis predicate objects.
    It focuses on TAMS-specific requirements including timerange queries and basic comparisons.
    
    **Supported Dictionary Formats:**
    
    1. **Simple Equality:**
       ```python
       predicates = {
           'is_active': True,
           'format': 'urn:x-nmos:format:video',
           'source_id': 'source_123'
       }
       ```
    
    2. **Comparison Operators:**
       ```python
       predicates = {
           'duration': {'gt': 30.0},           # duration > 30.0
           'file_size': {'gte': 1024},        # file_size >= 1024
           'timestamp': {'lt': '2024-01-01'}, # timestamp < 2024-01-01
           'bitrate': {'lte': 5000000}        # bitrate <= 5000000
       }
       ```
    
    3. **Range Queries:**
       ```python
       predicates = {
           'timestamp': {'between': ['2024-01-01', '2024-01-31']},
           'duration': {'in': [30.0, 60.0, 90.0]}
       }
       ```
    
    4. **Timerange Queries (TAMS Specific):**
       ```python
       predicates = {
           'timerange': {
               'overlaps': {
                   'start': '2024-01-01T00:00:00Z',
                   'end': '2024-01-01T23:59:59Z'
               }
           }
       }
       ```
    
    5. **OR Logic:**
       ```python
       predicates = {
           'format': {'or': ['urn:x-nmos:format:video', 'urn:x-nmos:format:audio']},
           'source_id': {'or': ['source_1', 'source_2', 'source_3']}
       }
       ```
    
    6. **Compound AND/OR Logic:**
       ```python
       predicates = {
           'and': [
               {'format': 'urn:x-nmos:format:video'},
               {'or': [
                   {'source_id': 'source_1'},
                   {'source_id': 'source_2'}
               ]},
               {'timerange': {'overlaps': {'start': '2024-01-01', 'end': '2024-01-02'}}}
           ]
       }
       ```
    
    7. **Null Checks:**
       ```python
       predicates = {
           'metadata': {'is_null': True},
           'tags': {'is_not_null': True}
       }
       ```
    
    **Expected Predicates Generated:**
    
    The builder converts these dictionaries to Ibis predicate objects that can be used
    directly in VAST database queries. For example:
    
    - Simple equality becomes: `table.column == value`
    - Comparisons become: `table.column > value`, `table.column <= value`
    - Timerange overlaps become: `(table.start_time <= end) & (table.end_time >= start)`
    - OR logic becomes: `(table.column == value1) | (table.column == value2)`
    - Compound logic becomes: `(condition1) & ((condition2) | (condition3))`
    
    **Usage Example:**
    
    ```python
    builder = PredicateBuilder()
    
    # Simple query
    predicates = {'format': 'urn:x-nmos:format:video'}
    vast_predicates = builder.build_vast_predicates(predicates)
    
    # Timerange query
    predicates = {
        'timerange': {
            'overlaps': {
                'start': '2024-01-01T00:00:00Z',
                'end': '2024-01-01T23:59:59Z'
            }
        }
    }
    vast_predicates = builder.build_vast_predicates(predicates)
    
    # Use in VAST query
    result = table.filter(vast_predicates).execute()
    ```
    """
    
    def build_vast_predicates(self, predicates: Dict[str, Any]) -> Optional[Any]:
        """
        Convert Python predicates to VAST-compatible Ibis predicate objects.
        
        Focuses on TAMS requirements:
        - Timerange overlap queries
        - Simple equality comparisons
        - Basic range comparisons
        - OR logic for multiple values
        - Compound AND/OR logic
        
        Args:
            predicates: Dictionary of column names and their conditions
            
        Returns:
            Ibis predicate object or None if no predicates
            
        Raises:
            ValueError: If predicate format is invalid
        """
        if not predicates:
            logger.debug("No predicates provided, returning None")
            return None
            
        logger.debug(f"Building VAST predicates from input: {predicates}")
        
        try:
            # Handle compound logic (AND/OR at top level)
            if 'and' in predicates:
                logger.debug("Processing AND logic at top level")
                result = self._build_and_predicates(predicates['and'])
                logger.debug(f"AND logic result: {result}")
                return result
            elif 'or' in predicates:
                logger.debug("Processing OR logic at top level")
                result = self._build_or_predicates(predicates['or'])
                logger.debug(f"OR logic result: {result}")
                return result
            
            # Handle individual column predicates
            built_predicates = []
            for column, condition in predicates.items():
                logger.debug(f"Processing column '{column}' with condition: {condition}")
                
                if column == 'timerange':
                    predicate = self._build_timerange_predicate(condition)
                else:
                    predicate = self._build_column_predicate(column, condition)
                
                if predicate is not None:
                    built_predicates.append(predicate)
                    logger.debug(f"Built predicate for '{column}': {predicate}")
                else:
                    logger.debug(f"No predicate built for '{column}'")
            
            if not built_predicates:
                logger.debug("No predicates were built, returning None")
                return None
            elif len(built_predicates) == 1:
                logger.debug(f"Single predicate result: {built_predicates[0]}")
                return built_predicates[0]
            else:
                # Combine all predicates with AND logic
                result = built_predicates[0].and_(built_predicates[1:])
                logger.debug(f"Combined AND predicates result: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Error building predicates: {e}")
            raise ValueError(f"Invalid predicate format: {e}")
    
    def _build_and_predicates(self, conditions: List[Dict[str, Any]]) -> Any:
        """Build AND logic for multiple conditions"""
        if not conditions:
            logger.debug("No conditions for AND logic, returning None")
            return None
            
        logger.debug(f"Building AND predicates from conditions: {conditions}")
        predicates = []
        for i, condition in enumerate(conditions):
            logger.debug(f"Processing AND condition {i+1}: {condition}")
            predicate = self.build_vast_predicates(condition)
            if predicate is not None:
                predicates.append(predicate)
                logger.debug(f"Added predicate {i+1} to AND list: {predicate}")
            else:
                logger.debug(f"Condition {i+1} produced no predicate")
        
        if not predicates:
            logger.debug("No predicates built for AND logic, returning None")
            return None
        elif len(predicates) == 1:
            logger.debug(f"Single AND predicate result: {predicates[0]}")
            return predicates[0]
        else:
            result = predicates[0].and_(predicates[1:])
            logger.debug(f"Combined AND predicates result: {result}")
            return result
    
    def _build_or_predicates(self, conditions: List[Dict[str, Any]]) -> Any:
        """Build OR logic for multiple conditions"""
        if not conditions:
            logger.debug("No conditions for OR logic, returning None")
            return None
            
        logger.debug(f"Building OR predicates from conditions: {conditions}")
        predicates = []
        for i, condition in enumerate(conditions):
            logger.debug(f"Processing OR condition {i+1}: {condition}")
            predicate = self.build_vast_predicates(condition)
            if predicate is not None:
                predicates.append(predicate)
                logger.debug(f"Added predicate {i+1} to OR list: {predicate}")
            else:
                logger.debug(f"Condition {i+1} produced no predicate")
        
        if not predicates:
            logger.debug("No predicates built for OR logic, returning None")
            return None
        elif len(predicates) == 1:
            logger.debug(f"Single OR predicate result: {predicates[0]}")
            return predicates[0]
        else:
            result = predicates[0].or_(predicates[1:])
            logger.debug(f"Combined OR predicates result: {result}")
            return result
    
    def _build_column_predicate(self, column: str, condition: Any) -> Optional[Any]:
        """Build predicate for a single column"""
        try:
            logger.debug(f"Building predicate for column '{column}' with condition: {condition}")
            
            # Handle OR logic for multiple values
            if isinstance(condition, dict) and 'or' in condition:
                logger.debug(f"Column '{column}' has OR logic with values: {condition['or']}")
                result = self._build_column_or_predicate(column, condition['or'])
                logger.debug(f"OR logic result for column '{column}': {result}")
                return result
            
            # Handle comparison operators
            if isinstance(condition, dict):
                logger.debug(f"Column '{column}' has comparison operators: {condition}")
                result = self._build_comparison_predicate(column, condition)
                logger.debug(f"Comparison result for column '{column}': {result}")
                return result
            
            # Handle simple equality
            logger.debug(f"Column '{column}' has simple equality with value: {condition}")
            result = self._build_equality_predicate(column, condition)
            logger.debug(f"Equality result for column '{column}': {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error building predicate for column {column}: {e}")
            return None
    
    def _build_column_or_predicate(self, column: str, values: List[Any]) -> Any:
        """Build OR predicate for multiple values of the same column"""
        if not values:
            return None
            
        predicates = []
        for value in values:
            predicate = self._build_equality_predicate(column, value)
            if predicate is not None:
                predicates.append(predicate)
        
        if not predicates:
            return None
        elif len(predicates) == 1:
            return predicates[0]
        else:
            return predicates[0].or_(predicates[1:])
    
    def _build_equality_predicate(self, column: str, value: Any) -> Any:
        """Build equality predicate for a column"""
        if value is None:
            return getattr(_, column).isnull()
        else:
            return getattr(_, column) == value
    
    def _build_comparison_predicate(self, column: str, condition: Dict[str, Any]) -> Any:
        """Build comparison predicate for a column"""
        column_ref = getattr(_, column)
        
        for operator, value in condition.items():
            if operator == 'eq':
                return column_ref == value
            elif operator == 'ne':
                return column_ref != value
            elif operator == 'gt':
                return column_ref > value
            elif operator == 'gte':
                return column_ref >= value
            elif operator == 'lt':
                return column_ref < value
            elif operator == 'lte':
                return column_ref <= value
            elif operator == 'in':
                if isinstance(value, (list, tuple)):
                    return column_ref.isin(value)
                else:
                    raise ValueError(f"Invalid 'in' value: {value}")
            elif operator == 'is_null':
                return column_ref.isnull()
            elif operator == 'is_not_null':
                return column_ref.notnull()
            else:
                raise ValueError(f"Unsupported operator: {operator}")
        
        raise ValueError(f"No valid operator found in condition: {condition}")
    
    def _build_timerange_predicate(self, condition: Dict[str, Any]) -> Optional[Any]:
        """
        Build timerange predicate for TAMS timerange queries.
        
        Supports:
        - overlaps: Check if timeranges overlap
        - equals: Check if timeranges are exactly equal
        - contains: Check if one timerange contains another
        - within: Check if one timerange is within another
        
        Args:
            condition: Timerange condition dictionary
            
        Returns:
            Ibis predicate for timerange comparison
        """
        try:
            logger.debug(f"Building timerange predicate from condition: {condition}")
            
            for operator, timerange in condition.items():
                logger.debug(f"Processing timerange operator '{operator}' with value: {timerange}")
                
                if operator == 'overlaps':
                    result = self._build_overlaps_predicate(timerange)
                    logger.debug(f"Overlaps predicate result: {result}")
                    return result
                elif operator == 'equals':
                    result = self._build_equals_predicate(timerange)
                    logger.debug(f"Equals predicate result: {result}")
                    return result
                elif operator == 'contains':
                    result = self._build_contains_predicate(timerange)
                    logger.debug(f"Contains predicate result: {result}")
                    return result
                elif operator == 'within':
                    result = self._build_within_predicate(timerange)
                    logger.debug(f"Within predicate result: {result}")
                    return result
                else:
                    raise ValueError(f"Unsupported timerange operator: {operator}")
                    
        except Exception as e:
            logger.error(f"Error building timerange predicate: {e}")
            return None
    
    def _build_overlaps_predicate(self, timerange: Dict[str, Any]) -> Any:
        """
        Build predicate for timerange overlap.
        
        Two timeranges overlap if:
        start1 <= end2 AND start2 <= end1
        
        Args:
            timerange: Dictionary with 'start' and 'end' keys
            
        Returns:
            Ibis predicate for overlap check
        """
        start = self._parse_timestamp(timerange.get('start'))
        end = self._parse_timestamp(timerange.get('end'))
        
        if start is None or end is None:
            raise ValueError("Timerange must have both 'start' and 'end' values")
        
        # Overlap: (table.start_time <= end) AND (table.end_time >= start)
        return (
            (_.start_time <= end) & 
            (_.end_time >= start)
        )
    
    def _build_equals_predicate(self, timerange: Dict[str, Any]) -> Any:
        """Build predicate for exact timerange equality"""
        start = self._parse_timestamp(timerange.get('start'))
        end = self._parse_timestamp(timerange.get('end'))
        
        if start is None or end is None:
            raise ValueError("Timerange must have both 'start' and 'end' values")
        
        return (_.start_time == start) & (_.end_time == end)
    
    def _build_contains_predicate(self, timerange: Dict[str, Any]) -> Any:
        """Build predicate for timerange containment"""
        start = self._parse_timestamp(timerange.get('start'))
        end = self._parse_timestamp(timerange.get('end'))
        
        if start is None or end is None:
            raise ValueError("Timerange must have both 'start' and 'end' values")
        
        # Contains: (table.start_time <= start) AND (table.end_time >= end)
        return (
            (_.start_time <= start) & 
            (_.end_time >= end)
        )
    
    def _build_within_predicate(self, timerange: Dict[str, Any]) -> Any:
        """Build predicate for timerange within check"""
        start = self._parse_timestamp(timerange.get('start'))
        end = self._parse_timestamp(timerange.get('end'))
        
        if start is None or end is None:
            raise ValueError("Timerange must have both 'start' and 'end' values")
        
        # Within: (table.start_time >= start) AND (table.end_time <= end)
        return (
            (_.start_time >= start) & 
            (_.end_time <= end)
        )
    
    def _parse_timestamp(self, timestamp: Any) -> Any:
        """
        Parse timestamp value to appropriate format.
        
        Args:
            timestamp: Timestamp value (string, datetime, or other)
            
        Returns:
            Parsed timestamp value
        """
        logger.debug(f"Parsing timestamp: {timestamp} (type: {type(timestamp)})")
        
        if timestamp is None:
            logger.debug("Timestamp is None, returning None")
            return None
        
        # If it's already a datetime object, return as is
        if isinstance(timestamp, datetime):
            logger.debug(f"Timestamp is already datetime object: {timestamp}")
            return timestamp
        
        # If it's a string, try to parse it
        if isinstance(timestamp, str):
            try:
                # Handle ISO format timestamps
                if 'T' in timestamp or 'Z' in timestamp:
                    logger.debug(f"Timestamp is ISO format, returning as string: {timestamp}")
                    return timestamp  # Return as string for VAST to handle
                
                # Handle simple date formats
                if re.match(r'^\d{4}-\d{2}-\d{2}$', timestamp):
                    logger.debug(f"Timestamp is simple date format: {timestamp}")
                    return timestamp
                
                # Handle datetime formats
                if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', timestamp):
                    logger.debug(f"Timestamp is datetime format: {timestamp}")
                    return timestamp
                    
            except Exception as e:
                logger.warning(f"Could not parse timestamp {timestamp}: {e}")
        
        # Return as is for other types
        logger.debug(f"Returning timestamp as-is: {timestamp}")
        return timestamp
