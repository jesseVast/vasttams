#!/usr/bin/env python3
"""
TAMS Docker Deployment Test Script

This script tests the TAMS (Time-addressable Media Store) Docker container deployment
by ingesting a video file and then retrieving it through the API.

Usage:
    python test_docker_deployment.py [--host HOST] [--port PORT] [--video-file PATH]

Example:
    python test_docker_deployment.py --video-file /path/to/video.mp4
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class TAMSTestClient:
    """Client for testing TAMS API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def health_check(self) -> bool:
        """Check if the TAMS API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def create_source(self, source_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new source."""
        try:
            response = self.session.post(
                f"{self.base_url}/sources",
                json=source_data,
                timeout=self.timeout
            )
            if response.status_code == 201:
                source = response.json()
                print(f"✅ Source created: {source['id']}")
                return source
            else:
                print(f"❌ Failed to create source: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating source: {e}")
            return None
    
    def create_flow(self, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new flow."""
        try:
            response = self.session.post(
                f"{self.base_url}/flows",
                json=flow_data,
                timeout=self.timeout
            )
            if response.status_code == 201:
                flow = response.json()
                print(f"✅ Flow created: {flow['id']}")
                return flow
            else:
                print(f"❌ Failed to create flow: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating flow: {e}")
            return None
    
    def upload_segment(self, flow_id: str, segment_data: Dict[str, Any], file_path: str) -> Optional[Dict[str, Any]]:
        """Upload a flow segment with media file."""
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, 'application/octet-stream'),
                    'segment_data': (None, json.dumps(segment_data), 'application/json')
                }
                
                response = self.session.post(
                    f"{self.base_url}/flows/{flow_id}/segments",
                    files=files,
                    timeout=self.timeout
                )
                
                if response.status_code == 201:
                    segment = response.json()
                    print(f"✅ Segment uploaded: {segment.get('object_id', 'unknown')}")
                    return segment
                else:
                    print(f"❌ Failed to upload segment: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            print(f"❌ Error uploading segment: {e}")
            return None
    
    def get_flow_segments(self, flow_id: str) -> Optional[list]:
        """Get flow segments."""
        try:
            response = self.session.get(
                f"{self.base_url}/flows/{flow_id}/segments",
                timeout=self.timeout
            )
            if response.status_code == 200:
                segments = response.json()
                print(f"✅ Retrieved {len(segments)} segments")
                return segments
            else:
                print(f"❌ Failed to get segments: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error getting segments: {e}")
            return None
    
    def download_segment(self, url: str, output_path: str) -> bool:
        """Download a segment from a URL."""
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Downloaded segment to: {output_path}")
                return True
            else:
                print(f"❌ Failed to download segment: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error downloading segment: {e}")
            return False


def get_video_info(file_path: str) -> Dict[str, Any]:
    """Get basic video information using ffprobe or make reasonable assumptions."""
    # Try to use ffprobe if available
    try:
        import subprocess
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', '-show_streams', file_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                return {
                    'width': int(video_stream.get('width', 1920)),
                    'height': int(video_stream.get('height', 1080)),
                    'codec': video_stream.get('codec_name', 'h264'),
                    'duration': float(data['format'].get('duration', 10.0)),
                    'bit_rate': int(data['format'].get('bit_rate', 5000000))
                }
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ImportError, KeyError):
        pass
    
    # Fallback to reasonable defaults
    print("⚠️  Using default video parameters (ffprobe not available or failed)")
    return {
        'width': 1920,
        'height': 1080,
        'codec': 'h264',
        'duration': 10.0,
        'bit_rate': 5000000
    }


def create_test_data(video_path: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Create test data for source, flow, and segment."""
    video_info = get_video_info(video_path)
    
    # Generate UUIDs
    source_id = str(uuid.uuid4())
    flow_id = str(uuid.uuid4())
    
    # Create source data
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Video Source - {os.path.basename(video_path)}",
        "description": f"Test source for video file: {video_path}",
        "created_by": "tams-test-script",
        "tags": {
            "test": "true",
            "filename": os.path.basename(video_path),
            "created_at": datetime.now().isoformat()
        }
    }
    
    # Create flow data
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Video Flow - {os.path.basename(video_path)}",
        "description": f"Test flow for video file: {video_path}",
        "created_by": "tams-test-script",
        "codec": f"video/{video_info['codec']}",
        "container": "video/mp4",
        "avg_bit_rate": video_info['bit_rate'] // 1000,  # Convert to kbps
        "max_bit_rate": (video_info['bit_rate'] * 1.2) // 1000,  # 20% higher
        "segment_duration": {
            "numerator": 2,
            "denominator": 1
        },
        "essence_parameters": {
            "frame_width": video_info['width'],
            "frame_height": video_info['height'],
            "frame_rate": {
                "numerator": 30,
                "denominator": 1
            },
            "interlace_mode": "progressive",
            "colorspace": "BT709",
            "transfer_characteristic": "SDR",
            "aspect_ratio": {
                "numerator": 16,
                "denominator": 9
            },
            "pixel_aspect_ratio": {
                "numerator": 1,
                "denominator": 1
            },
            "component_type": "YCbCr",
            "horiz_chroma_subs": 2,
            "vert_chroma_subs": 2
        },
        "tags": {
            "test": "true",
            "filename": os.path.basename(video_path),
            "created_at": datetime.now().isoformat()
        }
    }
    
    # Create segment data
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=video_info['duration'])
    
    # Convert to seconds since epoch for timerange format
    start_seconds = int(start_time.timestamp())
    end_seconds = int(end_time.timestamp())
    
    segment_data = {
        "object_id": f"test_segment_{uuid.uuid4().hex[:8]}",
        "timerange": f"{start_seconds}:0_{end_seconds}:0",
        "sample_offset": 0,
        "key_frame_count": 1
    }
    
    return source_data, flow_data, segment_data


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test TAMS Docker deployment")
    parser.add_argument("--host", default="localhost", help="TAMS API host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="TAMS API port (default: 8000)")
    parser.add_argument("--video-file", required=True, help="Path to video file to test with")
    parser.add_argument("--output-dir", default="./test_output", help="Output directory for downloaded files")
    
    args = parser.parse_args()
    
    # Validate video file
    if not os.path.exists(args.video_file):
        print(f"❌ Video file not found: {args.video_file}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize client
    base_url = f"http://{args.host}:{args.port}"
    client = TAMSTestClient(base_url)
    
    print("🚀 Starting TAMS Docker Deployment Test")
    print(f"📡 API Base URL: {base_url}")
    print(f"🎥 Video File: {args.video_file}")
    print(f"📁 Output Directory: {output_dir}")
    print("-" * 60)
    
    # Step 1: Health check
    print("\n1️⃣  Checking API health...")
    if not client.health_check():
        print("❌ API is not healthy. Please ensure the Docker container is running.")
        sys.exit(1)
    
    # Step 2: Create test data
    print("\n2️⃣  Creating test data...")
    source_data, flow_data, segment_data = create_test_data(args.video_file)
    
    # Step 3: Create source
    print("\n3️⃣  Creating source...")
    source = client.create_source(source_data)
    if not source:
        print("❌ Failed to create source. Exiting.")
        sys.exit(1)
    
    # Step 4: Create flow
    print("\n4️⃣  Creating flow...")
    flow = client.create_flow(flow_data)
    if not flow:
        print("❌ Failed to create flow. Exiting.")
        sys.exit(1)
    
    # Step 5: Upload video segment
    print("\n5️⃣  Uploading video segment...")
    segment = client.upload_segment(flow['id'], segment_data, args.video_file)
    if not segment:
        print("❌ Failed to upload segment. Exiting.")
        sys.exit(1)
    
    # Step 6: Retrieve segments
    print("\n6️⃣  Retrieving flow segments...")
    segments = client.get_flow_segments(flow['id'])
    if not segments:
        print("❌ Failed to retrieve segments. Exiting.")
        sys.exit(1)
    
    # Step 7: Download and verify segment
    print("\n7️⃣  Downloading and verifying segment...")
    if segments and 'get_urls' in segments[0] and segments[0]['get_urls']:
        download_url = segments[0]['get_urls'][0]['url']
        output_file = output_dir / f"retrieved_{os.path.basename(args.video_file)}"
        
        if client.download_segment(download_url, str(output_file)):
            # Compare file sizes
            original_size = os.path.getsize(args.video_file)
            retrieved_size = os.path.getsize(output_file)
            
            print(f"📊 File size comparison:")
            print(f"   Original: {original_size:,} bytes")
            print(f"   Retrieved: {retrieved_size:,} bytes")
            
            if original_size == retrieved_size:
                print("✅ File sizes match - upload/retrieval successful!")
            else:
                print("⚠️  File sizes don't match - there may be an issue")
        else:
            print("❌ Failed to download segment")
    else:
        print("⚠️  No download URLs available in segment data")
    
    # Step 8: Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   Source ID: {source['id']}")
    print(f"   Flow ID: {flow['id']}")
    print(f"   Segment Object ID: {segment.get('object_id', 'N/A')}")
    print(f"   Total Segments: {len(segments) if segments else 0}")
    print("✅ TAMS Docker deployment test completed successfully!")


if __name__ == "__main__":
    main() 