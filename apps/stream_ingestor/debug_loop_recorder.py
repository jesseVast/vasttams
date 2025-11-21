#!/usr/bin/env python3
"""
Debug script to check why loop recorder isn't working for a specific flow.

Usage:
    python debug_loop_recorder.py <flow_id> [--server-url URL] [--username USER] [--password PASS]
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "client"))

try:
    from vasttamsclient import TAMSClient
except ImportError:
    print("Error: vasttamsclient not found. Install with: pip install -e ../../src/client")
    sys.exit(1)


async def debug_flow(flow_id: str, server_url: str, username: str, password: str):
    """Debug a specific flow to see why loop recorder isn't working."""
    print(f"🔍 Debugging loop recorder for flow: {flow_id}")
    print(f"   Server: {server_url}")
    print()
    
    async with TAMSClient(server_url, username, password) as client:
        try:
            # Get the flow
            print("1️⃣  Fetching flow...")
            flow = await client.get_flow(flow_id)
            if not flow:
                print(f"   ❌ Flow {flow_id} not found!")
                return
            
            print(f"   ✅ Flow found: {flow.id}")
            print(f"   Label: {flow.label}")
            print(f"   Source ID: {flow.source_id}")
            print()
            
            # Check tags
            print("2️⃣  Checking flow tags...")
            if not flow.tags:
                print("   ❌ Flow has no tags!")
                return
            
            # Get tags dict
            tags_dict = None
            if hasattr(flow.tags, 'root'):
                tags_dict = flow.tags.root
            elif isinstance(flow.tags, dict):
                tags_dict = flow.tags
            else:
                print(f"   ❌ Tags format not recognized: {type(flow.tags)}")
                return
            
            if not tags_dict:
                print("   ❌ Tags dict is empty!")
                return
            
            print(f"   ✅ Tags found: {tags_dict}")
            
            # Check for loop_recorder_duration
            loop_duration = tags_dict.get('loop_recorder_duration')
            if not loop_duration:
                print("   ❌ No 'loop_recorder_duration' tag found!")
                print("   💡 Set it with: PUT /flows/{flow_id}/tags/loop_recorder_duration")
                return
            
            print(f"   ✅ loop_recorder_duration: {loop_duration} seconds ({int(loop_duration)/60:.1f} minutes)")
            
            # Validate duration value
            try:
                duration_int = int(loop_duration)
                if duration_int <= 0:
                    print(f"   ❌ Invalid duration value: {loop_duration} (must be > 0)")
                    return
                print(f"   ✅ Duration value is valid: {duration_int}s")
            except (ValueError, TypeError):
                print(f"   ❌ Invalid duration value: {loop_duration} (must be integer)")
                return
            
            print()
            
            # Get segments
            print("3️⃣  Checking flow segments...")
            segments = await client.list_flow_segments(flow_id)
            
            if not segments:
                print("   ⚠️  No segments found for this flow")
                print("   💡 Loop recorder only runs when segments exist")
                return
            
            print(f"   ✅ Found {len(segments)} segments")
            
            # Check segment timeranges
            segments_with_timerange = sum(1 for s in segments if s.timerange)
            print(f"   Segments with timerange: {segments_with_timerange}/{len(segments)}")
            
            if segments_with_timerange == 0:
                print("   ⚠️  No segments have timeranges - duration calculation will fail!")
                print("   💡 Segments need timeranges for loop recorder to work")
                return
            
            # Calculate duration
            print()
            print("4️⃣  Calculating flow duration...")
            
            # Sort segments by timerange
            sorted_segments = sorted(
                [s for s in segments if s.timerange],
                key=lambda s: _get_timerange_start(s.timerange)
            )
            
            if len(sorted_segments) < 2:
                print(f"   ⚠️  Need at least 2 segments with timeranges to calculate duration")
                print(f"   Found: {len(sorted_segments)} segments with timeranges")
                return
            
            first_segment = sorted_segments[0]
            last_segment = sorted_segments[-1]
            
            print(f"   First segment timerange: {first_segment.timerange}")
            print(f"   Last segment timerange: {last_segment.timerange}")
            
            # Parse timeranges
            start_time = _parse_timerange(first_segment.timerange)
            end_time = _parse_timerange(last_segment.timerange)
            
            if not start_time or not end_time:
                print("   ❌ Could not parse timeranges!")
                return
            
            duration_seconds = (end_time - start_time).total_seconds()
            print(f"   ✅ Calculated duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.1f} minutes)")
            print(f"   Limit: {duration_int} seconds ({duration_int/60:.1f} minutes)")
            
            if duration_seconds > duration_int:
                excess = duration_seconds - duration_int
                print(f"   ⚠️  Duration EXCEEDS limit by {excess:.1f} seconds!")
                print(f"   💡 Loop recorder should delete oldest segments")
                print(f"   💡 Check server logs for loop recorder activity")
            else:
                print(f"   ✅ Duration is within limit (no deletion needed)")
            
            print()
            print("5️⃣  Summary:")
            print(f"   Flow ID: {flow_id}")
            print(f"   Loop recorder duration: {duration_int}s")
            print(f"   Current flow duration: {duration_seconds:.1f}s")
            print(f"   Segments: {len(segments)}")
            print(f"   Status: {'EXCEEDS LIMIT' if duration_seconds > duration_int else 'Within limit'}")
            
            if duration_seconds > duration_int:
                print()
                print("🔧 Troubleshooting:")
                print("   1. Check server logs for loop recorder messages:")
                print("      grep 'Loop recorder' server.log")
                print("   2. Verify events are being emitted:")
                print("      grep 'flow-segments/created' server.log")
                print("   3. Check if loop recorder is enabled in server config")
                print("   4. Verify segment deletion permissions")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def _parse_timerange(timerange):
    """Parse TAMS timerange to datetime."""
    import re
    from datetime import datetime
    
    if not timerange:
        return None
    
    try:
        timerange_str = str(timerange.value) if hasattr(timerange, 'value') else str(timerange)
        pattern = r'\[(\d+):(\d+)'
        match = re.search(pattern, timerange_str)
        
        if match:
            seconds = int(match.group(1))
            nanos = int(match.group(2))
            return datetime.fromtimestamp(seconds + (nanos / 1e9), tz=datetime.timezone.utc)
    except Exception:
        pass
    
    return None


def _get_timerange_start(timerange):
    """Get start time of timerange as float for sorting."""
    parsed = _parse_timerange(timerange)
    if parsed:
        return parsed.timestamp()
    return 0.0


def main():
    parser = argparse.ArgumentParser(description="Debug loop recorder for a specific flow")
    parser.add_argument("flow_id", help="Flow ID to debug")
    parser.add_argument("--server-url", default="http://localhost:8000", help="TAMS server URL")
    parser.add_argument("--username", default="admin", help="TAMS username")
    parser.add_argument("--password", default="admin", help="TAMS password")
    parser.add_argument("--skip-auth", action="store_true", help="Skip authentication (for testing)")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("LOOP RECORDER DIAGNOSTIC TOOL")
    print("=" * 70)
    print()
    print("This tool will check:")
    print("  1. If flow exists")
    print("  2. If loop_recorder_duration tag is set")
    print("  3. If segments exist and have timeranges")
    print("  4. Calculate current flow duration vs limit")
    print("  5. Identify why loop recorder might not be working")
    print()
    print("=" * 70)
    print()
    
    try:
        asyncio.run(debug_flow(args.flow_id, args.server_url, args.username, args.password))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

