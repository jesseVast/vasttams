# Stream Video File Script

This script (`stream_file.sh`) loops a video file and streams it to a supported protocol for testing `stream_ingestor`.

## Quick Start

```bash
# Stream video file to UDP (default, simplest)
./stream_file.sh video.mp4 udp

# Stream video file to SRT
./stream_file.sh video.mp4 srt

# Stream video file to RTMP
./stream_file.sh video.mp4 rtmp
```

## Usage

```bash
./stream_file.sh <video_file> [protocol] [options]
```

### Protocols

- **UDP** (default): Simple UDP streaming - fastest but no error recovery
- **SRT**: Secure Reliable Transport - best for low latency with error recovery
- **RTMP**: Real-Time Messaging Protocol - common for live streaming
- **RTSP**: Real-Time Streaming Protocol - for IP cameras and streaming servers
- **HTTP/HLS**: HTTP Live Streaming - creates HLS playlist and segments

### Examples

#### UDP Streaming

```bash
# Default UDP stream (127.0.0.1:1234)
./stream_file.sh video.mp4 udp

# Custom UDP host and port
./stream_file.sh video.mp4 udp --udp-host 192.168.1.100 --udp-port 5000
```

**To receive UDP stream:**
```bash
ffplay udp://127.0.0.1:1234
```

#### SRT Streaming

**Important**: SRT requires one side to be `caller` and the other to be `listener`.

**Option 1: File stream as caller (recommended for stream_ingestor)**
```bash
# File streams as caller (default)
./stream_file.sh video.mp4 srt

# Make sure stream_ingestor is listening first:
# python stream_ingestor.py --srt-url srt://127.0.0.1:5000?mode=listener
```

**Option 2: File stream as listener**
```bash
# File waits for connection (listener mode)
./stream_file.sh video.mp4 srt --srt-mode listener

# Then connect stream_ingestor as caller:
# python stream_ingestor.py --srt-url srt://127.0.0.1:5000?mode=caller
```

**Custom SRT host and port:**
```bash
./stream_file.sh video.mp4 srt --srt-host 192.168.1.100 --srt-port 5001
```

#### RTMP Streaming

```bash
# Default RTMP (localhost:1935/live/stream)
./stream_file.sh video.mp4 rtmp

# Custom RTMP URL
./stream_file.sh video.mp4 rtmp --rtmp-url rtmp://server.com/live/mystream
```

#### RTSP Streaming

```bash
# Default RTSP
./stream_file.sh video.mp4 rtsp

# Custom RTSP URL
./stream_file.sh video.mp4 rtsp --rtsp-url rtsp://192.168.1.100:8554/stream
```

**Note**: RTSP streaming typically requires an RTSP server. FFmpeg can act as a basic RTSP server, but for production use a dedicated server like MediaMTX.

#### HTTP/HLS Streaming

```bash
# Create HLS stream
./stream_file.sh video.mp4 http
```

This creates an HLS playlist and segments in `/tmp/hls_stream_*/`. To serve via HTTP:

```bash
# In another terminal, serve the HLS files
cd /tmp/hls_stream_*
python3 -m http.server 8001
```

Then access: `http://localhost:8001/playlist.m3u8`

### Quality Settings

```bash
# High quality (60fps, 5Mbps)
./stream_file.sh video.mp4 udp \
  --fps 60 \
  --bitrate 5000k

# Medium quality (30fps, 2.5Mbps) - default
./stream_file.sh video.mp4 udp \
  --fps 30 \
  --bitrate 2500k

# Low quality (30fps, 1Mbps)
./stream_file.sh video.mp4 udp \
  --fps 30 \
  --bitrate 1000k
```

## Testing with stream_ingestor

### Method 1: File Stream as Caller (Recommended)

**Step 1: Start stream_ingestor first (listener):**
```bash
cd apps/stream_ingestor
python stream_ingestor.py \
  --srt-url srt://127.0.0.1:5000?mode=listener \
  --chunk-duration 5 \
  --verbose
```

**Step 2: Start file stream (caller):**
```bash
# In another terminal
cd apps/stream_ingestor
./stream_file.sh video.mp4 srt
```

### Method 2: File Stream as Listener

**Step 1: Start file stream first (listener):**
```bash
cd apps/stream_ingestor
./stream_file.sh video.mp4 srt --srt-mode listener
```

**Step 2: Start stream_ingestor (caller):**
```bash
# In another terminal
cd apps/stream_ingestor
python stream_ingestor.py \
  --srt-url srt://127.0.0.1:5000?mode=caller \
  --chunk-duration 5 \
  --verbose
```

### UDP Stream (Simplest)

**Terminal 1:**
```bash
./stream_file.sh video.mp4 udp
```

**Terminal 2:**
```bash
python stream_ingestor.py \
  --srt-url udp://127.0.0.1:1234 \
  --chunk-duration 5 \
  --verbose
```

UDP doesn't require a listener, so you can start them in any order.

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--srt-host HOST` | SRT host address | `127.0.0.1` |
| `--srt-port PORT` | SRT port | `5000` |
| `--srt-mode MODE` | SRT mode: `caller` or `listener` | `caller` |
| `--udp-host HOST` | UDP host address | `127.0.0.1` |
| `--udp-port PORT` | UDP port | `1234` |
| `--rtmp-url URL` | RTMP stream URL | `rtmp://localhost:1935/live/stream` |
| `--rtsp-url URL` | RTSP stream URL | `rtsp://127.0.0.1:8554/stream` |
| `--fps FPS` | Output framerate | `30` |
| `--bitrate RATE` | Video bitrate | `2500k` |
| `--help, -h` | Show help message | - |

## Notes

- **Loop**: The video file loops continuously using `-stream_loop -1`
- **Real-time**: Uses `-re` flag to stream at the video's native framerate
- **Encoding**: All streams are encoded to H.264 video and AAC audio for compatibility
- **Low latency**: Uses `tune zerolatency` and GOP size of 2 seconds for low latency streaming
- **HLS cleanup**: HLS output directory is automatically cleaned up on script exit

## Troubleshooting

### Video file not found
```bash
# Check file exists
ls -lh video.mp4

# Use absolute path if needed
./stream_file.sh /path/to/video.mp4 udp
```

### Connection refused (SRT)
- **For caller mode**: Make sure the receiver (stream_ingestor) is running in listener mode first
- **For listener mode**: Make sure the caller (stream_ingestor) connects after the listener starts
- Check that the port is not already in use: `lsof -i :5000`
- Verify firewall settings if using remote hosts

### Port already in use
```bash
# Use a different port
./stream_file.sh video.mp4 srt --srt-port 5001
```

### RTSP not working
- RTSP typically requires a dedicated RTSP server
- FFmpeg's built-in RTSP support is limited
- Consider using MediaMTX or similar for production RTSP streaming

### HLS output location
- HLS files are created in `/tmp/hls_stream_*/`
- The directory is automatically cleaned up when the script exits
- To keep files, copy them before stopping the script

## Comparison with Camera Stream

| Feature | Camera Stream (`stream_camera.sh`) | File Stream (`stream_file.sh`) |
|---------|-----------------------------------|-------------------------------|
| **Input** | Live camera (macOS AVFoundation) | Video file (loops) |
| **Use Case** | Testing with live camera | Testing with known video content |
| **Advantages** | Real-time, live content | Repeatable, consistent content |
| **Best For** | Testing camera integration | Testing stream processing logic |

Both scripts support the same protocols and can be used interchangeably for testing stream_ingestor.

