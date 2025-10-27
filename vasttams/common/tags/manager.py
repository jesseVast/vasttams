"""
TAMS Tag Management System

This module provides enhanced tag management capabilities optimized for VAST database.
Following TAMS appnote 0003 requirements for tag names and metadata management.

Key Features:
- Tag validation and standardization
- VAST-optimized tag querying
- Tag proposal workflow
- Tag analytics and usage tracking
- JSON field optimization for VAST
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .timestamp_utils import get_tams_timestamp

logger = logging.getLogger(__name__)


class TagValidationLevel(Enum):
    """Tag validation levels"""
    STRICT = "strict"      # Only allow predefined tags
    MODERATE = "moderate"  # Allow predefined + validated custom tags
    PERMISSIVE = "permissive"  # Allow any tags with basic validation


@dataclass
class TagDefinition:
    """Definition of a standardized tag"""
    name: str
    description: str
    data_type: str  # string, number, boolean, array, object
    required: bool = False
    allowed_values: Optional[List[str]] = None
    pattern: Optional[str] = None  # regex pattern for validation
    examples: Optional[List[str]] = None
    deprecated: bool = False
    replacement: Optional[str] = None


@dataclass
class TagProposal:
    """Tag proposal for new standardized tags"""
    name: str
    description: str
    data_type: str
    justification: str
    examples: List[str]
    proposed_by: str
    proposed_at: datetime
    status: str = "pending"  # pending, approved, rejected
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class TAMSTagManager:
    """
    Enhanced tag management system optimized for VAST database.
    
    This class provides tag validation, querying, and management capabilities
    that work efficiently with VAST's JSON field support.
    """
    
    def __init__(self, validation_level: TagValidationLevel = TagValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.standardized_tags: Dict[str, TagDefinition] = {}
        self.tag_proposals: List[TagProposal] = []
        self._load_standardized_tags()
    
    def _load_standardized_tags(self):
        """Load standardized tag definitions"""
        # Core TAMS tags
        self.standardized_tags.update({
            "tams:format": TagDefinition(
                name="tams:format",
                description="Media format specification",
                data_type="string",
                required=True,
                examples=["urn:x-nmos:format:video", "urn:x-nmos:format:audio"]
            ),
            "tams:codec": TagDefinition(
                name="tams:codec",
                description="Codec used for encoding",
                data_type="string",
                examples=["H.264", "AAC", "PCM"]
            ),
            "tams:resolution": TagDefinition(
                name="tams:resolution",
                description="Video resolution",
                data_type="string",
                pattern=r"^\d+x\d+$",
                examples=["1920x1080", "3840x2160"]
            ),
            "tams:frame_rate": TagDefinition(
                name="tams:frame_rate",
                description="Video frame rate",
                data_type="number",
                examples=[24, 25, 30, 50, 60]
            ),
            "tams:bitrate": TagDefinition(
                name="tams:bitrate",
                description="Bitrate in bits per second",
                data_type="number",
                examples=[1000000, 5000000, 10000000]
            ),
            "tams:duration": TagDefinition(
                name="tams:duration",
                description="Media duration in seconds",
                data_type="number",
                examples=[60, 300, 3600]
            ),
            "tams:language": TagDefinition(
                name="tams:language",
                description="Language code (ISO 639-1)",
                data_type="string",
                pattern=r"^[a-z]{2}$",
                examples=["en", "fr", "de", "es"]
            ),
            "tams:region": TagDefinition(
                name="tams:region",
                description="Geographic region",
                data_type="string",
                examples=["US", "EU", "UK", "APAC"]
            ),
            "tams:department": TagDefinition(
                name="tams:department",
                description="BBC department or division",
                data_type="string",
                examples=["News", "Sport", "Drama", "Documentary"]
            ),
            "tams:programme": TagDefinition(
                name="tams:programme",
                description="Programme or show identifier",
                data_type="string",
                examples=["BBC_News", "Match_of_the_Day", "EastEnders"]
            ),
            "tams:episode": TagDefinition(
                name="tams:episode",
                description="Episode number or identifier",
                data_type="string",
                examples=["S01E01", "2024-01-15", "Special"]
            ),
            "tams:quality": TagDefinition(
                name="tams:quality",
                description="Quality rating or tier",
                data_type="string",
                allowed_values=["draft", "review", "approved", "master"],
                examples=["draft", "review", "approved", "master"]
            ),
            "tams:rights": TagDefinition(
                name="tams:rights",
                description="Rights and usage restrictions",
                data_type="object",
                examples=[{"territory": "UK", "expiry": "2025-12-31"}]
            ),
            "tams:metadata_version": TagDefinition(
                name="tams:metadata_version",
                description="Version of metadata schema",
                data_type="string",
                pattern=r"^\d+\.\d+$",
                examples=["1.0", "2.1", "3.0"]
            ),
            "tams:created_by": TagDefinition(
                name="tams:created_by",
                description="User or system that created the content",
                data_type="string",
                examples=["user123", "ingest_system", "editor_workflow"]
            ),
            "tams:workflow_stage": TagDefinition(
                name="tams:workflow_stage",
                description="Current stage in production workflow",
                data_type="string",
                allowed_values=["ingest", "edit", "review", "approval", "publish"],
                examples=["ingest", "edit", "review", "approval", "publish"]
            )
        })
    
    def validate_tag(self, name: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a tag name and value according to TAMS standards.
        
        Args:
            name: Tag name
            value: Tag value
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check if tag is standardized
        if name in self.standardized_tags:
            definition = self.standardized_tags[name]
            
            # Check if deprecated
            if definition.deprecated:
                replacement = definition.replacement or "None"
                return False, f"Tag '{name}' is deprecated. Use '{replacement}' instead."
            
            # Validate data type
            if not self._validate_data_type(value, definition.data_type):
                return False, f"Tag '{name}' must be of type {definition.data_type}, got {type(value).__name__}"
            
            # Validate pattern if specified
            if definition.pattern and isinstance(value, str):
                if not re.match(definition.pattern, value):
                    return False, f"Tag '{name}' value '{value}' does not match required pattern"
            
            # Validate allowed values if specified
            if definition.allowed_values and value not in definition.allowed_values:
                return False, f"Tag '{name}' value '{value}' not in allowed values: {definition.allowed_values}"
        
        # Custom tag validation based on validation level
        if self.validation_level == TagValidationLevel.STRICT:
            return False, f"Custom tag '{name}' not allowed in strict mode"
        
        # Basic validation for custom tags
        if not self._is_valid_tag_name(name):
            return False, f"Invalid tag name '{name}'. Must be alphanumeric with underscores and colons"
        
        if not self._is_valid_tag_value(value):
            return False, f"Invalid tag value for '{name}'. Value must be serializable"
        
        return True, None
    
    def _validate_data_type(self, value: Any, expected_type: str) -> bool:
        """Validate that value matches expected data type"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        return False
    
    def _is_valid_tag_name(self, name: str) -> bool:
        """Validate tag name format"""
        # Allow alphanumeric, underscores, colons, and hyphens
        pattern = r"^[a-zA-Z0-9_:-]+$"
        return bool(re.match(pattern, name)) and len(name) <= 100
    
    def _is_valid_tag_value(self, value: Any) -> bool:
        """Validate that tag value is serializable"""
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False
    
    def validate_tags(self, tags: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a complete set of tags.
        
        Args:
            tags: Dictionary of tag names to values
            
        Returns:
            Tuple[bool, List[str]]: (all_valid, error_messages)
        """
        errors = []
        all_valid = True
        
        for name, value in tags.items():
            is_valid, error = self.validate_tag(name, value)
            if not is_valid:
                all_valid = False
                errors.append(f"Tag '{name}': {error}")
        
        return all_valid, errors
    
    def standardize_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize tags by applying validation and formatting rules.
        
        Args:
            tags: Raw tags dictionary
            
        Returns:
            Dict[str, Any]: Standardized tags
        """
        standardized = {}
        
        for name, value in tags.items():
            # Validate tag
            is_valid, error = self.validate_tag(name, value)
            if not is_valid:
                logger.warning("Skipping invalid tag: %s", error)
                continue
            
            # Apply standardization rules
            if name in self.standardized_tags:
                definition = self.standardized_tags[name]
                
                # Convert to expected data type
                if definition.data_type == "string" and not isinstance(value, str):
                    value = str(value)
                elif definition.data_type == "number" and isinstance(value, str):
                    try:
                        value = float(value) if '.' in value else int(value)
                    except ValueError:
                        logger.warning("Cannot convert tag value to number: %s", value)
                        continue
                
                # Apply case normalization for certain tags
                if name in ["tams:language"] and isinstance(value, str):
                    value = value.lower()
                elif name in ["tams:region"] and isinstance(value, str):
                    value = value.upper()
            
            standardized[name] = value
        
        return standardized
    
    def create_tag_proposal(self, name: str, description: str, data_type: str, 
                          justification: str, examples: List[str], proposed_by: str) -> TagProposal:
        """
        Create a new tag proposal.
        
        Args:
            name: Proposed tag name
            description: Tag description
            data_type: Expected data type
            justification: Why this tag is needed
            examples: Example values
            proposed_by: User proposing the tag
            
        Returns:
            TagProposal: Created proposal
        """
        proposal = TagProposal(
            name=name,
            description=description,
            data_type=data_type,
            justification=justification,
            examples=examples,
            proposed_by=proposed_by,
            proposed_at=get_tams_timestamp()
        )
        
        self.tag_proposals.append(proposal)
        logger.info("Created tag proposal for '%s' by %s", name, proposed_by)
        
        return proposal
    
    def approve_tag_proposal(self, proposal_name: str, reviewed_by: str) -> bool:
        """
        Approve a tag proposal and add it to standardized tags.
        
        Args:
            proposal_name: Name of the tag proposal
            reviewed_by: User approving the proposal
            
        Returns:
            bool: True if approved successfully
        """
        for proposal in self.tag_proposals:
            if proposal.name == proposal_name and proposal.status == "pending":
                proposal.status = "approved"
                proposal.reviewed_by = reviewed_by
                proposal.reviewed_at = get_tams_timestamp()
                
                # Add to standardized tags
                definition = TagDefinition(
                    name=proposal.name,
                    description=proposal.description,
                    data_type=proposal.data_type,
                    examples=proposal.examples
                )
                self.standardized_tags[proposal.name] = definition
                
                logger.info("Approved tag proposal for '%s' by %s", proposal_name, reviewed_by)
                return True
        
        return False
    
    def get_tag_analytics(self, tags_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate analytics for tag usage across a dataset.
        
        Args:
            tags_data: List of tag dictionaries from sources/flows
            
        Returns:
            Dict[str, Any]: Tag usage analytics
        """
        analytics = {
            "total_items": len(tags_data),
            "tag_frequency": {},
            "tag_value_frequency": {},
            "standardized_tag_usage": {},
            "custom_tag_usage": {},
            "validation_errors": []
        }
        
        for item_tags in tags_data:
            if not item_tags:
                continue
                
            for name, value in item_tags.items():
                # Count tag frequency
                analytics["tag_frequency"][name] = analytics["tag_frequency"].get(name, 0) + 1
                
                # Count value frequency
                value_key = f"{name}:{str(value)}"
                analytics["tag_value_frequency"][value_key] = analytics["tag_value_frequency"].get(value_key, 0) + 1
                
                # Categorize as standardized or custom
                if name in self.standardized_tags:
                    analytics["standardized_tag_usage"][name] = analytics["standardized_tag_usage"].get(name, 0) + 1
                else:
                    analytics["custom_tag_usage"][name] = analytics["custom_tag_usage"].get(name, 0) + 1
                
                # Validate tag
                is_valid, error = self.validate_tag(name, value)
                if not is_valid:
                    analytics["validation_errors"].append({
                        "tag": name,
                        "value": value,
                        "error": error
                    })
        
        return analytics
    
    def generate_vast_query_for_tags(self, tag_filters: Dict[str, Any]) -> str:
        """
        Generate VAST query expression for tag filtering using PyArrow Map types.
        
        Args:
            tag_filters: Dictionary of tag name to value filters
            
        Returns:
            str: VAST query expression
        """
        conditions = []
        
        for name, value in tag_filters.items():
            if isinstance(value, str):
                # String match in Map
                conditions.append(f"tags[\"{name}\"] == \"{value}\"")
            elif isinstance(value, (int, float)):
                # Numeric match in Map
                conditions.append(f"tags[\"{name}\"] == {value}")
            elif isinstance(value, bool):
                # Boolean match in Map
                conditions.append(f"tags[\"{name}\"] == {str(value).lower()}")
            elif isinstance(value, list):
                # Array contains in Map
                if value:
                    value_str = ", ".join([f'"{v}"' if isinstance(v, str) else str(v) for v in value])
                    conditions.append(f"tags[\"{name}\"] in ({value_str})")
        
        return " && ".join(conditions) if conditions else "true"
    
    def generate_sql_query_for_tags(self, table_name: str, tag_filters: Dict[str, Any], 
                                  select_columns: str = "*", limit: int = 100) -> str:
        """
        Generate SQL query for tag filtering using PyArrow Map types.
        
        Args:
            table_name: Name of the table to query
            tag_filters: Dictionary of tag name to value filters
            select_columns: Columns to select (default: "*")
            limit: Maximum number of results (default: 100)
            
        Returns:
            str: SQL query string
        """
        conditions = []
        
        for name, value in tag_filters.items():
            # Escape single quotes in tag names and values
            escaped_name = name.replace("'", "''")
            
            if isinstance(value, str):
                # String match in Map
                escaped_value = value.replace("'", "''")
                conditions.append(f"tags['{escaped_name}'] = '{escaped_value}'")
            elif isinstance(value, (int, float)):
                # Numeric match in Map
                conditions.append(f"tags['{escaped_name}'] = {value}")
            elif isinstance(value, bool):
                # Boolean match in Map
                conditions.append(f"tags['{escaped_name}'] = {str(value).lower()}")
            elif isinstance(value, list):
                # Array contains in Map
                if value:
                    value_list = []
                    for v in value:
                        if isinstance(v, str):
                            escaped_v = v.replace("'", "''")
                            value_list.append(f"'{escaped_v}'")
                        else:
                            value_list.append(str(v))
                    value_str = ", ".join(value_list)
                    conditions.append(f"tags['{escaped_name}'] IN ({value_str})")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT {select_columns}
        FROM {table_name}
        WHERE {where_clause}
        LIMIT {limit}
        """
        
        return sql.strip()
    
    def get_standardized_tags(self) -> Dict[str, TagDefinition]:
        """Get all standardized tag definitions"""
        return self.standardized_tags.copy()
    
    def get_tag_proposals(self, status: Optional[str] = None) -> List[TagProposal]:
        """Get tag proposals, optionally filtered by status"""
        if status:
            return [p for p in self.tag_proposals if p.status == status]
        return self.tag_proposals.copy()


# Global tag manager instance
_tag_manager = TAMSTagManager()


def get_tag_manager() -> TAMSTagManager:
    """Get the global tag manager instance"""
    return _tag_manager


def validate_tags(tags: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate tags using the global tag manager.
    
    Args:
        tags: Dictionary of tag names to values
        
    Returns:
        Tuple[bool, List[str]]: (all_valid, error_messages)
    """
    return _tag_manager.validate_tags(tags)


def standardize_tags(tags: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to standardize tags using the global tag manager.
    
    Args:
        tags: Raw tags dictionary
        
    Returns:
        Dict[str, Any]: Standardized tags
    """
    return _tag_manager.standardize_tags(tags)


def generate_vast_tag_query(tag_filters: Dict[str, Any]) -> str:
    """
    Convenience function to generate VAST query for tag filtering.
    
    Args:
        tag_filters: Dictionary of tag name to value filters
        
    Returns:
        str: VAST query expression
    """
    return _tag_manager.generate_vast_query_for_tags(tag_filters)


def generate_sql_tag_query(table_name: str, tag_filters: Dict[str, Any], 
                          select_columns: str = "*", limit: int = 100) -> str:
    """
    Convenience function to generate SQL query for tag filtering.
    
    Args:
        table_name: Name of the table to query
        tag_filters: Dictionary of tag name to value filters
        select_columns: Columns to select (default: "*")
        limit: Maximum number of results (default: 100)
        
    Returns:
        str: SQL query string
    """
    return _tag_manager.generate_sql_query_for_tags(table_name, tag_filters, select_columns, limit)
