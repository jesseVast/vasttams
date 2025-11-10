"""
Detect embedded chapter markers in video files using ffprobe.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def detect_embedded_chapters(video_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Detect embedded chapter markers in a video file using ffprobe.
    
    Args:
        video_path: Path to video file
        
    Returns:
        List of chapter dictionaries with 'start', 'end', and optionally 'title' keys,
        or None if no chapters found or error occurred
    """
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        logger.warning(f"Video file not found: {video_path}")
        return None
    
    try:
        # Use ffprobe to extract chapters
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_chapters",
            "-of", "json",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        probe_data = json.loads(result.stdout)
        chapters = probe_data.get("chapters", [])
        
        if not chapters:
            logger.debug(f"No embedded chapters found in {video_path_obj.name}")
            return None
        
        # Convert ffprobe chapter format to our format
        # ffprobe chapters have: id, time_base, start, start_time, end, end_time, tags
        chapter_list = []
        for chapter in chapters:
            start_time = float(chapter.get("start_time", 0))
            end_time = float(chapter.get("end_time", 0))
            
            # Get title from tags if available
            title = None
            if "tags" in chapter:
                title = chapter["tags"].get("title") or chapter["tags"].get("TITLE")
            
            chapter_list.append({
                "start": start_time,
                "end": end_time,
                "title": title
            })
        
        logger.info(f"Found {len(chapter_list)} embedded chapter markers in {video_path_obj.name}")
        return chapter_list
        
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timeout for {video_path} - no embedded chapters detected")
        return None
    except subprocess.CalledProcessError as e:
        logger.debug(f"ffprobe error for {video_path}: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse ffprobe output for {video_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error detecting embedded chapters in {video_path}: {e}")
        return None


def has_embedded_chapters(video_path: str) -> bool:
    """
    Quick check if video file has embedded chapter markers.
    
    Args:
        video_path: Path to video file
        
    Returns:
        True if embedded chapters are detected, False otherwise
    """
    chapters = detect_embedded_chapters(video_path)
    return chapters is not None and len(chapters) > 0

