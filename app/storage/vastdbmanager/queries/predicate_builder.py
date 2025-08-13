"""Predicate processing and VAST-SQL conversion for VastDBManager"""

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PredicateBuilder:
    """Converts Python predicates to VAST-optimized filter expressions"""
    
    def build_vast_predicates(self, predicates: Dict[str, Any]) -> str:
        """
        Convert Python predicates to VAST-optimized filter expressions.
        
        Args:
            predicates: Dictionary of column predicates
                Example: {
                    'format': 'urn:x-nmos:format:video',
                    'frame_width': {'gte': 1920},
                    'created': {'between': [start_time, end_time]},
                    'tags': {'contains': 'live'}
                }
                
        Returns:
            VAST-compatible filter string
        """
        if not predicates:
            return ""
        
        filter_parts = []
        
        for column, condition in predicates.items():
            if isinstance(condition, dict):
                # Complex condition (range, comparison, etc.)
                for operator, value in condition.items():
                    filter_part = self._build_complex_predicate(column, operator, value)
                    if filter_part:
                        filter_parts.append(filter_part)
            else:
                # Simple equality
                filter_part = self._build_simple_predicate(column, condition)
                if filter_part:
                    filter_parts.append(filter_part)
        
        if filter_parts:
            return " AND ".join(filter_parts)
        return ""
    
    def _build_simple_predicate(self, column: str, value: Any) -> str:
        """Build simple equality predicate"""
        if value is None:
            return f"{column} IS NULL"
        elif isinstance(value, str):
            return f"{column} = '{value}'"
        elif isinstance(value, (int, float, bool)):
            return f"{column} = {value}"
        else:
            logger.warning(f"Unsupported value type for column {column}: {type(value)}")
            return ""
    
    def _build_complex_predicate(self, column: str, operator: str, value: Any) -> str:
        """Build complex predicate with operators"""
        try:
            if operator == 'eq':
                return self._build_simple_predicate(column, value)
            elif operator == 'ne':
                if value is None:
                    return f"{column} IS NOT NULL"
                return f"{column} != {self._format_value(value)}"
            elif operator in ['gt', 'gte', 'lt', 'lte']:
                op_map = {'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}
                return f"{column} {op_map[operator]} {self._format_value(value)}"
            elif operator == 'between':
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    start, end = value
                    return f"{column} BETWEEN {self._format_value(start)} AND {self._format_value(end)}"
                else:
                    logger.warning(f"Invalid 'between' value for column {column}: {value}")
                    return ""
            elif operator == 'in':
                if isinstance(value, (list, tuple)):
                    formatted_values = [self._format_value(v) for v in value]
                    return f"{column} IN ({', '.join(formatted_values)})"
                else:
                    logger.warning(f"Invalid 'in' value for column {column}: {value}")
                    return ""
            elif operator == 'contains':
                if isinstance(value, str):
                    return f"{column} LIKE '%{value}%'"
                else:
                    logger.warning(f"Invalid 'contains' value for column {column}: {value}")
                    return ""
            elif operator == 'starts_with':
                if isinstance(value, str):
                    return f"{column} LIKE '{value}%'"
                else:
                    logger.warning(f"Invalid 'starts_with' value for column {column}: {value}")
                    return ""
            elif operator == 'ends_with':
                if isinstance(value, str):
                    return f"{column} LIKE '%{value}'"
                else:
                    logger.warning(f"Invalid 'ends_with' value for column {column}: {value}")
                    return ""
            else:
                logger.warning(f"Unsupported operator '{operator}' for column {column}")
                return ""
                
        except Exception as e:
            logger.error(f"Error building predicate for {column} {operator} {value}: {e}")
            return ""
    
    def _format_value(self, value: Any) -> str:
        """Format value for SQL predicate"""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif isinstance(value, datetime):
            return f"'{value.isoformat()}'"
        else:
            return f"'{str(value)}'"
