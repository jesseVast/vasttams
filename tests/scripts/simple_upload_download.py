#!/usr/bin/env python3
"""
Simple script to demonstrate TAMS client upload and download workflow.

Creates:
- 1 source
- 1 flow
- 1 segment with file upload
- Downloads the segment

Usage:
    python simple_upload_download.py [--server-url URL] [--username USER] [--password PASS] [--file PATH]
"""

import asyncio
import sys
import argparse
import tempfile
from pathlib import Path

# Add src/client to path for imports
client_path = Path(__file__).parent.parent.parent / "src" / "client"
if str(client_path) not in sys.path:
    sys.path.insert(0, str(client_path))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSClientError


async def main():
    parser = argparse.ArgumentParser(description="Simple TAMS upload/download test")
    parser.add_argument("--server-url", default="http://localhost:8000", help="TAMS server URL")
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--password", default="vastdata", help="Password")
    parser.add_argument("--file", help="File to upload (default: creates temporary test file)")
    
    args = parser.parse_args()
    
    # Create temporary test file if not provided
    if args.file:
        test_file = Path(args.file)
        if not test_file.exists():
            print(f"❌ Error: File not found: {test_file}")
            return 1
    else:
        # Create a small test file
        test_file = Path(tempfile.mkdtemp()) / "test_video.mp4"
        test_file.write_bytes(b"fake video data " * 100)  # ~1.6KB
        print(f"📁 Created temporary test file: {test_file}")
    
    print("=" * 80)
    print("Simple TAMS Upload/Download Test")
    print("=" * 80)
    
    try:
        # Create client
        print(f"\n[1] Connecting to TAMS server: {args.server_url}")
        client = TAMSClient(
            server_url=args.server_url,
            username=args.username,
            password=args.password,
            timeout=60
        )
        
        async with client:
            # Create source
            print("\n[2] Creating source...")
            source = client.TAMSSource(
                format="urn:x-nmos:format:video",
                label="Simple Test Source"
            )
            await source._ensure_created()
            print(f"✅ Created source: {source.id} - {source.label}")
            
            # Create flow
            print("\n[3] Creating flow...")
            flow = source.TAMSFlow(
                format="urn:x-nmos:format:video",
                codec="video/h264",
                label="Simple Test Flow",
                frame_width=1920,
                frame_height=1080,
                frame_rate={"numerator": 25, "denominator": 1}
            )
            await flow._ensure_created()
            print(f"✅ Created flow: {flow.id} - {flow.label}")
            
            # Upload segment
            print(f"\n[4] Uploading segment from file: {test_file}")
            segment = await flow.add_segment(
                file_path=str(test_file),
                timerange={"value": "[0:0_10:0)"},
                auto_probe=False
            )
            print(f"✅ Created segment with object_id: {segment.object_id}")
            print(f"   Timerange: {segment.timerange}")
            
            # List segments to verify
            print("\n[5] Listing segments...")
            segments = await flow.list_segments()
            print(f"✅ Found {len(segments)} segment(s)")
            for seg in segments:
                print(f"   - Object ID: {seg.object_id}, Timerange: {seg.timerange.get('value', 'N/A')}")
            
            # Download segment (get URLs)
            print("\n[6] Getting download URLs for segment...")
            # Refresh segment to get get_urls
            await segment.refresh()
            segment_data = segment._data
            
            # Get URLs from segment data
            get_urls = segment_data.get("get_urls", [])
            if get_urls:
                print(f"✅ Found {len(get_urls)} download URL(s):")
                for i, url_info in enumerate(get_urls, 1):
                    if isinstance(url_info, dict):
                        url = url_info.get("url", "N/A")
                        presigned = url_info.get("presigned", False)
                        print(f"   [{i}] {url} (presigned: {presigned})")
                    else:
                        print(f"   [{i}] {url_info}")
                
                # Download using first URL
                if get_urls:
                    url_info = get_urls[0]
                    download_url = url_info.get("url") if isinstance(url_info, dict) else str(url_info)
                    if download_url:
                        print(f"\n[7] Downloading from: {download_url}")
                        import requests
                        import asyncio
                        
                        # Use requests for S3 downloads (run in thread pool for async compatibility)
                        def _download_file():
                            response = requests.get(download_url, stream=True)
                            if response.status_code == 200:
                                return response.content
                            else:
                                raise Exception(f"Download failed with status: {response.status_code}, Error: {response.text}")
                        
                        try:
                            downloaded_data = await asyncio.to_thread(_download_file)
                            print(f"✅ Downloaded {len(downloaded_data)} bytes")
                            
                            # Verify data matches
                            original_data = test_file.read_bytes()
                            if downloaded_data == original_data:
                                print("✅ Download verification: Data matches original file!")
                            else:
                                print(f"⚠️  Download verification: Data size differs (original: {len(original_data)}, downloaded: {len(downloaded_data)})")
                        except Exception as e:
                            print(f"❌ Download failed: {e}")
                    else:
                        print("⚠️  No URL found in first get_urls entry")
            else:
                print("⚠️  No download URLs available in segment")
                print(f"   Segment data keys: {list(segment_data.keys())}")
            
            # Cleanup
            print("\n[8] Cleaning up...")
            try:
                # Delete segments first
                await flow.delete_segments()
                print("✅ Deleted segments")
                
                # Delete flow
                await flow.delete()
                print("✅ Deleted flow")
                
                # Delete source
                await source.delete()
                print("✅ Deleted source")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
            
            # Cleanup temp file if we created it
            if not args.file and test_file.exists():
                test_file.unlink()
                test_file.parent.rmdir()
                print("✅ Cleaned up temporary file")
            
            print("\n" + "=" * 80)
            print("✅ Test completed successfully!")
            print("=" * 80)
            return 0
            
    except TAMSClientError as e:
        print(f"\n❌ TAMS Client Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

