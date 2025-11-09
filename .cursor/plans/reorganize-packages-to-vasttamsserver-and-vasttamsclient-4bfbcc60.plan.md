<!-- 4bfbcc60-1e1c-4ba3-b763-bb765e060d46 99aa9da1-7322-46a6-90e3-ba2653d129ab -->
# Folder Ingestor Application

## Overview

Create `apps/folder_ingestor/` application that ingests all files from a folder into TAMS. Each folder becomes one source and one flow. Media files are chunked into 30-second segments, non-media files are stored as data files.

## Structure

```
apps/folder_ingestor/
├── README.md
├── requirements.txt
├── folder_ingestor.py (main application)
├── media_processor.py (handles chunking via jthaloor-ffmpeg)
├── file_detector.py (uses ffprobe to detect media files)
└── config.json.example (example configuration)
```

## Implementation Details

### 1. Main Application (`folder_ingestor.py`)

- **CLI Interface**: Accept folder path, source format, label, description via argparse
- **Config File Support**: Optional JSON config file for additional settings (TAMS server URL, credentials, chunk duration, etc.)
- **Workflow**:

  1. Validate folder exists and is readable
  2. Create TAMS client connection
  3. Create source with format, label, description
  4. Set source tag `folder_path` with absolute folder path
  5. Detect all files in folder (recursive or flat - need to decide)
  6. For each file:

     - Use ffprobe to detect if media (video/audio)
     - If media: chunk and upload segments
     - If non-media: upload as data file

  1. Create single flow for the source
  2. Upload all segments/data files to the flow

### 2. Media Detection (`file_detector.py`)

- Use `ffprobe` to detect file type
- Function: `detect_media_type(file_path: str) -> Optional[str]`
- Returns: `"video"`, `"audio"`, or `None` (non-media)
- Handle ffprobe errors gracefully (non-media files will fail)

### 3. Media Processing (`media_processor.py`)

- **Dependency**: Install `jthaloor-ffmpeg` from `~/Developer/gitlab/jthaloor-ffmpeg` (local install)
- **Chunking**: Use jthaloor-ffmpeg's chunk output functionality to split media into 30s chunks
- **Function**: `chunk_media_file(file_path: str, chunk_duration: int = 30) -> List[Path]`
- Returns list of chunk file paths
- Each chunk will be uploaded as a separate segment

### 4. TAMS Integration

- **Source Creation**: 
  - Format from CLI/config
  - Label and description from CLI/config
  - Tag `folder_path` with absolute path
- **Flow Creation**:
  - Single flow per folder
  - Format matches source format
  - Codec determined from first media file (or default)
  - Essence parameters from first video/audio file
- **Segment Creation**:
  - Each media chunk becomes a segment
  - Segment tag `filename` with original filename
  - Segment tag `chunk_index` with chunk number
  - Timerange calculated based on chunk position
- **Data Files**:
  - Non-media files uploaded as data objects
  - Need to research TAMS data file handling (may need to create objects directly or use a special flow type)

### 5. Configuration

- **CLI Arguments**:
  - `--folder` (required): Path to folder to ingest
  - `--format` (required): Source format URN (e.g., `urn:x-nmos:format:video`)
  - `--label` (optional): Source label
  - `--description` (optional): Source description
  - `--config` (optional): Path to JSON config file
  - `--server-url` (optional): TAMS server URL
  - `--username` (optional): TAMS username
  - `--password` (optional): TAMS password
  - `--chunk-duration` (optional): Chunk duration in seconds (default: 30)
- **Config File** (JSON):
  ```json
  {
    "server_url": "http://localhost:8000",
    "username": "user",
    "password": "pass",
    "chunk_duration": 30,
    "recursive": false
  }
  ```


### 6. Error Handling

- Handle missing files gracefully
- Handle ffprobe failures (treat as non-media)
- Handle chunking failures (log and continue)
- Handle upload failures (retry logic or skip)
- Provide progress feedback

### 7. Dependencies

- `vasttamsclient` (from `../src/client`)
- `jthaloor-ffmpeg` (local install from `~/Developer/gitlab/jthaloor-ffmpeg`)
- `ffmpeg`/`ffprobe` (system dependency)

## Files to Create/Modify

1. `apps/folder_ingestor/folder_ingestor.py` - Main application entry point
2. `apps/folder_ingestor/media_processor.py` - Media chunking using jthaloor-ffmpeg
3. `apps/folder_ingestor/file_detector.py` - Media file detection using ffprobe
4. `apps/folder_ingestor/requirements.txt` - Dependencies
5. `apps/folder_ingestor/README.md` - Usage documentation
6. `apps/folder_ingestor/config.json.example` - Example configuration
7. Update `apps/README.md` - Add folder_ingestor to available applications

## Key Implementation Notes

- **jthaloor-ffmpeg Integration**: Need to research the module's API for chunking. May need to:
  - Create a VideoProcessor instance
  - Configure chunk output
  - Process file and collect chunk paths
- **Data Files**: Research TAMS 8.0 spec for handling non-media files. May need to:
  - Create objects with appropriate content-type
  - Use a data flow type or special handling
- **Segment Timerange**: Calculate timerange for each chunk based on:
  - Chunk index * chunk_duration
  - Need to handle frame rate for accurate timestamps
- **Async Processing**: Use asyncio for concurrent uploads where possible
- **Duplicate Detection Performance**:
  - Query segments once per flow (not per file) using tag filters
  - Build in-memory lookup: `{file_path: {chunk_indices}}`
  - Use TAMS API tag filtering: `/flows/{flow_id}/segments?tag.file_path={path}`
  - Cache segment list during processing to avoid repeated queries
  - Only re-query if process is interrupted and resumed
- **Resume Efficiency**:
  - Single API call to list all segments with tag filters
  - Parse segment tags to build processing state map
  - No local state files needed (all state in TAMS tags)
  - Minimal overhead: one segment list query per resume

### To-dos

- [ ] Research jthaloor-ffmpeg module API for chunking functionality - understand how to use VideoProcessor and chunk outputs
- [ ] Research TAMS 8.0 specification for handling non-media data files - understand object creation and flow types
- [ ] Create file_detector.py module with ffprobe-based media detection (video/audio/non-media)
- [ ] Create media_processor.py module using jthaloor-ffmpeg for 30s chunking
- [ ] Create folder_ingestor.py main application with CLI, config file support, and TAMS integration
- [ ] Create requirements.txt with dependencies (vasttamsclient, jthaloor-ffmpeg, etc.)
- [ ] Create README.md and config.json.example with usage instructions and examples
- [ ] Update apps/README.md to include folder_ingestor in available applications list