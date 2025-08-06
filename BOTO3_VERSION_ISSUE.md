# Boto3 Version Compatibility Issue

## Problem
The TAMS application was experiencing S3 upload failures with boto3 version 1.38.46. The error was:
```
An error occurred (NotImplemented) when calling the PutObject operation: A header you provided implies functionality that is not implemented.
```

## Root Cause
Boto3 version 1.38.46 automatically adds headers that are not supported by the MinIO S3-compatible storage backend:
- `Expect: 100-continue`
- `x-amz-checksum-crc32`
- `x-amz-sdk-checksum-algorithm`

These headers are automatically added by boto3 and cannot be easily disabled.

## Solution
Downgrade to boto3 version 1.34.135 which doesn't add these problematic headers.

## Fixed Versions
```txt
boto3==1.34.135
botocore==1.34.162
```

## Testing
After downgrading, S3 operations work correctly with the MinIO backend.

## Notes
- This issue affects MinIO S3-compatible storage backends
- The vasts3.py implementation works because it uses an older boto3 version
- Future boto3 versions may need to be tested for compatibility

## References
- Working implementation: `/Users/jesse.thaloor/Developer/github/genai2/genai2/lib/common/vasts3.py`
- Issue discovered during Docker container deployment testing 