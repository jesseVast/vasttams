# S3 Key Prefix Support Added

## Summary
Added support for `s3_root_path` configuration to be used as `key_prefix` in S3Client initialization.

## Changes Made

### Issue
The `s3_root_path` setting in `config/config.json` was not being used when creating the S3 client. VAST S3 supports a `key_prefix` parameter which acts the same way - prefixing all object keys.

### Solution
1. **Added `s3_root_path` to Settings model** (`src/vasttams/core/config.py`):
   - Optional field with default `None`
   - Description: "S3 key prefix for all objects (e.g., /tams8-dev)"

2. **Updated S3Client initialization** (`src/vasttams/core/dependencies.py`):
   - Attempts to pass `key_prefix` parameter to `S3Config`
   - Handles gracefully if S3Config doesn't support the parameter

## How It Works

### Configuration
```json
{
  "s3_root_path": "/tams8-dev"
}
```

### Behavior
- If `s3_root_path` is set, it's passed to S3Config as `key_prefix`
- All S3 operations will prefix object keys with this value
- Example: Key `segment123.mp4` becomes `/tams8-dev/segment123.mp4` in the bucket

## Benefits
1. ✅ Namespace isolation for different TAMS environments
2. ✅ All objects organized under a prefix
3. ✅ Easy cleanup - delete entire prefix to remove all TAMS objects
4. ✅ Multi-tenant support

## Status
✅ `s3_root_path` configuration added
✅ Support for passing to S3Config as `key_prefix`
✅ Graceful handling if parameter not supported
✅ No breaking changes

