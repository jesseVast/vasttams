"""
TAMS Ingest Client Constants

Constants and default values for the TAMS Ingest Client module.
"""

# TAMS API Defaults
DEFAULT_TAMS_BASE_URL = "http://localhost:8000"
DEFAULT_TAMS_TIMEOUT = 30
DEFAULT_TAMS_RETRY_ATTEMPTS = 3
DEFAULT_TAMS_VERIFY_SSL = False

# TAMS API Endpoints
TAMS_ENDPOINTS = {
    "health": "/health",
    "service": "/service",
    "sources": "/sources",
    "flows": "/flows",
    "flow_segments": "/flows/{flow_id}/segments",
    "analytics": "/analytics"
}

# TAMS API Headers
TAMS_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# TAMS Data Formats
TAMS_FORMATS = {
    "VIDEO": "urn:x-nmos:format:video",
    "AUDIO": "urn:x-nmos:format:audio", 
    "DATA": "urn:x-nmos:format:data",
    "IMAGE": "urn:x-tam:format:image",
    "MULTI": "urn:x-nmos:format:multi"
}

# Source and Flow Defaults
DEFAULT_SOURCE_LABEL = "Media Source"
DEFAULT_FLOW_LABEL = "Media Flow"
DEFAULT_SOURCE_DESCRIPTION = "Media source created by TAMS Ingest Client"
DEFAULT_FLOW_DESCRIPTION = "Media flow created by TAMS Ingest Client"

# Video Processing Defaults
DEFAULT_CHUNK_DURATION = 30  # seconds
DEFAULT_SEGMENT_OVERLAP = 0  # seconds
DEFAULT_VIDEO_CODEC = "h264"
DEFAULT_AUDIO_CODEC = "aac"

# S3 Integration Defaults
DEFAULT_S3_BUCKET = "tams-videos"
DEFAULT_S3_PREFIX = "ingested"
DEFAULT_S3_REGION = "us-east-1"

# Auto-detection Defaults
DEFAULT_VIDEO_RESOLUTION = "1920x1080"
DEFAULT_VIDEO_FPS = 30
DEFAULT_VIDEO_BITRATE = "5000k"
DEFAULT_AUDIO_BITRATE = "128k"

# Error Messages
TAMS_ERRORS = {
    "SOURCE_CREATION_FAILED": "Failed to create TAMS source",
    "FLOW_CREATION_FAILED": "Failed to create TAMS flow",
    "SEGMENT_UPLOAD_FAILED": "Failed to upload segment to TAMS",
    "S3_UPLOAD_FAILED": "Failed to upload to S3",
    "MEDIA_ANALYSIS_FAILED": "Failed to analyze media properties",
    "INVALID_MEDIA_FORMAT": "Invalid media format",
    "UNSUPPORTED_MEDIA_TYPE": "Unsupported media type",
    "API_CONNECTION_FAILED": "Failed to connect to TAMS API",
    "CONFIGURATION_ERROR": "Configuration error"
}

# Media Type Detection
def get_media_type_from_extension(extension: str) -> str:
    """Get TAMS media type from file extension."""
    extension = extension.lower()
    
    if extension in SUPPORTED_VIDEO_FORMATS:
        return TAMS_FORMATS["VIDEO"]
    elif extension in SUPPORTED_AUDIO_FORMATS:
        return TAMS_FORMATS["AUDIO"]
    elif extension in SUPPORTED_IMAGE_FORMATS:
        return TAMS_FORMATS["IMAGE"]
    elif extension in SUPPORTED_DATA_FORMATS:
        return TAMS_FORMATS["DATA"]
    else:
        return TAMS_FORMATS["DATA"]  # Default to data for unknown types

def get_mime_type_from_extension(extension: str) -> str:
    """Get MIME type from file extension."""
    extension = extension.lower()
    
    # Check all format dictionaries
    for format_dict in [SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS, 
                       SUPPORTED_IMAGE_FORMATS, SUPPORTED_DATA_FORMATS]:
        if extension in format_dict:
            return format_dict[extension]
    
    return "application/octet-stream"  # Default MIME type

def get_supported_extensions() -> list:
    """Get all supported file extensions."""
    extensions = []
    for format_dict in [SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS, 
                       SUPPORTED_IMAGE_FORMATS, SUPPORTED_DATA_FORMATS]:
        extensions.extend(format_dict.keys())
    return sorted(extensions)

# Supported Video Formats
SUPPORTED_VIDEO_FORMATS = {
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".m4v": "video/x-m4v",
    ".flv": "video/x-flv",
    ".wmv": "video/x-ms-wmv"
}

# Supported Audio Formats
SUPPORTED_AUDIO_FORMATS = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".wma": "audio/x-ms-wma",
    ".opus": "audio/opus"
}

# Supported Image Formats
SUPPORTED_IMAGE_FORMATS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon"
}

# Supported Data Formats
SUPPORTED_DATA_FORMATS = {
    ".json": "application/json",
    ".xml": "application/xml",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".dat": "application/octet-stream",
    ".bin": "application/octet-stream"
}

# Video Codec Mappings
VIDEO_CODEC_MAPPINGS = {
    "h264": "libx264",
    "h265": "libx265",
    "vp8": "libvpx",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1"
}

# Audio Codec Mappings
AUDIO_CODEC_MAPPINGS = {
    "aac": "aac",
    "mp3": "libmp3lame",
    "opus": "libopus",
    "vorbis": "libvorbis",
    "flac": "flac",
    "wma": "wmav2",
    "pcm": "pcm_s16le"
}

# Image Codec Mappings
IMAGE_CODEC_MAPPINGS = {
    "jpeg": "mjpeg",
    "png": "png",
    "gif": "gif",
    "bmp": "bmp",
    "tiff": "tiff",
    "webp": "libwebp"
}

# Data Codec Mappings (for binary data)
DATA_CODEC_MAPPINGS = {
    "raw": "raw",
    "base64": "base64",
    "hex": "hex"
}

# Resolution Mappings
RESOLUTION_MAPPINGS = {
    "480p": "854x480",
    "720p": "1280x720", 
    "1080p": "1920x1080",
    "1440p": "2560x1440",
    "4k": "3840x2160",
    "8k": "7680x4320"
}

# FPS Mappings
FPS_MAPPINGS = {
    8: "8",
    15: "15",
    24: "24",
    25: "25",
    30: "30",
    50: "50",
    60: "60"
}

# Bitrate Mappings
BITRATE_MAPPINGS = {
    "low": "1000k",
    "medium": "2500k", 
    "high": "5000k",
    "ultra": "10000k"
}
