"""
CLI entry point for stream ingestor.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src" / "client"))

from .ingestor import StreamIngestor

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
        description="Ingest live video streams (SRT) into TAMS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--srt-url",
        required=True,
        help="SRT stream URL (e.g., srt://host:port?params)"
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=30,
        help="Chunk duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--chunk-format",
        choices=["original", "hls"],
        default="hls",
        help="Chunk format: 'original' (MP4 with H.264/AAC) or 'hls' (HLS-compatible TS with H.264/AAC) (default: hls). Note: Live streams require encoding, so 'original' uses H.264/AAC encoding for MP4."
    )
    parser.add_argument(
        "--loop-recorder-duration",
        type=int,
        default=900,
        help="Loop recorder duration in seconds - maximum duration to keep segments (default: 900 = 15 minutes)"
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
        "--label",
        help="Source/flow label"
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
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        # Enable DEBUG logging for all modules
        logging.getLogger().setLevel(logging.DEBUG)
        # Also enable debug for vasttamsclient
        logging.getLogger('vasttamsclient').setLevel(logging.DEBUG)
        # And jthaloor-ffmpeg
        logging.getLogger('jthaloor').setLevel(logging.DEBUG)
        logger.info("🔍 Verbose logging enabled")
    
    # Load config file if provided
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Get settings from args or config
    server_url = args.server_url or config.get("server_url") or "http://localhost:8000"
    username = args.username or config.get("username") or "admin"
    password = args.password or config.get("password") or "admin"
    chunk_duration = args.chunk_duration if args.chunk_duration is not None else config.get("chunk_duration", 30)
    chunk_format = args.chunk_format or config.get("chunk_format", "hls")
    loop_recorder_duration = args.loop_recorder_duration if args.loop_recorder_duration is not None else config.get("loop_recorder_duration", 900)
    srt_url = args.srt_url or config.get("srt_url")
    label = args.label or config.get("label") or "Stream Ingestor"
    description = args.description or config.get("description") or "Live stream ingestion"
    tags_str = args.tags or config.get("tags")
    
    # Parse tags if provided
    tags = {}
    if tags_str:
        tags = parse_tags(tags_str)
    
    # Validate SRT URL is provided
    if not srt_url:
        logger.error("❌ SRT URL is required")
        logger.error("   → Use --srt-url to specify a stream URL")
        logger.error("   → Example: --srt-url srt://stream.example.com:5000")
        sys.exit(1)
    
    input_source = srt_url
    input_type = "srt"
    logger.info(f"📺 Input source: SRT stream ({srt_url})")
    
    # Display configuration
    logger.info("⚙️  Configuration:")
    logger.info(f"   → TAMS Server: {server_url}")
    logger.info(f"   → Username: {username}")
    logger.info(f"   → Chunk Duration: {chunk_duration}s")
    logger.info(f"   → Chunk Format: {chunk_format.upper()}")
    logger.info(f"   → Loop Recorder Duration: {loop_recorder_duration}s ({loop_recorder_duration/60:.1f} minutes)")
    logger.info(f"   → Label: {label}")
    
    if args.verbose:
        logger.debug("📋 Detailed configuration:")
        logger.debug(f"   → Description: {description}")
        logger.debug(f"   → Input type: {input_type}")
        logger.debug(f"   → Config file: {args.config or 'None'}")
    
    try:
        async with StreamIngestor(
            server_url=server_url,
            username=username,
            password=password,
            chunk_duration=chunk_duration,
            chunk_format=chunk_format,
            loop_recorder_duration=loop_recorder_duration,
            input_source=input_source,
            input_type=input_type,
            label=label,
            description=description,
            tags=tags
        ) as ingestor:
            # Set up signal handlers for clean shutdown using asyncio
            shutdown_event = asyncio.Event()
            shutdown_requested = False
            
            def signal_handler():
                """Handle shutdown signals."""
                nonlocal shutdown_requested
                if not shutdown_requested:
                    shutdown_requested = True
                    logger.info("\n\n🛑 Shutdown signal received, shutting down gracefully...")
                    shutdown_event.set()
            
            # Register signal handlers using asyncio (works better with event loop)
            signal_handlers_registered = False
            if sys.platform != 'win32':
                # On Unix systems, use asyncio signal handlers
                try:
                    loop = asyncio.get_running_loop()
                    loop.add_signal_handler(signal.SIGINT, signal_handler)
                    loop.add_signal_handler(signal.SIGTERM, signal_handler)
                    signal_handlers_registered = True
                except (RuntimeError, NotImplementedError):
                    # Fallback to regular signal handlers if asyncio handlers not available
                    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
                    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
            else:
                # On Windows, use regular signal handlers
                signal.signal(signal.SIGINT, lambda s, f: signal_handler())
                signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
            
            try:
                # Start ingestion
                await ingestor.start()
                
                # Wait for shutdown signal or completion with timeout to allow signal checking
                try:
                    # Use a loop with short sleeps to allow signal handling
                    while not shutdown_event.is_set() and ingestor.running:
                        try:
                            await asyncio.wait_for(shutdown_event.wait(), timeout=0.5)
                            break
                        except asyncio.TimeoutError:
                            # Check if ingestor is still running
                            if not ingestor.running:
                                break
                            continue
                except KeyboardInterrupt:
                    # Also handle KeyboardInterrupt (Ctrl+C) as fallback
                    if not shutdown_requested:
                        shutdown_requested = True
                        logger.info("\n\n🛑 Interrupt received, shutting down gracefully...")
                
                # Clean shutdown
                logger.info("Initiating shutdown...")
                await ingestor.stop()
                logger.info("✅ Shutdown complete")
                sys.exit(0)
            except KeyboardInterrupt:
                # Handle Ctrl+C during start or wait
                if not shutdown_requested:
                    shutdown_requested = True
                    logger.info("\n\n🛑 Interrupt received, shutting down gracefully...")
                    try:
                        await ingestor.stop()
                    except Exception as e:
                        logger.warning(f"Error during shutdown: {e}")
                    logger.info("✅ Shutdown complete")
                    sys.exit(0)
            finally:
                # Remove signal handlers
                if signal_handlers_registered and sys.platform != 'win32':
                    try:
                        loop = asyncio.get_running_loop()
                        loop.remove_signal_handler(signal.SIGINT)
                        loop.remove_signal_handler(signal.SIGTERM)
                    except (RuntimeError, NotImplementedError):
                        pass
                
                # Ensure cleanup even if something goes wrong
                if shutdown_requested:
                    try:
                        await ingestor.stop()
                    except Exception as e:
                        logger.warning(f"Error during final cleanup: {e}")
        
    except KeyboardInterrupt:
        # If KeyboardInterrupt happens during setup, handle it cleanly
        logger.info("\n\n🛑 Interrupt received, shutting down...")
        sys.exit(0)
    except Exception as e:
        # Don't show traceback for KeyboardInterrupt (should be caught above, but just in case)
        if isinstance(e, KeyboardInterrupt):
            logger.info("\n\n🛑 Interrupt received, shutting down...")
            sys.exit(0)
        # Provide user-friendly error messages
        error_str = str(e).lower()
        
        if "authentication failed" in error_str or "invalid username or password" in error_str:
            logger.error("❌ Authentication failed")
            logger.error("   → Please check your username and password")
            logger.error(f"   → Server: {server_url}")
            logger.error(f"   → Username: {username}")
            if args.verbose:
                logger.error(f"   → Details: {e}")
        elif "validation error" in error_str or "field required" in error_str:
            logger.error("❌ Validation error")
            logger.error("   → TAMS server rejected the request")
            logger.error(f"   → Server: {server_url}")
            if args.verbose:
                logger.error(f"   → Details: {e}")
        elif "connection" in error_str and ("refused" in error_str or "failed" in error_str):
            logger.error("❌ Connection failed")
            logger.error("   → Cannot connect to TAMS server")
            logger.error(f"   → Server: {server_url}")
            logger.error("   → Make sure the TAMS server is running")
            if args.verbose:
                logger.error(f"   → Details: {e}")
        elif "jthaloor" in error_str or "import" in error_str:
            logger.error("❌ Missing dependency")
            logger.error("   → jthaloor-ffmpeg module not found")
            logger.error("   → Install with: pip install -e ~/Developer/gitlab/jthaloor-ffmpeg")
            if args.verbose:
                logger.error(f"   → Details: {e}")
        elif "ffmpeg" in error_str or "ffprobe" in error_str:
            logger.error("❌ FFmpeg not found")
            logger.error("   → FFmpeg is required but not installed or not in PATH")
            logger.error("   → Install FFmpeg: brew install ffmpeg (on macOS)")
            if args.verbose:
                logger.error(f"   → Details: {e}")
        else:
            logger.error(f"❌ Stream ingestion failed: {e}")
            if not args.verbose:
                logger.error("   → Run with --verbose for more details")
            else:
                import traceback
                logger.error("\n" + traceback.format_exc())
        
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

