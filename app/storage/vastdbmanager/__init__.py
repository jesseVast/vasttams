"""VastDBManager - Modular VAST database management with hybrid analytics"""

from .core import VastDBManager

__version__ = "2.0.0"
__all__ = ['VastDBManager']

# Backward compatibility - import the main class
VastDBManager = VastDBManager
