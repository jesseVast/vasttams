"""
Stream processor for capturing and chunking live video streams.

Handles OSX camera and SRT stream inputs, chunks them using jthaloor-ffmpeg,
and uploads chunks to TAMS.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional, Callable, Any
import sys

# Import jthaloor-ffmpeg components
try:
    from jthaloor.ffmpeg.processor import VideoProcessor
    from jthaloor.ffmpeg.models import VideoSource
    from jthaloor.ffmpeg.outputs import ChunkOutput, OutputChain, BaseOutput
    from jthaloor.ffmpeg.config import VideoProcessorConfig
    import ffmpeg
    JTHALOOR_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"jthaloor-ffmpeg not available: {e}")
    logger.error("Please install jthaloor-ffmpeg from ~/Developer/gitlab/jthaloor-ffmpeg")
    JTHALOOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class LiveStreamChunkOutput(ChunkOutput):
    """
    Custom ChunkOutput for live streams that adds segment_list_flags live.
    
    This ensures FFmpeg writes chunks incrementally as they're created,
    rather than waiting until the stream ends.
    """
    
    def __init__(self, *args, framerate: Optional[int] = None, **kwargs):
        """Initialize with optional framerate for GOP size calculation."""
        super().__init__(*args, **kwargs)
        self.framerate = framerate
    
    def build_stream(self, input_stream: ffmpeg.Stream) -> ffmpeg.Stream:
        """
        Build chunk output stream with live streaming support.
        
        Adds segment_list_flags live for live streams to ensure chunks
        are written incrementally.
        """
        self.ensure_output_directory()
        
        # Get chunk segments based on mode
        segments = self._get_chunk_segments()
        
        # If no segments (duration mode or fallback), use standard segment muxer
        if not segments:
            output_pattern = str(Path(self.output_path) / self.filename_template.format(chunk_id='%03d'))
            
            # Build output with segment options and timestamp metadata
            # CRITICAL: For live streams, we need segment_format to ensure proper chunking
            # Without it, FFmpeg may create one continuously growing file
            output_options = {
                'vcodec': self.vcodec,
                'acodec': self.acodec,
                'preset': self.preset,
                'segment_time': self.duration,  # Duration of each chunk in seconds
                'f': 'segment',
                'segment_format': self.format,  # CRITICAL: Explicitly set segment format (mpegts, mp4, etc.)
                'reset_timestamps': 1,
                'map': '0',  # Include all streams
                'segment_list_flags': 'live',  # CRITICAL: Write chunks incrementally for live streams
                'segment_list_size': 0,  # Keep all chunks in list (0 = unlimited)
            }
            
            # CRITICAL: For proper chunking, we need to control GOP size to align keyframes with segment boundaries
            # Set GOP size to match segment duration (e.g., 5s * 30fps = 150 frames for 5-second chunks at 30fps)
            # This ensures keyframes align with segment boundaries for clean cuts
            # Only set if we're encoding (not copying codecs)
            if self.vcodec != 'copy':
                # Use provided framerate or default to 30fps
                fps = self.framerate if self.framerate else 30
                gop_size = int(self.duration * fps)
                output_options['g'] = gop_size  # GOP size in frames
                output_options['sc_threshold'] = 0  # Disable scene change detection for consistent GOP
                # Force keyframes at segment boundaries for reliable chunking
                # This ensures segments start at keyframes even if GOP size doesn't perfectly align
                output_options['force_key_frames'] = f"expr:gte(t,n_forced*{self.duration})"
                logger.debug(f"LiveStreamChunkOutput: Setting GOP size to {gop_size} frames (for {self.duration}s chunks at {fps}fps)")
                logger.debug(f"LiveStreamChunkOutput: Forcing keyframes every {self.duration}s")
            
            # CRITICAL: For live streams (especially SRT), we need to prevent FFmpeg from exiting
            # Add options to keep the stream alive and continue creating segments
            # Without these, FFmpeg may exit after the first segment
            output_options['fflags'] = '+genpts'  # Generate presentation timestamps
            output_options['avoid_negative_ts'] = 'make_zero'  # Handle timestamp issues
            # Don't exit on error - keep trying to process the stream
            # This is especially important for SRT streams that may have temporary connection issues
            
            # Add timestamp metadata if requested
            if self.include_timestamps:
                output_options['metadata'] = 'title=Chunk %03d'
                output_options['segment_list'] = str(Path(self.output_path) / 'chunks.txt')
                output_options['segment_list_type'] = 'flat'
            
            logger.debug(f"LiveStreamChunkOutput: Using segment_list_flags=live for incremental chunk writing")
            logger.debug(f"LiveStreamChunkOutput: segment_time={self.duration}s, segment_format={self.format}")
            logger.debug(f"LiveStreamChunkOutput: output_pattern={output_pattern}")
            logger.debug(f"LiveStreamChunkOutput: output_options keys: {list(output_options.keys())}")
            return input_stream.output(output_pattern, **output_options)  # type: ignore
        
        # For marker/metadata-based chunking, use parent implementation
        return super().build_stream(input_stream)


class StreamProcessor:
    """Processes live video streams, chunking and uploading to TAMS."""
    
    def __init__(
        self,
        input_source: str,
        input_type: str,
        chunk_duration: int,
        chunk_format: str,
        upload_callback: Callable[[Path, int], asyncio.Task],
        output_dir: Optional[str] = None
    ):
        """
        Initialize stream processor.
        
        Args:
            input_source: Streaming protocol URL (e.g., srt://, rtmp://, udp://, rtsp://, http://, etc.)
            input_type: Type of input (default: "stream" - any streaming protocol)
            chunk_duration: Duration of each chunk in seconds
            chunk_format: Output format ("hls" or "original")
            upload_callback: Async callback function(chunk_path, chunk_index) -> Task
            output_dir: Optional output directory for chunks (default: temp directory)
        """
        if not JTHALOOR_AVAILABLE:
            raise ImportError("jthaloor-ffmpeg module is not available. Please install it.")
        
        self.input_source = input_source
        self.input_type = input_type
        self.chunk_duration = chunk_duration
        self.chunk_format = chunk_format
        self.upload_callback = upload_callback
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="tams_stream_chunks_")
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        self.processor: Optional[VideoProcessor] = None
        self.job_id: Optional[str] = None
        self.running = False
        self.chunk_index = 0
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Determine output format and codecs based on chunk_format
        if chunk_format == "hls":
            self.file_ext = ".ts"
            self.output_format = "mpegts"
            self.vcodec = "libx264"  # H.264 for HLS compatibility
            self.acodec = "aac"  # AAC for HLS compatibility
            logger.info("Stream processor configured for HLS format (MPEG-TS with H.264/AAC)")
        else:
            # For MP4 output with live streams (camera/SRT), we must encode
            # Raw video from cameras cannot be copied directly into MP4 container
            self.file_ext = ".mp4"
            self.output_format = "mp4"
            self.vcodec = "libx264"  # H.264 for MP4 compatibility (must encode, can't copy rawvideo)
            self.acodec = "aac"  # AAC for MP4 compatibility (must encode, can't copy raw audio)
            logger.info("Stream processor configured for MP4 format (H.264/AAC encoding)")
            logger.info("  Note: Live streams require encoding (rawvideo not supported in MP4)")
        
        # Generate chunk filename template
        self.chunk_template = f"stream_chunk_{{chunk_id}}{self.file_ext}"
    
    def _build_input_url(self) -> str:
        """Build the input URL for ffmpeg based on input type."""
        # For streaming protocols, just return the URL as-is
        # FFmpeg will auto-detect the protocol from the URL format
        return self.input_source
    
    async def start(self):
        """Start processing the stream."""
        if self.running:
            logger.warning("Stream processor already running")
            return
        
        logger.info(f"Starting stream processor (input: {self.input_type}, source: {self.input_source})")
        
        try:
            # Create VideoProcessor
            config = VideoProcessorConfig()
            self.processor = VideoProcessor(config=config)
            await self.processor.start()
            
            # Build input URL
            input_url = self._build_input_url()
            logger.info(f"Using input URL: {input_url}")
            
            # Detect if this is an SRT stream
            is_srt = input_url.startswith('srt://')
            
            # For SRT streams, add input options to keep connection alive and handle reconnection
            # This prevents FFmpeg from exiting after the first segment
            input_options = {}
            if is_srt:
                # SRT-specific options to keep connection alive
                input_options = {
                    'reconnect': '1',  # Enable reconnection
                    'reconnect_at_eof': '1',  # Reconnect even if stream seems to end
                    'reconnect_streamed': '1',  # Reconnect for streamed inputs
                    'reconnect_delay_max': '2',  # Max delay between reconnection attempts (seconds)
                }
                logger.info("SRT stream detected - adding reconnection options to keep connection alive")
                logger.debug(f"SRT input options: {input_options}")
            
            # Create video source - let FFmpeg auto-detect protocol from URL
            source = VideoSource(url=input_url, protocol=None, input_options=input_options if input_options else None)
            logger.debug(f"VideoSource created: url={input_url}, protocol=auto-detect, input_options={input_options if input_options else 'None'}")
            
            # Create chunk output
            logger.info(f"Creating ChunkOutput:")
            logger.info(f"  - Template: {self.chunk_template}")
            logger.info(f"  - Output path: {self.output_path}")
            logger.info(f"  - Duration: {self.chunk_duration}s")
            logger.info(f"  - Format: {self.output_format}")
            logger.info(f"  - Video codec: {self.vcodec}")
            logger.info(f"  - Audio codec: {self.acodec}")
            
            # For live streams, we need to use segment_list_flags live
            # This makes FFmpeg write chunks incrementally as they're created
            # We'll create a custom ChunkOutput that adds this flag
            # Note: Framerate detection from stream metadata could be added here if needed
            framerate = None  # Will use default if not specified
            
            chunk_output = LiveStreamChunkOutput(
                filename_template=self.chunk_template,
                output_path=str(self.output_path),
                duration=self.chunk_duration,
                format=self.output_format,
                vcodec=self.vcodec,
                acodec=self.acodec,
                include_timestamps=True,
                chunk_mode="duration",
                framerate=framerate
            )
            
            # Create output chain
            output_chain = OutputChain([chunk_output])
            
            # Add stream to processor
            logger.info(f"Adding stream to processor...")
            logger.info(f"📋 Stream configuration:")
            logger.info(f"   Input URL: {input_url}")
            logger.info(f"   Input type: {self.input_type}")
            logger.info(f"   Protocol: {source.protocol if hasattr(source, 'protocol') else 'auto-detect'}")
            logger.info(f"   Output directory: {self.output_path}")
            logger.info(f"   Chunk template: {self.chunk_template}")
            logger.info(f"   Chunk duration: {self.chunk_duration}s")
            logger.info(f"   Output format: {self.output_format}")
            logger.info(f"   Video codec: {self.vcodec}")
            logger.info(f"   Audio codec: {self.acodec}")
            
            self.job_id = await self.processor.add_stream(source, output_chain)
            logger.info(f"Stream processing started (job_id: {self.job_id})")
            logger.info(f"Output directory: {self.output_path}")
            logger.info(f"Watch this directory for chunk files: {self.output_path}")
            logger.info(f"Expected chunk pattern: {self.chunk_template.replace('{chunk_id}', '*')}")
            
            # Wait a moment and check initial status
            await asyncio.sleep(2)
            try:
                initial_status = await self.processor.get_stream_status(self.job_id)
                if initial_status:
                    status_value = initial_status.status.value
                    logger.info(f"Initial stream status: {status_value}")
                    if hasattr(initial_status, 'error_message') and initial_status.error_message:
                        logger.error(f"❌ Initial status has error message: {initial_status.error_message}")
                    if hasattr(initial_status, 'outputs') and initial_status.outputs:
                        logger.info(f"Initial status has {len(initial_status.outputs)} output(s)")
                        for i, output in enumerate(initial_status.outputs):
                            logger.debug(f"  Output {i}: {output}")
                    
                    # Warn if status is not "processing" for a live stream
                    if status_value != "processing":
                        logger.warning(f"⚠️  Initial status is '{status_value}' - expected 'processing' for live stream")
                        if status_value == "completed":
                            logger.warning("   This might indicate FFmpeg stopped immediately after starting")
                        elif status_value == "failed":
                            logger.error("   Stream processing failed immediately - check FFmpeg logs")
                    
                    # Check if FFmpeg process is actually running
                    if hasattr(self.processor, '_active_processes'):
                        process = self.processor._active_processes.get(self.job_id)
                        if process:
                            if process.returncode is None:
                                logger.info(f"✅ FFmpeg process is running (PID: {process.pid})")
                            else:
                                logger.error(f"❌ FFmpeg process already finished with return code: {process.returncode}")
                        else:
                            logger.warning("⚠️  No FFmpeg process found in active_processes")
                else:
                    logger.warning("Could not get initial stream status")
                
                # Check if output directory exists and is writable
                if not self.output_path.exists():
                    logger.error(f"❌ Output directory does not exist: {self.output_path}")
                elif not self.output_path.is_dir():
                    logger.error(f"❌ Output path is not a directory: {self.output_path}")
                else:
                    logger.info(f"✅ Output directory exists and is writable: {self.output_path}")
                    
            except Exception as e:
                logger.warning(f"Error getting initial status: {e}", exc_info=True)
            
            self.running = True
            
            # Start monitoring for new chunks
            self._monitor_task = asyncio.create_task(self._monitor_chunks())
            
        except Exception as e:
            logger.error(f"Failed to start stream processor: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def _monitor_chunks(self):
        """Monitor for new chunk files and trigger uploads."""
        logger.info("Starting chunk monitor")
        logger.info(f"Monitoring directory: {self.output_path}")
        logger.info(f"Chunk template: {self.chunk_template}")
        logger.info(f"Looking for pattern: {self.chunk_template.replace('{chunk_id}', '*')}")
        logger.info(f"File extension: {self.file_ext}")
        
        # Log initial directory state
        initial_files = list(self.output_path.glob('*'))
        logger.info(f"Initial files in directory: {len(initial_files)}")
        if initial_files:
            logger.info(f"  Files: {[f.name for f in initial_files[:10]]}")
        
        seen_chunks = set()
        last_file_count = 0
        check_count = 0
        no_chunks_warning_count = 0
        
        try:
            while self.running:
                check_count += 1
                
                # Check for new chunk files
                pattern = self.chunk_template.replace('{chunk_id}', '*')
                chunk_files = sorted(self.output_path.glob(pattern))
                current_file_count = len(chunk_files)
                
                # Log directory contents periodically for debugging
                if check_count % 10 == 0:  # Every 10 checks (10 seconds)
                        all_files = list(self.output_path.glob('*'))
                        logger.info(f"📁 Directory check #{check_count}: Found {current_file_count} chunk files, {len(all_files)} total files")
                        if all_files:
                            logger.info(f"   Files in directory: {[f.name for f in all_files[:10]]}")  # Show first 10
                            # Show file sizes
                            for f in all_files[:5]:
                                try:
                                    size = f.stat().st_size
                                    logger.info(f"   {f.name}: {size} bytes")
                                except Exception:
                                    pass
                        else:
                            no_chunks_warning_count += 1
                            if no_chunks_warning_count >= 3:  # After 30 seconds with no files
                                logger.warning(f"   ⚠️  No files found in output directory after {check_count * 1}s: {self.output_path}")
                                # Check if FFmpeg process is still running
                                if self.processor and self.job_id:
                                    try:
                                        status = await self.processor.get_stream_status(self.job_id)
                                        if status:
                                            logger.warning(f"   Stream status: {status.status.value}")
                                        if hasattr(self.processor, '_active_processes'):
                                            process = self.processor._active_processes.get(self.job_id)
                                            if process:
                                                if process.returncode is None:
                                                    logger.warning(f"   FFmpeg process is running (PID: {process.pid}) but no files created")
                                                else:
                                                    logger.error(f"   FFmpeg process exited with code: {process.returncode}")
                                            else:
                                                logger.error(f"   No FFmpeg process found!")
                                    except Exception as e:
                                        logger.warning(f"   Error checking process status: {e}")
                        
                        # Also check for any .ts or .mp4 files (in case pattern doesn't match)
                        ts_files = list(self.output_path.glob('*.ts'))
                        mp4_files = list(self.output_path.glob('*.mp4'))
                        if ts_files or mp4_files:
                            logger.info(f"   Found {len(ts_files)} .ts files and {len(mp4_files)} .mp4 files")
                            if ts_files:
                                logger.info(f"   .ts files: {[f.name for f in ts_files[:5]]}")
                            if mp4_files:
                                logger.info(f"   .mp4 files: {[f.name for f in mp4_files[:5]]}")
                
                # Log if file count changed
                if current_file_count != last_file_count:
                    logger.info(f"📊 Chunk file count changed: {last_file_count} -> {current_file_count}")
                    if current_file_count > last_file_count:
                        new_files = [f for f in chunk_files if f not in seen_chunks]
                        logger.info(f"   New files detected: {[f.name for f in new_files]}")
                    elif current_file_count < last_file_count:
                        logger.warning(f"   ⚠️  Chunk file count decreased! This might indicate files were deleted.")
                    last_file_count = current_file_count
                
                # Log if no new chunks for a while (potential issue)
                if check_count > 20 and current_file_count == 1 and last_file_count == 1:
                    # Only one chunk after 20 seconds - might be stuck
                    if check_count % 10 == 0:  # Every 10 seconds
                        logger.warning(f"⚠️  Only 1 chunk detected after {check_count} seconds - stream might be stuck")
                        logger.warning(f"   Check if FFmpeg is still running and creating chunks")
                        logger.warning(f"   Output directory: {self.output_path}")
                        # Check file sizes to see if the chunk is still growing
                        if chunk_files:
                            chunk_size = chunk_files[0].stat().st_size
                            logger.warning(f"   Current chunk size: {chunk_size} bytes")
                
                for chunk_file in chunk_files:
                    if chunk_file not in seen_chunks and chunk_file.exists():
                        # New chunk detected
                        seen_chunks.add(chunk_file)
                        
                        # Extract chunk index from filename
                        chunk_idx = self._extract_chunk_index(chunk_file)
                        
                        logger.info(f"New chunk detected: {chunk_file.name} (index: {chunk_idx})")
                        
                        # Trigger upload callback
                        try:
                            # Wait for chunk file to have data
                            # For live streams, chunks are written incrementally
                            # Wait up to chunk_duration seconds for file to have data
                            max_wait = self.chunk_duration + 5  # Add 5s buffer
                            wait_interval = 0.5
                            waited = 0
                            file_size = 0
                            
                            while waited < max_wait:
                                if chunk_file.exists():
                                    file_size = chunk_file.stat().st_size
                                    if file_size > 0:
                                        # File has data, but wait a bit more to ensure it's complete
                                        # For live streams, we upload as soon as we have data
                                        # (chunk might still be growing, but that's OK)
                                        await asyncio.sleep(1.0)
                                        # Check if file size is stable (not growing rapidly)
                                        new_size = chunk_file.stat().st_size
                                        if abs(new_size - file_size) < file_size * 0.1:  # Less than 10% growth
                                            break
                                        file_size = new_size
                                await asyncio.sleep(wait_interval)
                                waited += wait_interval
                            
                            # Final size check
                            if not chunk_file.exists():
                                logger.warning(f"Chunk {chunk_idx} file disappeared, skipping upload")
                                continue
                                
                            file_size = chunk_file.stat().st_size
                            if file_size == 0:
                                logger.warning(f"Chunk {chunk_idx} file is still empty after {waited}s wait, skipping upload")
                                continue
                            
                            logger.info(f"📤 Creating upload task for chunk {chunk_idx} (size: {file_size} bytes, waited {waited:.1f}s)")
                            # upload_callback is async and returns a Task, so we need to await it to get the Task
                            upload_task = await self.upload_callback(chunk_file, chunk_idx)
                            # Don't await the task itself - let uploads happen in parallel
                            logger.debug(f"Upload task created for chunk {chunk_idx}")
                            
                            # Add a callback to log when upload completes
                            # Capture chunk_idx in closure to avoid issues with multiple chunks
                            def make_completion_callback(idx):
                                def log_upload_completion(task):
                                    try:
                                        if task.exception():
                                            logger.error(f"❌ Upload task for chunk {idx} failed: {task.exception()}")
                                        else:
                                            logger.info(f"✅ Upload task for chunk {idx} completed successfully")
                                    except Exception as e:
                                        logger.warning(f"Error checking upload task status for chunk {idx}: {e}")
                                return log_upload_completion
                            
                            upload_task.add_done_callback(make_completion_callback(chunk_idx))
                            
                        except Exception as e:
                            logger.error(f"Failed to create upload task for chunk {chunk_idx}: {e}", exc_info=True)
                
                # Check processor status
                if self.job_id and self.processor:
                    try:
                        status = await self.processor.get_stream_status(self.job_id)
                        if status:
                            status_value = status.status.value
                            if status_value == "failed":
                                error_msg = getattr(status, 'error_message', 'Unknown error')
                                logger.error(f"❌ Stream processing failed: {error_msg}")
                                logger.error(f"   Check output directory: {self.output_path}")
                                # For live streams, "failed" might mean FFmpeg stopped
                                # Log more details if available
                                if hasattr(status, 'outputs') and status.outputs:
                                    logger.error(f"   Outputs: {status.outputs}")
                                self.running = False
                                break
                            elif status_value == "completed":
                                # For live streams, "completed" shouldn't happen unless stream ended
                                logger.warning(f"⚠️  Stream processing marked as 'completed' - this is unexpected for live streams")
                                logger.warning(f"   This might indicate the input stream ended or FFmpeg stopped")
                                # Check for any remaining chunks
                                final_chunks = sorted(self.output_path.glob(pattern))
                                logger.info(f"   Final chunk count: {len(final_chunks)}")
                                # For live streams, we should keep running even if status says completed
                                # The stream might have temporarily stopped but could resume
                                # Only stop if we've been in "completed" state for a while
                                if not hasattr(self, '_completed_count'):
                                    self._completed_count = 0
                                self._completed_count += 1
                                if self._completed_count > 10:  # 10 seconds of "completed" status
                                    logger.error("   Stream has been 'completed' for 10+ seconds, stopping")
                                    self.running = False
                                    break
                                else:
                                    logger.debug(f"   Stream 'completed' status (count: {self._completed_count}/10), continuing to monitor...")
                            elif status_value == "processing":
                                # Reset completed count if we're processing again
                                if hasattr(self, '_completed_count'):
                                    self._completed_count = 0
                                # Log periodically that processing is ongoing
                                if check_count % 30 == 0:  # Every 30 seconds
                                    logger.debug(f"Stream processing ongoing (status: {status_value})")
                            else:
                                # Unknown status
                                logger.debug(f"Stream status: {status_value}")
                    except Exception as e:
                        logger.warning(f"Error checking stream status: {e}", exc_info=True)
                
                # Wait before next check
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.debug("Chunk monitor cancelled")
            self.running = False
        except KeyboardInterrupt:
            # KeyboardInterrupt will be handled by the CLI, just stop running
            logger.debug("KeyboardInterrupt received in chunk monitor")
            self.running = False
            raise  # Re-raise to let CLI handle it
        except Exception as e:
            logger.error(f"Error in chunk monitor: {e}", exc_info=True)
            self.running = False
    
    def _extract_chunk_index(self, chunk_path: Path) -> int:
        """Extract chunk index from filename."""
        try:
            # Extract number from filename like "stream_chunk_000.ts"
            name = chunk_path.stem
            if '_chunk_' in name:
                num_str = name.split('_chunk_')[-1]
                return int(num_str)
        except (ValueError, IndexError):
            pass
        # Fallback: use current chunk_index and increment
        idx = self.chunk_index
        self.chunk_index += 1
        return idx
    
    async def stop(self):
        """Stop processing the stream."""
        if not self.running and not self.processor:
            return
        
        logger.info("Stopping stream processor")
        self.running = False
        
        # Cancel monitor task first (with timeout)
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await asyncio.wait_for(self._monitor_task, timeout=2.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning("Monitor task did not cancel in time, continuing...")
        
        # Stop processor and kill FFmpeg process (with timeout)
        if self.processor:
            try:
                # If we have a job_id, try to remove the specific stream first
                if self.job_id:
                    try:
                        removed = await asyncio.wait_for(
                            self.processor.remove_stream(self.job_id),
                            timeout=5.0
                        )
                        if removed:
                            logger.info(f"Removed stream {self.job_id}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout removing stream {self.job_id}, forcing stop...")
                    except Exception as e:
                        logger.warning(f"Error removing stream {self.job_id}: {e}")
                
                # Stop the processor (will kill all remaining processes)
                await asyncio.wait_for(self.processor.stop(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout stopping processor, some processes may still be running")
            except Exception as e:
                logger.warning(f"Error stopping processor: {e}")
        
        logger.info("Stream processor stopped")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

