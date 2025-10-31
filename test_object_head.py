#!/usr/bin/env python3
"""
Simple script to get object HEAD info using boto3
"""
import boto3
import json
from botocore.client import Config

# Read config
with open('config/config.json') as f:
    config = json.load(f)

# Get S3 settings
s3_config = config.get("storage_backends", [{}])[0]
endpoint = s3_config.get("endpoint_url", "http://localhost:9000")
bucket = s3_config.get("bucket_name", "tams")
access_key = s3_config.get("access_key", "")
secret_key = s3_config.get("secret_key", "")
root_path = s3_config.get("root_path", "").strip('/')

# Object ID to check
object_id = "31b51864-a529-48ba-b44c-f0f4a4a31bcb"
flow_id = "f09b47dd-5645-41c0-a22e-69bfe61eed99"

# Create S3 client
s3_client = boto3.client(
    's3',
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version='s3v4')
)

# First, let's search for objects matching this ID
print(f"Searching for object: {object_id}")
print(f"Bucket: {bucket}")
print()

# List objects and find the one with this ID
try:
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, MaxKeys=1000)
    
    found_path = None
    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if object_id in key:
                found_path = key
                print(f"✅ Found object at: {key}")
                print(f"   Size in listing: {obj['Size']} bytes")
                break
        if found_path:
            break
    
    if found_path:
        print(f"\nGetting HEAD for: {found_path}")
        response = s3_client.head_object(Bucket=bucket, Key=found_path)
        print(f"✅ HEAD Response:")
        print(f"ContentLength: {response.get('ContentLength')}")
        print(f"ContentType: {response.get('ContentType')}")
        print(f"ETag: {response.get('ETag')}")
        print(f"LastModified: {response.get('LastModified')}")
        print(f"\nAll headers:")
        for key, value in response.items():
            print(f"  {key}: {value}")
        
        # Now test vasts3.get_object_metadata() to see what it returns
        print(f"\n" + "="*60)
        print(f"Testing vasts3.get_object_metadata() for comparison:")
        print("="*60)
        from vasts3 import S3Client, S3Config
        
        s3_vasts3_config = S3Config(
            endpoint_url=endpoint,
            bucket_name=bucket,
            access_key=access_key,
            secret_key=secret_key,
            region="us-east-1",
            use_ssl=False,
            key_prefix=root_path if root_path else None
        )
        vasts3_client = S3Client(s3_vasts3_config)
        
        # The storage_path we use in the code doesn't include root_path prefix
        # Remove the root_path prefix if it's in the found_path
        key_for_vasts3 = found_path
        if root_path and found_path.startswith(root_path + "/"):
            key_for_vasts3 = found_path[len(root_path) + 1:]
        elif root_path and found_path.startswith(root_path):
            key_for_vasts3 = found_path[len(root_path):]
        
        print(f"\nCalling vasts3.get_object_metadata(key='{key_for_vasts3}')")
        try:
            vasts3_metadata = vasts3_client.get_object_metadata(key=key_for_vasts3)
            print(f"✅ vasts3 returned: {type(vasts3_metadata)}")
            print(f"Value: {vasts3_metadata}")
            print(f"Repr: {repr(vasts3_metadata)}")
            
            if isinstance(vasts3_metadata, dict):
                print(f"\nDict keys: {list(vasts3_metadata.keys())}")
                for k, v in vasts3_metadata.items():
                    print(f"  {k}: {v} (type: {type(v).__name__})")
                size = vasts3_metadata.get('ContentLength') or vasts3_metadata.get('content-length') or vasts3_metadata.get('content_length') or vasts3_metadata.get('size')
                print(f"\nExtracted size: {size} (type: {type(size)})")
            elif hasattr(vasts3_metadata, '__dict__'):
                print(f"\nObject attributes:")
                for attr in dir(vasts3_metadata):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(vasts3_metadata, attr)
                            if not callable(value):
                                print(f"  {attr}: {value} (type: {type(value).__name__})")
                        except:
                            pass
            elif hasattr(vasts3_metadata, 'ContentLength'):
                print(f"ContentLength attribute: {vasts3_metadata.ContentLength}")
            elif hasattr(vasts3_metadata, 'content_length'):
                print(f"content_length attribute: {vasts3_metadata.content_length}")
        except Exception as e:
            print(f"❌ Error calling vasts3.get_object_metadata(): {e}")
            import traceback
            traceback.print_exc()
            
    else:
        print(f"❌ Object ID {object_id} not found in bucket")
        print(f"\nSample objects in bucket:")
        pages = paginator.paginate(Bucket=bucket, MaxKeys=10)
        for page in pages:
            for obj in page.get('Contents', [])[:10]:
                print(f"  {obj['Key']} ({obj['Size']} bytes)")
            break
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
