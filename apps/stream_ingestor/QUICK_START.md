# Quick Start Guide

This guide helps you quickly test the stream_ingestor with a camera stream. For production use, you'll typically ingest streams from external sources.

## Simplest Test: UDP Stream

UDP is the easiest protocol to test because it doesn't require a listener to be running first.

### Step 1: Start Camera Stream (UDP)

Using the included `stream_camera.sh` script:

```bash
cd apps/stream_ingestor
./stream_camera.sh udp
```

This will stream to `udp://127.0.0.1:1234` by default.

### Step 2: Start stream_ingestor

In another terminal:

```bash
cd apps/stream_ingestor
python stream_ingestor.py \
  --srt-url udp://127.0.0.1:1234 \
  --chunk-duration 5 \
  --verbose
```

That's it! UDP doesn't require a listener, so you can start them in any order.

## SRT Stream (More Reliable)

SRT requires one side to be `caller` and the other `listener`. The listener must start first.

### Step 1: Start stream_ingestor (Listener)

```bash
cd apps/stream_ingestor
python stream_ingestor.py \
  --srt-url srt://127.0.0.1:5000?mode=listener \
  --chunk-duration 5 \
  --verbose
```

Wait until you see "Stream ingestion started" message.

### Step 2: Start Camera Stream (Caller)

In another terminal:

```bash
cd apps/stream_ingestor
./stream_camera.sh srt
```

The camera will connect to the waiting listener.

**Note**: For production, you would typically ingest streams from external sources (not from a local camera script).

## Troubleshooting

### "Connection failed" or "Input/output error"

**For SRT:**
- Make sure stream_ingestor is running first (in listener mode)
- Check the port is correct (default: 5000)
- Verify no firewall is blocking the connection

**For UDP:**
- UDP should work regardless of order
- Check the port is correct (default: 1234)
- Make sure both are using the same port

### Check if port is in use

```bash
# Check SRT port
lsof -i :5000

# Check UDP port
lsof -i :1234
```

### Test with ffplay

You can test the camera stream directly with ffplay:

```bash
# UDP
./stream_camera.sh udp
# In another terminal:
ffplay udp://127.0.0.1:1234

# SRT (camera as caller)
./stream_camera.sh srt
# In another terminal:
ffplay -i srt://127.0.0.1:5000?mode=listener
```

## Protocol Comparison

| Protocol | Pros | Cons | Best For |
|----------|------|------|----------|
| **UDP** | Simple, no handshake needed | No error recovery, packets can be lost | Testing, local networks |
| **SRT** | Error recovery, encryption, low latency | Requires listener/caller setup | Production, unreliable networks |
| **RTMP** | Widely supported | Higher latency | Broadcasting to CDNs |

For testing, **UDP is recommended** because it's the simplest.

