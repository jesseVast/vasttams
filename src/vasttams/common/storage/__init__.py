"""
Storage infrastructure for TAMS.

This module contains storage interfaces, main service, and shared
storage utilities like table initialization and timestamps.
"""

from .dependencies import get_storage_service

__all__ = ["get_storage_service"]

