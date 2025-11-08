#!/usr/bin/env python3
"""
Test Data Ingestion Script - Split Version

This script creates a test dataset with:
- 1 source
- 2 flows (each flow gets half the discovered video files)
- Multiple objects and segments (one per video file, distributed across the 2 flows)

This validates the workflow where multiple files belong to a single flow.
Automatically discovers and processes all video files from test_videos/ directory
"""

import requests
import json
import uuid
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "vastdata"

# Path to test videos directory (relative to script location)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEST_VIDEOS_DIR = PROJECT_ROOT / "test_videos"

# Supported video file extensions
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.ts', '.mkv', '.avi', '.mov', '.webm', '.m4v', '.m3u8'}

# Track created resources for cleanup
created_resources = {
    "sources": [],
    "flows": [],
    "objects": [],
    "segments": []
}


def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_default_storage_id(token: str) -> str:
    """Fetch the default storage backend id (fallback to first backend)."""
    resp = requests.get(
        f"{API_BASE_URL}/service/storage-backends",
        headers=get_headers(token)
    )
    resp.raise_for_status()
    backends = resp.json()
    if isinstance(backends, dict) and "data" in backends:
        backends = backends["data"]
    if not backends:
        raise RuntimeError("No storage backends available")
    default_backend = next((b for b in backends if b.get("default_storage") is True), None)
    return (default_backend or backends[0]).get("id")


def get_headers(token):
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_source(token: str) -> Dict:
    """Create a single test source"""
    source_id = str(uuid.uuid4())
    format_type = "urn:x-nmos:format:video"
    
    source_data = {
        "id": source_id,
        "format": format_type,
        "label": "Test Source (Split)",
        "description": "Single source for split flow ingestion test"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/sources",
        json=source_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["sources"].append(source_id)
    print(f"✅ Created source: {source_id[:8]}...")
    return result


def extract_video_metadata(video_path: Path) -> Dict:
    """Extract video metadata using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(result.stdout)
        
        # Find video and audio streams
        video_stream = None
        audio_stream = None
        
        for stream in probe_data.get('streams', []):
            if stream.get('codec_type') == 'video' and video_stream is None:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and audio_stream is None:
                audio_stream = stream
        
        if not video_stream:
            raise ValueError(f"No video stream found in {video_path}")
        
        # Parse frame rate (format: "25/1" or "29.97")
        r_frame_rate = video_stream.get('r_frame_rate', '0/1')
        if '/' in r_frame_rate:
            num, den = map(int, r_frame_rate.split('/'))
            frame_rate = {"numerator": num, "denominator": den}
        else:
            # Try to parse as decimal
            fps = float(r_frame_rate)
            frame_rate = {"numerator": int(fps * 1000), "denominator": 1000}
        
        # Extract codec name and map to TAMS format
        codec_name = video_stream.get('codec_name', '').lower()
        codec_mapping = {
            'h264': 'video/h264',
            'hevc': 'video/hevc',
            'h265': 'video/hevc',
            'mpeg4': 'video/mpeg4',
            'mpeg2video': 'video/mpeg2',
            'vp8': 'video/vp8',
            'vp9': 'video/vp9',
            'av1': 'video/av1',
        }
        codec = codec_mapping.get(codec_name, f'video/{codec_name}' if codec_name else 'video/h264')
        
        # Extract bitrate
        video_bitrate = int(video_stream.get('bit_rate', 0))
        format_bitrate = int(probe_data.get('format', {}).get('bit_rate', 0))
        bitrate = video_bitrate if video_bitrate > 0 else format_bitrate
        
        metadata = {
            "codec": codec,
            "frame_width": int(video_stream.get('width', 1920)),
            "frame_height": int(video_stream.get('height', 1080)),
            "frame_rate": frame_rate,
            "vfr": video_stream.get('r_frame_rate') != video_stream.get('avg_frame_rate', ''),
            "bitrate": bitrate,
            "duration": float(probe_data.get('format', {}).get('duration', 0)),
        }
        
        # Add audio info if present
        if audio_stream:
            audio_codec_name = audio_stream.get('codec_name', '').lower()
            audio_codec_mapping = {
                'aac': 'audio/aac',
                'mp3': 'audio/mpeg',
                'opus': 'audio/opus',
                'vorbis': 'audio/vorbis',
                'ac3': 'audio/ac3',
            }
            metadata["audio_codec"] = audio_codec_mapping.get(audio_codec_name, f'audio/{audio_codec_name}')
            metadata["audio_sample_rate"] = int(audio_stream.get('sample_rate', 48000))
            metadata["audio_channels"] = int(audio_stream.get('channels', 2))
        
        return metadata
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFprobe failed: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("FFprobe not found. Please install FFmpeg.")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse FFprobe output: {e}")
    except Exception as e:
        raise RuntimeError(f"Video metadata extraction failed: {e}")


def create_video_flow(token: str, source_id: str, flow_num: int, video_metadata: Dict, label: str = None) -> Dict:
    """Create a video flow from extracted metadata"""
    flow_id = str(uuid.uuid4())
    
    essence_parameters = {
        "frame_width": video_metadata.get("frame_width", 1920),
        "frame_height": video_metadata.get("frame_height", 1080),
        "frame_rate": video_metadata.get("frame_rate", {"numerator": 25, "denominator": 1}),
        "vfr": video_metadata.get("vfr", False)
    }
    
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "generation": 1,
        "format": "urn:x-nmos:format:video",
        "label": label or f"Flow {flow_num}",
        "description": f"Flow {flow_num} containing multiple video files"
    }
    
    # Use metadata from first video for flow properties
    flow_data["codec"] = video_metadata.get("codec", "video/h264")
    flow_data["essence_parameters"] = essence_parameters
    
    # Add bitrate if available
    if video_metadata.get("bitrate"):
        flow_data["avg_bit_rate"] = video_metadata["bitrate"]
    
    response = requests.post(
        f"{API_BASE_URL}/flows",
        json=flow_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["flows"].append(flow_id)
    
    width = essence_parameters["frame_width"]
    height = essence_parameters["frame_height"]
    fps = essence_parameters["frame_rate"]["numerator"] / essence_parameters["frame_rate"]["denominator"]
    print(f"✅ Created flow {flow_num}: {flow_id[:8]}... ({width}x{height} @ {fps:.2f}fps, {video_metadata.get('codec', 'video/h264')})")
    return result


def discover_video_files(directory: Path) -> List[Dict[str, Any]]:
    """
    Dynamically discover all video files in the test_videos directory.
    
    Returns:
        List of dicts with 'path' (Path), 'name' (str), 'extension' (str), and 'metadata' (Dict)
    """
    if not directory.exists():
        raise FileNotFoundError(f"Test videos directory not found: {directory}")
    
    video_files = []
    for file_path in sorted(directory.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            # Skip HLS playlist files (we want the actual video segments)
            if file_path.suffix.lower() == '.m3u8':
                continue
            
            try:
                # Extract metadata immediately to validate file is readable
                metadata = extract_video_metadata(file_path)
                video_files.append({
                    'path': file_path,
                    'name': file_path.name,
                    'extension': file_path.suffix.lower(),
                    'metadata': metadata,
                    'size': file_path.stat().st_size
                })
            except Exception as e:
                print(f"⚠️  Warning: Skipping {file_path.name} - failed to extract metadata: {e}")
                continue
    
    if not video_files:
        raise FileNotFoundError(
            f"No valid video files found in {directory}. "
            f"Supported formats: {', '.join(SUPPORTED_VIDEO_EXTENSIONS)}"
        )
    
    return video_files


def get_presigned_url(token: str, flow_id: str) -> Tuple[str, str, str]:
    """Get presigned URL for S3 upload
    
    Returns:
        Tuple of (presigned_url, object_id, content_type)
    """
    # Ensure allocation uses a concrete storage backend for dynamic get_urls
    storage_id = get_default_storage_id(token)
    # TAMS spec: POST /flows/{flowId}/storage accepts limit and storage_id (no label)
    storage_data = {
        "limit": 1,  # Request only 1 presigned URL
        "storage_id": storage_id
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows/{flow_id}/storage",
        json=storage_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    
    # Extract presigned URL from response
    # Note: put_url now includes "content-type" per TAMS 8.0 AppNote 0018
    if "media_objects" in result and len(result["media_objects"]) > 0:
        media_obj = result["media_objects"][0]
        object_id = media_obj["object_id"]
        put_url_obj = media_obj["put_url"]
        presigned_url = put_url_obj["url"]
        # Extract content-type from put_url (required for S3 upload header)
        content_type = put_url_obj.get("content-type", "application/octet-stream")
        return presigned_url, object_id, content_type
    else:
        raise ValueError(f"No media_objects in response: {result}")


def upload_to_s3(presigned_url: str, file_path: Path, content_type: str = "application/octet-stream") -> bool:
    """Upload file to S3 using presigned URL
    
    Args:
        presigned_url: The presigned S3 URL
        file_path: Path to the file to upload
        content_type: Content-Type header value (must match what was used to sign the URL)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")
    
    # Set Content-Type header - required when presigned URL includes content-type in signature
    headers = {"Content-Type": content_type}
    
    # Read file in binary mode and upload
    with open(file_path, 'rb') as f:
        response = requests.put(
            presigned_url,
            data=f,
            headers=headers
        )
    response.raise_for_status()
    return True


def create_segment(token: str, flow_id: str, object_id: str, 
                  start_seconds: float = 0.0, duration_seconds: float = 10.0, 
                  frame_rate: Optional[Dict] = None) -> Dict:
    """Create a segment for the flow
    
    Args:
        token: Authentication token
        flow_id: Flow ID
        object_id: Object ID
        start_seconds: Start time in seconds
        duration_seconds: Duration in seconds
        frame_rate: Optional frame rate dict with numerator/denominator (defaults to 25fps)
    """
    # Use provided frame rate or default to 25 fps
    if frame_rate:
        fps = frame_rate['numerator'] / frame_rate['denominator'] if frame_rate['denominator'] > 0 else 25
    else:
        fps = 25
    
    # TAMS timerange format: [start_end) where times are seconds:nanoseconds
    # Format: [start_seconds:nanoseconds_end_seconds:nanoseconds)
    # Handle fractional seconds by converting to nanoseconds
    start_seconds_int = int(start_seconds)
    start_nanoseconds = int((start_seconds - start_seconds_int) * 1_000_000_000)
    
    end_seconds_float = start_seconds + duration_seconds
    end_seconds_int = int(end_seconds_float)
    end_nanoseconds = int((end_seconds_float - end_seconds_int) * 1_000_000_000)
    
    start_time = f"{start_seconds_int}:{start_nanoseconds}"
    end_time = f"{end_seconds_int}:{end_nanoseconds}"
    timerange_str = f"[{start_time}_{end_time})"
    
    # Calculate sample offsets based on actual frame rate
    sample_offset = int(start_seconds * fps)
    sample_count = int(duration_seconds * fps)
    
    segment_data = {
        "object_id": object_id,
        "timerange": {
            "value": timerange_str
        },
        "sample_offset": sample_offset,
        "sample_count": sample_count,
        "ts_offset": {
            "value": f"{start_seconds_int}:{start_nanoseconds}"  # Timestamp format: seconds:nanoseconds
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows/{flow_id}/segments",
        json=segment_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["segments"].append((flow_id, object_id))
    return result


def main():
    """Run the complete test data ingestion with split flows"""
    print("🧪 Starting Test Data Ingestion (Split Flows)\n")
    print("=" * 60)
    
    # Dynamically discover all video files
    print(f"📂 Scanning {TEST_VIDEOS_DIR} for video files...")
    discovered_videos = discover_video_files(TEST_VIDEOS_DIR)
    
    print(f"📹 Found {len(discovered_videos)} video file(s):")
    for idx, video_info in enumerate(discovered_videos, 1):
        file_size_mb = video_info['size'] / 1024 / 1024
        metadata = video_info['metadata']
        resolution = f"{metadata['frame_width']}x{metadata['frame_height']}"
        codec = metadata.get('codec', 'unknown')
        fps_num = metadata['frame_rate']['numerator']
        fps_den = metadata['frame_rate']['denominator']
        fps = fps_num / fps_den if fps_den > 0 else 0
        duration = metadata.get('duration', 0)
        print(f"   {idx}. {video_info['name']}")
        print(f"      Size: {file_size_mb:.2f} MB | Resolution: {resolution} | Codec: {codec}")
        print(f"      Frame rate: {fps:.2f} fps | Duration: {duration:.2f}s")
    
    # Split videos into two halves
    total_videos = len(discovered_videos)
    split_point = total_videos // 2
    first_half = discovered_videos[:split_point]
    second_half = discovered_videos[split_point:]
    
    print(f"\n📊 Split distribution:")
    print(f"   Flow 1: {len(first_half)} video(s)")
    print(f"   Flow 2: {len(second_half)} video(s)")
    
    try:
        # 1. Login
        print("\n1. Logging in...")
        token = login()
        print("✅ Logged in successfully")
        
        # 2. Create single source
        print("\n2. Creating source...")
        source = create_source(token)
        source_id = source["id"]
        
        # 3. Create 2 flows (using metadata from first video in each half)
        print("\n3. Creating flows...")
        flows_data = []
        
        # Flow 1 - use first video's metadata
        if first_half:
            flow1_metadata = first_half[0]['metadata']
            flow1 = create_video_flow(token, source_id, 1, flow1_metadata, "Flow 1 (First Half)")
            flows_data.append({
                'flow_id': flow1["id"],
                'flow_label': "Flow 1 (First Half)",
                'videos': first_half
            })
        
        # Flow 2 - use first video's metadata
        if second_half:
            flow2_metadata = second_half[0]['metadata']
            flow2 = create_video_flow(token, source_id, 2, flow2_metadata, "Flow 2 (Second Half)")
            flows_data.append({
                'flow_id': flow2["id"],
                'flow_label': "Flow 2 (Second Half)",
                'videos': second_half
            })
        
        # 4. Upload all videos to their respective flows
        print(f"\n4. Creating objects via S3 uploads...")
        objects_data = []
        
        for flow_data in flows_data:
            flow_id = flow_data['flow_id']
            videos = flow_data['videos']
            
            print(f"\n   Processing {flow_data['flow_label']} ({len(videos)} video(s)):")
            for idx, video_info in enumerate(videos, 1):
                video_path = video_info['path']
                video_name = video_info['name']
                
                print(f"   [{idx}/{len(videos)}] Uploading {video_name}...")
                # TAMS spec: POST /flows/{flowId}/storage uses limit and storage_id (no label)
                presigned_url, object_id, content_type = get_presigned_url(token, flow_id)
                
                # Upload video file
                upload_to_s3(presigned_url, video_path, content_type)
                
                duration = video_info['metadata'].get("duration", 5)
                objects_data.append({
                    'flow_id': flow_id,
                    'object_id': object_id,
                    'video_name': video_name,
                    'duration': duration,
                    'flow_label': flow_data['flow_label'],
                    'video_info': video_info
                })
                created_resources["objects"].append(object_id)
                print(f"   ✅ Uploaded: {object_id[:8]}... ({video_name})")
        
        # 5. Create segments (one per object) with sequential timeranges
        print(f"\n5. Creating segments ({len(objects_data)} segment(s))...")
        segments_created = 0
        
        # Group objects by flow_id to track cumulative time per flow
        objects_by_flow = {}
        for obj_data in objects_data:
            flow_id = obj_data['flow_id']
            if flow_id not in objects_by_flow:
                objects_by_flow[flow_id] = []
            objects_by_flow[flow_id].append(obj_data)
        
        # Process each flow's segments sequentially
        for flow_id, flow_objects in objects_by_flow.items():
            cumulative_start = 0.0  # Start at 0 seconds
            flow_label = flow_objects[0]['flow_label'] if flow_objects else "Unknown"
            
            print(f"\n   Processing segments for {flow_label}:")
            for idx, obj_data in enumerate(flow_objects, 1):
                # Use actual video duration
                duration_float = float(obj_data['duration']) if obj_data['duration'] > 0 else 5.0
                duration_int = int(duration_float)
                
                # Get frame rate from video metadata for accurate sample calculations
                frame_rate = obj_data['video_info']['metadata'].get('frame_rate') if obj_data['video_info'] else None
                
                # Calculate start and end times for this segment
                start_seconds = cumulative_start
                end_seconds = start_seconds + duration_float
                
                create_segment(
                    token, 
                    obj_data['flow_id'], 
                    obj_data['object_id'], 
                    start_seconds=start_seconds, 
                    duration_seconds=duration_float,
                    frame_rate=frame_rate
                )
                segments_created += 1
                
                timerange_display = f"[{start_seconds:.2f}s_{end_seconds:.2f}s)"
                print(f"   ✅ [{idx}/{len(flow_objects)}] {obj_data['video_name']}: {timerange_display}")
                
                # Update cumulative start time for next segment
                cumulative_start = end_seconds
        
        print("\n" + "=" * 60)
        print("✅ Test Data Ingestion Completed Successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  📊 Source: 1")
        print(f"    - Source ID: {source_id[:8]}...")
        print(f"  📹 Flows: 2")
        for idx, flow_data in enumerate(flows_data, 1):
            print(f"    - Flow {idx}: {flow_data['flow_id'][:8]}... ({len(flow_data['videos'])} videos)")
        print(f"  📦 Objects: {len(created_resources['objects'])}")
        print(f"  🎬 Segments: {segments_created}")
        print(f"\nTo verify, check analytics at: {API_BASE_URL}/analytics/summary")
        
        # Save resource IDs for reference
        output_file = "test_data_resources_split.json"
        with open(output_file, "w") as f:
            json.dump({
                "source": source_id,
                "flows": [{"id": f['flow_id'], "label": f['flow_label'], "video_count": len(f['videos'])} for f in flows_data],
                "objects": created_resources["objects"],
                "segments_count": segments_created,
                "videos_processed": len(discovered_videos),
                "distribution": {
                    "flow_1_count": len(first_half),
                    "flow_2_count": len(second_half)
                }
            }, f, indent=2)
        print(f"\n💾 Resource IDs saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Test data ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

