"""
Type definitions and constants for folder ingestor.
"""

from typing import Dict, Optional, Set, Tuple
from pathlib import Path

# Type aliases
ProcessedMap = Dict[str, Set[int]]  # file_path -> set of chunk indices
FlowsDict = Dict[str, str]  # media_type -> flow_id
MetadataMap = Dict[Path, Path]  # media_file -> metadata_file

