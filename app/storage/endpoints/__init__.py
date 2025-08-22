"""
TAMS endpoint-specific storage modules

This module organizes TAMS-specific storage logic by API endpoints.

TAMS API COMPLIANCE:
====================

All endpoint modules implement strict TAMS API compliance rules:

DELETE OPERATIONS:
- Sources: cascade=false fails if dependent flows exist
- Flows: cascade=false fails if dependent segments exist  
- Segments: fail if dependent objects exist
- Objects: immutable, fail if flow references exist

CASCADE OPERATIONS:
- cascade=true: deletes parent + all dependencies
- cascade=false: blocks deletion when dependencies exist
- Proper referential integrity enforcement

This ensures data consistency and prevents corruption
while maintaining TAMS API specification compliance.
"""

from .sources.sources_storage import SourcesStorage
from .flows.flows_storage import FlowsStorage
from .segments.segments_storage import SegmentsStorage
from .segments.segments_s3 import SegmentsS3
from .objects.objects_storage import ObjectsStorage
from .analytics.analytics_engine import AnalyticsEngine

__all__ = [
    "SourcesStorage",
    "FlowsStorage", 
    "SegmentsStorage",
    "SegmentsS3",
    "ObjectsStorage",
    "AnalyticsEngine"
]
