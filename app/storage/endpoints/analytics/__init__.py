"""
TAMS analytics endpoint storage module

This module handles TAMS-specific analytics operations including:
- Flow usage analytics
- Storage usage analytics
- Time range analysis
- Performance metrics
"""

from .analytics_engine import AnalyticsEngine

__all__ = [
    "AnalyticsEngine"
]
