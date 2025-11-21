# Stream Camera Script

This script (`stream_camera.sh`) streams from a camera (macOS AVFoundation) to a supported protocol for testing `stream_ingestor`.

## Quick Start

```bash
# Stream to SRT (default)
./stream_camera.sh srt

# Stream to UDP
./stream_camera.sh udp

# Stream to RTMP
./stream_camera.sh rtmp
```

## Usage

```bash
./stream_camera.sh [protocol] [camera_index] [options]
```

### Protocols

- **SRT** (default): Secure Reliable Transport - best for low latency
- **UDP**: Simple UDP streaming - fastest but no error recovery
- **RTMP**: Real-Time Messaging Protocol - common for live streaming

### Examples

#### SRT Streaming

**Important**: SRT requires one side to be `caller` and the other to be `listener`.

**Option 1: Camera as caller (recommended for stream_ingestor)**
```bash
# Camera streams as caller (default)
./stream_camera.sh srt

# Make sure stream_ingestor is listening first:
# python stream_ingestor.py --srt-url srt://127.0.0.1:5000?mode=listener
```

**Option 2: Camera as listener**
```bash
# Camera waits for connection (listener mode)
./stream_camera.sh srt 0 --srt-mode listener

# Then connect stream_ingestor as caller:
# python stream_ingestor.py --srt-url srt://127.0.0.1:5000?mode=caller
```

**Custom SRT host and port:**
```bash
./stream_camera.sh srt 0 --srt-host 192.168.1.100 --srt-port 5001
```

#### UDP Streaming

```bash
# Default UDP stream (127.0.0.1:1234)
./stream_camera.sh udp

# Custom UDP host and port
./stream_camera.sh udp 0 --udp-host 192.168.1.100 --udp-port 5000
```

**To receive UDP stream:**
```bash
ffplay udp://127.0.0.1:1234
```

#### RTMP Streaming

```bash
# Default RTMP (localhost:1935/live/stream)
./stream_camera.sh rtmp

# Custom RTMP URL
./stream_camera.sh rtmp 0 --rtmp-url rtmp://server.com/live/mystream
```

### Camera Selection

```bash
# Use camera 0 (default)
./stream_camera.sh srt 0

# Use camera 1
./stream_camera.sh srt 1
```

**List available cameras:**
```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

### Quality Settings

```bash
# High quality (1080p, 60fps, 5Mbps)
./stream_camera.sh srt 0 \
  --resolution 1920x1080 \
  --fps 60 \
  --bitrate 5000k

# Medium quality (720p, 30fps, 2.5Mbps) - default
./stream_camera.sh srt 0 \
  --resolution 1280x720 \
  --fps 30 \
  --bitrate 2500k

# Low quality (480p, 30fps, 1Mbps)
./stream_camera.sh srt 0 \
  --resolution 640x480 \
  --fps 30 \
  --bitrate 1000k
```

## Testing with stream_ingestor

### Method 1: Camera as Caller (Recommended)

**Step 1: Start stream_ingestor first (listener):**
```bash
cd apps/stream_ingestor
python stream_ingestor.py \
  --srt-url srt://127.0.0.1:5000?mode=listener \
  --chunk-duration 5 \
  --verbose
```

**Step 2: Start camera stream (caller):**
```bash
# In another terminal
cd apps/stream_ingestor
./stream_camera.sh srt 0
```

### Method 2: Camera as Listener

**Step 1: Start camera stream first (listener):**
```bash
cd apps/stream_ingestor
./stream_camera.sh srt 0 --srt-mode listener
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

### Alternative: UDP Stream

**Terminal 1 - Stream to UDP:**
```bash
./stream_camera.sh udp 0
```

**Terminal 2 - Ingest UDP stream:**
```bash
python stream_ingestor.py \
  --srt-url udp://127.0.0.1:1234 \
  --chunk-duration 5 \
  --verbose
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--srt-host HOST` | SRT host address | `127.0.0.1` |
| `--srt-port PORT` | SRT port | `5000` |
| `--srt-mode MODE` | SRT mode: `caller` or `listener` | `caller` |
| `--udp-host HOST` | UDP host address | `127.0.0.1` |
| `--udp-port PORT` | UDP port | `1234` |
| `--rtmp-url URL` | RTMP stream URL | `rtmp://localhost:1935/live/stream` |
| `--fps FPS` | Framerate | `30` |
| `--resolution RES` | Resolution (WIDTHxHEIGHT) | `1280x720` |
| `--bitrate RATE` | Video bitrate | `2500k` |
| `--help, -h` | Show help message | - |

## Notes

- **SRT mode**: 
  - `caller`: Initiates connection (use with `mode=listener` in receiver)
  - `listener`: Waits for connection (use with `mode=caller` in receiver)

- **Camera permissions**: On macOS, grant camera permissions to Terminal:
  - System Preferences → Security & Privacy → Privacy → Camera

- **FFmpeg encoding**: The script uses H.264 video and AAC audio encoding, which is compatible with all streaming protocols.

- **Low latency**: Uses `tune zerolatency` and GOP size of 2 seconds for low latency streaming.

## Troubleshooting

### Camera not found
```bash
# List available cameras
ffmpeg -f avfoundation -list_devices true -i ""

# Try different camera index
./stream_camera.sh srt 1
```

### Permission denied
- Grant camera permissions to Terminal in System Preferences
- Or use a different terminal application

### Port already in use
```bash
# Use a different port
./stream_camera.sh srt 0 --srt-port 5001
```

### Connection refused (SRT)
- **For caller mode**: Make sure the receiver (stream_ingestor) is running in listener mode first
- **For listener mode**: Make sure the caller (stream_ingestor) connects after the listener starts
- Check that the port is not already in use: `lsof -i :5000`
- Verify firewall settings if using remote hosts

