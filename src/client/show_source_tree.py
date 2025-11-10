#!/usr/bin/env python3
"""
Show Source Tree Script

Displays the complete tree structure of a TAMS source including:
- Source metadata and tags
- All flows with their properties and tags
- All segments with their timeranges and export options
- Supported export/download options for each segment

Usage:
    python show_source_tree.py --source-id <source_id> --server <url> --username <user> --password <pass>
    python show_source_tree.py --source-id <source_id> --server <url> --username <user> --password <pass> --json
    python show_source_tree.py --source-id <source_id> --server <url> --username <user> --password <pass> --export-json <file.json>
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path to import vasttamsclient
sys.path.insert(0, str(Path(__file__).parent))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSAPIError, TAMSClientError


def format_timerange(timerange: Dict[str, Any]) -> str:
    """Format timerange dictionary to string."""
    if isinstance(timerange, dict):
        return timerange.get("value", str(timerange))
    return str(timerange)


def format_size(size_bytes: Optional[int]) -> str:
    """Format bytes to human-readable size."""
    if size_bytes is None:
        return "N/A"
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def print_source_tree(tree: Dict[str, Any], verbose: bool = False):
    """Print source tree in a human-readable format."""
    source = tree.get("source", {})
    flows = tree.get("flows", [])
    
    print("\n" + "=" * 80)
    print("SOURCE TREE")
    print("=" * 80)
    
    # Source information
    print(f"\n📁 Source: {source.get('id', 'N/A')}")
    print(f"   Format: {source.get('format', 'N/A')}")
    print(f"   Label: {source.get('label', 'N/A')}")
    if source.get('description'):
        print(f"   Description: {source['description']}")
    
    # Source tags
    source_tags = source.get("tags", {})
    if source_tags:
        print(f"   Tags: {len(source_tags)} tag(s)")
        if verbose:
            for key, value in source_tags.items():
                print(f"      - {key}: {value}")
    
    # Flows
    print(f"\n📊 Flows: {len(flows)} flow(s)")
    
    for flow_idx, flow in enumerate(flows, 1):
        print(f"\n   Flow {flow_idx}: {flow.get('id', 'N/A')}")
        print(f"      Format: {flow.get('format', 'N/A')}")
        print(f"      Codec: {flow.get('codec', 'N/A')}")
        print(f"      Label: {flow.get('label', 'N/A')}")
        if flow.get('description'):
            print(f"      Description: {flow['description']}")
        
        # Flow tags
        flow_tags = flow.get("tags", {})
        if flow_tags:
            print(f"      Tags: {len(flow_tags)} tag(s)")
            if verbose:
                for key, value in flow_tags.items():
                    print(f"         - {key}: {value}")
        
        # Segments
        segments = flow.get("segments", [])
        print(f"      Segments: {len(segments)} segment(s)")
        
        for seg_idx, segment in enumerate(segments, 1):
            print(f"\n         Segment {seg_idx}: {segment.get('object_id', 'N/A')}")
            timerange = segment.get("timerange", {})
            timerange_str = format_timerange(timerange)
            print(f"            Timerange: {timerange_str}")
            
            if segment.get("sample_offset") is not None:
                print(f"            Sample Offset: {segment.get('sample_offset')}")
            if segment.get("sample_count") is not None:
                print(f"            Sample Count: {segment.get('sample_count')}")
            
            # Export options (get_urls)
            get_urls = segment.get("get_urls", [])
            if get_urls:
                print(f"            Export Options: {len(get_urls)} URL(s) available")
                for url_idx, url_info in enumerate(get_urls, 1):
                    url = url_info.get("url", "N/A")
                    presigned = url_info.get("presigned", False)
                    label = url_info.get("label", "N/A")
                    storage_id = url_info.get("storage_id", "N/A")
                    
                    url_type = "Presigned" if presigned else "Direct"
                    print(f"               Option {url_idx}:")
                    print(f"                  Type: {url_type}")
                    print(f"                  Label: {label}")
                    if verbose:
                        print(f"                  Storage ID: {storage_id}")
                        print(f"                  URL: {url}")
                    else:
                        # Truncate URL for display
                        url_display = url[:60] + "..." if len(url) > 60 else url
                        print(f"                  URL: {url_display}")
                    
                    # Show additional metadata if verbose
                    if verbose:
                        for key, value in url_info.items():
                            if key not in ["url", "presigned", "label", "storage_id"]:
                                print(f"                  {key}: {value}")
            else:
                print(f"            Export Options: No URLs available (may need to request with accept_get_urls)")
            
            # Object information
            obj = segment.get("object", {})
            if obj:
                print(f"            Object ID: {obj.get('id', 'N/A')}")
                if obj.get("file_size"):
                    print(f"            Object Size: {format_size(obj.get('file_size'))}")
                if obj.get("content_type"):
                    print(f"            Content Type: {obj.get('content_type')}")
    
    print("\n" + "=" * 80)
    print("EXPORT OPTIONS SUMMARY")
    print("=" * 80)
    
    # Summarize export options
    total_segments = sum(len(flow.get("segments", [])) for flow in flows)
    segments_with_urls = 0
    total_urls = 0
    presigned_count = 0
    direct_count = 0
    
    for flow in flows:
        for segment in flow.get("segments", []):
            get_urls = segment.get("get_urls", [])
            if get_urls:
                segments_with_urls += 1
                total_urls += len(get_urls)
                for url_info in get_urls:
                    if url_info.get("presigned", False):
                        presigned_count += 1
                    else:
                        direct_count += 1
    
    print(f"\nTotal Segments: {total_segments}")
    print(f"Segments with Export URLs: {segments_with_urls}")
    print(f"Total Export URLs Available: {total_urls}")
    print(f"  - Presigned URLs: {presigned_count}")
    print(f"  - Direct URLs: {direct_count}")
    
    if segments_with_urls < total_segments:
        print(f"\n⚠️  Note: {total_segments - segments_with_urls} segment(s) have no export URLs.")
        print("   You may need to request URLs using query parameters:")
        print("   - accept_get_urls: Filter by label")
        print("   - presigned: true/false to filter presigned URLs")
        print("   - verbose_storage: true to include storage metadata")


async def main():
    parser = argparse.ArgumentParser(
        description="Show TAMS source tree with export options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show source tree
  python show_source_tree.py --source-id <id> --server http://localhost:8000 --username user --password pass

  # Show with verbose output
  python show_source_tree.py --source-id <id> --server http://localhost:8000 --username user --password pass --verbose

  # Export to JSON file
  python show_source_tree.py --source-id <id> --server http://localhost:8000 --username user --password pass --export-json output.json

  # Show as JSON
  python show_source_tree.py --source-id <id> --server http://localhost:8000 --username user --password pass --json
        """
    )
    
    parser.add_argument("--source-id", required=True, help="Source ID to display")
    parser.add_argument("--server", required=True, help="TAMS server URL (e.g., http://localhost:8000)")
    parser.add_argument("--username", required=True, help="Username for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output including all tags and URLs")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of formatted text")
    parser.add_argument("--export-json", help="Export tree to JSON file")
    parser.add_argument("--accept-get-urls", help="Comma-separated list of get_urls labels to include")
    parser.add_argument("--presigned", type=bool, help="Filter presigned URLs (true/false)")
    parser.add_argument("--verbose-storage", action="store_true", help="Include verbose storage metadata in get_urls")
    
    args = parser.parse_args()
    
    # Build query parameters for segments with export URLs
    # By default, get_urls should be included, but we can filter them
    segment_params = {}
    if args.accept_get_urls:
        segment_params["accept_get_urls"] = args.accept_get_urls
    if args.presigned is not None:
        segment_params["presigned"] = str(args.presigned).lower()
    if args.verbose_storage:
        segment_params["verbose_storage"] = "true"
    
    try:
        async with TAMSClient(
            server_url=args.server,
            username=args.username,
            password=args.password
        ) as client:
            # Use the existing export_source_tree function to get the base tree
            # But we need to build it manually to avoid it printing JSON to stdout
            # Get source if source_id provided
            source = await client.get_source(args.source_id)
            if source is None:
                print(f"Error: Source '{args.source_id}' not found", file=sys.stderr)
                return 1
            
            # Build source data with tags
            source_data = source._data.copy()
            try:
                source_tags = await source.get_tags()
                if source_tags:
                    source_data["tags"] = source_tags
            except Exception as e:
                print(f"Warning: Failed to get source tags: {e}", file=sys.stderr)
                source_data["tags"] = {}
            
            # Get all flows for this source
            flows_list = await source.list_flows()
            flows_data = []
            
            for flow in flows_list:
                # Build flow data with tags
                flow_data = flow._data.copy()
                try:
                    flow_tags = await flow.get_tags()
                    if flow_tags:
                        flow_data["tags"] = flow_tags
                except Exception as e:
                    print(f"Warning: Failed to get flow tags: {e}", file=sys.stderr)
                    flow_data["tags"] = {}
                
                # Get all segments for this flow (with export options if params provided)
                segments = await flow.list_segments(**segment_params)
                segments_data = []
                
                for segment in segments:
                    # Build segment data
                    segment_data = segment._data.copy()
                    
                    # Get object for this segment
                    object_id = segment.object_id
                    try:
                        from vasttamsclient.api import objects as object_api
                        object_data = await object_api.get_object(client, object_id)
                        if object_data:
                            segment_data["object"] = object_data
                        else:
                            segment_data["object"] = None
                    except Exception as e:
                        segment_data["object"] = None
                    
                    segments_data.append(segment_data)
                
                flow_data["segments"] = segments_data
                flows_data.append(flow_data)
            
            # Build complete tree structure
            tree = {
                "source": source_data,
                "flows": flows_data
            }
            
            # Output
            if args.json:
                print(json.dumps(tree, indent=2, default=str))
            elif args.export_json:
                output_path = Path(args.export_json)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(tree, indent=2, default=str), encoding='utf-8')
                print(f"Source tree exported to {args.export_json}")
            else:
                print_source_tree(tree, verbose=args.verbose)
            
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

