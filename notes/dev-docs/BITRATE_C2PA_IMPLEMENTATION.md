# Bit Rate Auto-Calculation & C2PA Support

## Overview

Implementation of TAMS App Note 0013 (Bit Rate Calculation) and App Note 0011 (C2PA Provenance).

## Bit Rate Auto-Calculation (App Note 0013)

### Implementation

**Location**: `src/vasttams/flows/bitrate_calculator.py`

### Features

1. **Average Bit Rate Calculation**
   ```python
   avg_bit_rate = int(total_segment_bit_size / (total_segment_duration_sec * 1000))  # kbit/sec
   ```

2. **Maximum Bit Rate Calculation**
   ```python
   max_bit_rate = int(peak_segment_bit_rate / 1000)  # kbit/sec
   ```
   - Peak calculated over contiguous sequences
   - Duration between 0.5x and 1.5x target segment duration
   - Includes HLS extension for single large segments

### Usage

```python
from vasttams.flows.bitrate_calculator import BitRateCalculator

# Calculate from segments
avg_bit_rate = await BitRateCalculator.calculate_avg_bit_rate(segments)
max_bit_rate = await BitRateCalculator.calculate_max_bit_rate(
    segments, 
    target_segment_duration=1.0  # 1 second target
)
```

### Integration Points

The calculator can be integrated into:

1. **Flow Creation**: Auto-calculate when segments are added
2. **Flow Updates**: Recalculate when segments change
3. **Manual Calculation**: Via admin endpoint

### Segment Size Detection

The calculator attempts to determine segment size through:

1. **Custom Function**: Provide `get_segment_size_fn` for custom logic
2. **Sample Count Estimation**: Rough estimate from `sample_count` field
3. **HTTP HEAD Request**: Fetch `content-length` from segment URL

### Limitations

- Segment sizes must be available (via URL or metadata)
- Requires timerange parsing to calculate durations
- HLS-style calculation assumes target segment duration is known

## C2PA Provenance Support (App Note 0011)

### Implementation

**Location**: `src/vasttams/common/c2pa_utils.py`

### Features

1. **Metadata Validation**
   - Validates C2PA manifest structure
   - Checks for required fields (version, assertions)
   - Validates assertion structure

2. **Tag Extraction**
   - Extracts C2PA manifests from TAMS tags
   - Supports C2PA as JSON in tags
   - Automatic parsing and conversion

3. **Chain Validation**
   - Validates assertion chains
   - Checks for claims and signatures
   - Placeholder for cryptographic verification

### Usage

```python
from vasttams.common.c2pa_utils import C2PAValidator, validate_c2pa_in_metadata

# Validate C2PA metadata
is_valid, error = C2PAValidator.validate_c2pa_metadata(metadata)

# Extract from tags
manifest = C2PAValidator.extract_c2pa_from_tags(tags)

# Create C2PA tag for storage
c2pa_tag = C2PAValidator.create_c2pa_tag(manifest)
```

### Storage

C2PA data can be stored:

1. **In Tags**: Use `c2pa` tag with JSON manifest
2. **In Metadata**: Direct C2PA metadata structure
3. **As Provenance**: Referenced by source/flow

### Example C2PA Tag

```json
{
  "c2pa": {
    "version": "1.0",
    "assertions": [
      {
        "assertion_type": "claim",
        "assertion_data": {
          "source": "camera_01",
          "timestamp": "2024-01-01T00:00:00Z"
        }
      }
    ],
    "metadata": {
      "creator": "BBC TAMS",
      "created": "2024-01-01T00:00:00Z"
    }
  }
}
```

## Integration Status

### Bit Rate Calculator

- ✅ **Module Created**: `src/vasttams/flows/bitrate_calculator.py`
- ✅ **App Note Formulas**: Implemented exactly as specified
- ⚠️ **Integration Pending**: Not yet integrated into flow creation/update
- ⚠️ **Segment Size Detection**: Partial (needs storage backend integration)

### C2PA Support

- ✅ **Module Created**: `src/vasttams/common/c2pa_utils.py`
- ✅ **Validation Functions**: Complete
- ✅ **Tag Integration**: Ready for use
- ⚠️ **Storage Integration**: Not yet tested with real C2PA data
- ⚠️ **Cryptographic Verification**: Placeholder (not implemented)

## Recommendations

### For Bit Rate Calculator

1. **Add Auto-Calculation Trigger**
   - When segments are added to a flow
   - When segments are deleted from a flow
   - On flow GET if bit rates are missing

2. **Enhance Segment Size Detection**
   - Add size metadata to segment schema
   - Cache segment sizes for performance
   - Support multiple storage backends

3. **Admin Endpoint**
   - `POST /flows/{flow_id}/recalculate-bit-rates`
   - Manually trigger recalculation

### For C2PA Support

1. **Add Provenance Endpoint**
   - `GET /sources/{source_id}/provenance`
   - `GET /flows/{flow_id}/provenance`

2. **Validate on Create**
   - Optionally validate C2PA on flow/source creation
   - Flag invalid C2PA without rejecting

3. **Cryptographic Verification**
   - Integrate C2PA verification library
   - Verify signatures on read

## Testing

### Bit Rate Calculator Tests Needed

```python
async def test_calculate_avg_bit_rate():
    segments = create_test_segments()
    avg_bit_rate = await BitRateCalculator.calculate_avg_bit_rate(segments)
    assert avg_bit_rate > 0

async def test_calculate_max_bit_rate():
    segments = create_test_segments()
    max_bit_rate = await BitRateCalculator.calculate_max_bit_rate(segments, 1.0)
    assert max_bit_rate > 0
```

### C2PA Validation Tests Needed

```python
def test_validate_c2pa_metadata():
    metadata = {"c2pa": {"version": "1.0", "assertions": []}}
    is_valid, _ = C2PAValidator.validate_c2pa_metadata(metadata)
    assert is_valid

def test_extract_c2pa_from_tags():
    tags = {"c2pa": {"version": "1.0", "assertions": []}}
    manifest = C2PAValidator.extract_c2pa_from_tags(tags)
    assert manifest is not None
```

## Conclusion

✅ **Bit Rate Calculator**: Module complete, integration pending
✅ **C2PA Support**: Module complete, ready for use

Both features are implemented per app notes. Integration into main flow service can be added as needed.

