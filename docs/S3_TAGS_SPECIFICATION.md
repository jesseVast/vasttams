# S3 Tags Specification for TAMS API

## Overview

This document specifies the expected S3 tags behavior for the TAMS (Time-addressable Media Store) API system. The video uploader is expected to ingest S3 tags that contain essential metadata to enable complete reconstruction of TAMS data model entities.

## Purpose

S3 tags serve as a metadata layer that allows the TAMS system to:
- Reconstruct Source, Flow, and Segment records from S3 objects
- Maintain data integrity and relationships
- Enable disaster recovery scenarios
- Provide metadata persistence independent of the TAMS database

## Tag Structure Requirements

### 1. Source Metadata Tags

Source tags contain information about the media source that generated the content:

| Tag Name | Description | Required | Example |
|----------|-------------|----------|---------|
| `tams:source_id` | Source identifier (UUID) | ✅ Yes | `tams:source_id=550e8400-e29b-41d4-a716-446655440000` |
| `tams:source_format` | Content format type | ✅ Yes | `tams:source_format=urn:x-nmos:format:video` |
| `tams:source_label` | Human-readable source label | ❌ No | `tams:source_label=Main Camera 1` |
| `tams:source_description` | Source description | ❌ No | `tams:source_description=Primary studio camera` |

**Supported Source Formats:**
- `urn:x-nmos:format:video` - Video content
- `urn:x-nmos:format:audio` - Audio content  
- `urn:x-tam:format:image` - Image content
- `urn:x-nmos:format:data` - Data content
- `urn:x-nmos:format:multi` - Multi-format content

### 2. Flow Metadata Tags

Flow tags contain information about the media flow that processes the source:

| Tag Name | Description | Required | Example |
|----------|-------------|----------|---------|
| `tams:flow_id` | Flow identifier (UUID) | ✅ Yes | `tams:flow_id=550e8400-e29b-41d4-a716-446655440001` |
| `tams:flow_label` | Flow label | ❌ No | `tams:flow_label=Main Video Stream` |
| `tams:flow_description` | Flow description | ❌ No | `tams:flow_description=Primary video processing pipeline` |
| `tams:flow_codec` | Media codec information | ❌ No | `tams:flow_codec=video/H.264` |
| `tams:flow_container` | Container format | ❌ No | `tams:flow_container=video/MP4` |

### 3. Segment Metadata Tags

Segment tags contain information about the specific media segment:

| Tag Name | Description | Required | Example |
|----------|-------------|----------|---------|
| `tams:segment_id` | Segment identifier (UUID) | ✅ Yes | `tams:segment_id=550e8400-e29b-41d4-a716-446655440002` |
| `tams:segment_timerange` | Time range for the segment | ✅ Yes | `tams:segment_timerange=[2024-01-01T10:00:00Z:2024-01-01T10:00:10Z)` |
| `tams:segment_sample_offset` | Sample offset from start | ❌ No | `tams:segment_sample_offset=0` |
| `tams:segment_sample_count` | Number of samples in segment | ❌ No | `tams:segment_sample_count=300` |

## Tag Naming Convention

### Prefix
All TAMS-related tags use the `tams:` prefix to avoid conflicts with other systems and provide clear identification.

### Format
```
tams:entity_type:field_name=value
```

### Examples
```
tams:source_id=550e8400-e29b-41d4-a716-446655440000
tams:flow_codec=video/H.264
tams:segment_timerange=[2024-01-01T10:00:00Z:2024-01-01T10:00:10Z)
```

## Implementation Requirements

### Video Uploader Responsibilities

1. **Tag Application**: Apply all required and optional tags during S3 object upload
2. **Metadata Extraction**: Extract metadata from TAMS API responses and apply as tags
3. **Validation**: Ensure all required tags are present before upload
4. **Consistency**: Maintain consistent tag values across related objects

### Tag Validation

The video uploader should validate:
- All required tags are present
- Tag values match expected formats (UUIDs, time ranges, etc.)
- No duplicate tag names
- Tag values don't exceed S3 limits

### S3 Tag Limits

- **Maximum Tags per Object**: 10 tags
- **Tag Key Length**: 128 characters maximum
- **Tag Value Length**: 256 characters maximum
- **Tag Key Characters**: Unicode letters, digits, spaces, and `+ - = . _ : / @`
- **Tag Value Characters**: Unicode letters, digits, spaces, and `+ - = . _ : / @`

## Data Reconstruction

### From S3 Tags to TAMS Records

The system should be able to reconstruct:

1. **Source Record**:
   ```json
   {
     "id": "550e8400-e29b-41d4-a716-446655440000",
     "format": "urn:x-nmos:format:video",
     "label": "Main Camera 1",
     "description": "Primary studio camera"
   }
   ```

2. **Flow Record**:
   ```json
   {
     "id": "550e8400-e29b-41d4-a716-446655440001",
     "source_id": "550e8400-e29b-41d4-a716-446655440000",
     "label": "Main Video Stream",
     "description": "Primary video processing pipeline",
     "codec": "video/H.264",
     "container": "video/MP4"
   }
   ```

3. **Segment Record**:
   ```json
   {
     "object_id": "550e8400-e29b-41d4-a716-446655440002",
     "timerange": "[2024-01-01T10:00:00Z:2024-01-01T10:00:10Z)",
     "sample_offset": 0,
     "sample_count": 300
   }
   ```

## Error Handling

### Missing Required Tags
If required tags are missing, the system should:
1. Log the missing tag information
2. Attempt to infer values from other available tags
3. Mark the object as requiring manual intervention
4. Notify administrators of incomplete metadata

### Invalid Tag Values
If tag values are invalid, the system should:
1. Log the validation error
2. Attempt to parse or correct the value
3. Mark the object as requiring review
4. Provide clear error messages for debugging

## Best Practices

### Tag Organization
1. **Group Related Tags**: Keep source, flow, and segment tags together
2. **Consistent Ordering**: Apply tags in a consistent order for easier debugging
3. **Descriptive Values**: Use clear, descriptive values for optional tags

### Performance Considerations
1. **Minimal Tags**: Only include essential metadata to stay within S3 limits
2. **Efficient Queries**: Design tags to support efficient S3 object queries
3. **Batch Operations**: Apply tags during upload to avoid additional API calls

### Maintenance
1. **Regular Validation**: Periodically validate tag consistency across objects
2. **Tag Auditing**: Monitor tag usage and identify optimization opportunities
3. **Documentation Updates**: Keep this specification updated with any changes

## Example Implementation

### Python Example (boto3)
```python
import boto3
from datetime import datetime

def apply_tams_tags(s3_client, bucket, key, source_data, flow_data, segment_data):
    """Apply TAMS tags to S3 object"""
    
    tags = {
        # Source tags
        'tams:source_id': source_data['id'],
        'tams:source_format': source_data['format'],
        'tams:source_label': source_data.get('label', ''),
        'tams:source_description': source_data.get('description', ''),
        
        # Flow tags
        'tams:flow_id': flow_data['id'],
        'tams:flow_label': flow_data.get('label', ''),
        'tams:flow_description': flow_data.get('description', ''),
        'tams:flow_codec': flow_data.get('codec', ''),
        'tams:flow_container': flow_data.get('container', ''),
        
        # Segment tags
        'tams:segment_id': segment_data['id'],
        'tams:segment_timerange': segment_data['timerange'],
        'tams:segment_sample_offset': str(segment_data.get('sample_offset', 0)),
        'tams:segment_sample_count': str(segment_data.get('sample_count', 0))
    }
    
    # Remove empty tags
    tags = {k: v for k, v in tags.items() if v}
    
    # Apply tags to S3 object
    s3_client.put_object_tagging(
        Bucket=bucket,
        Key=key,
        Tagging={'TagSet': [{'Key': k, 'Value': v} for k, v in tags.items()]}
    )
```

### JavaScript Example (AWS SDK v3)
```javascript
import { S3Client, PutObjectTaggingCommand } from '@aws-sdk/client-s3';

async function applyTamsTags(s3Client, bucket, key, sourceData, flowData, segmentData) {
    const tags = {
        // Source tags
        'tams:source_id': sourceData.id,
        'tams:source_format': sourceData.format,
        'tams:source_label': sourceData.label || '',
        'tams:source_description': sourceData.description || '',
        
        // Flow tags
        'tams:flow_id': flowData.id,
        'tams:flow_label': flowData.label || '',
        'tams:flow_description': flowData.description || '',
        'tams:flow_codec': flowData.codec || '',
        'tams:flow_container': flowData.container || '',
        
        // Segment tags
        'tams:segment_id': segmentData.id,
        'tams:segment_timerange': segmentData.timerange,
        'tams:segment_sample_offset': String(segmentData.sampleOffset || 0),
        'tams:segment_sample_count': String(segmentData.sampleCount || 0)
    };
    
    // Remove empty tags
    const filteredTags = Object.fromEntries(
        Object.entries(tags).filter(([_, value]) => value)
    );
    
    // Apply tags to S3 object
    const command = new PutObjectTaggingCommand({
        Bucket: bucket,
        Key: key,
        Tagging: {
            TagSet: Object.entries(filteredTags).map(([key, value]) => ({
                Key: key,
                Value: value
            }))
        }
    });
    
    await s3Client.send(command);
}
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | December 2024 | Initial specification document |

## Related Documentation

- [TAMS API Specification](../api/TimeAddressableMediaStore.yaml)
- [TAMS Architecture Overview](./ARCHITECTURE.md)
- [TAMS Deployment Guide](./DEPLOYMENT.md)
- [TAMS Development Guide](./DEVELOPMENT.md)

## Support

For questions or clarifications about this specification, please:
1. Review the TAMS API documentation
2. Check the implementation examples
3. Contact the TAMS development team
4. Open an issue in the TAMS repository
