"""
Main stream ingestor class.

Orchestrates the stream ingestion process: TAMS connection, source/flow creation,
and stream processing.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src" / "client"))

from vasttamsclient import TAMSClient
from .stream_processor import StreamProcessor

logger = logging.getLogger(__name__)


class StreamIngestor:
    """Main stream ingestor class."""
    
    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        chunk_duration: int = 30,
        chunk_format: str = "hls",
        loop_recorder_duration: int = 900,
        input_source: str = None,
        input_type: str = "stream",
        label: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[dict] = None
    ):
        """
        Initialize stream ingestor.
        
        Args:
            server_url: TAMS server URL
            username: TAMS username
            password: TAMS password
            chunk_duration: Duration of each chunk in seconds (default: 30)
            chunk_format: Chunk format - "hls" or "original" (default: "hls")
            loop_recorder_duration: Loop recorder duration in seconds - maximum duration to keep segments (default: 900 = 15 minutes)
            input_source: Streaming protocol URL (e.g., srt://, rtmp://, udp://, rtsp://, http://, etc.)
            input_type: Type of input (default: "stream" - any streaming protocol)
            label: Optional source/flow label
            description: Optional source description
        """
        if not input_source:
            raise ValueError("input_source is required (streaming protocol URL)")
        
        self.server_url = server_url
        self.username = username
        self.password = password
        self.chunk_duration = chunk_duration
        self.chunk_format = chunk_format
        self.loop_recorder_duration = loop_recorder_duration
        self.input_source = input_source
        self.input_type = input_type
        self.label = label or "Stream Ingestor"
        self.description = description or "Live stream ingestion"
        self.tags = tags or {}
        
        self.client: Optional[TAMSClient] = None
        self.source: Optional[Any] = None
        self.flow: Optional[Any] = None
        self.stream_processor: Optional[StreamProcessor] = None
        self.running = False
        self.chunk_index = 0
        self._upload_tasks = set()
        
    async def __aenter__(self):
        """Async context manager entry."""
        try:
            logger.info(f"🔌 Connecting to TAMS server: {self.server_url}")
            self.client = TAMSClient(
                server_url=self.server_url,
                username=self.username,
                password=self.password,
                timeout=300,
                limit=100,
                limit_per_host=30,
                keepalive_timeout=60,
                api_version=None  # Use /api/tams/latest (default)
            )
            await self.client.__aenter__()
            logger.info(f"✅ Connected to TAMS server")
            
            # Create source and flow
            await self._setup_source_and_flow()
            
            return self
        except Exception as e:
            # Clean up client connection on error
            if self.client:
                try:
                    await self.client.__aexit__(None, None, None)
                except:
                    pass
            raise
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _setup_source_and_flow(self):
        """Create or get source and flow, set up loop_recorder_duration tag."""
        if self.client is None:
            raise RuntimeError("Client not initialized")
        
        # Determine codec and container based on chunk format
        if self.chunk_format == "hls":
            # HLS format: MPEG-TS with H.264/AAC
            codec = "video/h264"
            container = "video/mp2t"
        else:
            # Original format: will depend on input, but default to H.264/MP4
            codec = "video/h264"
            container = "video/mp4"
        
        # Default essence parameters for live stream (1920x1080, 30fps)
        # These can be overridden later if we detect different values from the stream
        essence_parameters = {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {
                "numerator": 30,
                "denominator": 1
            },
            "vfr": False  # Assume constant frame rate for live streams
        }
        
        # Try to find existing source by stream_input_source tag (the URL)
        logger.info(f"🔍 Looking for existing source with stream_input_source={self.input_source}...")
        existing_sources = await self.client.list_sources_by_tag(
            "stream_input_source",
            self.input_source
        )
        
        if existing_sources:
            # Reuse existing source
            self.source = existing_sources[0]
            logger.info(f"♻️  Reusing existing source: {self.source.id} (label: {self.source.label})")
            
            # Update ingest_started tag
            await self.source.set_tag("ingest_started", datetime.now().isoformat())
        else:
            # Create new source
            logger.info(f"➕ Creating new source...")
            self.source = self.client.TAMSSource(
                format="urn:x-nmos:format:video",
                label=self.label,
                description=self.description
            )
            await self.source._ensure_created()
            logger.info(f"✅ Created source: {self.source.id}")
            
            # Set source tags
            await self.source.set_tag("stream_input_type", self.input_type)
            await self.source.set_tag("stream_input_source", self.input_source)
            await self.source.set_tag("chunk_duration", str(self.chunk_duration))
            await self.source.set_tag("chunk_format", self.chunk_format)
            await self.source.set_tag("ingest_started", datetime.now().isoformat())
            
            # Set user-provided tags
            for key, value in self.tags.items():
                await self.source.set_tag(key, str(value))
        
        # Try to find existing flow with matching video specs
        logger.info(f"🔍 Looking for existing flow with matching specs (codec={codec}, container={container})...")
        existing_flows = await self.source.list_flows()
        
        # Find flow that matches codec, container, and essence_parameters
        matching_flow = None
        for flow in existing_flows:
            flow_codec = flow._data.get("codec")
            flow_container = flow._data.get("container")
            flow_essence = flow._data.get("essence_parameters", {})
            
            # Check if codec and container match
            if flow_codec == codec and flow_container == container:
                # Check if essence_parameters match
                if self._essence_parameters_match(flow_essence, essence_parameters):
                    matching_flow = flow
                    logger.info(f"♻️  Found matching flow: {flow.id}")
                    break
        
        if matching_flow:
            # Reuse existing flow
            self.flow = matching_flow
            logger.info(f"♻️  Reusing existing flow: {self.flow.id} (label: {self.flow.label})")
        else:
            # Create new flow with essence parameters
            logger.info(f"➕ Creating new flow...")
            self.flow = self.source.TAMSFlow(
                format="urn:x-nmos:format:video",
                codec=codec,
                container=container,
                label=f"{self.label} - Flow"
            )
            # Set essence parameters
            self.flow._data["essence_parameters"] = essence_parameters
            
            await self.flow._ensure_created()
            logger.info(f"✅ Created flow: {self.flow.id}")
            
            # Set flow tags
            await self.flow.set_tag("chunk_duration", str(self.chunk_duration))
            await self.flow.set_tag("chunk_format", self.chunk_format)
            await self.flow.set_tag("stream_input_type", self.input_type)
            
            # Set user-provided tags
            for key, value in self.tags.items():
                await self.flow.set_tag(key, str(value))
        
        # Set/update loop_recorder_duration tag (always update in case it changed)
        logger.info(f"🏷️  Setting loop_recorder_duration tag to {self.loop_recorder_duration}s ({self.loop_recorder_duration/60:.1f} minutes)")
        await self.flow.set_tag("loop_recorder_duration", str(self.loop_recorder_duration))
    
    def _essence_parameters_match(self, flow_essence: dict, new_essence: dict) -> bool:
        """Check if essence parameters match (allowing for minor differences)."""
        # Compare key parameters
        keys_to_check = ["frame_width", "frame_height", "vfr"]
        for key in keys_to_check:
            if flow_essence.get(key) != new_essence.get(key):
                return False
        
        # Compare frame_rate
        flow_rate = flow_essence.get("frame_rate", {})
        new_rate = new_essence.get("frame_rate", {})
        if flow_rate.get("numerator") != new_rate.get("numerator") or \
           flow_rate.get("denominator") != new_rate.get("denominator"):
            return False
        
        return True
    
    async def _upload_chunk(self, chunk_path: Path, chunk_idx: int) -> asyncio.Task:
        """Upload a chunk to TAMS flow."""
        async def upload():
            try:
                logger.info(f"🚀 Starting upload for chunk {chunk_idx} ({chunk_path.name})")
                
                # Verify file exists and has data
                if not chunk_path.exists():
                    raise FileNotFoundError(f"Chunk file does not exist: {chunk_path}")
                
                file_size = chunk_path.stat().st_size
                if file_size == 0:
                    raise ValueError(f"Chunk file is empty: {chunk_path}")
                
                logger.debug(f"Chunk {chunk_idx} file size: {file_size} bytes")
                
                # Calculate timerange for chunk
                start_seconds = chunk_idx * self.chunk_duration
                end_seconds = start_seconds + self.chunk_duration
                
                timerange = {
                    "value": f"[{start_seconds}:0_{end_seconds}:0)"
                }
                
                logger.info(f"📤 Uploading chunk {chunk_idx} to flow {self.flow.id} (timerange: {timerange['value']})")
                
                if self.flow is None:
                    raise RuntimeError("Flow not initialized")
                
                # Upload chunk with timeout
                logger.debug(f"Calling flow.add_segment for chunk {chunk_idx}...")
                try:
                    segment = await asyncio.wait_for(
                        self.flow.add_segment(
                            file_path=str(chunk_path),
                            timerange=timerange,
                            auto_probe=False  # Don't probe chunks
                        ),
                        timeout=300  # 5 minute timeout for upload
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Upload of chunk {chunk_idx} timed out after 5 minutes")
                
                logger.info(f"✅ Uploaded chunk {chunk_idx} (segment ID: {segment.id}, object ID: {segment.object_id})")
                
                # Clean up chunk file after successful upload
                try:
                    chunk_path.unlink()
                    logger.debug(f"🗑️  Deleted chunk file: {chunk_path.name}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to delete chunk file {chunk_path.name}: {e}")
                
                return segment
                
            except Exception as e:
                logger.error(f"❌ Failed to upload chunk {chunk_idx}: {e}", exc_info=True)
                # Don't re-raise - let the task complete with exception so callback can log it
                raise
        
        task = asyncio.create_task(upload())
        self._upload_tasks.add(task)
        task.add_done_callback(self._upload_tasks.discard)
        return task
    
    async def start(self):
        """Start stream ingestion."""
        if self.running:
            logger.warning("Stream ingestor already running")
            return
        
        logger.info("🚀 Starting stream ingestion...")
        self.running = True
        
        # Create stream processor
        self.stream_processor = StreamProcessor(
            input_source=self.input_source,
            input_type=self.input_type,
            chunk_duration=self.chunk_duration,
            chunk_format=self.chunk_format,
            upload_callback=self._upload_chunk
        )
        
        # Start stream processor
        await self.stream_processor.start()
        
        logger.info("✅ Stream ingestion started")
        
        # Wait for stream processor to finish (or until interrupted)
        # Use short sleeps to allow signal handling
        try:
            while self.running and self.stream_processor.running:
                await asyncio.sleep(0.5)  # Shorter sleep for more responsive signal handling
        except KeyboardInterrupt:
            # KeyboardInterrupt will be handled by the CLI, just stop running
            logger.debug("KeyboardInterrupt received in start() loop")
            self.running = False
            raise  # Re-raise to let CLI handle it
    
    async def stop(self):
        """Stop stream ingestion."""
        if not self.running and not self.stream_processor:
            return
        
        logger.info("🛑 Stopping stream ingestion...")
        self.running = False
        
        # Stop stream processor first (kills FFmpeg subprocess)
        if self.stream_processor:
            try:
                await asyncio.wait_for(self.stream_processor.stop(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️  Timeout stopping stream processor, forcing shutdown...")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping stream processor: {e}")
        
        # Wait for pending uploads to complete (with shorter timeout for shutdown)
        if self._upload_tasks:
            pending_count = len(self._upload_tasks)
            logger.info(f"⏳ Waiting for {pending_count} pending upload(s) to complete...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._upload_tasks, return_exceptions=True),
                    timeout=10.0  # Shorter timeout for shutdown
                )
                logger.info(f"✅ All {pending_count} upload(s) completed")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  Timeout waiting for uploads ({pending_count} still pending), continuing shutdown...")
                # Cancel remaining upload tasks
                for task in self._upload_tasks:
                    if not task.done():
                        task.cancel()
            except Exception as e:
                logger.warning(f"⚠️  Error waiting for uploads: {e}")
        
        # Update source tags (with timeout)
        if self.source:
            try:
                await asyncio.wait_for(
                    self.source.set_tag("ingest_stopped", datetime.now().isoformat()),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.debug("Timeout updating source tags, continuing shutdown...")
            except Exception as e:
                logger.debug(f"Failed to update source tags: {e}")
        
        # Close TAMS client connection (with timeout)
        if self.client:
            try:
                logger.debug("Closing TAMS client connection...")
                await asyncio.wait_for(self.client.close(wait_timeout=5.0), timeout=10.0)
                logger.debug("TAMS client connection closed")
            except asyncio.TimeoutError:
                logger.warning("⚠️  Timeout closing TAMS client, continuing shutdown...")
            except Exception as e:
                logger.warning(f"⚠️  Error closing TAMS client: {e}")
        
        logger.info("✅ Stream ingestion stopped")

