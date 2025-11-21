"""
Stream Ingestor Package

Ingests live video streams (SRT or OSX camera) into TAMS with configurable chunking
and loop recording support.
"""

from .ingestor import StreamIngestor

__all__ = ["StreamIngestor"]

