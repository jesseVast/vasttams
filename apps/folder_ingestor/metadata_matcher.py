"""
Metadata file matching and detection.

Heuristically matches metadata files to media files and detects marker formats.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, List

logger = logging.getLogger(__name__)


def match_metadata_to_media(media_file: Path, all_files: List[Path]) -> Optional[Path]:
    """
    Heuristically match a metadata file to a media file.
    
    Matches patterns like:
    - soccer.mp4 + soccer_metadata.txt
    - video.mov + video_metadata.json
    - file.mp4 + file_metadata.txt
    - file.mp4 + file.metadata.json
    
    Args:
        media_file: Path to the media file
        all_files: List of all files in the folder
        
    Returns:
        Path to matching metadata file, or None if not found
    """
    media_stem = media_file.stem
    media_dir = media_file.parent
    
    # Common metadata file patterns
    patterns = [
        f"{media_stem}_metadata.txt",
        f"{media_stem}_metadata.json",
        f"{media_stem}.metadata.txt",
        f"{media_stem}.metadata.json",
        f"{media_stem}_markers.txt",
        f"{media_stem}_markers.json",
        f"{media_stem}.markers.txt",
        f"{media_stem}.markers.json",
    ]
    
    for pattern in patterns:
        metadata_path = media_dir / pattern
        if metadata_path in all_files:
            logger.debug(f"Matched metadata file {metadata_path.name} to {media_file.name}")
            return metadata_path
    
    return None


def detect_metadata_format(metadata_file: Path) -> Optional[str]:
    """
    Detect if a metadata file is FFMETADATA1 or JSON format.
    
    Args:
        metadata_file: Path to metadata file
        
    Returns:
        "ffmetadata" if FFMETADATA1 format, "json" if JSON format, None if neither
    """
    if not metadata_file.exists():
        return None
    
    try:
        # Check file extension first
        ext = metadata_file.suffix.lower()
        if ext == ".json":
            # Try to parse as JSON
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if it has the expected structure
                if isinstance(data, (list, dict)):
                    # Check if it looks like marker data
                    if isinstance(data, list):
                        # Array of segments
                        if len(data) > 0 and isinstance(data[0], dict):
                            if 'start' in data[0] and 'end' in data[0]:
                                return "json"
                    elif isinstance(data, dict):
                        # Object with chapters key
                        if 'chapters' in data and isinstance(data['chapters'], list):
                            if len(data['chapters']) > 0 and isinstance(data['chapters'][0], dict):
                                if 'start' in data['chapters'][0] and 'end' in data['chapters'][0]:
                                    return "json"
        
        # Check for FFMETADATA1 format
        with open(metadata_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line == ";FFMETADATA1":
                return "ffmetadata"
            
            # Also check if file contains [CHAPTER] markers
            content = f.read()
            if "[CHAPTER]" in content and ("START=" in content or "END=" in content):
                return "ffmetadata"
    
    except (json.JSONDecodeError, UnicodeDecodeError, IOError) as e:
        logger.debug(f"Error detecting metadata format for {metadata_file}: {e}")
        return None
    
    return None


def find_metadata_files(folder: Path, all_files: List[Path]) -> Dict[Path, Path]:
    """
    Find all metadata files and match them to media files.
    
    Args:
        folder: Folder path
        all_files: List of all files in the folder
        
    Returns:
        Dict mapping media file paths to metadata file paths
    """
    metadata_map: Dict[Path, Path] = {}
    
    # Find all media files
    media_files = []
    for file_path in all_files:
        if file_path.is_file():
            # Check if it's a media file (has common video/audio extensions)
            ext = file_path.suffix.lower()
            if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', 
                      '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']:
                media_files.append(file_path)
    
    # Match metadata files to media files
    for media_file in media_files:
        metadata_file = match_metadata_to_media(media_file, all_files)
        if metadata_file:
            # Verify it's a valid marker format
            format_type = detect_metadata_format(metadata_file)
            if format_type in ("ffmetadata", "json"):
                metadata_map[media_file] = metadata_file
                logger.info(f"📎 Found metadata file: {metadata_file.name} -> {media_file.name} ({format_type} format)")
            else:
                logger.debug(f"Metadata file {metadata_file.name} is not a valid marker format")
    
    return metadata_map

