#!/usr/bin/env python3
"""
Debug S3 presigned URL generation directly
"""
import asyncio
import requests
import json

async def debug_s3_urls():
    """Debug S3 presigned URL generation"""
    print("🔍 Debugging S3 Presigned URL Generation")
    print("=" * 50)
    
    # First, let's check if we can get a segment with storage_path
    try:
        print("📋 Getting segment with storage_path...")
        response = requests.get("http://localhost:8000/flows/d2e3f4a5-6b7c-4d8e-9f0a-1b2c3d4e5f6a/segments")
        if response.status_code == 200:
            segments = response.json()
            if segments:
                latest_segment = segments[-1]
                print(f"   Latest segment: {latest_segment.get('object_id')}")
                print(f"   Storage path: {latest_segment.get('storage_path')}")
                print(f"   Get URLs count: {len(latest_segment.get('get_urls', []))}")
                
                # Try to access the S3 object directly using the storage path
                if latest_segment.get('storage_path'):
                    storage_path = latest_segment['storage_path']
                    print(f"\n🌐 Testing direct S3 access...")
                    print(f"   Storage path: {storage_path}")
                    
                    # Try to generate a presigned URL manually
                    # This will help us see if the issue is with S3 or with our get_urls generation
                    try:
                        # Check if the object exists in S3 by trying to get its metadata
                        # We'll use the S3 endpoint directly
                        s3_endpoint = "http://172.200.204.91"  # From your config
                        bucket = "jthaloor-s3"
                        object_key = storage_path
                        
                        print(f"   S3 Endpoint: {s3_endpoint}")
                        print(f"   Bucket: {bucket}")
                        print(f"   Object Key: {object_key}")
                        
                        # Try to get object metadata (HEAD request)
                        s3_url = f"{s3_endpoint}/{bucket}/{object_key}"
                        print(f"   Testing URL: {s3_url}")
                        
                        # This won't work without proper S3 authentication, but it helps debug
                        print(f"   Note: Direct S3 access requires proper authentication")
                        
                    except Exception as e:
                        print(f"   ❌ S3 test failed: {e}")
                
        else:
            print(f"   Failed to get segments: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n🔧 Next steps:")
    print("   1. Check server logs for S3 presigned URL generation errors")
    print("   2. Verify S3 client configuration in S3Core")
    print("   3. Test if presigned URLs can be generated manually")

if __name__ == "__main__":
    asyncio.run(debug_s3_urls())
