"""
TAMS segments endpoint storage module

This module handles TAMS-specific segment operations including:
- Segment creation and storage
- Segment metadata management
- Segment retrieval and querying
"""

from .segments_storage import SegmentsStorage
from .segments_s3 import SegmentsS3

__all__ = [
    "SegmentsStorage",
    "SegmentsS3"
]
