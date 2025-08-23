#!/usr/bin/env python3
"""
Batch media upload script for TAMS API

This script uploads a series of media files from a directory, creating a common source
and individual flows for each media file.

Usage:
    python batch_video_upload.py <source_name> <media_directory> [options]

Examples:
    python batch_video_upload.py "TV Series Season 1" ./episodes/
    python batch_video_upload.py "Security Recordings" ./daily_recordings/ --flow-prefix "Day"
    python batch_video_upload.py "Event Coverage" ./event_videos/ --resolution "3840x2160"
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional

# Add the current directory to Python path to import tams_video_uploader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from tams_video_upload import TAMSClient, DEFAULT_UPLOAD_TIMEOUT
except ImportError:
    print("❌ Error: Could not import tams_video_upload")
    print("   Make sure tams_video_upload.py is in the same directory")
    sys.exit(1)

def get_media_files(directory: str, extensions: List[str] = None) -> List[Path]:
    """Get all media files from directory with specified extensions"""
    if extensions is None:
        extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
    
    media_files = []
    for ext in extensions:
        media_files.extend(Path(directory).glob(f"*{ext}"))
        media_files.extend(Path(directory).glob(f"*{ext.upper()}"))
    
    # Sort files for consistent ordering
    media_files.sort()
    return media_files

def upload_series(
    base_source_name: str, 
    media_directory: str, 
    flow_prefix: str = "Episode",
    resolution: str = "1920x1080",
    frame_rate: str = "30/1",
    codec: str = "video/mp4",
            base_url: str = os.getenv("TAMS_API_BASE_URL", "http://localhost:8000"),
    timeout: int = DEFAULT_UPLOAD_TIMEOUT,
    dry_run: bool = False
) -> bool:
    """
    Upload a series of media files from a directory
    
    Args:
        base_source_name: Common source name for all media files
        media_directory: Directory containing media files
        flow_prefix: Prefix for flow names (e.g., "Episode", "Day", "Part")
        resolution: Media resolution
        frame_rate: Media frame rate
        codec: Media codec
        base_url: TAMS API base URL
        timeout: Upload timeout in seconds (default: matches presigned URL expiry)
        dry_run: If True, only show what would be uploaded without actually uploading
        
    Returns:
        True if all uploads succeeded, False otherwise
    """
    
    # Validate directory
    if not os.path.isdir(media_directory):
        print(f"❌ Error: {media_directory} is not a valid directory")
        return False
    
    # Get media files
    media_files = get_media_files(media_directory)
    
    if not media_files:
        print(f"❌ No media files found in {media_directory}")
        print(f"   Supported extensions: .mp4, .mov, .avi, .mkv, .wmv, .flv")
        return False
    
    print(f"🎬 Batch Upload: {base_source_name}")
    print(f"📁 Directory: {media_directory}")
    print(f"📹 Found {len(media_files)} media files")
    print(f"🔧 Flow prefix: {flow_prefix}")
    print(f"📊 Resolution: {resolution}")
    print(f"🎞️  Frame rate: {frame_rate}")
    print(f"💾 Codec: {codec}")
    print(f"🌐 API URL: {base_url}")
    print(f"⏱️  Upload timeout: {timeout}s (matches presigned URL expiry)")
    
    if dry_run:
        print(f"\n🔍 DRY RUN MODE - No actual uploads will be performed")
    
    print(f"\n{'='*60}")
    
    # Initialize uploader with timeout
    uploader = TAMSClient(base_url=base_url, timeout=timeout)
    
    success_count = 0
    failure_count = 0
    
    for i, media_file in enumerate(media_files, 1):
        print(f"\n📤 [{i:02d}/{len(media_files):02d}] Processing: {media_file.name}")
        print(f"   📁 Path: {media_file}")
        print(f"   📊 Size: {media_file.stat().st_size / (1024*1024):.1f} MB")
        
        if dry_run:
            flow_name = f"{flow_prefix} {i:02d}"
            print(f"   🔍 Would create flow: {flow_name}")
            print(f"   🔍 Would upload to source: {base_source_name}")
            success_count += 1
            continue
        
        try:
            # Upload with series naming
            flow_name = f"{flow_prefix} {i:02d}"
            
            print(f"   🔧 Creating flow: {flow_name}")
            
            # Step 1: Create source (only for first file, reuse for others)
            if i == 1:
                source_id = uploader.create_source(base_source_name)
                if not source_id:
                    print(f"   ❌ Failed to create source for {media_file.name}")
                    failure_count += 1
                    continue
            else:
                # Reuse the source ID from the first upload
                source_id = uploader._last_source_id if hasattr(uploader, '_last_source_id') else None
                if not source_id:
                    print(f"   ❌ No source ID available for {media_file.name}")
                    failure_count += 1
                    continue
            
            # Store source ID for reuse
            uploader._last_source_id = source_id
            
            # Step 2: Create video flow
            flow_id = uploader.create_video_flow(
                flow_name, 
                source_id,
                int(resolution.split('x')[0]),
                int(resolution.split('x')[1]),
                frame_rate,
                codec
            )
            if not flow_id:
                print(f"   ❌ Failed to create flow for {media_file.name}")
                failure_count += 1
                continue
            
            # Step 3: Allocate storage
            storage_response = uploader.allocate_storage(flow_id, object_count=1)
            if not storage_response:
                print(f"   ❌ Failed to allocate storage for {media_file.name}")
                failure_count += 1
                continue
            
            # Step 4: Upload video to S3
            if storage_response.get('media_objects'):
                media_object = storage_response['media_objects'][0]
                object_id = media_object['object_id']
                put_url = media_object['put_url']['url']
                put_headers = media_object['put_url'].get('headers', {})
                
                # Extract storage_path from metadata if available
                storage_path = None
                if media_object.get('metadata') and media_object['metadata'].get('storage_path'):
                    storage_path = media_object['metadata']['storage_path']
                
                upload_success = uploader.upload_video_to_s3(put_url, media_file, codec, put_headers)
                if not upload_success:
                    print(f"   ❌ Failed to upload {media_file.name} to S3")
                    failure_count += 1
                    continue
                
                # Step 5: Create flow segment with storage_path
                segment_success = uploader.create_flow_segment(flow_id, object_id, storage_path=storage_path)
                if not segment_success:
                    print(f"   ❌ Failed to create segment for {media_file.name}")
                    failure_count += 1
                    continue
                
                print(f"   ✅ Successfully uploaded {media_file.name}")
                success_count += 1
            else:
                print(f"   ❌ No media objects in storage response for {media_file.name}")
                failure_count += 1
                
        except Exception as e:
            print(f"   ❌ Error uploading {media_file.name}: {e}")
            failure_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"🎉 Batch upload complete: {base_source_name}")
    print(f"📊 Results:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {failure_count}")
    print(f"   📁 Total: {len(media_files)}")
    
    if failure_count == 0:
        print(f"🎊 All media files uploaded successfully!")
        return True
    else:
        print(f"⚠️  {failure_count} media files failed to upload")
        return False

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Batch upload videos to TAMS API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_media_upload.py "TV Series Season 1" ./episodes/
  python batch_media_upload.py "Security Recordings" ./daily_recordings/ --flow-prefix "Day"
  python batch_media_upload.py "Event Coverage" ./event_videos/ --resolution "3840x2160" --dry-run
  python batch_media_upload.py "Long Videos" ./videos/ --timeout 7200  # 2 hour timeout
        
Note: The timeout should match or exceed the presigned URL expiry time (default: 1 hour)
        """
    )
    
    parser.add_argument(
        "source_name",
        help="Common source name for all videos in the series"
    )
    
    parser.add_argument(
        "media_directory",
        help="Directory containing media files to upload"
    )
    
    parser.add_argument(
        "--flow-prefix",
        default="Episode",
        help="Prefix for flow names (default: Episode)"
    )
    
    parser.add_argument(
        "--resolution",
        default="1920x1080",
        help="Video resolution (default: 1920x1080)"
    )
    
    parser.add_argument(
        "--frame-rate",
        default="30/1",
        help="Video frame rate (default: 30/1)"
    )
    
    parser.add_argument(
        "--codec",
        default="video/mp4",
        help="Video codec (default: video/mp4)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_UPLOAD_TIMEOUT,
        help=f"Upload timeout in seconds (default: {DEFAULT_UPLOAD_TIMEOUT}s, matches presigned URL expiry)"
    )
    
    parser.add_argument(
        "--base-url",
        default=os.getenv("TAMS_API_BASE_URL", "http://localhost:8000"),
        help="TAMS API base URL (default: from TAMS_API_BASE_URL env var or http://localhost:8000)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )
    
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"],
        help="Media file extensions to process (default: all common media formats)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.source_name.strip():
        print("❌ Error: Source name cannot be empty")
        sys.exit(1)
    
    if not os.path.isdir(args.media_directory):
        print(f"❌ Error: {args.media_directory} is not a valid directory")
        sys.exit(1)
    
    # Perform batch upload
    try:
        success = upload_series(
            base_source_name=args.source_name,
            media_directory=args.media_directory,
            flow_prefix=args.flow_prefix,
            resolution=args.resolution,
            frame_rate=args.frame_rate,
            codec=args.codec,
            base_url=args.base_url,
            timeout=args.timeout,
            dry_run=args.dry_run
        )
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Upload interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
