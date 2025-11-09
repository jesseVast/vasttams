"""
Media file detection using ffprobe.

Detects if a file is a video, audio, or non-media file.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def detect_media_type(file_path: str) -> Optional[str]:
    """
    Detect if a file is a video, audio, or non-media file using ffprobe.
    
    Args:
        file_path: Path to the file to detect
        
    Returns:
        "video" if video file, "audio" if audio file, None if non-media or error
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        logger.warning(f"File not found: {file_path}")
        return None
    
    try:
        # Use ffprobe to detect file type
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30  # 30 second timeout for probe
        )
        
        probe_data = json.loads(result.stdout)
        
        # Check streams for video or audio
        has_video = False
        has_audio = False
        
        for stream in probe_data.get("streams", []):
            codec_type = stream.get("codec_type", "").lower()
            if codec_type == "video":
                has_video = True
            elif codec_type == "audio":
                has_audio = True
        
        # Determine media type
        if has_video:
            return "video"
        elif has_audio:
            return "audio"
        else:
            # File exists but has no video/audio streams - treat as non-media
            return None
            
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timeout for {file_path} - treating as non-media")
        return None
    except subprocess.CalledProcessError as e:
        # ffprobe failed - likely not a media file
        logger.debug(f"ffprobe failed for {file_path}: {e.stderr if e.stderr else 'unknown error'}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse ffprobe output for {file_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error detecting media type for {file_path}: {e}")
        return None

