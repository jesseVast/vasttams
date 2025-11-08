# TAMS Tag Implementation Guide

## 📋 **OVERVIEW**
This guide provides practical implementation steps for integrating the TAMS standard tags into our application, based on the official TAMS appnotes.

## 🎯 **IMPLEMENTATION PRIORITIES**

### **Phase 1: Core Tags (Immediate)**
Implement the most essential tags that are currently in use:

1. **`input_quality`** - Media quality classification
2. **`flow_status`** - Workflow management
3. **`hls_exclude`** - HLS filtering (if needed)

### **Phase 2: Reference Tags (Short-term)**
Implement tags for Flow references and provenance:

1. **`originating_id`** - Flow reference tracking
2. **`originating_timerange`** - Time-based references
3. **`c2pa-provenance`** - Content authenticity

### **Phase 3: Advanced Tags (Long-term)**
Implement experimental and implementation-specific tags as needed.

---

## 🔧 **TECHNICAL IMPLEMENTATION**

### **1. Tag Validation System**

Create a comprehensive tag validation system:

```python
# app/storage/tag_validation.py

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class TagDefinition:
    name: str
    status: str  # 'in_use', 'proposed', 'experimental', 'deprecated', 'implementation_specific'
    description: str
    valid_values: Optional[List[str]] = None
    replacement: Optional[str] = None
    usage_notes: Optional[str] = None

class FlowStatus(Enum):
    AWAITING_CONTENT = "awaiting_content"
    INGESTING = "ingesting"
    REPLICATION_IN_PROGRESS = "replication_in_progress"
    CLOSED_COMPLETE = "closed_complete"

class InputQuality(Enum):
    INTERMEDIATE = "intermediate"
    CONTRIBUTION = "contribution"
    WEB = "web"

# Standard tag definitions
STANDARD_FLOW_TAGS = {
    'flow_status': TagDefinition(
        name='flow_status',
        status='proposed',
        description='Current status of a Flow',
        valid_values=[status.value for status in FlowStatus],
        usage_notes='Use for workflow management and status tracking'
    ),
    'input_quality': TagDefinition(
        name='input_quality',
        status='in_use',
        description='Describes the quality of the media',
        valid_values=[quality.value for quality in InputQuality],
        usage_notes='Essential for media quality classification'
    ),
    'originating_id': TagDefinition(
        name='originating_id',
        status='proposed',
        description='ID of the originating Flow when created by reference',
        valid_values=None,  # UUID format
        usage_notes='Use when creating Flows by reference to track origin'
    ),
    'originating_timerange': TagDefinition(
        name='originating_timerange',
        status='proposed',
        description='Timerange in originating Flow corresponding to current Flow',
        valid_values=None,  # TimeRange format
        usage_notes='Critical for time-based references'
    ),
    'c2pa-provenance': TagDefinition(
        name='c2pa-provenance',
        status='proposed',
        description='Signals presence of C2PA provenance data',
        valid_values=['true', 'false'],
        usage_notes='Important for content authenticity and provenance'
    ),
    'hls_exclude': TagDefinition(
        name='hls_exclude',
        status='experimental',
        description='Indicates if the Flow should be excluded from HLS manifest generation',
        valid_values=['true', 'false'],
        usage_notes='Use for HLS filtering and manifest optimization'
    ),
    'hls_segments': TagDefinition(
        name='hls_segments',
        status='experimental',
        description='Limits the number of segments in the HLS manifest',
        valid_values=None,  # Integer
        usage_notes='Use for HLS optimization and segment control'
    )
}

# Deprecated tags with replacements
DEPRECATED_TAGS = {
    'created_by': TagDefinition(
        name='created_by',
        status='deprecated',
        description='Records who created the Flow',
        replacement='created_by field in Flow metadata',
        usage_notes='Use the created_by field in Flow metadata instead'
    ),
    'creation_date': TagDefinition(
        name='creation_date',
        status='deprecated',
        description='Records when the Flow was created',
        replacement='created field in Flow metadata',
        usage_notes='Use the created field in Flow metadata instead'
    ),
    'hls_segment_length': TagDefinition(
        name='hls_segment_length',
        status='deprecated',
        description='Segment duration for HLS',
        replacement='segment_duration field in Flow metadata',
        usage_notes='Use the segment_duration field in Flow metadata instead'
    )
}

def validate_tag(tag_name: str, tag_value: str, entity_type: str = 'flow') -> bool:
    """Validate a tag name and value against standard definitions"""
    
    # Check if tag is deprecated
    if tag_name in DEPRECATED_TAGS:
        deprecation_info = DEPRECATED_TAGS[tag_name]
        raise ValueError(f"Tag '{tag_name}' is deprecated. {deprecation_info.usage_notes}")
    
    # Check if tag is defined in standards
    if entity_type == 'flow' and tag_name in STANDARD_FLOW_TAGS:
        tag_def = STANDARD_FLOW_TAGS[tag_name]
        
        # Validate value if valid_values are defined
        if tag_def.valid_values and tag_value not in tag_def.valid_values:
            raise ValueError(f"Invalid value '{tag_value}' for tag '{tag_name}'. Valid values: {tag_def.valid_values}")
        
        return True
    
    # Allow custom tags but log warning
    print(f"Warning: Custom tag '{tag_name}' used. Consider proposing it for standardization.")
    return True

def get_tag_definition(tag_name: str, entity_type: str = 'flow') -> Optional[TagDefinition]:
    """Get the definition for a standard tag"""
    if entity_type == 'flow' and tag_name in STANDARD_FLOW_TAGS:
        return STANDARD_FLOW_TAGS[tag_name]
    return None

def get_recommended_tags(entity_type: str = 'flow') -> List[str]:
    """Get list of recommended tags for an entity type"""
    if entity_type == 'flow':
        return [tag_name for tag_name, tag_def in STANDARD_FLOW_TAGS.items() 
                if tag_def.status in ['in_use', 'proposed']]
    return []
```

### **2. Enhanced Tag Service**

Update the tag service to include validation and standard tag support:

```python
# app/storage/enhanced_tag_service.py

from .tag_service import TagStorageService
from .tag_validation import validate_tag, get_tag_definition, get_recommended_tags
from typing import Dict, List, Optional

class EnhancedTagStorageService(TagStorageService):
    """Enhanced tag service with standard tag support and validation"""
    
    async def update_source_tag(self, source_id: str, name: str, value: str) -> bool:
        """Update a specific source tag with validation"""
        # Validate the tag
        validate_tag(name, value, 'source')
        
        # Call parent method
        return await super().update_source_tag(source_id, name, value)
    
    async def update_flow_tag(self, flow_id: str, name: str, value: str) -> bool:
        """Update a specific flow tag with validation"""
        # Validate the tag
        validate_tag(name, value, 'flow')
        
        # Call parent method
        return await super().update_flow_tag(flow_id, name, value)
    
    async def get_tag_suggestions(self, entity_type: str = 'flow') -> List[Dict[str, Any]]:
        """Get suggested tags for an entity type"""
        recommended_tags = get_recommended_tags(entity_type)
        suggestions = []
        
        for tag_name in recommended_tags:
            tag_def = get_tag_definition(tag_name, entity_type)
            if tag_def:
                suggestions.append({
                    'name': tag_name,
                    'description': tag_def.description,
                    'status': tag_def.status,
                    'valid_values': tag_def.valid_values,
                    'usage_notes': tag_def.usage_notes
                })
        
        return suggestions
    
    async def validate_tags(self, tags: Dict[str, str], entity_type: str = 'flow') -> Dict[str, List[str]]:
        """Validate a set of tags and return validation results"""
        errors = {}
        warnings = {}
        
        for tag_name, tag_value in tags.items():
            try:
                validate_tag(tag_name, tag_value, entity_type)
            except ValueError as e:
                errors[tag_name] = [str(e)]
            except Exception as e:
                warnings[tag_name] = [f"Validation warning: {str(e)}"]
        
        return {'errors': errors, 'warnings': warnings}
```

### **3. API Enhancements**

Add endpoints for tag management and validation:

```python
# app/api/tags_router.py

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
from ..storage.enhanced_tag_service import EnhancedTagStorageService

router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("/standards/flow")
async def get_flow_tag_standards():
    """Get standard Flow tag definitions"""
    from ..storage.tag_validation import STANDARD_FLOW_TAGS
    
    return {
        "entity_type": "flow",
        "tags": {
            name: {
                "name": tag_def.name,
                "status": tag_def.status,
                "description": tag_def.description,
                "valid_values": tag_def.valid_values,
                "usage_notes": tag_def.usage_notes
            }
            for name, tag_def in STANDARD_FLOW_TAGS.items()
        }
    }

@router.get("/standards/source")
async def get_source_tag_standards():
    """Get standard Source tag definitions"""
    from ..storage.tag_validation import STANDARD_SOURCE_TAGS
    
    return {
        "entity_type": "source",
        "tags": {
            name: {
                "name": tag_def.name,
                "status": tag_def.status,
                "description": tag_def.description,
                "valid_values": tag_def.valid_values,
                "usage_notes": tag_def.usage_notes
            }
            for name, tag_def in STANDARD_SOURCE_TAGS.items()
        }
    }

@router.get("/suggestions/{entity_type}")
async def get_tag_suggestions(
    entity_type: str,
    tag_service: EnhancedTagStorageService = Depends(get_enhanced_tag_service)
):
    """Get tag suggestions for an entity type"""
    if entity_type not in ['flow', 'source']:
        raise HTTPException(status_code=400, detail="Entity type must be 'flow' or 'source'")
    
    suggestions = await tag_service.get_tag_suggestions(entity_type)
    return {"entity_type": entity_type, "suggestions": suggestions}

@router.post("/validate")
async def validate_tags(
    tags: Dict[str, str],
    entity_type: str = 'flow',
    tag_service: EnhancedTagStorageService = Depends(get_enhanced_tag_service)
):
    """Validate a set of tags"""
    if entity_type not in ['flow', 'source']:
        raise HTTPException(status_code=400, detail="Entity type must be 'flow' or 'source'")
    
    results = await tag_service.validate_tags(tags, entity_type)
    return {
        "entity_type": entity_type,
        "validation_results": results,
        "is_valid": len(results['errors']) == 0
    }
```

---

## 📊 **IMPLEMENTATION CHECKLIST**

### **Phase 1: Foundation**
- [ ] Create tag validation system
- [ ] Implement standard tag definitions
- [ ] Add validation to existing tag service
- [ ] Create tag suggestion endpoints

### **Phase 2: Core Tags**
- [ ] Implement `input_quality` tag validation
- [ ] Add `flow_status` tag support
- [ ] Create tag documentation endpoints
- [ ] Add deprecation warnings for old tags

### **Phase 3: Advanced Features**
- [ ] Implement reference tags (`originating_id`, `originating_timerange`)
- [ ] Add provenance support (`c2pa-provenance`)
- [ ] Create tag analytics and reporting
- [ ] Add tag migration utilities

### **Phase 4: Testing & Documentation**
- [ ] Create comprehensive test suite
- [ ] Add tag usage examples
- [ ] Create migration guides
- [ ] Update API documentation

---

## 🎯 **BENEFITS**

1. **Standardization**: Consistent tag usage across the application
2. **Validation**: Prevents invalid tag values and deprecated usage
3. **Documentation**: Clear guidance on tag usage and meaning
4. **Future-proofing**: Easy to add new standard tags
5. **Compliance**: Aligns with TAMS appnotes recommendations

---

**Last Updated**: January 2025  
**Status**: Implementation Guide  
**Next Review**: After Phase 1 completion












