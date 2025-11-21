#!/usr/bin/env python3
"""
Cascade delete a flow or source by ID, or cleanup empty sources/flows

This script will:
1. Connect to TAMS server with provided credentials
2. Either delete a specific ID or cleanup all empty sources/flows
3. Count all sub-elements that will be deleted (flows, segments, objects)
4. Display the counts and ask for confirmation
5. Perform cascade deletion if confirmed

Usage:
    # Delete specific ID
    python cascade_delete.py <id> --server <server_url> --username <user> --password <pass>
    
    # Cleanup empty sources and flows
    python cascade_delete.py --cleanup-empty --server <server_url> --username <user> --password <pass>
    
Examples:
    # Delete with confirmation prompt
    python cascade_delete.py abc-123 --server http://localhost:8000 --username admin --password secret
    
    # Delete with auto-confirmation
    python cascade_delete.py abc-123 --server http://localhost:8000 --username admin --password secret --yes
    
    # Cleanup all empty sources and flows
    python cascade_delete.py --cleanup-empty --server http://localhost:8000 --username admin --password secret
    
    # Cleanup empty with auto-confirmation
    python cascade_delete.py --cleanup-empty --server http://localhost:8000 --username admin --password secret --yes
"""

import sys
import os
import asyncio
import argparse
from typing import Optional, Dict, Any, List

# Add the src directory to the path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(root_dir, 'src', 'client'))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSAPIError, TAMSConnectionError, TAMSAuthenticationError


class DeleteStats:
    """Statistics for deletion operations"""
    def __init__(self):
        self.sources = 0
        self.flows = 0
        self.segments = 0
        self.objects = 0
        self.flow_details: List[Dict[str, Any]] = []
        self.source_details: List[Dict[str, Any]] = []
        
    def add_flow(self, flow_id: str, label: str, segment_count: int, object_count: int):
        """Add flow details"""
        self.flows += 1
        self.segments += segment_count
        self.objects += object_count
        self.flow_details.append({
            "id": flow_id,
            "label": label or "(no label)",
            "segments": segment_count,
            "objects": object_count
        })
    
    def add_source(self, source_id: str, label: str, flow_count: int):
        """Add source details"""
        self.sources += 1
        self.source_details.append({
            "id": source_id,
            "label": label or "(no label)",
            "flows": flow_count
        })
    
    def __str__(self):
        """String representation"""
        lines = []
        if self.sources > 0:
            lines.append(f"Sources:  {self.sources}")
        if self.flows > 0:
            lines.append(f"Flows:    {self.flows}")
        if self.segments > 0:
            lines.append(f"Segments: {self.segments}")
        if self.objects > 0:
            lines.append(f"Objects:  {self.objects}")
        return "\n".join(lines) if lines else "Nothing to delete"


async def count_flow_elements(client: TAMSClient, flow_id: str) -> Dict[str, int]:
    """
    Count segments and objects in a flow.
    
    Returns:
        Dict with 'segments' and 'objects' counts
    """
    from vasttamsclient.api import segments as segment_api
    
    # Get all segments for this flow
    url = f"{client.server_url}{client.api_prefix}/flows/{flow_id}/segments"
    headers = await client._get_headers()
    
    # Ensure session is available
    await client._ensure_session()
    if client._session is None:
        raise TAMSConnectionError("Client session not available")
    
    async with client._session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            # Handle both dict with "data" key and direct list response
            if isinstance(data, dict):
                segments = data.get("data", [])
            elif isinstance(data, list):
                segments = data
            else:
                segments = []
            segment_count = len(segments)
            
            # Count unique objects (segments may reference the same object)
            object_ids = set()
            for seg in segments:
                obj_id = seg.get("object_id")
                if obj_id:
                    object_ids.add(obj_id)
            
            return {
                "segments": segment_count,
                "objects": len(object_ids)
            }
        elif response.status == 404:
            return {"segments": 0, "objects": 0}
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list segments: {error_text}", response.status, error_text)


async def analyze_source_deletion(client: TAMSClient, source_id: str) -> DeleteStats:
    """
    Analyze what will be deleted when deleting a source.
    
    Returns:
        DeleteStats object with counts
    """
    stats = DeleteStats()
    stats.sources = 1
    
    # Get source to verify it exists
    source = await client.get_source(source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")
    
    print(f"📊 Analyzing source: {source_id}")
    print(f"   Label: {source._data.get('label', '(no label)')}")
    print(f"   Format: {source._data.get('format', 'unknown')}")
    print()
    
    # Get all flows for this source
    print("🔍 Counting flows and segments...")
    flows = await source.list_flows()
    
    if not flows:
        print("   No flows found")
        return stats
    
    print(f"   Found {len(flows)} flow(s)")
    
    # Count segments and objects for each flow
    for flow in flows:
        flow_id = flow._data.get("id")
        flow_label = flow._data.get("label", "(no label)")
        
        counts = await count_flow_elements(client, flow_id)
        stats.add_flow(flow_id, flow_label, counts["segments"], counts["objects"])
        
        print(f"   - Flow: {flow_id[:8]}... ({flow_label})")
        print(f"     Segments: {counts['segments']}, Objects: {counts['objects']}")
    
    return stats


async def analyze_flow_deletion(client: TAMSClient, flow_id: str) -> DeleteStats:
    """
    Analyze what will be deleted when deleting a flow.
    
    Returns:
        DeleteStats object with counts
    """
    stats = DeleteStats()
    
    # Get flow to verify it exists
    flow = await client.get_flow(flow_id)
    if not flow:
        raise ValueError(f"Flow not found: {flow_id}")
    
    print(f"📊 Analyzing flow: {flow_id}")
    print(f"   Label: {flow._data.get('label', '(no label)')}")
    print(f"   Format: {flow._data.get('format', 'unknown')}")
    print(f"   Codec: {flow._data.get('codec', 'unknown')}")
    print()
    
    # Count segments and objects
    print("🔍 Counting segments and objects...")
    counts = await count_flow_elements(client, flow_id)
    
    stats.add_flow(flow_id, flow._data.get('label'), counts["segments"], counts["objects"])
    
    print(f"   Segments: {counts['segments']}")
    print(f"   Objects:  {counts['objects']}")
    
    return stats


async def delete_source(client: TAMSClient, source_id: str) -> bool:
    """
    Delete a source with cascade.
    
    Returns:
        True if successful
    """
    try:
        source = await client.get_source(source_id)
        if not source:
            print(f"❌ Source not found: {source_id}")
            return False
        
        print(f"🗑️  Deleting source {source_id}...")
        await source.delete(cascade=True)
        print(f"✅ Successfully deleted source {source_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to delete source: {e}")
        return False


async def delete_flow(client: TAMSClient, flow_id: str) -> bool:
    """
    Delete a flow with cascade.
    
    Returns:
        True if successful
    """
    try:
        from vasttamsclient.api import flows as flow_api
        
        print(f"🗑️  Deleting flow {flow_id}...")
        await flow_api.delete_flow(client, flow_id, cascade=True)
        print(f"✅ Successfully deleted flow {flow_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to delete flow: {e}")
        return False


def get_user_confirmation(stats: DeleteStats, entity_type: str, entity_id: str) -> bool:
    """
    Get manual confirmation from user.
    
    Args:
        stats: DeleteStats object with counts
        entity_type: "source" or "flow"
        entity_id: ID of the entity to delete
    
    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "=" * 80)
    print(f"🚨 WARNING: CASCADE DELETE {entity_type.upper()}")
    print("=" * 80)
    print(f"⚠️  You are about to cascade delete {entity_type}: {entity_id}")
    print()
    print("📊 The following will be PERMANENTLY DELETED:")
    print()
    for line in str(stats).split('\n'):
        print(f"   {line}")
    print()
    print("⚠️  This action is IRREVERSIBLE!")
    print("⚠️  All data will be PERMANENTLY LOST!")
    print()
    
    while True:
        response = input("Type 'yes' to confirm deletion: ").strip().lower()
        if response == "yes":
            print("✅ Confirmation received. Proceeding with deletion...")
            return True
        elif response in ['no', 'n', 'cancel', 'abort', 'quit', 'exit']:
            print("❌ Deletion cancelled by user.")
            return False
        else:
            print("❌ Invalid response. Please type 'yes' to confirm or 'no' to cancel.")


async def find_empty_sources_and_flows(client: TAMSClient) -> DeleteStats:
    """
    Find all sources and flows with no segments.
    
    Returns:
        DeleteStats object with empty sources and flows
    """
    stats = DeleteStats()
    
    print("🔍 Scanning all sources and flows for empty entries...")
    print()
    
    # Get all sources
    sources = await client.list_sources()
    print(f"📋 Found {len(sources)} total source(s)")
    
    empty_sources = []
    empty_flows = []
    
    # Check each source
    for source in sources:
        source_id = source._data.get("id")
        source_label = source._data.get("label", "(no label)")
        
        # Get all flows for this source
        flows = await source.list_flows()
        
        if not flows:
            # Source has no flows - it's empty
            empty_sources.append({
                "id": source_id,
                "label": source_label,
                "reason": "no flows"
            })
            stats.add_source(source_id, source_label, 0)
            continue
        
        # Check if all flows are empty
        all_flows_empty = True
        source_has_empty_flows = False
        
        for flow in flows:
            flow_id = flow._data.get("id")
            flow_label = flow._data.get("label", "(no label)")
            
            # Count segments for this flow
            counts = await count_flow_elements(client, flow_id)
            
            if counts["segments"] == 0:
                # This flow is empty
                empty_flows.append({
                    "id": flow_id,
                    "label": flow_label,
                    "source_id": source_id,
                    "source_label": source_label
                })
                stats.add_flow(flow_id, flow_label, 0, 0)
                source_has_empty_flows = True
            else:
                all_flows_empty = False
        
        # If all flows are empty, the source is effectively empty
        if all_flows_empty and flows:
            empty_sources.append({
                "id": source_id,
                "label": source_label,
                "reason": "all flows empty"
            })
            stats.add_source(source_id, source_label, len(flows))
    
    # Also check for flows that might not be under sources we checked
    # (in case there are orphaned flows)
    all_flows = await client.list_flows()
    print(f"📋 Found {len(all_flows)} total flow(s)")
    
    # Check flows we haven't already processed
    processed_flow_ids = {f["id"] for f in empty_flows}
    for flow in all_flows:
        flow_id = flow._data.get("id")
        if flow_id not in processed_flow_ids:
            counts = await count_flow_elements(client, flow_id)
            if counts["segments"] == 0:
                flow_label = flow._data.get("label", "(no label)")
                source_id = flow._data.get("source_id", "unknown")
                empty_flows.append({
                    "id": flow_id,
                    "label": flow_label,
                    "source_id": source_id,
                    "source_label": "(unknown)"
                })
                stats.add_flow(flow_id, flow_label, 0, 0)
    
    # Print summary
    print()
    print("📊 Empty Sources Found:")
    if empty_sources:
        for src in empty_sources[:10]:  # Show first 10
            print(f"   - {src['id'][:8]}... ({src['label']}) - {src['reason']}")
        if len(empty_sources) > 10:
            print(f"   ... and {len(empty_sources) - 10} more")
    else:
        print("   None")
    
    print()
    print("📊 Empty Flows Found:")
    if empty_flows:
        for flow in empty_flows[:10]:  # Show first 10
            print(f"   - {flow['id'][:8]}... ({flow['label']}) - Source: {flow['source_label']}")
        if len(empty_flows) > 10:
            print(f"   ... and {len(empty_flows) - 10} more")
    else:
        print("   None")
    
    return stats


async def cleanup_empty(
    server_url: str,
    username: str,
    password: str,
    auto_confirm: bool = False
) -> int:
    """
    Cleanup all empty sources and flows.
    
    Args:
        server_url: TAMS server URL
        username: Username for authentication
        password: Password for authentication
        auto_confirm: If True, skip confirmation prompt
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Create client
        print(f"🔌 Connecting to TAMS server: {server_url}")
        async with TAMSClient(server_url, username, password) as client:
            print(f"✅ Connected successfully")
            print()
            
            # Find empty sources and flows
            stats = await find_empty_sources_and_flows(client)
            
            print()
            
            # Check if there's anything to delete
            if stats.sources == 0 and stats.flows == 0:
                print("✅ No empty sources or flows found. Nothing to delete.")
                return 0
            
            # Get confirmation unless auto-confirm is enabled
            if not auto_confirm:
                print("=" * 80)
                print("🚨 WARNING: CLEANUP EMPTY SOURCES AND FLOWS")
                print("=" * 80)
                print("⚠️  You are about to delete the following empty entries:")
                print()
                for line in str(stats).split('\n'):
                    print(f"   {line}")
                print()
                print("⚠️  This action is IRREVERSIBLE!")
                print("⚠️  All data will be PERMANENTLY LOST!")
                print()
                
                while True:
                    response = input("Type 'yes' to confirm deletion: ").strip().lower()
                    if response == "yes":
                        print("✅ Confirmation received. Proceeding with deletion...")
                        break
                    elif response in ['no', 'n', 'cancel', 'abort', 'quit', 'exit']:
                        print("❌ Deletion cancelled by user.")
                        return 1
                    else:
                        print("❌ Invalid response. Please type 'yes' to confirm or 'no' to cancel.")
            else:
                print("⚠️  Auto-confirmation enabled (--yes flag)")
                print("⚠️  Proceeding without manual confirmation...")
                print()
                print("📊 Will delete:")
                for line in str(stats).split('\n'):
                    print(f"   {line}")
                print()
            
            # Perform deletions
            deleted_sources = 0
            failed_sources = 0
            deleted_flows = 0
            failed_flows = 0
            
            # Delete empty flows first (to avoid issues with sources that have flows)
            if stats.flows > 0:
                print(f"\n🗑️  Deleting {stats.flows} empty flow(s)...")
                for flow_detail in stats.flow_details:
                    flow_id = flow_detail["id"]
                    success = await delete_flow(client, flow_id)
                    if success:
                        deleted_flows += 1
                    else:
                        failed_flows += 1
            
            # Delete empty sources
            if stats.sources > 0:
                print(f"\n🗑️  Deleting {stats.sources} empty source(s)...")
                for source_detail in stats.source_details:
                    source_id = source_detail["id"]
                    success = await delete_source(client, source_id)
                    if success:
                        deleted_sources += 1
                    else:
                        failed_sources += 1
            
            # Summary
            print()
            print("=" * 80)
            print("📊 CLEANUP SUMMARY")
            print("=" * 80)
            print(f"✅ Successfully deleted sources: {deleted_sources}")
            if failed_sources > 0:
                print(f"❌ Failed to delete sources: {failed_sources}")
            print(f"✅ Successfully deleted flows: {deleted_flows}")
            if failed_flows > 0:
                print(f"❌ Failed to delete flows: {failed_flows}")
            print()
            
            if failed_sources == 0 and failed_flows == 0:
                print("✅ Cleanup completed successfully!")
                return 0
            else:
                print("⚠️  Cleanup completed with some failures")
                return 1
                
    except TAMSAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return 1
    except TAMSConnectionError as e:
        print(f"❌ Connection error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def cascade_delete(
    entity_id: str,
    server_url: str,
    username: str,
    password: str,
    auto_confirm: bool = False
) -> int:
    """
    Main cascade delete function.
    
    Args:
        entity_id: Source or Flow ID to delete
        server_url: TAMS server URL
        username: Username for authentication
        password: Password for authentication
        auto_confirm: If True, skip confirmation prompt
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Create client
        print(f"🔌 Connecting to TAMS server: {server_url}")
        async with TAMSClient(server_url, username, password) as client:
            print(f"✅ Connected successfully")
            print()
            
            # Try to determine if it's a source or flow
            is_source = False
            is_flow = False
            
            # Try as source first
            try:
                source = await client.get_source(entity_id)
                if source:
                    is_source = True
            except Exception:
                pass
            
            # Try as flow if not a source
            if not is_source:
                try:
                    flow = await client.get_flow(entity_id)
                    if flow:
                        is_flow = True
                except Exception:
                    pass
            
            if not is_source and not is_flow:
                print(f"❌ Error: ID '{entity_id}' not found as source or flow")
                return 1
            
            # Analyze what will be deleted
            if is_source:
                stats = await analyze_source_deletion(client, entity_id)
                entity_type = "source"
            else:
                stats = await analyze_flow_deletion(client, entity_id)
                entity_type = "flow"
            
            print()
            
            # Check if there's anything to delete
            if stats.flows == 0 and stats.segments == 0 and stats.objects == 0:
                if is_source:
                    print("ℹ️  Source has no flows, segments, or objects")
                    print("   Only the source itself will be deleted")
                else:
                    print("ℹ️  Flow has no segments or objects")
                    print("   Only the flow itself will be deleted")
            
            # Get confirmation unless auto-confirm is enabled
            if not auto_confirm:
                if not get_user_confirmation(stats, entity_type, entity_id):
                    return 1
            else:
                print("⚠️  Auto-confirmation enabled (--yes flag)")
                print("⚠️  Proceeding without manual confirmation...")
                print()
                print("📊 Will delete:")
                for line in str(stats).split('\n'):
                    print(f"   {line}")
                print()
            
            # Perform deletion
            if is_source:
                success = await delete_source(client, entity_id)
            else:
                success = await delete_flow(client, entity_id)
            
            if success:
                print()
                print("✅ Cascade deletion completed successfully!")
                return 0
            else:
                print()
                print("❌ Cascade deletion failed!")
                return 1
                
    except TAMSAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return 1
    except TAMSConnectionError as e:
        print(f"❌ Connection error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TAMS Cascade Delete Tool - Delete a source or flow with all dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This script will cascade delete and permanently remove data!

Examples:
  # Delete source with confirmation prompt
  %(prog)s abc-123 --server http://localhost:8000 --username admin --password secret
  
  # Delete flow with confirmation prompt
  %(prog)s flow-456 --server http://localhost:8000 --username admin --password secret
  
  # Delete with auto-confirmation (skip prompt)
  %(prog)s abc-123 --server http://localhost:8000 --username admin --password secret --yes
  
  # Cleanup all empty sources and flows
  %(prog)s --cleanup-empty --server http://localhost:8000 --username admin --password secret
  
  # Cleanup empty with auto-confirmation
  %(prog)s --cleanup-empty --server http://localhost:8000 --username admin --password secret --yes
  
  # Using environment variables for credentials
  export TAMS_SERVER=http://localhost:8000
  export TAMS_USERNAME=admin
  export TAMS_PASSWORD=secret
  %(prog)s abc-123 --yes
  %(prog)s --cleanup-empty --yes
        """
    )
    
    parser.add_argument(
        "id",
        type=str,
        nargs="?",
        default=None,
        help="Source or Flow ID to delete (optional if --cleanup-empty is used)"
    )
    
    parser.add_argument(
        "--server",
        type=str,
        default=os.environ.get("TAMS_SERVER", "http://localhost:8000"),
        help="TAMS server URL (default: $TAMS_SERVER or http://localhost:8000)"
    )
    
    parser.add_argument(
        "--username",
        type=str,
        default=os.environ.get("TAMS_USERNAME"),
        help="Username for authentication (default: $TAMS_USERNAME)"
    )
    
    parser.add_argument(
        "--password",
        type=str,
        default=os.environ.get("TAMS_PASSWORD"),
        help="Password for authentication (default: $TAMS_PASSWORD)"
    )
    
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt and auto-confirm deletion (dangerous!)"
    )
    
    parser.add_argument(
        "--cleanup-empty",
        action="store_true",
        help="Find and delete all sources and flows with no segments"
    )
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()
    
    # Validate required arguments
    if not args.username:
        print("❌ Error: Username is required (use --username or set TAMS_USERNAME)", file=sys.stderr)
        return 1
    
    if not args.password:
        print("❌ Error: Password is required (use --password or set TAMS_PASSWORD)", file=sys.stderr)
        return 1
    
    # Check if cleanup-empty mode
    if args.cleanup_empty:
        print("🚀 TAMS Cleanup Empty Sources and Flows")
        print("=" * 80)
        print()
        return await cleanup_empty(
            server_url=args.server,
            username=args.username,
            password=args.password,
            auto_confirm=args.yes
        )
    
    # Validate ID is provided for normal delete mode
    if not args.id:
        print("❌ Error: Either provide an ID to delete or use --cleanup-empty", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print("  Delete by ID: python cascade_delete.py <id> [options]", file=sys.stderr)
        print("  Cleanup empty: python cascade_delete.py --cleanup-empty [options]", file=sys.stderr)
        print("\nUse --help for full usage information", file=sys.stderr)
        return 1
    
    print("🚀 TAMS Cascade Delete Tool")
    print("=" * 80)
    print()
    
    return await cascade_delete(
        entity_id=args.id,
        server_url=args.server,
        username=args.username,
        password=args.password,
        auto_confirm=args.yes
    )


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(1)

