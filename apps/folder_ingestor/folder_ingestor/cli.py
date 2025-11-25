"""
CLI entry point for folder ingestor.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src" / "client"))

from .ingestor import FolderIngestor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_tags(tags_str: str) -> dict:
    """
    Parse tags from CLI string format.
    
    Supports both ':' and '=' as key-value separators.
    Format: 'key1:value1,key2=value2,key3:value with spaces'
    Values can contain spaces and will be preserved as-is.
    
    Args:
        tags_str: Comma-separated tags string
        
    Returns:
        Dictionary of tag key-value pairs
    """
    tags = {}
    if not tags_str:
        return tags
    
    # Split by comma to get individual tags
    tag_pairs = tags_str.split(',')
    
    for tag_pair in tag_pairs:
        tag_pair = tag_pair.strip()
        if not tag_pair:
            continue
        
        # Try to split by ':' first, then '=' if ':' not found
        if ':' in tag_pair:
            # Split by ':' - take first occurrence as separator
            parts = tag_pair.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
        elif '=' in tag_pair:
            # Split by '=' - take first occurrence as separator
            parts = tag_pair.split('=', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
        else:
            # No separator found, treat as key with empty value
            logger.warning(f"Tag '{tag_pair}' has no separator (':' or '='), skipping")
            continue
        
        if key:
            tags[key] = value
    
    return tags


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest files from a folder into TAMS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--folder",
        required=True,
        help="Path to folder to ingest"
    )
    parser.add_argument(
        "--format",
        help="Source format URN (e.g., urn:x-nmos:format:video). If not provided, will be auto-detected from folder contents."
    )
    parser.add_argument(
        "--label",
        help="Source label"
    )
    parser.add_argument(
        "--description",
        help="Source description"
    )
    parser.add_argument(
        "--tags",
        help="Comma-separated tags in format 'key1:value1,key2=value2'. Values can contain spaces. Both ':' and '=' are supported as separators."
    )
    parser.add_argument(
        "--config",
        help="Path to JSON config file"
    )
    parser.add_argument(
        "--server-url",
        help="TAMS server URL"
    )
    parser.add_argument(
        "--username",
        help="TAMS username"
    )
    parser.add_argument(
        "--password",
        help="TAMS password"
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=30,
        help="Chunk duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run through the process without creating anything in TAMS"
    )
    parser.add_argument(
        "--max-parallel-uploads",
        type=int,
        default=4,
        help="Maximum number of parallel uploads (default: 4)"
    )
    parser.add_argument(
        "--no-chunking",
        action="store_true",
        help="Upload files as-is without chunking (default: False). Overrides metadata-based chunking."
    )
    parser.add_argument(
        "--use-metadata",
        action="store_true",
        help="Use metadata files for marker-based chunking if available (default: False). If not set, uses duration-based chunking."
    )
    parser.add_argument(
        "--include-originals",
        action="store_true",
        help="In addition to chunks, also upload original files to a separate flow (default: False). Only applies when chunking is enabled."
    )
    parser.add_argument(
        "--chunk-format",
        choices=["original", "mp4", "hls"],
        default="original",
        help="Chunk format: 'original' (copy codecs, MP4), 'mp4' (transcode to H.264/AAC MP4), or 'hls' (HLS-compatible TS with H.264/AAC) (default: original)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config file if provided
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Get settings from args or config
    server_url = args.server_url or config.get("server_url") or "http://localhost:8000"
    username = args.username or config.get("username") or "admin"
    password = args.password or config.get("password") or "admin"
    chunk_duration = args.chunk_duration or config.get("chunk_duration", 30)
    recursive = args.recursive or config.get("recursive", False)
    dry_run = args.dry_run or config.get("dry_run", False)
    max_parallel_uploads = args.max_parallel_uploads or config.get("max_parallel_uploads", 4)
    no_chunking = args.no_chunking or config.get("no_chunking", False)
    use_metadata = args.use_metadata or config.get("use_metadata", False)
    include_originals = args.include_originals or config.get("include_originals", False)
    chunk_format = args.chunk_format or config.get("chunk_format", "original")
    # Format can be None (will be auto-detected)
    source_format = args.format or config.get("format") or None
    tags_str = args.tags or config.get("tags")
    
    # Parse tags if provided
    tags = {}
    if tags_str:
        tags = parse_tags(tags_str)
    
    try:
        async with FolderIngestor(
            server_url=server_url,
            username=username,
            password=password,
            chunk_duration=chunk_duration,
            recursive=recursive,
            dry_run=dry_run,
            max_parallel_uploads=max_parallel_uploads,
            no_chunking=no_chunking,
            use_metadata=use_metadata,
            include_originals=include_originals,
            chunk_format=chunk_format
        ) as ingestor:
            source_id, flows_dict, multi_flow_id = await ingestor.ingest_folder(
                folder_path=args.folder,
                source_format=source_format,
                source_label=args.label,
                source_description=args.description,
                tags=tags
            )
            print(f"✅ Ingestion completed successfully!")
            print(f"   Source ID: {source_id}")
            print(f"   Flows: {len(flows_dict)}")
            for media_type, flow_id in flows_dict.items():
                print(f"      - {media_type}: {flow_id}")
            if multi_flow_id:
                print(f"   Multi-flow ID: {multi_flow_id}")
        
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

