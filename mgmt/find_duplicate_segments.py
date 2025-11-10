#!/usr/bin/env python3
"""
Find and optionally remove duplicate segments in a TAMS flow.

Identifies duplicate segments by:
- Same timerange
- Same object_id
- Overlapping timeranges

Usage:
    python find_duplicate_segments.py --flow-id <flow_id> --server <url> --username <user> --password <pass>
    python find_duplicate_segments.py --flow-id <flow_id> --server <url> --username <user> --password <pass> --remove
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict

# Add parent directory to path to import vasttamsclient
sys.path.insert(0, str(Path(__file__).parent))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSAPIError, TAMSClientError


def format_timerange(timerange: Dict[str, Any]) -> str:
    """Format timerange dictionary to string."""
    if isinstance(timerange, dict):
        return timerange.get("value", str(timerange))
    return str(timerange)


def parse_timerange(timerange_str: str) -> Tuple[float, float]:
    """
    Parse timerange string like "[0:0_10:0)" to (start, end) in seconds.
    
    Format: [MM:SS_MM:SS) or [HH:MM:SS_HH:MM:SS)
    """
    try:
        # Remove brackets and parentheses
        timerange_str = timerange_str.strip("[]()")
        if "_" not in timerange_str:
            return (0.0, 0.0)
        
        start_str, end_str = timerange_str.split("_", 1)
        
        def parse_time(time_str: str) -> float:
            """Parse time string to seconds."""
            parts = time_str.split(":")
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            return 0.0
        
        start = parse_time(start_str)
        end = parse_time(end_str)
        return (start, end)
    except Exception:
        return (0.0, 0.0)


def find_duplicates_by_timerange(segments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Find segments with identical timeranges."""
    timerange_map = defaultdict(list)
    
    for seg in segments:
        timerange = seg.get("timerange", {})
        timerange_str = format_timerange(timerange)
        timerange_map[timerange_str].append(seg)
    
    # Return only entries with duplicates
    return {tr: segs for tr, segs in timerange_map.items() if len(segs) > 1}


def find_duplicates_by_object_id(segments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Find segments with identical object_ids."""
    object_map = defaultdict(list)
    
    for seg in segments:
        object_id = seg.get("object_id", "")
        if object_id:
            object_map[object_id].append(seg)
    
    # Return only entries with duplicates
    return {obj_id: segs for obj_id, segs in object_map.items() if len(segs) > 1}


def find_overlapping_segments(segments: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Find segments with overlapping timeranges."""
    overlaps = []
    
    for i, seg1 in enumerate(segments):
        timerange1 = seg1.get("timerange", {})
        timerange_str1 = format_timerange(timerange1)
        start1, end1 = parse_timerange(timerange_str1)
        
        for seg2 in segments[i + 1:]:
            timerange2 = seg2.get("timerange", {})
            timerange_str2 = format_timerange(timerange2)
            start2, end2 = parse_timerange(timerange_str2)
            
            # Check for overlap (not just exact match)
            if start1 < end2 and start2 < end1:
                overlaps.append((seg1, seg2))
    
    return overlaps


async def main():
    parser = argparse.ArgumentParser(
        description="Find and optionally remove duplicate segments in a TAMS flow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find duplicates
  python find_duplicate_segments.py --flow-id <id> --server http://localhost:8000 --username user --password pass

  # Find and remove duplicates (keeps first occurrence)
  python find_duplicate_segments.py --flow-id <id> --server http://localhost:8000 --username user --password pass --remove
        """
    )
    
    parser.add_argument("--flow-id", required=True, help="Flow ID to check")
    parser.add_argument("--server", required=True, help="TAMS server URL (e.g., http://localhost:8000)")
    parser.add_argument("--username", required=True, help="Username for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    parser.add_argument("--remove", action="store_true", help="Remove duplicate segments (keeps first occurrence)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    
    args = parser.parse_args()
    
    try:
        async with TAMSClient(
            server_url=args.server,
            username=args.username,
            password=args.password
        ) as client:
            # Get flow
            flow = await client.get_flow(args.flow_id)
            if flow is None:
                print(f"Error: Flow '{args.flow_id}' not found", file=sys.stderr)
                return 1
            
            print(f"\n{'='*80}")
            print(f"Analyzing Flow: {args.flow_id}")
            print(f"Label: {flow.label or 'N/A'}")
            print(f"Format: {flow.format or 'N/A'}")
            print(f"{'='*80}\n")
            
            # Get all segments
            print("📊 Fetching segments...")
            segments = await flow.list_segments()
            print(f"   Found {len(segments)} total segments\n")
            
            if not segments:
                print("✅ No segments found in flow")
                return 0
            
            # Convert to dict format for analysis
            segments_data = [seg._data for seg in segments]
            
            # Find duplicates by timerange
            print("🔍 Checking for duplicate timeranges...")
            timerange_duplicates = find_duplicates_by_timerange(segments_data)
            if timerange_duplicates:
                print(f"   ⚠️  Found {len(timerange_duplicates)} timerange(s) with duplicates:")
                total_dup_segments = 0
                for timerange, segs in timerange_duplicates.items():
                    count = len(segs)
                    total_dup_segments += count - 1  # -1 because we keep one
                    print(f"      Timerange: {timerange}")
                    print(f"         Duplicates: {count} segments")
                    if args.verbose:
                        for seg in segs:
                            obj_id = seg.get("object_id", "N/A")
                            seg_id = seg.get("id", "N/A")
                            print(f"            - Segment ID: {seg_id}, Object ID: {obj_id}")
                print(f"   Total duplicate segments by timerange: {total_dup_segments}\n")
            else:
                print("   ✅ No duplicate timeranges found\n")
            
            # Find duplicates by object_id
            print("🔍 Checking for duplicate object_ids...")
            object_duplicates = find_duplicates_by_object_id(segments_data)
            if object_duplicates:
                print(f"   ⚠️  Found {len(object_duplicates)} object_id(s) with duplicates:")
                total_dup_objects = 0
                for object_id, segs in object_duplicates.items():
                    count = len(segs)
                    total_dup_objects += count - 1
                    print(f"      Object ID: {object_id}")
                    print(f"         Duplicates: {count} segments")
                    if args.verbose:
                        for seg in segs:
                            timerange = format_timerange(seg.get("timerange", {}))
                            seg_id = seg.get("id", "N/A")
                            print(f"            - Segment ID: {seg_id}, Timerange: {timerange}")
                print(f"   Total duplicate segments by object_id: {total_dup_objects}\n")
            else:
                print("   ✅ No duplicate object_ids found\n")
            
            # Find overlapping segments
            print("🔍 Checking for overlapping timeranges...")
            overlaps = find_overlapping_segments(segments_data)
            if overlaps:
                print(f"   ⚠️  Found {len(overlaps)} overlapping segment pairs:")
                for seg1, seg2 in overlaps[:10]:  # Show first 10
                    timerange1 = format_timerange(seg1.get("timerange", {}))
                    timerange2 = format_timerange(seg2.get("timerange", {}))
                    obj_id1 = seg1.get("object_id", "N/A")
                    obj_id2 = seg2.get("object_id", "N/A")
                    print(f"      Overlap:")
                    print(f"         Segment 1: {seg1.get('id', 'N/A')} - {timerange1} (Object: {obj_id1})")
                    print(f"         Segment 2: {seg2.get('id', 'N/A')} - {timerange2} (Object: {obj_id2})")
                if len(overlaps) > 10:
                    print(f"      ... and {len(overlaps) - 10} more overlaps")
                print()
            else:
                print("   ✅ No overlapping timeranges found\n")
            
            # Summary
            total_duplicates = len(timerange_duplicates) + len(object_duplicates)
            if total_duplicates == 0 and len(overlaps) == 0:
                print("✅ No duplicates found!")
                return 0
            
            print(f"{'='*80}")
            print("SUMMARY")
            print(f"{'='*80}")
            print(f"Total segments: {len(segments)}")
            print(f"Duplicate timeranges: {len(timerange_duplicates)}")
            print(f"Duplicate object_ids: {len(object_duplicates)}")
            print(f"Overlapping pairs: {len(overlaps)}")
            print()
            
            # Remove duplicates if requested
            if args.remove:
                print("🗑️  Removing duplicates...")
                removed_count = 0
                
                # Remove duplicates by timerange (keep first, remove rest)
                # We need to get the actual segment objects to delete them properly
                all_segments = await flow.list_segments()
                
                for timerange_str, segs in timerange_duplicates.items():
                    # Sort by segment ID to ensure consistent ordering
                    segs_sorted = sorted(segs, key=lambda s: s.get("id", ""))
                    keep_seg = segs_sorted[0]
                    remove_segs = segs_sorted[1:]
                    
                    print(f"   Processing timerange: {timerange_str} ({len(remove_segs)} duplicates to remove)")
                    
                    for seg_data in remove_segs:
                        object_id = seg_data.get("object_id", "")
                        if object_id:
                            try:
                                # Find the actual segment object by object_id and timerange
                                matching_segments = [
                                    seg for seg in all_segments
                                    if seg.object_id == object_id
                                    and format_timerange(seg.timerange) == timerange_str
                                ]
                                
                                if matching_segments:
                                    # Delete the segment using its delete method
                                    segment_to_delete = matching_segments[0]
                                    await segment_to_delete.delete()
                                    removed_count += 1
                                    if args.verbose:
                                        print(f"      ✅ Removed segment (object: {object_id}, timerange: {timerange_str})")
                                else:
                                    if args.verbose:
                                        print(f"      ⚠️  Segment not found (object: {object_id}, timerange: {timerange_str})")
                            except Exception as e:
                                print(f"      ❌ Failed to remove segment (object: {object_id}): {e}", file=sys.stderr)
                
                print(f"✅ Removed {removed_count} duplicate segments")
            else:
                print("💡 Use --remove to remove duplicate segments (keeps first occurrence)")
            
            return 0
            
    except TAMSAPIError as e:
        print(f"TAMS API Error: {e}", file=sys.stderr)
        return 1
    except TAMSClientError as e:
        print(f"TAMS Client Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

