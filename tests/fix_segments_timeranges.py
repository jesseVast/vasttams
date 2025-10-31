#!/usr/bin/env python3
"""
Fix Segments Timeranges Script

This script:
- Reads existing objects and segments from previous ingestion
- Creates new flows
- Creates new segments with corrected sequential timeranges using existing objects

Useful for fixing timerange offsets without re-uploading video files.
"""

import requests
import json
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "vastdata"

# Path to resource file from previous ingestion
SCRIPT_DIR = Path(__file__).parent
RESOURCE_FILE = SCRIPT_DIR / "test_data_resources_split.json"

# Track created resources
created_resources = {
    "sources": [],
    "flows": [],
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


def get_headers(token):
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_flow_segments(token: str, flow_id: str) -> List[Dict]:
    """Get all segments for a flow"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/flows/{flow_id}/segments",
            headers=get_headers(token)
        )
        response.raise_for_status()
        result = response.json()
        # Handle both data wrapper and direct array
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        elif isinstance(result, list):
            return result
        else:
            return []
    except Exception as e:
        print(f"⚠️  Warning: Failed to get segments for flow {flow_id[:8]}...: {e}")
        return []


def get_flow_details(token: str, flow_id: str) -> Optional[Dict]:
    """Get flow details"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/flows/{flow_id}",
            headers=get_headers(token)
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Warning: Failed to get flow {flow_id[:8]}...: {e}")
        return None


def get_source_details(token: str, source_id: str) -> Optional[Dict]:
    """Get source details"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/sources/{source_id}",
            headers=get_headers(token)
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Warning: Failed to get source {source_id[:8]}...: {e}")
        return None


def create_source_from_existing(token: str, existing_source_id: str) -> Dict:
    """Create a new source based on existing source"""
    existing_source = get_source_details(token, existing_source_id)
    if not existing_source:
        raise ValueError(f"Source {existing_source_id} not found")
    
    new_source_id = str(uuid.uuid4())
    source_data = {
        "id": new_source_id,
        "format": existing_source.get("format", "urn:x-nmos:format:video"),
        "label": f"{existing_source.get('label', 'Source')} (Fixed)",
        "description": f"Recreated source with fixed segment timeranges"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/sources",
        json=source_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["sources"].append(new_source_id)
    print(f"✅ Created source: {new_source_id[:8]}...")
    return result


def create_flow_from_existing(token: str, source_id: str, existing_flow: Dict, flow_num: int) -> Dict:
    """Create a new flow based on existing flow metadata"""
    flow_id = str(uuid.uuid4())
    
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "generation": 1,
        "format": existing_flow.get("format", "urn:x-nmos:format:video"),
        "label": f"{existing_flow.get('label', 'Flow')} (Fixed)",
        "description": f"Recreated flow {flow_num} with sequential segment timeranges"
    }
    
    # Copy over flow properties if available
    if "codec" in existing_flow:
        flow_data["codec"] = existing_flow["codec"]
    if "essence_parameters" in existing_flow:
        flow_data["essence_parameters"] = existing_flow["essence_parameters"]
    if "avg_bit_rate" in existing_flow:
        flow_data["avg_bit_rate"] = existing_flow["avg_bit_rate"]
    if "container" in existing_flow:
        flow_data["container"] = existing_flow["container"]
    
    response = requests.post(
        f"{API_BASE_URL}/flows",
        json=flow_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["flows"].append(flow_id)
    print(f"✅ Created flow {flow_num}: {flow_id[:8]}...")
    return result


def create_segment_with_timerange(token: str, flow_id: str, object_id: str,
                                  start_seconds: float, duration_seconds: float,
                                  frame_rate: Optional[Dict] = None) -> Dict:
    """Create a segment with specific timerange
    
    Args:
        token: Authentication token
        flow_id: Flow ID
        object_id: Object ID (existing object)
        start_seconds: Start time in seconds (float)
        duration_seconds: Duration in seconds (float)
        frame_rate: Optional frame rate dict with numerator/denominator (defaults to 25fps)
    """
    # Use provided frame rate or default to 25 fps
    if frame_rate:
        fps = frame_rate['numerator'] / frame_rate['denominator'] if frame_rate['denominator'] > 0 else 25
    else:
        fps = 25
    
    # TAMS timerange format: [start_end) where times are seconds:nanoseconds
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
            "value": f"{start_seconds_int}:{start_nanoseconds}"
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


def extract_duration_from_timerange(timerange_str: str) -> float:
    """Extract duration from TAMS timerange string
    
    Args:
        timerange_str: Timerange in format "[start_end)" or "[start:nanoseconds_end:nanoseconds)"
    
    Returns:
        Duration in seconds as float
    """
    try:
        # Remove brackets
        timerange = timerange_str.strip('[]()')
        if '_' not in timerange:
            return 0.0
        
        parts = timerange.split('_')
        if len(parts) != 2:
            return 0.0
        
        start_str = parts[0]
        end_str = parts[1].rstrip(')')
        
        # Parse start time (seconds:nanoseconds)
        start_parts = start_str.split(':')
        start_seconds = float(start_parts[0])
        if len(start_parts) > 1:
            start_seconds += float(start_parts[1]) / 1_000_000_000
        
        # Parse end time (seconds:nanoseconds)
        end_parts = end_str.split(':')
        end_seconds = float(end_parts[0])
        if len(end_parts) > 1:
            end_seconds += float(end_parts[1]) / 1_000_000_000
        
        return end_seconds - start_seconds
    except Exception as e:
        print(f"⚠️  Warning: Failed to parse timerange {timerange_str}: {e}")
        return 5.0  # Default duration


def get_frame_rate_from_flow(flow: Dict) -> Optional[Dict]:
    """Extract frame rate from flow essence_parameters"""
    essence_params = flow.get("essence_parameters", {})
    if "frame_rate" in essence_params:
        return essence_params["frame_rate"]
    return None


def main():
    """Fix segments by creating new flows and segments with sequential timeranges"""
    print("🔧 Starting Segment Timerange Fix\n")
    print("=" * 60)
    
    # Load resource file
    if not RESOURCE_FILE.exists():
        print(f"❌ Resource file not found: {RESOURCE_FILE}")
        print("   Please run ingest_test_data_split.py first to generate the resource file.")
        return
    
    print(f"📂 Loading resources from {RESOURCE_FILE}...")
    with open(RESOURCE_FILE, 'r') as f:
        resources = json.load(f)
    
    # Get original source and flows
    original_source_id = resources.get("source")
    original_flows = resources.get("flows", [])
    
    if not original_source_id or not original_flows:
        print("❌ Invalid resource file: missing source or flows")
        return
    
    print(f"📊 Found:")
    print(f"   Source: {original_source_id[:8]}...")
    print(f"   Flows: {len(original_flows)}")
    
    try:
        # 1. Login
        print("\n1. Logging in...")
        token = login()
        print("✅ Logged in successfully")
        
        # 2. Create new source
        print("\n2. Creating new source...")
        new_source = create_source_from_existing(token, original_source_id)
        new_source_id = new_source["id"]
        
        # 3. Process each original flow
        print("\n3. Processing original flows...")
        new_flows_data = []
        
        for flow_idx, original_flow_info in enumerate(original_flows, 1):
            original_flow_id = original_flow_info.get("id")
            print(f"\n   Processing original flow {flow_idx}: {original_flow_id[:8]}...")
            
            # Get original flow details
            original_flow = get_flow_details(token, original_flow_id)
            if not original_flow:
                print(f"   ⚠️  Skipping flow {original_flow_id[:8]}... (not found)")
                continue
            
            # Get all segments for this flow
            segments = get_flow_segments(token, original_flow_id)
            if not segments:
                print(f"   ⚠️  Skipping flow {original_flow_id[:8]}... (no segments found)")
                continue
            
            print(f"   Found {len(segments)} segment(s)")
            
            # Sort segments by sample_offset to maintain order
            segments_sorted = sorted(segments, key=lambda s: s.get("sample_offset", 0))
            
            # Create new flow
            new_flow = create_flow_from_existing(token, new_source_id, original_flow, flow_idx)
            new_flow_id = new_flow["id"]
            
            # Get frame rate from flow
            frame_rate = get_frame_rate_from_flow(original_flow)
            
            # 4. Create new segments with sequential timeranges
            print(f"\n   Creating {len(segments_sorted)} segment(s) with sequential timeranges:")
            cumulative_start = 0.0
            
            new_segments = []
            for seg_idx, segment in enumerate(segments_sorted, 1):
                object_id = segment.get("object_id")
                if not object_id:
                    print(f"   ⚠️  Skipping segment {seg_idx} (no object_id)")
                    continue
                
                # Extract duration from existing segment timerange
                timerange = segment.get("timerange", {}).get("value", "")
                duration = extract_duration_from_timerange(timerange)
                
                if duration <= 0:
                    duration = 5.0  # Default duration if can't parse
                
                # Calculate start and end times
                start_seconds = cumulative_start
                end_seconds = start_seconds + duration
                
                # Create new segment with corrected timerange
                try:
                    create_segment_with_timerange(
                        token,
                        new_flow_id,
                        object_id,
                        start_seconds=start_seconds,
                        duration_seconds=duration,
                        frame_rate=frame_rate
                    )
                    new_segments.append({
                        "object_id": object_id,
                        "timerange": f"[{start_seconds:.2f}s_{end_seconds:.2f}s)"
                    })
                    print(f"   ✅ [{seg_idx}/{len(segments_sorted)}] Object {object_id[:8]}...: "
                          f"[{start_seconds:.2f}s_{end_seconds:.2f}s)")
                    
                    # Update cumulative start time
                    cumulative_start = end_seconds
                except Exception as e:
                    print(f"   ❌ Failed to create segment {seg_idx}: {e}")
                    continue
            
            new_flows_data.append({
                "original_flow_id": original_flow_id,
                "new_flow_id": new_flow_id,
                "segments_count": len(new_segments)
            })
        
        print("\n" + "=" * 60)
        print("✅ Segment Timerange Fix Completed!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  📊 New Source: {new_source_id[:8]}...")
        print(f"  📹 New Flows: {len(new_flows_data)}")
        for idx, flow_data in enumerate(new_flows_data, 1):
            print(f"    - Flow {idx}: {flow_data['new_flow_id'][:8]}... "
                  f"({flow_data['segments_count']} segments)")
        print(f"  🎬 Total Segments: {len(created_resources['segments'])}")
        print(f"\nTo verify, check analytics at: {API_BASE_URL}/analytics/summary")
        
        # Save fixed resource IDs
        output_file = "test_data_resources_fixed.json"
        with open(output_file, "w") as f:
            json.dump({
                "source": new_source_id,
                "flows": [{"id": f['new_flow_id'], "original_id": f['original_flow_id'], 
                          "segments_count": f['segments_count']} for f in new_flows_data],
                "segments_count": len(created_resources['segments']),
                "original_source": original_source_id,
                "original_flows": original_flows
            }, f, indent=2)
        print(f"\n💾 Fixed resource IDs saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

