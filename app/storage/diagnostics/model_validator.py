"""
TAMS Model Validator for compliance checking

Validates all models against TAMS API specification to ensure compliance
and identify potential issues with field names, data types, and structure.
"""

import logging
import inspect
from typing import Dict, Any, List, Optional, Type, get_type_hints
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Model compliance levels"""
    COMPLIANT = "compliant"
    MINOR_ISSUES = "minor_issues"
    MAJOR_ISSUES = "major_issues"
    NON_COMPLIANT = "non_compliant"


class IssueType(Enum):
    """Types of compliance issues"""
    MISSING_FIELD = "missing_field"
    WRONG_FIELD_NAME = "wrong_field_name"
    WRONG_DATA_TYPE = "wrong_data_type"
    INVALID_VALIDATION = "invalid_validation"
    DEPRECATED_FIELD = "deprecated_field"
    TAMS_SPEC_VIOLATION = "tams_spec_violation"


@dataclass
class ValidationIssue:
    """A model validation issue"""
    issue_type: IssueType
    field_name: str
    severity: str  # "critical", "high", "medium", "low"
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    suggestion: Optional[str] = None
    tams_reference: Optional[str] = None


@dataclass
class ModelValidationResult:
    """Result of model validation"""
    model_name: str
    compliance_level: ComplianceLevel
    compliance_percentage: float
    issues: List[ValidationIssue]
    total_fields: int
    compliant_fields: int
    timestamp: datetime
    summary: str


class TAMSModelValidator:
    """TAMS compliance validator for all models"""
    
    def __init__(self):
        """Initialize model validator"""
        self.logger = logging.getLogger(__name__)
        
        # TAMS specification requirements
        self.tams_spec = self._load_tams_specification()
        
    def _load_tams_specification(self) -> Dict[str, Any]:
        """Load TAMS API specification requirements"""
        return {
            "Source": {
                "required_fields": ["id", "format", "label"],
                "optional_fields": ["description", "updated", "tags", "source_collection", "collected_by"],
                "field_types": {
                    "id": "str",
                    "format": "str", 
                    "label": "str",
                    "description": "Optional[str]",
                    "updated": "Optional[datetime]",
                    "tags": "Optional[Tags]"
                },
                "tams_reference": "api/schemas/source.json"
            },
            "Flow": {
                "required_fields": ["id", "source_id", "format"],
                "optional_fields": ["label", "description", "metadata_updated", "segments_updated", 
                                   "metadata_version", "generation", "segment_duration", "tags",
                                   "flow_collection", "collected_by"],
                "field_types": {
                    "id": "str",
                    "source_id": "str",
                    "format": "str",
                    "label": "Optional[str]",
                    "description": "Optional[str]",
                    "metadata_updated": "Optional[datetime]",
                    "segments_updated": "Optional[datetime]"
                },
                "tams_reference": "api/schemas/flow-core.json"
            },
            "VideoFlow": {
                "inherits": "Flow",
                "additional_fields": ["frame_width", "frame_height", "frame_rate"],
                "field_types": {
                    "frame_width": "Optional[int]",
                    "frame_height": "Optional[int]",
                    "frame_rate": "Optional[str]"  # TAMS timestamp format
                },
                "tams_reference": "api/schemas/flow-video.json"
            },
            "AudioFlow": {
                "inherits": "Flow", 
                "additional_fields": ["sample_rate", "channels"],
                "field_types": {
                    "sample_rate": "Optional[str]",  # TAMS timestamp format
                    "channels": "Optional[int]"
                },
                "tams_reference": "api/schemas/flow-audio.json"
            },
            "FlowSegment": {
                "required_fields": ["object_id", "timerange"],
                "optional_fields": ["ts_offset", "last_duration", "sample_offset", "sample_count", "get_urls"],
                "field_types": {
                    "object_id": "str",  # CRITICAL: Must be object_id not id
                    "timerange": "str",
                    "ts_offset": "Optional[str]",
                    "last_duration": "Optional[str]",
                    "get_urls": "Optional[List[GetUrl]]"
                },
                "tams_reference": "api/schemas/flow-segment.json"
            },
            "Object": {
                "required_fields": ["id", "referenced_by_flows"],
                "optional_fields": ["first_referenced_by_flow", "size", "created"],
                "field_types": {
                    "id": "str",  # CRITICAL: Must be id not object_id
                    "referenced_by_flows": "List[str]",  # CRITICAL: List of UUID strings
                    "first_referenced_by_flow": "Optional[str]",
                    "size": "Optional[int]",
                    "created": "Optional[datetime]"
                },
                "tams_reference": "api/schemas/object.json"
            },
            "GetUrl": {
                "required_fields": ["store_type", "provider", "region", "store_product", "url", "storage_id", "presigned", "controlled"],
                "optional_fields": ["availability_zone", "label"],
                "field_types": {
                    "store_type": "str",
                    "provider": "str", 
                    "region": "str",
                    "store_product": "str",
                    "url": "str",
                    "storage_id": "str",
                    "presigned": "bool",
                    "controlled": "bool"
                },
                "tams_reference": "api/schemas/storage-backend.json + flow-segment.json"
            },
            "Webhook": {
                "required_fields": ["url", "events"],
                "optional_fields": ["flow_ids", "source_ids", "flow_collected_by_ids", "source_collected_by_ids",
                                   "accept_get_urls", "accept_storage_ids", "presigned", "verbose_storage"],
                "field_types": {
                    "url": "str",
                    "events": "List[str]",
                    "flow_ids": "Optional[List[str]]",
                    "source_ids": "Optional[List[str]]"
                },
                "tams_reference": "api/schemas/webhook.json"
            }
        }
    
    def validate_model_compliance(self, model_class: Type) -> ModelValidationResult:
        """
        Check if model meets TAMS specification
        
        Args:
            model_class: Pydantic model class to validate
            
        Returns:
            ModelValidationResult with compliance status and issues
        """
        start_time = datetime.utcnow()
        model_name = model_class.__name__
        
        try:
            self.logger.debug(f"Validating model: {model_name}")
            
            # Get model specification
            spec = self._get_model_spec(model_name)
            if not spec:
                return ModelValidationResult(
                    model_name=model_name,
                    compliance_level=ComplianceLevel.NON_COMPLIANT,
                    compliance_percentage=0.0,
                    issues=[ValidationIssue(
                        issue_type=IssueType.TAMS_SPEC_VIOLATION,
                        field_name="N/A",
                        severity="critical",
                        message=f"No TAMS specification found for model {model_name}",
                        suggestion="Check if this model should be TAMS compliant"
                    )],
                    total_fields=0,
                    compliant_fields=0,
                    timestamp=start_time,
                    summary=f"Model {model_name} has no TAMS specification"
                )
            
            # Get model fields
            model_fields = self._get_model_fields(model_class)
            issues = []
            
            # Check required fields
            issues.extend(self._check_required_fields(model_name, model_fields, spec))
            
            # Check field types
            issues.extend(self._check_field_types(model_name, model_fields, spec))
            
            # Check for deprecated or wrong field names
            issues.extend(self._check_field_names(model_name, model_fields, spec))
            
            # Check for TAMS-specific validation issues
            issues.extend(self._check_tams_specific_issues(model_name, model_fields, spec))
            
            # Calculate compliance
            total_fields = len(model_fields)
            critical_issues = len([i for i in issues if i.severity == "critical"])
            high_issues = len([i for i in issues if i.severity == "high"])
            
            # Calculate compliance percentage
            compliance_score = max(0, 100 - (critical_issues * 25) - (high_issues * 10))
            compliance_percentage = min(100.0, compliance_score)
            
            # Determine compliance level
            if compliance_percentage >= 95:
                compliance_level = ComplianceLevel.COMPLIANT
            elif compliance_percentage >= 80:
                compliance_level = ComplianceLevel.MINOR_ISSUES
            elif compliance_percentage >= 60:
                compliance_level = ComplianceLevel.MAJOR_ISSUES
            else:
                compliance_level = ComplianceLevel.NON_COMPLIANT
            
            # Generate summary
            if compliance_level == ComplianceLevel.COMPLIANT:
                summary = f"Model {model_name} is TAMS compliant ({compliance_percentage:.1f}%)"
            else:
                issue_count = len(issues)
                summary = f"Model {model_name} has {issue_count} compliance issues ({compliance_percentage:.1f}%)"
            
            return ModelValidationResult(
                model_name=model_name,
                compliance_level=compliance_level,
                compliance_percentage=compliance_percentage,
                issues=issues,
                total_fields=total_fields,
                compliant_fields=total_fields - len([i for i in issues if i.severity in ["critical", "high"]]),
                timestamp=start_time,
                summary=summary
            )
            
        except Exception as e:
            self.logger.error(f"Model validation failed for {model_name}: {e}")
            return ModelValidationResult(
                model_name=model_name,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                compliance_percentage=0.0,
                issues=[ValidationIssue(
                    issue_type=IssueType.TAMS_SPEC_VIOLATION,
                    field_name="N/A",
                    severity="critical",
                    message=f"Validation failed: {str(e)}",
                    suggestion="Check model definition and structure"
                )],
                total_fields=0,
                compliant_fields=0,
                timestamp=start_time,
                summary=f"Model {model_name} validation failed"
            )
    
    def validate_all_models(self) -> Dict[str, ModelValidationResult]:
        """Validate all TAMS models for compliance"""
        try:
            # Import models
            from ...models.models import (
                Source, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
                FlowSegment, Object, GetUrl, Webhook
            )
            
            models_to_validate = [
                Source, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
                FlowSegment, Object, GetUrl, Webhook
            ]
            
            results = {}
            
            for model_class in models_to_validate:
                result = self.validate_model_compliance(model_class)
                results[model_class.__name__] = result
                
                # Log result
                level = "info" if result.compliance_level == ComplianceLevel.COMPLIANT else "warning"
                getattr(self.logger, level)(f"{result.summary}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to validate all models: {e}")
            return {}
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report for all models"""
        results = self.validate_all_models()
        
        if not results:
            return {
                "overall_compliance": 0.0,
                "status": "failed",
                "message": "Model validation failed",
                "models": {},
                "summary": {"compliant": 0, "minor_issues": 0, "major_issues": 0, "non_compliant": 0}
            }
        
        # Calculate overall compliance
        total_compliance = sum(r.compliance_percentage for r in results.values())
        overall_compliance = total_compliance / len(results) if results else 0.0
        
        # Count compliance levels
        summary = {
            "compliant": 0,
            "minor_issues": 0, 
            "major_issues": 0,
            "non_compliant": 0
        }
        
        for result in results.values():
            summary[result.compliance_level.value] += 1
        
        # Determine overall status
        if overall_compliance >= 95:
            status = "excellent"
        elif overall_compliance >= 80:
            status = "good"
        elif overall_compliance >= 60:
            status = "needs_improvement"
        else:
            status = "critical"
        
        # Generate critical issues list
        critical_issues = []
        for result in results.values():
            for issue in result.issues:
                if issue.severity == "critical":
                    critical_issues.append({
                        "model": result.model_name,
                        "field": issue.field_name,
                        "issue": issue.message,
                        "suggestion": issue.suggestion
                    })
        
        return {
            "overall_compliance": round(overall_compliance, 1),
            "status": status,
            "message": f"Overall TAMS compliance: {overall_compliance:.1f}%",
            "models": {name: {
                "compliance_percentage": result.compliance_percentage,
                "compliance_level": result.compliance_level.value,
                "issues_count": len(result.issues),
                "critical_issues": len([i for i in result.issues if i.severity == "critical"]),
                "summary": result.summary
            } for name, result in results.items()},
            "summary": summary,
            "critical_issues": critical_issues,
            "recommendations": self._generate_recommendations(results)
        }
    
    def _get_model_spec(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get TAMS specification for model"""
        spec = self.tams_spec.get(model_name)
        
        # Handle inheritance
        if spec and "inherits" in spec:
            parent_spec = self.tams_spec.get(spec["inherits"], {})
            inherited_spec = parent_spec.copy()
            
            # Merge specifications
            for key, value in spec.items():
                if key == "inherits":
                    continue
                elif key in ["required_fields", "optional_fields"] and key in inherited_spec:
                    inherited_spec[key] = inherited_spec[key] + value
                elif key == "field_types" and key in inherited_spec:
                    inherited_spec[key].update(value)
                else:
                    inherited_spec[key] = value
            
            return inherited_spec
        
        return spec
    
    def _get_model_fields(self, model_class: Type) -> Dict[str, Any]:
        """Get fields from Pydantic model"""
        try:
            # Get model fields from Pydantic model
            if hasattr(model_class, '__fields__'):
                return {name: field for name, field in model_class.__fields__.items()}
            elif hasattr(model_class, 'model_fields'):
                return model_class.model_fields
            else:
                # Fallback to type hints
                return get_type_hints(model_class)
        except Exception as e:
            self.logger.warning(f"Could not get fields for {model_class.__name__}: {e}")
            return {}
    
    def _check_required_fields(self, model_name: str, model_fields: Dict[str, Any], spec: Dict[str, Any]) -> List[ValidationIssue]:
        """Check for missing required fields"""
        issues = []
        required_fields = spec.get("required_fields", [])
        
        for field_name in required_fields:
            if field_name not in model_fields:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MISSING_FIELD,
                    field_name=field_name,
                    severity="critical",
                    message=f"Missing required TAMS field: {field_name}",
                    expected=field_name,
                    actual="Not present",
                    suggestion=f"Add required field '{field_name}' to {model_name} model",
                    tams_reference=spec.get("tams_reference")
                ))
        
        return issues
    
    def _check_field_types(self, model_name: str, model_fields: Dict[str, Any], spec: Dict[str, Any]) -> List[ValidationIssue]:
        """Check field types against TAMS specification"""
        issues = []
        expected_types = spec.get("field_types", {})
        
        for field_name, expected_type in expected_types.items():
            if field_name in model_fields:
                # Get actual field type (simplified check)
                actual_field = model_fields[field_name]
                
                # This is a simplified type check - in practice you'd need more sophisticated type comparison
                # For now, we'll focus on obvious mismatches
                
                # Check for common TAMS compliance issues
                if field_name == "referenced_by_flows" and "List[str]" in expected_type:
                    # This should be a simple list of strings, not complex objects
                    issues.append(ValidationIssue(
                        issue_type=IssueType.WRONG_DATA_TYPE,
                        field_name=field_name,
                        severity="critical",
                        message=f"Field {field_name} should be List[str] for TAMS compliance",
                        expected="List[str] (UUID strings)",
                        actual="Current implementation",
                        suggestion=f"Change {field_name} to List[str] containing Flow UUID strings",
                        tams_reference=spec.get("tams_reference")
                    ))
        
        return issues
    
    def _check_field_names(self, model_name: str, model_fields: Dict[str, Any], spec: Dict[str, Any]) -> List[ValidationIssue]:
        """Check for incorrect field names"""
        issues = []
        
        # Check for common TAMS field name issues
        tams_field_mappings = {
            "object_id": "id",  # Object model should use 'id' not 'object_id'
            "flow_references": "referenced_by_flows",  # Object model field name
            "metadata_updated": "updated",  # Source model uses 'updated' not 'metadata_updated'
        }
        
        # Check for wrong field names in Object model
        if model_name == "Object":
            if "object_id" in model_fields and "id" not in model_fields:
                issues.append(ValidationIssue(
                    issue_type=IssueType.WRONG_FIELD_NAME,
                    field_name="object_id",
                    severity="critical",
                    message="Object model should use 'id' field not 'object_id' for TAMS compliance",
                    expected="id",
                    actual="object_id",
                    suggestion="Rename 'object_id' field to 'id' in Object model",
                    tams_reference="api/schemas/object.json"
                ))
            
            if "flow_references" in model_fields and "referenced_by_flows" not in model_fields:
                issues.append(ValidationIssue(
                    issue_type=IssueType.WRONG_FIELD_NAME,
                    field_name="flow_references",
                    severity="critical",
                    message="Object model should use 'referenced_by_flows' not 'flow_references'",
                    expected="referenced_by_flows",
                    actual="flow_references",
                    suggestion="Rename 'flow_references' to 'referenced_by_flows' in Object model",
                    tams_reference="api/schemas/object.json"
                ))
        
        # Check for wrong field names in FlowSegment model
        if model_name == "FlowSegment":
            if "id" in model_fields and "object_id" not in model_fields:
                issues.append(ValidationIssue(
                    issue_type=IssueType.WRONG_FIELD_NAME,
                    field_name="id",
                    severity="critical",
                    message="FlowSegment model should use 'object_id' field not 'id' for TAMS compliance",
                    expected="object_id",
                    actual="id",
                    suggestion="Rename 'id' field to 'object_id' in FlowSegment model",
                    tams_reference="api/schemas/flow-segment.json"
                ))
        
        return issues
    
    def _check_tams_specific_issues(self, model_name: str, model_fields: Dict[str, Any], spec: Dict[str, Any]) -> List[ValidationIssue]:
        """Check for TAMS-specific compliance issues"""
        issues = []
        
        # Check GetUrl model for storage-backend compliance
        if model_name == "GetUrl":
            storage_backend_fields = ["store_type", "provider", "region", "store_product"]
            for field in storage_backend_fields:
                if field not in model_fields:
                    issues.append(ValidationIssue(
                        issue_type=IssueType.MISSING_FIELD,
                        field_name=field,
                        severity="high",
                        message=f"GetUrl missing storage-backend field: {field}",
                        expected=field,
                        actual="Not present",
                        suggestion=f"Add {field} field to GetUrl model for storage-backend compliance",
                        tams_reference="api/schemas/storage-backend.json"
                    ))
        
        # Check for dynamic fields that should be computed
        dynamic_fields = ["source_collection", "collected_by", "flow_collection"]
        for field in dynamic_fields:
            if field in model_fields:
                issues.append(ValidationIssue(
                    issue_type=IssueType.TAMS_SPEC_VIOLATION,
                    field_name=field,
                    severity="medium",
                    message=f"Field {field} should be computed dynamically, not stored",
                    expected="Dynamic computation",
                    actual="Static field",
                    suggestion=f"Remove {field} from model and compute dynamically from relationships",
                    tams_reference="TAMS dynamic collections specification"
                ))
        
        return issues
    
    def _generate_recommendations(self, results: Dict[str, ModelValidationResult]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Count issues by severity
        critical_count = sum(len([i for i in r.issues if i.severity == "critical"]) for r in results.values())
        high_count = sum(len([i for i in r.issues if i.severity == "high"]) for r in results.values())
        
        if critical_count > 0:
            recommendations.append(f"URGENT: Fix {critical_count} critical TAMS compliance issues immediately")
            recommendations.append("Critical issues prevent proper TAMS API integration")
        
        if high_count > 0:
            recommendations.append(f"Fix {high_count} high-priority TAMS compliance issues")
        
        # Model-specific recommendations
        non_compliant_models = [name for name, result in results.items() 
                               if result.compliance_level == ComplianceLevel.NON_COMPLIANT]
        
        if non_compliant_models:
            recommendations.append(f"Focus on these non-compliant models: {', '.join(non_compliant_models)}")
        
        # General recommendations
        overall_compliance = sum(r.compliance_percentage for r in results.values()) / len(results) if results else 0
        
        if overall_compliance < 90:
            recommendations.extend([
                "Review TAMS API specification documentation",
                "Update model field names to match TAMS requirements",
                "Implement missing required fields",
                "Test API responses against TAMS specification"
            ])
        
        return recommendations if recommendations else ["All models are TAMS compliant!"]
