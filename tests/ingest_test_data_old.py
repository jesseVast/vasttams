#!/usr/bin/env python3
"""
Test Data Ingestion Script

This script creates a complete test dataset by dynamically discovering video files:
- 1 source (or multiple sources based on video formats)
- N flows (one per discovered video file)
- N objects (via S3 uploads using discovered video files)
- N segments (one per object)

This validates the full workflow: source -> flow -> S3 upload -> segment creation
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


def create_source(token: str, source_num: int) -> Dict:
    """Create a test source"""
    source_id = str(uuid.uuid4())
    format_type = "urn:x-nmos:format:video" if source_num == 1 else "urn:x-nmos:format:video"
    
    # created_by and updated_by will be automatically set from authenticated user (admin)
    source_data = {
        "id": source_id,
        "format": format_type,
        "label": f"Test Source {source_num}",
        "description": f"Test source {source_num} for data ingestion"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/sources",
        json=source_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["sources"].append(source_id)
    print(f"✅ Created source {source_num}: {source_id[:8]}...")
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
        "label": label or f"Video Flow {flow_num}",
        "description": f"Test video flow {flow_num}",
        "codec": video_metadata.get("codec", "video/h264"),
        "essence_parameters": essence_parameters
    }
    
    # Add bitrate if available
    if video_metadata.get("bitrate"):
        flow_data["avg_bit_rate"] = video_metadata["bitrate"]
    
    # Add container info if available
    # Note: This would come from format metadata if needed
    
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
    print(f"✅ Created video flow {flow_num}: {flow_id[:8]}... ({width}x{height} @ {fps:.2f}fps, {video_metadata.get('codec', 'video/h264')})")
    return result


def create_audio_flow(token: str, source_id: str, flow_num: int) -> Dict:
    """Create an audio flow"""
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "generation": 1,
        "format": "urn:x-nmos:format:audio",
        "label": f"Audio Flow {flow_num}",
        "description": f"Test audio flow {flow_num}",
        "codec": "audio/aac",
        "essence_parameters": {
            "sample_rate": 48000,  # Integer, not an object
            "channels": 2
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows",
        json=flow_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["flows"].append(flow_id)
    print(f"✅ Created audio flow: {flow_id[:8]}...")
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


def get_presigned_url(token: str, flow_id: str, label: str = None) -> Tuple[str, str, str]:
    """Get presigned URL for S3 upload
    
    Returns:
        Tuple of (presigned_url, object_id, content_type)
    """
    if label is None:
        label = f"object-{str(uuid.uuid4())[:8]}"
    
    # Ensure allocation uses a concrete storage backend for dynamic get_urls
    storage_id = get_default_storage_id(token)
    storage_data = {
        "label": label,
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
                  start_seconds: int = 0, duration_seconds: int = 10, 
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
    start_time = f"{start_seconds}:0"
    end_time = f"{start_seconds + duration_seconds}:0"
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
            "value": f"{start_seconds}:0"  # Timestamp format: seconds:nanoseconds
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
    """Run the complete test data ingestion"""
    print("🧪 Starting Test Data Ingestion\n")
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
    
    try:
        # 1. Login
        print("\n1. Logging in...")
        token = login()
        print("✅ Logged in successfully")
        
        # 2. Group videos by format (for creating appropriate sources)
        print("\n2. Organizing videos by format...")
        videos_by_format = {}
        for video_info in discovered_videos:
            # Determine format based on metadata
            width = video_info['metadata'].get('frame_width', 0)
            height = video_info['metadata'].get('frame_height', 0)
            # Default to video format for now (can be extended for audio-only files)
            format_type = "urn:x-nmos:format:video"
            
            if format_type not in videos_by_format:
                videos_by_format[format_type] = []
            videos_by_format[format_type].append(video_info)
        
        print(f"   Found videos in {len(videos_by_format)} format(s)")
        for fmt, videos in videos_by_format.items():
            print(f"      - {fmt}: {len(videos)} video(s)")
        
        # 3. Create sources (one per format type)
        print("\n3. Creating sources...")
        source_map = {}  # format -> source_id
        for format_type, videos in videos_by_format.items():
            source_num = len(source_map) + 1
            source = create_source(token, source_num)
            source_id = source["id"]
            source_map[format_type] = source_id
        
        # 4. Create flows (one per video file)
        print(f"\n4. Creating flows from video metadata...")
        flows_data = []
        for idx, video_info in enumerate(discovered_videos, 1):
            format_type = "urn:x-nmos:format:video"  # Default for now
            source_id = source_map[format_type]
            metadata = video_info['metadata']
            flow_label = f"Flow {idx}: {video_info['name']}"
            
            flow = create_video_flow(token, source_id, idx, metadata, flow_label)
            flow_id = flow["id"]
            flows_data.append({
                'flow_id': flow_id,
                'flow_label': flow_label,
                'video_info': video_info
            })
        
        # 5. Create objects via S3 uploads using discovered video files
        print(f"\n5. Creating objects via S3 uploads (using {len(discovered_videos)} video file(s))...")
        objects_data = []
        
        for idx, flow_data in enumerate(flows_data, 1):
            flow_id = flow_data['flow_id']
            video_info = flow_data['video_info']
            video_path = video_info['path']
            video_name = video_info['name']
            
            print(f"   [{idx}/{len(flows_data)}] Uploading {video_name} for {flow_data['flow_label']}...")
            label = f"flow{idx}-{video_name.replace(' ', '_').replace('.', '_')}"
            presigned_url, object_id, content_type = get_presigned_url(token, flow_id, label)
            
            # Upload video file
            upload_to_s3(presigned_url, video_path, content_type)
            
            duration = video_info['metadata'].get("duration", 5)
            objects_data.append({
                'flow_id': flow_id,
                'object_id': object_id,
                'video_name': video_name,
                'duration': duration,
                'flow_label': flow_data['flow_label']
            })
            created_resources["objects"].append(object_id)
            print(f"✅ Created and uploaded object {idx}/{len(flows_data)}: {object_id[:8]}... ({video_name})")
        
        # 6. Create segments (one per object) using actual video duration
        print(f"\n6. Creating segments ({len(objects_data)} segment(s))...")
        segments_created = 0
        
        for obj_data in objects_data:
            duration_int = int(obj_data['duration']) if obj_data['duration'] > 0 else 5
            # Get frame rate from video metadata for accurate sample calculations
            video_info = next((f['video_info'] for f in flows_data if f['flow_id'] == obj_data['flow_id']), None)
            frame_rate = video_info['metadata'].get('frame_rate') if video_info else None
            
            create_segment(
                token, 
                obj_data['flow_id'], 
                obj_data['object_id'], 
                start_seconds=0, 
                duration_seconds=duration_int,
                frame_rate=frame_rate
            )
            segments_created += 1
            print(f"✅ Created segment {segments_created}/{len(objects_data)}: "
                  f"{obj_data['flow_label']} → Object {obj_data['object_id'][:8]}... "
                  f"(duration: {duration_int}s)")
        
        print("\n" + "=" * 60)
        print("✅ Test Data Ingestion Completed Successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  📊 Sources: {len(source_map)}")
        for idx, (format_type, source_id) in enumerate(source_map.items(), 1):
            # Count flows for this source (all flows use same source for now)
            flows_for_source = [f for f in flows_data]
            print(f"    - Source {idx}: {source_id[:8]}... ({format_type}, {len(flows_for_source)} flows)")
        print(f"  📹 Flows: {len(flows_data)}")
        for idx, flow_data in enumerate(flows_data, 1):
            video_name = flow_data['video_info']['name']
            print(f"    - Flow {idx}: {flow_data['flow_id'][:8]}... ({video_name})")
        print(f"  📦 Objects: {len(created_resources['objects'])}")
        print(f"  🎬 Segments: {segments_created}")
        print(f"\nTo verify, check analytics at: {API_BASE_URL}/analytics/summary")
        
        # Save resource IDs for reference
        with open("test_data_resources.json", "w") as f:
            json.dump({
                "sources": created_resources["sources"],
                "flows": [{"id": f['flow_id'], "label": f['flow_label'], "video": f['video_info']['name']} for f in flows_data],
                "objects": created_resources["objects"],
                "segments_count": segments_created,
                "videos_processed": len(discovered_videos)
            }, f, indent=2)
        print(f"\n💾 Resource IDs saved to: test_data_resources.json")
        
    except Exception as e:
        print(f"\n❌ Test data ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

