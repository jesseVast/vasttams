#!/usr/bin/env python3
"""
Check S3 bucket directly using our S3Core functionality
"""
import asyncio
import requests
import json

async def check_s3_bucket_directly():
    """Use the API to check S3 bucket contents"""
    print("🔍 Checking S3 Bucket Contents via API")
    print("=" * 50)
    
    # First, let's check what segments are registered
    try:
        print("📋 Getting registered segments...")
        response = requests.get("http://localhost:8000/flows/d2e3f4a5-6b7c-4d8e-9f0a-1b2c3d4e5f6a/segments")
        if response.status_code == 200:
            segments = response.json()
            print(f"   Found {len(segments)} registered segments:")
            
            for i, segment in enumerate(segments):
                print(f"   {i+1}. Object ID: {segment.get('object_id', 'N/A')}")
                print(f"      Timerange: {segment.get('timerange', 'N/A')}")
                print(f"      Storage Path: {segment.get('storage_path', 'N/A')}")
                print(f"      Get URLs: {len(segment.get('get_urls', []))} URLs")
                if segment.get('get_urls'):
                    for url in segment.get('get_urls', []):
                        print(f"        - {url.get('url', 'N/A')}")
                print()
            
            # Try to access one of the get_urls to see if the file exists
            if segments and segments[-1].get('get_urls'):
                test_url = segments[-1]['get_urls'][0]['url']
                print(f"🌐 Testing access to latest uploaded object...")
                print(f"   URL: {test_url}")
                
                try:
                    head_response = requests.head(test_url, timeout=10)
                    print(f"   HTTP Status: {head_response.status_code}")
                    print(f"   Content-Length: {head_response.headers.get('Content-Length', 'N/A')}")
                    print(f"   Content-Type: {head_response.headers.get('Content-Type', 'N/A')}")
                    
                    if head_response.status_code == 200:
                        # Try to download the content
                        get_response = requests.get(test_url, timeout=10)
                        if get_response.status_code == 200:
                            print(f"   ✅ File download successful! Size: {len(get_response.content)} bytes")
                            print(f"   Content preview: {get_response.content[:50]}...")
                        else:
                            print(f"   ❌ File download failed: {get_response.status_code}")
                    else:
                        print(f"   ❌ File not accessible via get_url")
                        
                except requests.exceptions.RequestException as e:
                    print(f"   ❌ Request failed: {e}")
            
        else:
            print(f"   Failed to get segments: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Error checking segments: {e}")

if __name__ == "__main__":
    asyncio.run(check_s3_bucket_directly())
