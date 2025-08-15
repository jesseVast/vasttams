#!/usr/bin/env python3
"""
TAMS Video Uploader CLI Client
Uploads video files to TAMS API, creating sources and flows as needed.
"""

import argparse
import json
import os
import sys
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import urllib.error
import urllib.parse
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_SOURCE_LABEL = "Video Source"
DEFAULT_FLOW_LABEL = "Video Flow"
DEFAULT_VIDEO_CODEC = "video/mp4"
DEFAULT_FRAME_RATE = "30/1"  # 30 fps
DEFAULT_FRAME_WIDTH = 1920
DEFAULT_FRAME_HEIGHT = 1080
DEFAULT_UPLOAD_TIMEOUT = 3600  # Match presigned URL expiry (1 hour)

class MediaAnalyzer:
    """Analyzes media files to extract metadata using FFprobe"""
    
    def __init__(self):
        self.ffprobe_path = self._find_ffprobe()
    
    def _find_ffprobe(self) -> str:
        """Find FFprobe executable path"""
        # Common paths for FFprobe
        possible_paths = [
            'ffprobe',
            '/opt/homebrew/bin/ffprobe',
            '/usr/local/bin/ffprobe',
            '/usr/bin/ffprobe'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                continue
        
        raise FileNotFoundError("FFprobe not found. Please install FFmpeg/FFprobe.")
    
    def analyze_media(self, file_path: str) -> Dict[str, Any]:
        """Analyze media file and return metadata"""
        try:
            # Get media information using FFprobe
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=DEFAULT_UPLOAD_TIMEOUT)
            if result.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {result.stderr}")
            
            data = json.loads(result.stdout)
            return self._parse_media_info(data, file_path)
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze media file: {e}")
    
    def _parse_media_info(self, data: Dict, file_path: str) -> Dict[str, Any]:
        """Parse FFprobe output into usable metadata"""
        format_info = data.get('format', {})
        streams = data.get('streams', [])
        
        # Find video and audio streams
        video_stream = None
        audio_stream = None
        
        for stream in streams:
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream
        
        # Extract metadata
        metadata = {
            'file_path': file_path,
            'file_size': int(format_info.get('size', 0)),
            'duration': float(format_info.get('duration', 0)),
            'bitrate': int(format_info.get('bit_rate', 0)),
            'format': format_info.get('format_name', 'unknown'),
            'video': {},
            'audio': {}
        }
        
        # Video metadata
        if video_stream:
            metadata['video'] = {
                'codec': video_stream.get('codec_name', 'unknown'),
                'codec_long': video_stream.get('codec_long_name', 'unknown'),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'frame_rate': self._parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                'pixel_format': video_stream.get('pix_fmt', 'unknown'),
                'bitrate': int(video_stream.get('bit_rate', 0)),
                'profile': video_stream.get('profile', 'unknown'),
                'level': video_stream.get('level', 'unknown')
            }
        
        # Audio metadata
        if audio_stream:
            metadata['audio'] = {
                'codec': audio_stream.get('codec_name', 'unknown'),
                'codec_long': audio_stream.get('codec_long_name', 'unknown'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bitrate': int(audio_stream.get('bit_rate', 0)),
                'language': audio_stream.get('tags', {}).get('language', 'unknown')
            }
        
        return metadata
    
    def _parse_frame_rate(self, frame_rate_str: str) -> str:
        """Parse frame rate string (e.g., '30/1' -> '30/1')"""
        try:
            if '/' in frame_rate_str:
                return frame_rate_str
            else:
                # Convert decimal to fraction (e.g., 30.0 -> '30/1')
                rate = float(frame_rate_str)
                return f"{int(rate)}/1"
        except:
            return "30/1"  # Default fallback

class TAMSClient:
    """TAMS API client for video upload operations"""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_UPLOAD_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TAMS-Video-Uploader/1.0'
        }
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    headers: Dict = None, expected_status: int = 200) -> Dict:
        """Make HTTP request using built-in urllib"""
        try:
            if headers is None:
                headers = {}
            
            # Merge session headers with request headers
            request_headers = {**self.session_headers, **headers}
            
            url = f"{self.base_url}{endpoint}"
            
            try:
                if method == "GET":
                    req = urllib.request.Request(url, headers=request_headers)
                elif method == "POST":
                    if data:
                        json_data = json.dumps(data).encode('utf-8')
                        req = urllib.request.Request(url, data=json_data, headers=request_headers, method='POST')
                    else:
                        req = urllib.request.Request(url, headers=request_headers, method='POST')
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Add timeout to prevent hanging (matches presigned URL expiry)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    response_data = response.read().decode('utf-8')
                    return {
                        'status_code': response.getcode(),
                        'data': json.loads(response_data) if response_data else None,
                        'headers': dict(response.headers)
                    }
                    
            except urllib.error.HTTPError as e:
                try:
                    error_data = e.read().decode('utf-8')
                    error_json = json.loads(error_data) if error_data else None
                except:
                    error_json = {'raw_error': str(e)}
                
                return {
                    'status_code': e.code,
                    'data': error_json,
                    'headers': dict(e.headers)
                }
            except urllib.error.URLError as e:
                return {
                    'status_code': 0,
                    'data': {'error': f'URL Error: {e.reason}'},
                    'headers': {}
                }
            except Exception as e:
                return {
                    'status_code': 0,
                    'data': {'error': str(e)},
                    'headers': {}
                }
                
        except Exception as e:
            return {
                'status_code': 0,
                'data': {'error': str(e)},
                'headers': {}
            }
    
    def create_source(self, source_name: str, format_type: str = "urn:x-nmos:format:video") -> Optional[str]:
        """Create a new source in TAMS"""
        print(f"🔧 Creating source: {source_name}")
        
        source_data = {
            "id": str(uuid.uuid4()),
            "format": format_type,
            "label": source_name,
            "description": f"Video source created by TAMS uploader: {source_name}",
            "created_by": "tams-uploader",
            "tags": {
                "uploader": "tams-video-uploader",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "video"
            }
        }
        
        response = self.make_request('POST', '/sources', data=source_data, expected_status=201)
        
        if response['status_code'] == 201:
            source_id = response['data']['id']
            print(f"✅ Source created successfully: {source_id}")
            return source_id
        else:
            print(f"❌ Failed to create source: {response['status_code']}")
            if response['data']:
                print(f"   Error: {response['data']}")
            return None
    
    def create_video_flow(self, flow_name: str, source_id: str, 
                          frame_width: int = DEFAULT_FRAME_WIDTH,
                          frame_height: int = DEFAULT_FRAME_HEIGHT,
                          frame_rate: str = DEFAULT_FRAME_RATE,
                          codec: str = DEFAULT_VIDEO_CODEC) -> Optional[str]:
        """Create a new video flow in TAMS"""
        print(f"🔧 Creating video flow: {flow_name}")
        
        # Parse frame rate
        if '/' in frame_rate:
            numerator, denominator = frame_rate.split('/')
            frame_rate_obj = {
                "numerator": int(numerator),
                "denominator": int(denominator)
            }
        else:
            frame_rate_obj = {"numerator": int(frame_rate), "denominator": 1}
        
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": flow_name,
            "description": f"Video flow created by TAMS uploader: {flow_name}",
            "created_by": "tams-uploader",
            "codec": codec,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "frame_rate": frame_rate_obj,
            "tags": {
                "uploader": "tams-video-uploader",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "flow_type": "video",
                "resolution": f"{frame_width}x{frame_height}",
                "frame_rate": frame_rate
            }
        }
        
        response = self.make_request('POST', '/flows', data=flow_data, expected_status=201)
        
        if response['status_code'] == 201:
            flow_id = response['data']['id']
            print(f"✅ Video flow created successfully: {flow_id}")
            return flow_id
        else:
            print(f"❌ Failed to create video flow: {response['status_code']}")
            if response['data']:
                print(f"   Error: {response['data']}")
            return None
    
    def allocate_storage(self, flow_id: str, object_count: int = 1) -> Optional[Dict]:
        """Allocate storage for media objects"""
        print(f"🔧 Allocating storage for {object_count} object(s)")
        
        storage_request = {
            "limit": object_count
        }
        
        response = self.make_request('POST', f'/flows/{flow_id}/storage', 
                                   data=storage_request, expected_status=201)
        
        if response['status_code'] == 201:
            print(f"✅ Storage allocated successfully")
            return response['data']
        else:
            print(f"❌ Failed to allocate storage: {response['status_code']}")
            if response['data']:
                print(f"   Error: {response['data']}")
            return None
    
    def upload_video_to_s3(self, put_url: str, video_path: Path, 
                           content_type: str = "video/mp4", 
                           put_headers: Dict[str, str] = None) -> bool:
        """Upload video file to S3 using presigned URL with requests library"""
        print(f"📤 Uploading video to S3: {video_path.name}")
        
        try:
            # Get file size for progress tracking
            file_size = video_path.stat().st_size
            print(f"📋 Using boto3 for S3 upload")
            print(f"📊 File size: {file_size:,} bytes")
            
            # Parse the presigned URL to extract bucket and key
            parsed_url = urllib.parse.urlparse(put_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                print(f"❌ Invalid presigned URL format: {put_url}")
                return False
            
            bucket_name = path_parts[0]
            object_key = '/'.join(path_parts[1:])
            
            print(f"📦 Uploading to bucket: {bucket_name}, key: {object_key}")
            
            # Note: We're using requests library for presigned URL uploads
            # boto3 is imported for potential future S3 operations, but presigned URLs
            # work best with direct HTTP requests
            
            # For presigned URLs, we'll use requests library directly
            # This is the most reliable approach for presigned URL uploads
            try:
                import requests
                print(f"📤 Using requests library for presigned URL upload")
                
                # Upload using the presigned URL with proper timeout
                with open(video_path, 'rb') as video_file:
                    response = requests.put(
                        put_url,
                        data=video_file,
                        timeout=self.timeout
                    )
                
                if response.status_code in [200, 201]:
                    print(f"✅ Video uploaded successfully to S3")
                    return True
                else:
                    print(f"❌ Upload failed with status: {response.status_code}")
                    print(f"📄 Response: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Upload failed: {e}")
                return False
                        
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_flow_segment(self, flow_id: str, object_id: str, 
                           start_time: str = "00:00:00.000", 
                           end_time: str = "00:05:00.000") -> bool:
        """Create a flow segment referencing the uploaded object"""
        print(f"🔧 Creating flow segment for object: {object_id}")
        
        segment_data = {
            "object_id": object_id,
            "timerange": f"[{start_time},{end_time})",
            "ts_offset": "0:0",
            "sample_offset": 0,
            "sample_count": 0,
            "key_frame_count": 0
        }
        
        print(f"📝 Segment data: {json.dumps(segment_data, indent=2)}")
        
        # Use form data approach since the API expects segment_data parameter
        try:
            import urllib.parse
            
            # Convert to form data
            form_data = urllib.parse.urlencode({
                'segment_data': json.dumps(segment_data)
            }).encode('utf-8')
            
            url = f"{self.base_url}/flows/{flow_id}/segments"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'TAMS-Video-Uploader/1.0'
            }
            
            req = urllib.request.Request(url, data=form_data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.getcode() == 201:
                    print(f"✅ Flow segment created successfully")
                    return True
                else:
                    print(f"❌ Failed to create flow segment: {response.getcode()}")
                    return False
                    
        except Exception as e:
            print(f"❌ Failed to create flow segment: {e}")
            return False
    
    def get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract basic video metadata (simplified)"""
        # This is a simplified metadata extraction
        # In production, you might use ffprobe or similar tools
        
        file_size = video_path.stat().st_size
        file_extension = video_path.suffix.lower()
        
        # Default metadata based on file extension
        metadata = {
            "codec": "video/mp4",
            "frame_width": DEFAULT_FRAME_WIDTH,
            "frame_height": DEFAULT_FRAME_HEIGHT,
            "frame_rate": DEFAULT_FRAME_RATE,
            "file_size": file_size,
            "file_extension": file_extension
        }
        
        # Override based on file extension
        if file_extension == '.mp4':
            metadata["codec"] = "video/mp4"
        elif file_extension == '.avi':
            metadata["codec"] = "video/x-msvideo"
        elif file_extension == '.mov':
            metadata["codec"] = "video/quicktime"
        elif file_extension == '.mkv':
            metadata["codec"] = "video/x-matroska"
        
        return metadata

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Upload video files to TAMS API with automatic media analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload with automatic media analysis (recommended)
  python tams_video_upload.py video.mp4
  
  # Demo mode (skip S3 upload for testing)
  python tams_video_upload.py video.mp4 --demo
  
  # Override analyzed metadata with custom values
  python tams_video_upload.py video.mp4 \\
    --source-name "My Video Source" \\
    --flow-name "My Video Flow" \\
    --frame-width 3840 \\
    --frame-height 2160 \\
    --frame-rate "60/1"
  
  # Upload to different TAMS instance
  python tams_video_upload.py video.mp4 \\
    --base-url "http://tams.example.com:8000"
        
Note: The script automatically analyzes video files using FFprobe to extract
resolution, frame rate, codec, and other metadata. Use the override flags
only if you need to specify different values than what's detected.
        """
    )
    
    # Required arguments
    parser.add_argument('video_file', type=str, help='Path to video file to upload')
    
    # Optional arguments
    parser.add_argument('--base-url', type=str, default=DEFAULT_BASE_URL,
                       help=f'TAMS API base URL (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--source-name', type=str, default=DEFAULT_SOURCE_LABEL,
                       help=f'Source label (default: {DEFAULT_SOURCE_LABEL})')
    parser.add_argument('--flow-name', type=str, default=DEFAULT_FLOW_LABEL,
                       help=f'Flow label (default: {DEFAULT_FLOW_LABEL})')
    parser.add_argument('--frame-width', type=int, default=DEFAULT_FRAME_WIDTH,
                       help=f'Video frame width in pixels (overrides detected value, default: {DEFAULT_FRAME_WIDTH})')
    parser.add_argument('--frame-height', type=int, default=DEFAULT_FRAME_HEIGHT,
                       help=f'Video frame height in pixels (overrides detected value, default: {DEFAULT_FRAME_HEIGHT})')
    parser.add_argument('--frame-rate', type=str, default=DEFAULT_FRAME_RATE,
                       help=f'Video frame rate as "numerator/denominator" (overrides detected value, default: {DEFAULT_FRAME_RATE})')
    parser.add_argument('--codec', type=str, default=DEFAULT_VIDEO_CODEC,
                       help=f'Video codec MIME type (overrides detected value, default: {DEFAULT_VIDEO_CODEC})')
    parser.add_argument('--timeout', type=int, default=DEFAULT_UPLOAD_TIMEOUT,
                       help=f'Upload timeout in seconds (default: {DEFAULT_UPLOAD_TIMEOUT}s, matches presigned URL expiry)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--demo', action='store_true',
                       help='Demo mode: skip S3 upload and create mock segment')
    
    args = parser.parse_args()
    
    # Validate video file
    video_path = Path(args.video_file)
    if not video_path.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)
    
    if not video_path.is_file():
        print(f"❌ Error: Path is not a file: {video_path}")
        sys.exit(1)
    
    # Initialize TAMS client and media analyzer
    print("🎬 TAMS Video Uploader")
    print("=" * 50)
    print(f"Video file: {video_path}")
    print(f"File size: {video_path.stat().st_size:,} bytes")
    print(f"Base URL: {args.base_url}")
    print(f"Source name: {args.source_name}")
    print(f"Flow name: {args.flow_name}")
    print()
    
    # Analyze media file to get actual metadata
    print("🔍 Analyzing media file...")
    try:
        analyzer = MediaAnalyzer()
        media_info = analyzer.analyze_media(str(video_path))
        
        # Use analyzed metadata instead of defaults
        actual_width = media_info['video'].get('width', args.frame_width)
        actual_height = media_info['video'].get('height', args.frame_height)
        actual_frame_rate = media_info['video'].get('frame_rate', args.frame_rate)
        actual_codec = f"video/{media_info['video'].get('codec', 'mp4')}"
        
        # Override defaults with actual values if not explicitly specified
        if args.frame_width == DEFAULT_FRAME_WIDTH:
            args.frame_width = actual_width
        if args.frame_height == DEFAULT_FRAME_HEIGHT:
            args.frame_height = actual_height
        if args.frame_rate == DEFAULT_FRAME_RATE:
            args.frame_rate = actual_frame_rate
        if args.codec == DEFAULT_VIDEO_CODEC:
            args.codec = actual_codec
        
        print("✅ Media analysis completed:")
        print(f"   Resolution: {actual_width}x{actual_height}")
        print(f"   Frame rate: {actual_frame_rate}")
        print(f"   Video codec: {media_info['video'].get('codec', 'unknown')}")
        print(f"   Audio codec: {media_info['audio'].get('codec', 'unknown')}")
        print(f"   Duration: {media_info['duration']:.2f}s")
        print(f"   Bitrate: {media_info['bitrate']:,} bps")
        print()
        
    except Exception as e:
        print(f"⚠️  Media analysis failed: {e}")
        print("   Using default metadata values")
        print()
    
    print(f"📊 Final upload parameters:")
    print(f"   Resolution: {args.frame_width}x{args.frame_height}")
    print(f"   Frame rate: {args.frame_rate}")
    print(f"   Codec: {args.codec}")
    print(f"   Upload timeout: {args.timeout}s (matches presigned URL expiry)")
    print()
    
    client = TAMSClient(args.base_url)
    
    try:
        # Step 1: Create source
        source_id = client.create_source(args.source_name)
        if not source_id:
            print("❌ Failed to create source. Aborting.")
            sys.exit(1)
        
        # Step 2: Create video flow
        flow_id = client.create_video_flow(
            args.flow_name, 
            source_id,
            args.frame_width,
            args.frame_height,
            args.frame_rate,
            args.codec
        )
        if not flow_id:
            print("❌ Failed to create video flow. Aborting.")
            sys.exit(1)
        
        # Step 3: Allocate storage
        storage_response = client.allocate_storage(flow_id, object_count=1)
        if not storage_response:
            print("❌ Failed to allocate storage. Aborting.")
            sys.exit(1)
        
        # Step 4: Upload video to S3
        if storage_response.get('media_objects'):
            media_object = storage_response['media_objects'][0]
            object_id = media_object['object_id']
            put_url = media_object['put_url']['url']
            put_headers = media_object['put_url']['headers']  # Extract the headers
            
            if args.demo:
                print("🎭 Demo mode: Skipping S3 upload")
                print(f"   Would upload to: {put_url}")
                print(f"   Object ID: {object_id}")
                print(f"   Headers: {put_headers}")
            else:
                upload_success = client.upload_video_to_s3(put_url, video_path, args.codec, put_headers)
                if not upload_success:
                    print("❌ Failed to upload video. Aborting.")
                    print("💡 Tip: Use --demo flag to test without S3 upload")
                    sys.exit(1)
            
            # Step 5: Create flow segment
            print(f"🔧 Creating flow segment for object: {object_id}")
            segment_success = client.create_flow_segment(flow_id, object_id)
            if not segment_success:
                print("❌ Failed to create flow segment. Aborting.")
                sys.exit(1)
            
            # Success summary
            print("\n🎉 Video upload completed successfully!")
            print("=" * 50)
            print(f"Source ID: {source_id}")
            print(f"Flow ID: {flow_id}")
            print(f"Object ID: {object_id}")
            print(f"Video file: {video_path.name}")
            if not args.demo:
                print(f"Uploaded to: {put_url}")
            else:
                print("Demo mode: S3 upload skipped")
            
        else:
            print("❌ No media objects in storage response")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
