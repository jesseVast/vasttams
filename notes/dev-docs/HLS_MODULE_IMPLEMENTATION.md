# HLS Module Implementation

## Summary

Created a separate HLS module (`src/vasttams/hls/`) that generates HLS playlists for TAMS flows without requiring Object Lambda or complex transcoding infrastructure.

## Files Created

### Module Structure
```
src/vasttams/hls/
├── __init__.py          # Module exports
├── models.py            # HLSPlaylist, HLSSegment models
├── manager.py           # HLSManager - playlist generation logic
├── router.py            # FastAPI endpoints
└── README.md            # Usage documentation
```

### Code Files

1. **src/vasttams/hls/__init__.py**
   - Exports: `HLSPlaylist`, `HLSSegment`, `HLSManager`

2. **src/vasttams/hls/models.py**
   - `HLSSegment`: Segment info (url, duration, sequence, discontinuity)
   - `HLSPlaylist`: Playlist data (version, target_duration, segments, endlist)
   - `HLSStream`: Multi-bitrate stream variant
   - `HLSMasterManifest`: Master playlist for multiple bitrates

3. **src/vasttams/hls/manager.py**
   - `HLSManager`: Main playlist generation logic
   - `generate_playlist()`: Creates HLS playlist from flow
   - `playlist_to_m3u8()`: Converts model to M3U8 format
   - Duration calculation from timeranges
   - URL selection with HLS label preference

4. **src/vasttams/hls/router.py**
   - `GET /hls/flows/{flow_id}/playlist.m3u8`: Returns M3U8 playlist
   - `GET /hls/flows/{flow_id}/status`: Returns HLS compatibility status

### Integration

**Modified**: `src/vasttams/main.py`
- Added import: `from .hls.router import router as hls_router`
- Registered router: `app.include_router(hls_router)`

## Implementation Details

### Playlist Generation

```python
# Flow
GET /hls/flows/{flow_id}/playlist.m3u8
    ↓
# HLSManager generates playlist
playlist = await hls_manager.generate_playlist(flow_id)
    ↓
# Get segments from database
segments = await segment_service.get_flow_segments(flow_id)
    ↓
# Convert to M3U8 format
m3u8_content = hls_manager.playlist_to_m3u8(playlist)
    ↓
# Return with proper content-type
Response(media_type="application/vnd.apple.mpegurl")
```

### Duration Calculation

Three methods (in priority order):

1. **Timerange-based** (preferred):
   - Parses: `[start_sec:start_nano_end_sec:end_nano)`
   - Calculates: `end - start`

2. **Sample-based** (fallback):
   - Uses: `sample_count / 30` (assumes 30 fps)

3. **Default**:
   - Uses: 1.0 second

### URL Selection

Priority order for segment URLs:

1. **HLS-labeled URLs**: URLs with label containing "hls"
2. **First URL**: Falls back to first URL in get_urls array

## Endpoints

### 1. GET /hls/flows/{flow_id}/playlist.m3u8

**Purpose**: Generate HLS playlist for a flow

**Response**: M3U8 format
```m3u8
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:1
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:1.0,
https://s3.../segment1.ts
#EXTINF:1.0,
https://s3.../segment2.ts
#EXT-X-ENDLIST
```

**Headers**:
- `Content-Type`: `application/vnd.apple.mpegurl`
- `Cache-Control`: `no-cache, no-store, must-revalidate`
- `Access-Control-Allow-Origin`: `*`

### 2. GET /hls/flows/{flow_id}/status

**Purpose**: Check HLS compatibility

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

## Usage Example

### Web Playback

```html
<video controls>
  <source 
    src="http://localhost:8000/hls/flows/flow-123/playlist.m3u8" 
    type="application/x-mpegURL">
</video>
```

### With hls.js

```javascript
import Hls from 'hls.js';

const video = document.getElementById('video');
const hls = new Hls();
hls.loadSource('http://localhost:8000/hls/flows/flow-123/playlist.m3u8');
hls.attachMedia(video);
```

### Command Line

```bash
# Using FFplay
ffplay http://localhost:8000/hls/flows/flow-123/playlist.m3u8

# Using VLC
vlc http://localhost:8000/hls/flows/flow-123/playlist.m3u8
```

## Benefits

1. **Simple**: No transcoding required
2. **Fast**: Direct segment URL generation
3. **Compatible**: Works with existing TAMS segments
4. **Standard**: Standard HLS format (playable everywhere)
5. **CORS-Enabled**: Works in web browsers

## Limitations

### Current Version

- ❌ No transcoding (assumes HLS-compatible segments)
- ❌ Single bitrate only (no multi-variant playlist)
- ❌ Static playlists (always includes ENDLIST)
- ❌ No discontinuity detection

### Future Enhancements

- ✅ Multi-bitrate support (master playlist)
- ✅ Live streaming (no ENDLIST)
- ✅ Discontinuity marking
- ✅ Background transcoding

## Testing

To test the HLS module:

```bash
# 1. Create a flow with segments
POST /flows
{
  "id": "flow-123",
  "source_id": "source-456",
  "format": "urn:x-nmos:format:video"
}

# 2. Add segments with URLs
POST /flows/{flow_id}/segments
{
  "object_id": "obj-123",
  "timerange": "[0:0_1:0)",
  "get_urls": [{
    "url": "https://s3.../segment1.ts",
    "storage_id": "...",
    "provider": "aws",
    "store_product": "s3"
  }]
}

# 3. Get HLS playlist
GET /hls/flows/{flow_id}/playlist.m3u8

# 4. Test playback
ffplay http://localhost:8000/hls/flows/{flow_id}/playlist.m3u8
```

## Status

✅ **Module Created**: `src/vasttams/hls/`
✅ **Router Created**: HLS endpoints added
✅ **Integration Complete**: Added to main app
✅ **No Linter Errors**: Code passes validation
⚠️ **Tests Pending**: Need to add tests

## Next Steps

1. Add tests in `tests/hls/`
2. Test with real flows and segments
3. Verify playback in various players
4. Add multi-bitrate support (future)

