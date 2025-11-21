#!/bin/bash
#
# Stream Camera to Supported Protocol
#
# This script streams from a camera (macOS AVFoundation) to a supported protocol
# (SRT, UDP, RTMP, etc.) for testing stream_ingestor.
#
# Usage:
#   ./stream_camera.sh [protocol] [camera_index] [options]
#
# Examples:
#   # Stream to SRT (default)
#   ./stream_camera.sh srt
#
#   # Stream to UDP
#   ./stream_camera.sh udp
#
#   # Stream to SRT with specific camera
#   ./stream_camera.sh srt 1
#
#   # Stream to SRT with custom port
#   ./stream_camera.sh srt 0 --srt-port 5001
#
#   # Stream to RTMP
#   ./stream_camera.sh rtmp 0 --rtmp-url rtmp://localhost:1935/live/stream
#

set -e

# Default values
# Note: UDP is simpler for testing (no listener required)
# Use SRT for production (better error recovery)
PROTOCOL=${1:-udp}
CAMERA_INDEX=${2:-0}
FPS=30
RESOLUTION="1280x720"
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

# Parse additional arguments
shift 2 2>/dev/null || shift 1 2>/dev/null || true
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
        --fps)
            FPS="$2"
            shift 2
            ;;
        --resolution)
            RESOLUTION="$2"
            shift 2
            ;;
        --bitrate)
            BITRATE="$2"
            shift 2
            ;;
        --help|-h)
            cat << EOF
Stream Camera to Supported Protocol

Usage: $0 [protocol] [camera_index] [options]

Protocols:
  srt     - SRT stream (default)
  udp     - UDP stream
  rtmp    - RTMP stream

Options:
  --srt-host HOST      SRT host (default: 127.0.0.1)
  --srt-port PORT      SRT port (default: 5000)
  --srt-mode MODE      SRT mode: caller or listener (default: caller)
  --udp-host HOST      UDP host (default: 127.0.0.1)
  --udp-port PORT      UDP port (default: 1234)
  --rtmp-url URL       RTMP URL (default: rtmp://localhost:1935/live/stream)
  --fps FPS            Framerate (default: 30)
  --resolution RES     Resolution WIDTHxHEIGHT (default: 1280x720)
  --bitrate RATE       Video bitrate (default: 2500k)
  --help, -h           Show this help

Examples:
  # Stream to SRT on default port
  $0 srt

  # Stream to UDP
  $0 udp

  # Stream to SRT with custom port
  $0 srt 0 --srt-port 5001

  # Stream to RTMP
  $0 rtmp 0 --rtmp-url rtmp://server.com/live/mystream

  # Stream with custom settings
  $0 srt 0 --fps 60 --resolution 1920x1080 --bitrate 5000k
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

# Detect OS
OS="$(uname -s)"
if [[ "$OS" != "Darwin" ]]; then
    echo "Warning: This script is designed for macOS (AVFoundation)"
    echo "On Linux, you may need to use v4l2 or other input devices"
    echo "Continuing anyway..."
fi

# Build FFmpeg command based on protocol
echo "📹 Streaming camera $CAMERA_INDEX to $PROTOCOL protocol..."
echo "   Resolution: $RESOLUTION"
echo "   Framerate: $FPS fps"
echo "   Bitrate: $BITRATE"
echo "   Audio: Disabled (video only)"
echo ""
echo "💡 Tip: For testing, UDP is simpler (no listener required)"
echo "   For production, SRT is more reliable (requires listener)"
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
        
        ffmpeg -f avfoundation \
            -framerate $FPS \
            -video_size $RESOLUTION \
            -i "${CAMERA_INDEX}:none" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -g $(($FPS * 2)) \
            -an \
            -f mpegts \
            "$SRT_URL"
        ;;
    
    udp)
        UDP_URL="udp://${UDP_HOST}:${UDP_PORT}"
        echo "UDP URL: $UDP_URL"
        echo "To receive: ffplay $UDP_URL"
        echo ""
        
        ffmpeg -f avfoundation \
            -framerate $FPS \
            -video_size $RESOLUTION \
            -i "${CAMERA_INDEX}:none" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -g $(($FPS * 2)) \
            -an \
            -f mpegts \
            "$UDP_URL"
        ;;
    
    rtmp)
        echo "RTMP URL: $RTMP_URL"
        echo ""
        
        ffmpeg -f avfoundation \
            -framerate $FPS \
            -video_size $RESOLUTION \
            -i "${CAMERA_INDEX}:none" \
            -c:v libx264 \
            -preset fast \
            -tune zerolatency \
            -b:v $BITRATE \
            -g $(($FPS * 2)) \
            -an \
            -f flv \
            "$RTMP_URL"
        ;;
    
    *)
        echo "Error: Unsupported protocol: $PROTOCOL"
        echo "Supported protocols: srt, udp, rtmp"
        exit 1
        ;;
esac

