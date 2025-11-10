# Folder Ingestor

Ingests all files from a folder into TAMS. Each folder becomes one source with separate flows for each media type (video, audio, data). When multiple media types are detected, a multi-essence flow is created to collect them. Media files are chunked into time-based segments, non-media files are stored as data files.

## Features

- **Automatic Media Detection**: Uses `ffprobe` to detect video and audio files
- **Multi-Essence Flow Support**: Automatically creates separate flows for each media type and a multi-essence flow to collect them
- **Media Chunking**: Chunks video/audio files into 30-second segments using `jthaloor-ffmpeg`
- **Chunk Format Options**: Supports original format (copy codecs, MP4) or HLS format (HLS-compatible TS with H.264/AAC)
- **Marker-Based Chunking**: Automatically detects and uses metadata files (FFMETADATA1 or JSON) for intelligent chunking
- **Metadata File Matching**: Heuristically matches metadata files to media files (e.g., `soccer.mp4` + `soccer_metadata.txt`)
- **Data File Support**: Uploads non-media files as data objects to a dedicated data flow
- **Resume Support**: Automatically resumes from where it left off if interrupted
- **Duplicate Detection**: Skips already-processed files and chunks across all flows
- **Progress Tracking**: Tracks ingestion state in source tags

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
python folder_ingestor.py \
  --folder /path/to/folder \
  --format urn:x-nmos:format:video \
  --server-url http://localhost:8000 \
  --username admin \
  --password admin
```

### With Configuration File

1. Copy `config.json.example` to `config.json`:
   ```bash
   cp config.json.example config.json
   ```

2. Edit `config.json` with your settings

3. Run with config file:
   ```bash
   python folder_ingestor.py \
     --folder /path/to/folder \
     --format urn:x-nmos:format:video \
     --config config.json
   ```

### Command Line Options

- `--folder` (required): Path to folder to ingest
- `--format` (required): Source format URN (e.g., `urn:x-nmos:format:video`, `urn:x-nmos:format:audio`)
- `--label` (optional): Source label
- `--description` (optional): Source description
- `--config` (optional): Path to JSON config file
- `--server-url` (optional): TAMS server URL (default: `http://localhost:8000`)
- `--username` (optional): TAMS username (default: `admin`)
- `--password` (optional): TAMS password (default: `admin`)
- `--chunk-duration` (optional): Chunk duration in seconds (default: 30)
- `--chunk-format` (optional): Chunk format - "original" (copy codecs, MP4) or "hls" (HLS-compatible TS with H.264/AAC) (default: original)
- `--recursive` (optional): Process subdirectories recursively
- `--verbose` (optional): Enable verbose logging

### Configuration File Format

```json
{
  "server_url": "http://localhost:8000",
  "username": "admin",
  "password": "admin",
  "chunk_duration": 30,
  "recursive": false
}
```

## How It Works

1. **Source Creation**: Creates a single source for the entire folder
   - Sets `folder_path` tag with absolute folder path
   - Sets `ingest_state` tag to track progress

2. **Media Type Detection**: Scans all files to detect media types
   - Detects video, audio, and data files
   - Groups files by type for routing to appropriate flows

3. **Flow Creation**: Creates separate flows for each detected media type
   - **Video Flow**: For video files (`urn:x-nmos:format:video`)
   - **Audio Flow**: For audio files (`urn:x-nmos:format:audio`)
   - **Data Flow**: For non-media files (`urn:x-nmos:format:data`)
   - Each flow has format-specific codec and essence parameters
   - If multiple types detected, creates a **Multi-Flow** (`urn:x-nmos:format:multi`) that collects all flows via `flow_collection`

4. **File Processing**:
   - **Media Files**: Chunked using `jthaloor-ffmpeg`
     - **Format Options**:
       - `original`: Copies original codecs to MP4 container (fast, preserves quality)
       - `hls`: Transcodes to HLS-compatible format (MPEG-TS with H.264/AAC) for streaming
     - **Marker-Based Chunking**: If a matching metadata file is found, uses markers from the file
       - Supports FFMETADATA1 format (`.txt` files with `;FFMETADATA1` header)
       - Supports JSON format (`.json` files with chapter/segment data)
       - Metadata files are matched heuristically (e.g., `soccer.mp4` + `soccer_metadata.txt`)
     - **Duration-Based Chunking**: Default 30-second segments if no metadata file found
     - Each chunk uploaded as a separate segment
     - Filename and file path stored in flow tags (mapped by object_id)
   - **Non-Media Files**: Uploaded as data files
     - Stored as segments with timerange `[0:0_0:0)`
     - Filename stored in flow tags

5. **Resume Support**:
   - On startup, queries TAMS for existing source with matching `folder_path` tag
   - Builds map of already-processed files/chunks from flow tags
   - Skips already-processed files/chunks
   - Resumes from missing chunks for partially-processed files

5. **Duplicate Detection**:
   - Uses flow tags to track which files/chunks have been processed
   - Pattern: `file_mapping_{object_id} = {filename}|{file_path}|{chunk_index}|{total_chunks}`
   - Efficiently queries once per flow, not per file

## Examples

### Ingest a Video Folder

```bash
python folder_ingestor.py \
  --folder /media/videos \
  --format urn:x-nmos:format:video \
  --label "Video Collection" \
  --description "Imported video files" \
  --chunk-duration 30
```

### Ingest an Audio Folder

```bash
python folder_ingestor.py \
  --folder /media/audio \
  --format urn:x-nmos:format:audio \
  --label "Audio Collection"
```

### Ingest with HLS Format Chunking

```bash
python folder_ingestor.py \
  --folder /media/videos \
  --format urn:x-nmos:format:video \
  --chunk-format hls \
  --chunk-duration 30
```

This will chunk files into HLS-compatible MPEG-TS segments with H.264 video and AAC audio codecs, suitable for streaming.

### Ingest Recursively

```bash
python folder_ingestor.py \
  --folder /media/mixed \
  --format urn:x-nmos:format:video \
  --recursive
```

### Resume Interrupted Ingestion

Simply run the same command again - the tool will automatically detect the existing source and resume from where it left off:

```bash
python folder_ingestor.py \
  --folder /media/videos \
  --format urn:x-nmos:format:video
```

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

### Chunking Failures

- Check that input files are valid media files
- Ensure sufficient disk space for temporary chunk files
- Check FFmpeg logs for encoding errors

## Metadata Files for Marker-Based Chunking

The tool automatically detects and uses metadata files for intelligent chunking:

### Supported Formats

1. **FFMETADATA1 Format** (`.txt` files):
   ```text
   ;FFMETADATA1
   timebase=1/1000
   
   [CHAPTER]
   TIMEBASE=1/1000
   START=0
   END=13000
   title=Segment 1
   
   [CHAPTER]
   TIMEBASE=1/1000
   START=13000
   END=28000
   title=Segment 2
   ```

2. **JSON Format** (`.json` files):
   ```json
   [
     {"start": 0.0, "end": 13.0, "title": "Segment 1"},
     {"start": 13.0, "end": 28.0, "title": "Segment 2"}
   ]
   ```
   
   Or with chapters key:
   ```json
   {
     "chapters": [
       {"start": 0.0, "end": 13.0, "title": "Segment 1"},
       {"start": 13.0, "end": 28.0, "title": "Segment 2"}
     ]
   }
   ```

### File Matching

Metadata files are matched to media files using heuristics:
- `soccer.mp4` + `soccer_metadata.txt` ✅
- `video.mov` + `video_metadata.json` ✅
- `file.mp4` + `file.metadata.txt` ✅
- `file.mp4` + `file_markers.json` ✅

Supported patterns:
- `{filename}_metadata.{txt,json}`
- `{filename}.metadata.{txt,json}`
- `{filename}_markers.{txt,json}`
- `{filename}.markers.{txt,json}`

## Notes

- Each folder becomes **one source** with **separate flows for each media type**
- When multiple media types are detected, a **multi-essence flow** is created to collect all flows
- Media files are chunked into **30-second segments** by default, or **using markers** if metadata files are found
- Files are routed to the appropriate flow based on their media type:
  - Video files → Video flow
  - Audio files → Audio flow
  - Non-media files → Data flow
- Filename and file path are stored in **flow tags** (not segment tags, as segments don't support tags in TAMS)
- The tool automatically handles resume and duplicate detection across all flows
- Progress is tracked in source tags: `ingest_state`, `files_processed`, `files_total`

