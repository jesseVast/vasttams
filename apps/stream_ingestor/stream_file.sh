#!/bin/bash
#
# Stream Video File in Loop to Supported Protocol
#
# This script loops a video file and streams it to a supported protocol
# (SRT, UDP, RTMP, RTSP, etc.) for testing stream_ingestor.
#
# Usage:
#   ./stream_file.sh [video_file] [protocol] [options]
#
# Examples:
#   # Stream video file to UDP (default)
#   ./stream_file.sh video.mp4 udp
#
#   # Stream video file to SRT
#   ./stream_file.sh video.mp4 srt
#
#   # Stream video file to RTMP
#   ./stream_file.sh video.mp4 rtmp
#
#   # Stream with custom SRT port
#   ./stream_file.sh video.mp4 srt --srt-port 5001
#

set -e

# Check if video file is provided
if [ $# -lt 1 ]; then
    echo "Error: Video file path is required"
    echo ""
    echo "Usage: $0 <video_file> [protocol] [options]"
    echo ""
    echo "Examples:"
    echo "  $0 video.mp4 udp"
    echo "  $0 video.mp4 srt"
    echo "  $0 video.mp4 rtmp --rtmp-url rtmp://localhost:1935/live/stream"
    echo ""
    echo "Use --help for full options"
    exit 1
fi

VIDEO_FILE="$1"
shift

# Check if video file exists
if [ ! -f "$VIDEO_FILE" ]; then
    echo "Error: Video file not found: $VIDEO_FILE"
    exit 1
fi

# Default values
# Note: UDP is simpler for testing (no listener required)
# Use SRT for production (better error recovery)
PROTOCOL=${1:-udp}
shift 2>/dev/null || shift 1 2>/dev/null || true

FPS=30
BITRATE="2500k"

# SRT defaults
SRT_HOST="127.0.0.1"
SRT_PORT=5000
SRT_MODE="caller"

# UDP defaults
UDP_HOST="127.0.0.1"
UDP_PORT=1234

# RTMP defaults
RTMP_URL="rtmp://localhost:1935/live/stream"

# RTSP defaults
RTSP_URL="rtsp://127.0.0.1:8554/stream"

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --srt-host)
            SRT_HOST="$2"
            shift 2
            ;;
        --srt-port)
            SRT_PORT="$2"
            shift 2
            ;;
        --srt-mode)
            SRT_MODE="$2"
            shift 2
            ;;
        --udp-host)
            UDP_HOST="$2"
            shift 2
            ;;
        --udp-port)
            UDP_PORT="$2"
            shift 2
            ;;
        --rtmp-url)
            RTMP_URL="$2"
            shift 2
            ;;
        --rtsp-url)
            RTSP_URL="$2"
            shift 2
            ;;
        --fps)
            FPS="$2"
            shift 2
            ;;
        --bitrate)
            BITRATE="$2"
            shift 2
            ;;
        --help|-h)
            cat << EOF
Stream Video File in Loop to Supported Protocol

Usage: $0 <video_file> [protocol] [options]

Protocols:
  udp     - UDP stream (default, simplest for testing)
  srt     - SRT stream (requires listener/caller setup)
  rtmp    - RTMP stream
  rtsp    - RTSP stream
  http    - HTTP/HLS stream (creates HLS playlist)

Options:
  --srt-host HOST      SRT host (default: 127.0.0.1)
  --srt-port PORT      SRT port (default: 5000)
  --srt-mode MODE      SRT mode: caller or listener (default: caller)
  --udp-host HOST      UDP host (default: 127.0.0.1)
  --udp-port PORT      UDP port (default: 1234)
  --rtmp-url URL       RTMP URL (default: rtmp://localhost:1935/live/stream)
  --rtsp-url URL       RTSP URL (default: rtsp://127.0.0.1:8554/stream)
  --fps FPS            Output framerate (default: 30)
  --bitrate RATE       Video bitrate (default: 2500k)
  --help, -h           Show this help

Examples:
  # Stream to UDP on default port
  $0 video.mp4 udp

  # Stream to SRT
  $0 video.mp4 srt

  # Stream to SRT with custom port
  $0 video.mp4 srt --srt-port 5001

  # Stream to RTMP
  $0 video.mp4 rtmp --rtmp-url rtmp://server.com/live/mystream

  # Stream with custom settings
  $0 video.mp4 udp --fps 60 --bitrate 5000k
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed or not in PATH"
    echo "Install with: brew install ffmpeg (on macOS)"
    exit 1
fi

# Get video file info
VIDEO_INFO=$(ffprobe -v quiet -print_format json -show_format -show_streams "$VIDEO_FILE" 2>/dev/null || echo "{}")
VIDEO_DURATION=$(echo "$VIDEO_INFO" | grep -o '"duration":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "0")

if [ -z "$VIDEO_DURATION" ] || [ "$VIDEO_DURATION" = "0" ]; then
    echo "Warning: Could not determine video duration, will loop indefinitely"
    VIDEO_DURATION=""
else
    echo "Video duration: ${VIDEO_DURATION}s"
fi

# Build FFmpeg command based on protocol
echo "📹 Streaming video file: $VIDEO_FILE"
echo "   Protocol: $PROTOCOL"
echo "   Output framerate: $FPS fps"
echo "   Bitrate: $BITRATE"
echo "   Loop: Continuous"
echo ""

case $PROTOCOL in
    srt)
        SRT_URL="srt://${SRT_HOST}:${SRT_PORT}?mode=${SRT_MODE}"
        echo "SRT URL: $SRT_URL"
        echo ""
        
        if [[ "$SRT_MODE" == "caller" ]]; then
            echo "⚠️  Using caller mode - make sure stream_ingestor is listening first!"
            echo "   Start stream_ingestor with: --srt-url srt://${SRT_HOST}:${SRT_PORT}?mode=listener"
            echo ""
        else
            echo "Using listener mode - waiting for connection..."
            echo "   Connect with: srt://${SRT_HOST}:${SRT_PORT}?mode=caller"
            echo ""
        fi
        
        ffmpeg -re \
            -stream_loop -1 \
            -i "$VIDEO_FILE" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -r $FPS \
            -g $(($FPS * 2)) \
            -c:a aac \
            -b:a 128k \
            -f mpegts \
            "$SRT_URL"
        ;;
    
    udp)
        UDP_URL="udp://${UDP_HOST}:${UDP_PORT}"
        echo "UDP URL: $UDP_URL"
        echo "To receive: ffplay $UDP_URL"
        echo ""
        
        ffmpeg -re \
            -stream_loop -1 \
            -i "$VIDEO_FILE" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -r $FPS \
            -g $(($FPS * 2)) \
            -c:a aac \
            -b:a 128k \
            -f mpegts \
            "$UDP_URL"
        ;;
    
    rtmp)
        echo "RTMP URL: $RTMP_URL"
        echo ""
        
        ffmpeg -re \
            -stream_loop -1 \
            -i "$VIDEO_FILE" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -r $FPS \
            -g $(($FPS * 2)) \
            -c:a aac \
            -b:a 128k \
            -f flv \
            "$RTMP_URL"
        ;;
    
    rtsp)
        echo "RTSP URL: $RTSP_URL"
        echo ""
        echo "Note: RTSP streaming requires an RTSP server. This example uses FFmpeg's RTSP server."
        echo "For production, use a dedicated RTSP server like MediaMTX or similar."
        echo ""
        
        ffmpeg -re \
            -stream_loop -1 \
            -i "$VIDEO_FILE" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -r $FPS \
            -g $(($FPS * 2)) \
            -c:a aac \
            -b:a 128k \
            -f rtsp \
            "$RTSP_URL"
        ;;
    
    http|hls)
        # For HTTP/HLS, we need to create a playlist and segments
        OUTPUT_DIR="/tmp/hls_stream_$$"
        mkdir -p "$OUTPUT_DIR"
        PLAYLIST="$OUTPUT_DIR/playlist.m3u8"
        
        echo "HLS Output directory: $OUTPUT_DIR"
        echo "HLS Playlist: $PLAYLIST"
        echo ""
        echo "To serve via HTTP, run a simple HTTP server:"
        echo "  cd $OUTPUT_DIR && python3 -m http.server 8001"
        echo "Then access: http://localhost:8001/playlist.m3u8"
        echo ""
        
        # Clean up on exit
        trap "rm -rf $OUTPUT_DIR" EXIT
        
        ffmpeg -re \
            -stream_loop -1 \
            -i "$VIDEO_FILE" \
            -c:v libx264 \
            -preset fast \
            -b:v $BITRATE \
            -r $FPS \
            -g $(($FPS * 2)) \
            -c:a aac \
            -b:a 128k \
            -f hls \
            -hls_time 2 \
            -hls_list_size 0 \
            -hls_flags delete_segments \
            "$PLAYLIST"
        ;;
    
    *)
        echo "Error: Unsupported protocol: $PROTOCOL"
        echo "Supported protocols: srt, udp, rtmp, rtsp, http, hls"
        exit 1
        ;;
esac

