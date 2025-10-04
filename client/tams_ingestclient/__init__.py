"""
TAMS Ingest Client Module

A unified client for uploading videos to TAMS (Time-addressable Media Store) service.
Provides source and flow management with automatic parameter detection and S3 integration.
"""

from .unified import UnifiedTAMSIngestClient, ingest_video_unified, create_source_unified, create_flow_unified
from .media_analyzer import UnifiedMediaAnalyzer, MediaAnalysisResult
from .config import TAMSIngestConfig
from .models import (
    Source,
    VideoFlow,
    FlowSegment,
    VideoIngestRequest,
    VideoIngestResult,
    VideoIngestRequestUpdated,
    VideoIngestResultUpdated,
    TAMSSegment,
    VideoAnalysisResult,
    Tags,
    ContentFormat,
    MimeType,
    TimeRange,
    TAMSSourceConfig,
    TAMSFlowConfig,
    SourceType,
    FlowType
)
from .constants import (
    DEFAULT_TAMS_BASE_URL,
    DEFAULT_TAMS_TIMEOUT,
    DEFAULT_TAMS_RETRY_ATTEMPTS,
    DEFAULT_TAMS_VERIFY_SSL,
    TAMS_FORMATS,
    TAMS_ENDPOINTS,
    DEFAULT_SOURCE_LABEL,
    DEFAULT_FLOW_LABEL,
    DEFAULT_CHUNK_DURATION,
    DEFAULT_SEGMENT_OVERLAP,
    get_media_type_from_extension,
    get_mime_type_from_extension,
    get_supported_extensions
)

__version__ = "1.0.0"
__all__ = [
    # Main Classes
    "UnifiedTAMSIngestClient",
    "TAMSIngestConfig",
    "UnifiedMediaAnalyzer",
    "MediaAnalysisResult",
    # Official API Models
    "Source",
    "VideoFlow",
    "FlowSegment",
    "Tags",
    "ContentFormat",
    "MimeType",
    "TimeRange",
    # Ingest Client Models
    "VideoIngestRequest",
    "VideoIngestResult",
    "TAMSSegment",
    "VideoAnalysisResult",
    "TAMSSourceConfig",
    "TAMSFlowConfig",
    "SourceType",
    "FlowType",
    # Functions
    "ingest_video_unified",
    "create_source_unified",
    "create_flow_unified",
    # Constants
    "DEFAULT_TAMS_BASE_URL",
    "DEFAULT_TAMS_TIMEOUT",
    "DEFAULT_TAMS_RETRY_ATTEMPTS",
    "DEFAULT_TAMS_VERIFY_SSL",
    "TAMS_FORMATS",
    "TAMS_ENDPOINTS",
    "DEFAULT_SOURCE_LABEL",
    "DEFAULT_FLOW_LABEL",
    "DEFAULT_CHUNK_DURATION",
    "DEFAULT_SEGMENT_OVERLAP",
    # Media Type Detection Functions
    "get_media_type_from_extension",
    "get_mime_type_from_extension",
    "get_supported_extensions"
]
