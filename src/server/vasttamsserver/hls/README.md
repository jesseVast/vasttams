# HLS Module for TAMS

## Overview

The HLS module provides HTTP Live Streaming (HLS) support for TAMS flows, allowing playback in standard HLS players.

## Features

- Generate HLS playlists (.m3u8) from TAMS flows
- Automatic duration calculation from segment timeranges
- Support for HLS-compatible segment URLs
- CORS-enabled responses for web playback

## Endpoints

### Get HLS Playlist

```
GET /hls/flows/{flow_id}/playlist.m3u8
```

**Description**: Returns HLS playlist in M3U8 format for the specified flow.

**Response**: 
- Content-Type: `application/vnd.apple.mpegurl`
- CORS headers included for web playback

**Example Response**:
```m3u8
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:1
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:1.0,
https://s3.amazonaws.com/bucket/path/segment1.ts
#EXTINF:1.0,
https://s3.amazonaws.com/bucket/path/segment2.ts
#EXTINF:1.0,
https://s3.amazonaws.com/bucket/path/segment3.ts
#EXT-X-ENDLIST
```

### Get HLS Status

```
GET /hls/flows/{flow_id}/status
```

**Description**: Returns information about HLS compatibility for a flow.

**Response**:
```json
{
  "flow_id": "flow-123",
  "hls_ready": true,
  "segment_count": 10,
  "reason": null,
  "playlist_url": "/hls/flows/flow-123/playlist.m3u8"
}
```

## How It Works

### Segment Requirements

For HLS playback, segments must have:
1. **Valid URLs**: Segments must have `get_urls` populated
2. **HLS-compatible format**: URLs should point to .ts files or other HLS-compatible media

### URL Selection

The HLS manager selects URLs in priority order:

1. **HLS-specific URLs**: URLs with label containing "hls"
2. **First available URL**: Falls back to first URL in `get_urls` array

### Duration Calculation

The playlist uses segment duration from:
1. **Timerange** (preferred): Parses TAMS timerange format
2. **Sample Count** (fallback): Estimates from `sample_count` (assumes 30 fps)
3. **Default** (last resort): Uses 1 second default

## Usage Examples

### Web Playback

```html
<video controls>
  <source src="http://your-tams-server:8000/hls/flows/flow-123/playlist.m3u8" type="application/x-mpegURL">
</video>
```

### With JavaScript (hls.js)

```javascript
import Hls from 'hls.js';

const video = document.getElementById('video');
const url = 'http://your-tams-server:8000/hls/flows/flow-123/playlist.m3u8';

if (Hls.isSupported()) {
  const hls = new Hls();
  hls.loadSource(url);
  hls.attachMedia(video);
} else if (video.canPlayType('application/vnd.apple.mpegurl')) {
  video.src = url;
}
```

### Testing with FFplay

```bash
ffplay http://localhost:8000/hls/flows/flow-123/playlist.m3u8
```

## Architecture

```
Client Request
    ↓
GET /hls/flows/{flow_id}/playlist.m3u8
    ↓
HLSManager.generate_playlist(flow_id)
    ↓
Get segments from database
    ↓
Parse segment URLs and durations
    ↓
Generate HLSPlaylist model
    ↓
Convert to M3U8 format
    ↓
Return with proper content-type
```

## File Structure

```
src/vasttams/hls/
├── __init__.py        # Module exports
├── models.py          # HLSPlaylist, HLSSegment models
├── manager.py         # HLSManager - playlist generation
├── router.py          # FastAPI endpoints
└── README.md          # This file
```

## Integration

The HLS module is integrated into the main FastAPI app:

```python
from .hls.router import router as hls_router
app.include_router(hls_router)
```

## Limitations

### Current Limitations

1. **No Transcoding**: Assumes segments are already HLS-compatible
2. **Single Bitrate**: Only generates single-variant playlist
3. **Static Playlist**: Always includes `#EXT-X-ENDLIST`
4. **No Discontinuity**: Doesn't mark discontinuities in streams

### Future Enhancements

1. **Multi-Bitrate Support**: Generate master playlist with variants
2. **Dynamic Playlists**: Support live streaming without ENDLIST
3. **Discontinuity Marking**: Detect and mark gaps in segments
4. **Transcoding Support**: Convert non-HLS segments on-the-fly

## Compatibility

- ✅ TAMS 8.0 compliant
- ✅ Standard HLS players (Safari, VLC, ffplay)
- ✅ Web players (hls.js, video.js)
- ✅ Mobile players (iOS AVPlayer, Android ExoPlayer)

## Configuration

No additional configuration required. Works automatically with existing TAMS flows and segments.

## Troubleshooting

### Empty Playlist

**Issue**: `/hls/flows/{flow_id}/playlist.m3u8` returns empty playlist

**Causes**:
- No segments in flow
- Segments missing `get_urls`
- Segments not HLS-compatible

**Solution**: Check segment URLs and ensure they're accessible

### CORS Issues

**Issue**: Browser blocks playback due to CORS

**Solution**: Already configured with `Access-Control-Allow-Origin: *`

### Duration Issues

**Issue**: Wrong segment durations in playlist

**Causes**:
- Incorrect timerange format
- Missing sample_count
- Invalid timerange values

**Solution**: Verify segment timeranges are in correct TAMS format

