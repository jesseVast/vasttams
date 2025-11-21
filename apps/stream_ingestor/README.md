# Stream Ingestor

Ingests live video streams from supported protocols (SRT, RTMP, UDP, RTSP, HTTP, etc.) into TAMS. The stream is continuously captured, chunked into time-based segments, and uploaded to TAMS. The flow is automatically configured with loop recording (900 seconds) to maintain a rolling buffer.

## Features

- **Live Stream Capture**: Supports multiple streaming protocols (SRT, RTMP, UDP, RTSP, HTTP/HTTPS, etc.)
- **Source and Flow Reuse**: Automatically reuses existing sources and flows when the URL and video specs match
- **Configurable Chunking**: Chunks stream into configurable duration segments (default: 30 seconds)
- **Chunk Format Options**: Supports HLS format (default, MPEG-TS with H.264/AAC) or original format (MP4 with H.264/AAC encoding)
- **Loop Recording**: Automatically configures `loop_recorder_duration` tag (900 seconds) on the flow
- **Continuous Processing**: Runs continuously, uploading chunks as they're created
- **Graceful Shutdown**: Handles Ctrl+C and waits for pending uploads to complete

## Prerequisites

1. **Python 3.12+**
2. **FFmpeg** (with `ffprobe`) installed and in PATH
3. **TAMS Server** running and accessible
4. **TAMS Client Library** installed:
   ```bash
   pip install -e ../../src/client
   ```
5. **jthaloor-ffmpeg** module installed:
   ```bash
   pip install -e ~/Developer/gitlab/jthaloor-ffmpeg
   ```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e ../../src/client
   pip install -e ~/Developer/gitlab/jthaloor-ffmpeg
   ```

2. Ensure FFmpeg is installed:
   ```bash
   ffmpeg -version
   ffprobe -version
   ```

## Usage

### Basic Usage

```bash
python stream_ingestor.py \
  --srt-url srt://stream.example.com:5000 \
  --server-url http://localhost:8000 \
  --username admin \
  --password admin
```

### Supported Protocols

The stream_ingestor accepts any streaming protocol URL that FFmpeg supports:

- **SRT**: `srt://host:port?mode=caller` or `srt://host:port?mode=listener`
- **RTMP**: `rtmp://host:port/path`
- **UDP**: `udp://host:port`
- **RTSP**: `rtsp://host:port/path`
- **HTTP/HTTPS**: `http://host/path/stream.m3u8` (HLS, DASH, etc.)

FFmpeg will auto-detect the protocol from the URL format.

### With Configuration File

1. Copy `config.json.example` to `config.json`:
   ```bash
   cp config.json.example config.json
   ```

2. Edit `config.json` with your settings

3. Run with config file:
   ```bash
   python stream_ingestor.py \
     --config config.json \
     --srt-url srt://stream.example.com:5000
   ```

### Command Line Options

- `--srt-url` (required): Streaming protocol URL (e.g., `srt://host:port`, `udp://host:port`, `rtmp://host/path`, etc.)
- `--loop-recorder-duration` (optional): Loop recorder duration in seconds - maximum duration to keep segments (default: 900 = 15 minutes)
- `--chunk-duration` (optional): Chunk duration in seconds (default: 30)
- `--chunk-format` (optional): Chunk format - "original" (MP4 with H.264/AAC encoding) or "hls" (HLS-compatible TS with H.264/AAC) (default: hls)
- `--server-url` (optional): TAMS server URL (default: `http://localhost:8000`). The client automatically uses `/api/tams/latest` for all API calls.
- `--username` (optional): TAMS username (default: `admin`)
- `--password` (optional): TAMS password (default: `admin`)
- `--label` (optional): Source/flow label (default: "Stream Ingestor")
- `--description` (optional): Source description (default: "Live stream ingestion")
- `--config` (optional): Path to JSON config file
- `--verbose` (optional): Enable verbose logging (DEBUG level for detailed output, including vasttamsclient and jthaloor-ffmpeg modules)

### Configuration File Format

```json
{
  "server_url": "http://localhost:8000",
  "username": "admin",
  "password": "admin",
  "srt_url": "srt://stream.example.com:5000",
  "chunk_duration": 30,
  "chunk_format": "hls",
  "loop_recorder_duration": 900,
  "label": "Stream Ingestor",
  "description": "Live stream ingestion"
}
```

**Note**: The `server_url` should be the base server URL (e.g., `http://localhost:8000`). The client automatically appends `/api/tams/latest` to all API calls.

## How It Works

1. **Source and Flow Management**: 
   - Looks for existing source by `stream_input_source` tag (the URL)
   - If found, reuses the existing source; otherwise creates a new one
   - Looks for existing flow with matching video specs (codec, container, essence_parameters)
   - If found, reuses the existing flow; otherwise creates a new one
   - Sets source tags: `stream_input_type`, `stream_input_source`, `chunk_duration`, `chunk_format`, `ingest_started`

2. **Flow Creation**: Creates or reuses a video flow for the stream
   - Codec and container determined by chunk format:
     - **HLS format**: `video/h264` codec, `video/mp2t` container
     - **Original format**: `video/h264` codec, `video/mp4` container
   - Sets default essence parameters (1920x1080 @ 30fps, non-VFR)
   - Sets `loop_recorder_duration` tag (default: 900 seconds = 15 minutes, configurable via `--loop-recorder-duration`)
   - Sets flow tags: `chunk_duration`, `chunk_format`, `stream_input_type`

3. **Stream Processing**:
   - Captures stream from protocol URL using `jthaloor-ffmpeg`
   - Chunks stream into time-based segments using configured duration
   - **Format Options**:
     - `hls`: Encodes to HLS-compatible format (MPEG-TS with H.264/AAC) for streaming
     - `original`: Encodes to MP4 with H.264/AAC (for live streams, encoding is required)
   - Uploads each chunk as a separate segment to the flow
   - Calculates timeranges based on chunk index and duration
   - Deletes chunk files after successful upload

4. **Loop Recording**:
   - The `loop_recorder_duration` tag is automatically set on the flow (default: 900 seconds = 15 minutes)
   - Duration is configurable via `--loop-recorder-duration` CLI option or config file
   - TAMS server automatically deletes old segments when flow duration exceeds the limit
   - Maintains a rolling buffer of content (e.g., 15 minutes by default)

5. **Continuous Operation**:
   - Runs continuously until interrupted (Ctrl+C)
   - Monitors for new chunks and uploads them as they're created
   - Handles errors gracefully (logs and continues)
   - Waits for pending uploads to complete on shutdown

## Examples

### Ingest SRT Stream with HLS Chunks (Default)

```bash
python stream_ingestor.py \
  --srt-url srt://stream.example.com:5000?mode=listener \
  --server-url http://localhost:8000 \
  --chunk-duration 30 \
  --chunk-format hls
```

### Ingest UDP Stream

```bash
python stream_ingestor.py \
  --srt-url udp://127.0.0.1:1234 \
  --chunk-duration 60 \
  --chunk-format original \
  --label "Live Event Stream"
```

### Ingest RTMP Stream

```bash
python stream_ingestor.py \
  --srt-url rtmp://stream.example.com:1935/live/stream \
  --chunk-duration 30
```

### Ingest HTTP/HLS Stream

```bash
python stream_ingestor.py \
  --srt-url http://stream.example.com/playlist.m3u8 \
  --chunk-duration 30
```

### Ingest with Custom Configuration and Verbose Logging

```bash
python stream_ingestor.py \
  --config config.json \
  --srt-url srt://stream.example.com:5000 \
  --chunk-duration 15 \
  --verbose
```

### Ingest with Custom Loop Recorder Duration

Set a 1-hour rolling buffer (3600 seconds):
```bash
python stream_ingestor.py \
  --srt-url srt://stream.example.com:5000 \
  --loop-recorder-duration 3600 \
  --server-url http://localhost:8000
```

Set a 30-minute rolling buffer (1800 seconds):
```bash
python stream_ingestor.py \
  --srt-url srt://stream.example.com:5000 \
  --loop-recorder-duration 1800 \
  --server-url http://localhost:8000
```

The `--verbose` flag enables detailed debug logging, including:
- TAMS client API calls and responses
- FFmpeg processing details
- Chunk creation and upload progress
- Full error tracebacks
- Internal state information

## Error Messages

The app provides user-friendly error messages for common issues:

### Authentication Failed
```
❌ Authentication failed
   → Please check your username and password
   → Server: http://localhost:8000
   → Username: admin
```
**Solution**: Verify your TAMS username and password are correct.

### Connection Failed
```
❌ Connection failed
   → Cannot connect to TAMS server
   → Server: http://localhost:8000
   → Make sure the TAMS server is running
```
**Solution**: Ensure the TAMS server is running and the URL is correct.

### Missing Dependency
```
❌ Missing dependency
   → jthaloor-ffmpeg module not found
   → Install with: pip install -e ~/Developer/gitlab/jthaloor-ffmpeg
```
**Solution**: Install the required jthaloor-ffmpeg module.

### FFmpeg Not Found
```
❌ FFmpeg not found
   → FFmpeg is required but not installed or not in PATH
   → Install FFmpeg: brew install ffmpeg (on macOS)
```
**Solution**: Install FFmpeg using your system's package manager.

For more detailed error information, run with the `--verbose` flag.

## Troubleshooting

### FFmpeg Not Found

Ensure FFmpeg is installed and in your PATH:
```bash
which ffmpeg
which ffprobe
```

### jthaloor-ffmpeg Import Error

Ensure the module is installed:
```bash
pip install -e ~/Developer/gitlab/jthaloor-ffmpeg
```

### TAMS Connection Error

Check that:
- TAMS server is running
- Server URL is correct
- Credentials are valid
- Network connectivity is available

### Stream Connection Issues

- Verify the stream URL is correct
- Check network connectivity to the stream server
- Ensure the stream server is running and accessible
- Check firewall settings
- For SRT: Ensure listener/caller mode is correctly configured

### Chunking Failures

- Check that input stream is valid
- Ensure sufficient disk space for temporary chunk files
- Check FFmpeg logs for encoding errors
- Verify chunk duration is reasonable (not too short or too long)
- Run with `--verbose` to see detailed FFmpeg output

## Streaming Protocols

### SRT (Secure Reliable Transport)

SRT provides error recovery, encryption, and low latency. It requires one side to be `caller` and the other `listener`.

**Example URLs:**
- Caller: `srt://host:port?mode=caller`
- Listener: `srt://host:port?mode=listener`

**Common parameters:**
- `latency`: Latency in milliseconds (default: 120)
- `passphrase`: Encryption passphrase
- `pbkeylen`: Encryption key length

### RTMP (Real-Time Messaging Protocol)

Widely supported protocol, commonly used for broadcasting to CDNs.

**Example URL:**
- `rtmp://host:port/path`

### UDP

Simple UDP streaming - fastest but no error recovery. Best for testing.

**Example URL:**
- `udp://host:port`

### RTSP (Real-Time Streaming Protocol)

Common for IP cameras and streaming servers.

**Example URL:**
- `rtsp://host:port/path`

### HTTP/HTTPS

For HLS, DASH, and other HTTP-based streaming protocols.

**Example URLs:**
- `http://host/path/playlist.m3u8`
- `https://host/path/manifest.mpd`

## Testing with Test Streams

For testing purposes, you can use the included scripts to create test streams:

### Camera Stream (`stream_camera.sh`)

Stream from a camera (macOS AVFoundation) to a protocol. See `STREAM_CAMERA.md` for details.

**Quick test with UDP:**
```bash
# Terminal 1: Stream camera to UDP
./stream_camera.sh udp

# Terminal 2: Ingest the UDP stream
python stream_ingestor.py --srt-url udp://127.0.0.1:1234 --verbose
```

### Video File Stream (`stream_file.sh`)

Loop a video file and stream it to a protocol. Useful for testing with known, repeatable content. See `STREAM_FILE.md` for details.

**Quick test with UDP:**
```bash
# Terminal 1: Stream video file to UDP
./stream_file.sh video.mp4 udp

# Terminal 2: Ingest the UDP stream
python stream_ingestor.py --srt-url udp://127.0.0.1:1234 --verbose
```

See `QUICK_START.md` for more testing examples.

## Notes

- Each stream URL creates **one source** (reused if URL matches)
- Each unique combination of URL + video specs creates **one flow** (reused if specs match)
- Chunks are uploaded continuously as they're created
- The flow is configured with `loop_recorder_duration` tag set to `900` seconds (15 minutes) by default
- Old segments are automatically deleted by TAMS when the flow duration exceeds the limit
- Chunk files are deleted after successful upload to save disk space
- The app runs continuously until interrupted (Ctrl+C)
- On shutdown, the app waits for pending uploads to complete (with timeout)
- Sources and flows are automatically reused when the URL and video specifications match
