"""
Folder Ingestor Package

Ingests files from folders into TAMS with support for chunking, metadata-based splitting,
and multi-essence flows.
"""

from .ingestor import FolderIngestor

__all__ = ["FolderIngestor"]

