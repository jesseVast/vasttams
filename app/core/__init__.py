"""
Core module for TAMS API
Contains configuration, dependencies, utilities, and telemetry
"""

from .config import Settings, get_settings, update_settings
# Import dependencies separately to avoid circular imports
from .utils import *
from .telemetry import TelemetryManager

__all__ = [
    "Settings",
    "get_settings", 
    "update_settings",
    "TelemetryManager"
] 