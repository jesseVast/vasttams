# TAMS Standard Tags Reference

## 📋 **OVERVIEW**
This document provides a comprehensive reference for standard tags used in the BBC TAMS (Time-based Asset Management System) based on [Appnote 0003 - Tag Names and Metadata](https://github.com/bbc/tams/blob/main/docs/appnotes/0003-tag-names.md).

## 🏷️ **TAG STATUS DEFINITIONS**

- **In Use**: Currently implemented and widely used
- **Proposed**: Suggested for standardization, under consideration
- **Experimental**: Being tested, may change
- **Implementation Specific**: Used by specific implementations
- **Deprecated**: No longer recommended, replaced by core API fields

---

## 🔄 **FLOW TAGS**

### **Deprecated Tags**
| Tag Name | Status | Replacement | Description |
|----------|--------|-------------|-------------|
| `created_by` | Deprecated | `created_by` field in Flow metadata | Records who created the Flow |
| `creation_date` | Deprecated | `created` field in Flow metadata | Records when the Flow was created |
| `proxy_of_flow` | Deprecated | - | Previously indicated a Flow is a proxy of another Flow |
| `hls_segment_length` | Deprecated | `segment_duration` field in Flow metadata | Segment duration for HLS |

### **Proposed Tags**
| Tag Name | Status | Description | Known Values |
|----------|--------|-------------|--------------|
| `flow_status` | Proposed | Current status of a Flow | `awaiting_content`, `ingesting`, `replication_in_progress`, `closed_complete` |
| `originating_id` | Proposed | ID of the originating Flow when created by reference | Flow UUID |
| `originating_timerange` | Proposed | Timerange in originating Flow corresponding to current Flow | TimeRange format |
| `c2pa-provenance` | Proposed | Signals presence of C2PA provenance data | Boolean/Flag |

### **In Use Tags**
| Tag Name | Status | Description | Known Values |
|----------|--------|-------------|--------------|
| `input_quality` | In Use | Describes the quality of the media | `intermediate`, `contribution`, `web` |

### **Implementation Specific Tags**
| Tag Name | Status | Description | Usage |
|----------|--------|-------------|-------|
| `salmon_created_by_job` | Implementation Specific | Records the Salmon job ID which created the Flow | Salmon workflow tracking |
| `writing_flow_timing_temi_timestamps` | Implementation Specific | Indicates inclusion of TEMI timing in MPEG-TS | Broadcast timing |
| `_cloudfit_squirrel_segmentation_rate` | Implementation Specific | Sets the segment rate of the Flow | CloudFit Squirrel system |
| `_tams_segmentation_rate` | Implementation Specific | Sets the segment rate of the Flow | TAMS internal segmentation |

### **Experimental Tags**
| Tag Name | Status | Description | Usage |
|----------|--------|-------------|-------|
| `hls_segments` | Experimental | Limits the number of segments in the HLS manifest | HLS optimization |
| `hls_exclude` | Experimental | Indicates if the Flow should be excluded from HLS manifest generation | HLS filtering |

---

## 📡 **SOURCE TAGS**

### **Experimental Tags**
| Tag Name | Status | Description | Usage |
|----------|--------|-------------|-------|
| `hls_exclude` | Experimental | Indicates if the Source should be excluded from HLS manifest generation | HLS filtering |

---

## 🎯 **RECOMMENDED IMPLEMENTATION**

### **Priority 1: In Use Tags**
Implement these tags first as they are actively used:
- `input_quality` - Essential for media quality classification

### **Priority 2: Proposed Tags**
Consider implementing these for future compatibility:
- `flow_status` - Useful for workflow management
- `originating_id` - Important for Flow references
- `originating_timerange` - Critical for time-based references
- `c2pa-provenance` - Important for content authenticity

### **Priority 3: Experimental Tags**
Implement based on specific needs:
- `hls_segments` - If HLS optimization is required
- `hls_exclude` - If HLS filtering is needed

### **Implementation Specific Tags**
Implement only if using the specific systems:
- `salmon_created_by_job` - Only if using Salmon workflow
- `writing_flow_timing_temi_timestamps` - Only for broadcast applications
- `_cloudfit_squirrel_segmentation_rate` - Only if using CloudFit Squirrel
- `_tams_segmentation_rate` - Only for TAMS internal segmentation

---

## 🔧 **TECHNICAL IMPLEMENTATION**

### **Tag Validation**
```python
# Example tag validation for flow_status
VALID_FLOW_STATUS_VALUES = [
    'awaiting_content',
    'ingesting', 
    'replication_in_progress',
    'closed_complete'
]

def validate_flow_status_tag(value):
    if value not in VALID_FLOW_STATUS_VALUES:
        raise ValueError(f"Invalid flow_status value: {value}")
    return value
```

### **Tag Documentation**
Each tag should include:
- **Name**: Exact tag name
- **Status**: Current status (In Use, Proposed, etc.)
- **Description**: What the tag represents
- **Valid Values**: List of acceptable values
- **Usage Examples**: How to use the tag
- **Deprecation Notes**: If applicable

---

## 📚 **REFERENCES**

- [TAMS Appnote 0003 - Tag Names and Metadata](https://github.com/bbc/tams/blob/main/docs/appnotes/0003-tag-names.md)
- [TAMS API Documentation](https://github.com/bbc/tams)
- [C2PA Provenance Documentation](https://c2pa.org/)

---

**Last Updated**: January 2025  
**Status**: Reference Document  
**Next Review**: When new tags are proposed















