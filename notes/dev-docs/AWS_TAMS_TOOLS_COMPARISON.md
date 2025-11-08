# AWS TAMS Tools Implementation Comparison

## Overview

The AWS TAMS Tools repository (https://github.com/aws-samples/time-addressable-media-store-tools) provides a reference implementation and web UI for the AWS TAMS API. This document compares their implementation features with ours.

## Key Features in AWS TAMS Tools

### 1. **MediaConvert Integration** ✅ Reference Implementation

**AWS Implementation:**
- Browse and monitor MediaConvert jobs using TAMS as input
- View job status, progress, and configuration
- Create export jobs from TAMS content

**Our Status:** ❌ Not implemented

**Recommendation:** We should add MediaConvert/transcoding job management as an optional module.

### 2. **HLS API Endpoint** ✅ Reference Implementation

**AWS Implementation:**
- HLS API endpoint for playing TAMS content
- Basic video player in WebUI
- Uses Object Lambda for dynamic content delivery

**Our Status:** ❌ Not implemented

**Recommendation:** Add an HLS manifest generation API for video playback.

### 3. **HLS Ingest** ✅ Reference Implementation

**AWS Implementation:**
- Ingest from MediaLive channels (HLS output)
- Ingest from MediaConvert jobs (HLS output)
- Ingest from external HLS manifest URLs
- Automatic flow creation

**Our Status:** ⚠️ Partial
- We have segment ingest
- Missing HLS-specific ingest workflows

**Recommendation:** Add HLS manifest parsing and automatic segment creation.

### 4. **FFmpeg Integration** ✅ Reference Implementation

**AWS Implementation:**
- Export via FFmpeg
- Conversion via FFmpeg (Rule-based or Batch)
- Configurable FFmpeg commands via SSM Parameter Store

**Our Status:** ❌ Not implemented

**Recommendation:** Add FFmpeg transcoding support as an optional module.

### 5. **Replication** ✅ Reference Implementation

**AWS Implementation:**
- Replicate content between TAMS stores
- Replicate to external systems
- Configurable connections via SSM Parameter Store

**Our Status:** ❌ Not implemented

**Recommendation:** Add content replication functionality.

### 6. **Loop Recorder** ✅ Reference Implementation

**AWS Implementation:**
- Automatically deletes older segments when flows exceed duration
- Triggered by `flows/segments_added` events
- Maintains flow duration based on `loop_recorder_duration` tag

**Our Status:** ❌ Not implemented (but easy to add)

**Recommendation:** Add event-driven segment cleanup for loop recording.

### 7. **Export Modal** ✅ Reference Implementation

**AWS Implementation:**
- Configurable export operations
- Defined via JSON in SSM Parameter Store
- Dynamic export configuration

**Our Status:** ❌ Not implemented

**Recommendation:** Add configurable export functionality.

## Comparison Matrix

| Feature | AWS TAMS Tools | Our Implementation | Status |
|---------|----------------|-------------------|--------|
| **Core TAMS API** | ✅ Full | ✅ Full | ✅ Complete |
| **Web UI** | ✅ Yes | ❌ No | Missing |
| **MediaConvert Integration** | ✅ Yes | ❌ No | Missing |
| **HLS API Endpoint** | ✅ Yes | ❌ No | Missing |
| **HLS Ingest** | ✅ Yes | ⚠️ Partial | Needs enhancement |
| **FFmpeg Integration** | ✅ Yes | ❌ No | Missing |
| **Replication** | ✅ Yes | ❌ No | Missing |
| **Loop Recorder** | ✅ Yes | ❌ No | Easy to add |
| **Export Configuration** | ✅ Yes | ❌ No | Missing |
| **Presigned URLs** | ✅ Yes | ✅ Yes | Complete |
| **Webhooks** | ✅ Yes | ✅ Yes | Complete |
| **Event Notifications** | ✅ Yes | ✅ Yes | Complete |

## Implementation Recommendations

### High Priority Features

#### 1. **Loop Recorder** (Easy Win)

**Implementation:**
```python
# In events/manager.py - add loop recorder logic
async def _check_loop_recorder_duration(self, flow_id: str):
    """Check if flow exceeds loop_recorder_duration and delete old segments"""
    flow = await self._get_flow(flow_id)
    
    if not flow.tags or 'loop_recorder_duration' not in flow.tags:
        return
    
    duration_limit = int(flow.tags['loop_recorder_duration'])
    
    # Get all segments
    segments = await self._get_flow_segments(flow_id)
    
    if flow.timerange and segments:
        total_duration = self._calculate_duration(flow.timerange)
        
        if total_duration > duration_limit:
            # Delete oldest segments until duration is within limit
            await self._delete_excess_segments(flow_id, duration_limit)
```

**Benefit:** Automatic flow duration management for live/loop recording scenarios.

#### 2. **HLS Manifest Generation** (Medium Priority)

**Implementation:**
```python
# New endpoint: GET /flows/{flow_id}/hls/manifest.m3u8
@router.get("/{flow_id}/hls/manifest.m3u8")
async def get_hls_manifest(flow_id: str):
    """Generate HLS manifest for flow"""
    # Generate M3U8 playlist with segments
    # Use get_urls for media URLs
    # Support master playlist and media playlists
    ...
```

**Benefit:** Enable video playback from TAMS content.

#### 3. **SSM Parameter Store Configuration** (Medium Priority)

**Implementation:**
- Store configuration in AWS Systems Manager Parameter Store
- Support for:
  - Export operations configuration
  - FFmpeg commands
  - Replication connections
  - Codec mappings

**Benefit:** Runtime configuration without code changes.

### Medium Priority Features

#### 4. **Transcoding Support**

**Implementation:**
- Add FFmpeg integration for conversion
- Rule-based automatic conversion
- Batch conversion support
- Store conversion rules in database

#### 5. **Content Replication**

**Implementation:**
- Replicate content to other TAMS stores
- External system replication
- Bi-directional sync
- Event-driven or scheduled replication

### Lower Priority (Nice to Have)

#### 6. **Web UI**

**Implementation:**
- Build a web interface similar to AWS TAMS Tools
- Browse sources, flows, and segments
- Video player integration
- Job management interface

#### 7. **MediaConvert Integration**

**Implementation:**
- Interface with AWS MediaConvert
- Create jobs from TAMS content
- Monitor job status
- Export functionality

## AWS TAMS Tools Architecture

### Deployment Model
- **Core Stack**: SAM-based deployment
- **Optional Components**: Deployable via CloudFormation parameters
- **Frontend**: Vite-based React application
- **Backend**: Serverless Lambda functions

### Key Components

1. **TAMS API Integration**: Uses AWS TAMS API
2. **Cognito Auth**: Same user pool as TAMS API
3. **Object Lambda**: For HLS manifest generation
4. **Step Functions**: For orchestration
5. **EventBridge**: For event-driven workflows

### Our Architecture vs. AWS TAMS Tools

| Aspect | AWS TAMS Tools | Our Implementation |
|--------|----------------|-------------------|
| **API Layer** | Serverless Lambda | FastAPI (Monolithic) |
| **Database** | DynamoDB | VAST Database |
| **Storage** | S3 | S3 ✅ |
| **Auth** | Cognito | Custom (JWT, Basic, URL Token) |
| **Events** | EventBridge | Custom EventManager ✅ |
| **Frontend** | React + Vite | Not implemented |

## Recommendations Summary

### ✅ Immediate Actions
1. **Add Loop Recorder** - Easy, high-value feature
2. **Add HLS Manifest Generation** - Enable video playback
3. **Document Export Configuration** - Support dynamic exports

### ⚠️ Medium-Term Goals
1. **Add FFmpeg Integration** - Transcoding support
2. **Add Replication** - Multi-store sync
3. **Add SSM Configuration** - Runtime configuration

### 🎯 Long-Term Goals
1. **Build Web UI** - User interface for TAMS
2. **Add MediaConvert Integration** - Production workflows
3. **Add More Transcoding Options** - Broader format support

## Conclusion

Our implementation is **fully compliant with TAMS 8.0 spec** and has a solid foundation. AWS TAMS Tools adds valuable production features on top of the core API.

**Key Gaps:**
- Missing: Web UI, transcoding, replication
- Partial: HLS support
- Complete: Core TAMS API, webhooks, presigned URLs

**Best Match with AWS:** 
- We both use presigned URLs for uploads ✅
- We both use S3 for storage ✅
- We both support webhooks ✅
- We differ in deployment (Serverless vs. Monolithic)

**Recommendation:**
- Keep our architecture (FastAPI + VAST Database)
- Add AWS TAMS Tools-style features as optional modules
- Focus on Loop Recorder and HLS support first

