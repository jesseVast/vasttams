"""
FFmpeg Probe Utility

Probes media files using ffprobe to extract essence parameters.
"""

import subprocess
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def probe_file(file_path: str) -> Dict[str, Any]:
    """
    Probe a media file using ffprobe.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Dict containing probe data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        subprocess.CalledProcessError: If ffprobe fails
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
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
            check=True
        )
        
        probe_data = json.loads(result.stdout)
        return probe_data
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe failed: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output: {e}")
        raise


def extract_video_essence_parameters(probe_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract video essence parameters from ffprobe data.
    
    Args:
        probe_data: FFprobe output data
        
    Returns:
        Dict with essence_parameters structure for TAMS
    """
    video_stream = None
    audio_stream = None
    
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "video" and not video_stream:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and not audio_stream:
            audio_stream = stream
    
    if not video_stream:
        raise ValueError("No video stream found in file")
    
    # Extract frame dimensions
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    
    # Extract frame rate
    frame_rate_str = video_stream.get("r_frame_rate", "0/1")
    avg_frame_rate_str = video_stream.get("avg_frame_rate", "0/1")
    
    # Check for variable frame rate
    # VFR is indicated when r_frame_rate (reported) differs from avg_frame_rate (average)
    # or when avg_frame_rate is 0/0 (unknown/undefined)
    vfr = False
    if avg_frame_rate_str:
        if avg_frame_rate_str == "0/0":
            # Unknown/undefined frame rate indicates VFR
            vfr = True
        elif frame_rate_str != avg_frame_rate_str:
            # Reported frame rate differs from average, indicating VFR
            vfr = True
    
    essence_params = {
        "frame_width": width,
        "frame_height": height,
        "vfr": vfr
    }
    
    # Only set frame_rate if vfr is False (fixed frame rate)
    # TAMS 8.0: If vfr=True, frame_rate MUST NOT be set
    if not vfr:
        if "/" in frame_rate_str:
            num, den = map(int, frame_rate_str.split("/"))
            if den > 0:  # Avoid division by zero
                essence_params["frame_rate"] = {"numerator": num, "denominator": den}
        else:
            try:
                frame_rate_val = float(frame_rate_str)
                if frame_rate_val > 0:
                    essence_params["frame_rate"] = {"numerator": int(frame_rate_val * 1000), "denominator": 1000}
            except (ValueError, TypeError):
                pass  # Skip invalid frame rate
    
    # Optional fields
    if "bit_depth" in video_stream:
        essence_params["bit_depth"] = int(video_stream["bit_depth"])
    if "pix_fmt" in video_stream:
        essence_params["pixel_format"] = video_stream["pix_fmt"]
    if "color_space" in video_stream:
        essence_params["colorspace"] = video_stream["color_space"]
    if "color_primaries" in video_stream:
        essence_params["color_primaries"] = video_stream["color_primaries"]
    if "color_trc" in video_stream:
        essence_params["transfer_characteristic"] = video_stream["color_trc"]
    
    return essence_params


def extract_audio_essence_parameters(probe_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract audio essence parameters from ffprobe data.
    
    Args:
        probe_data: FFprobe output data
        
    Returns:
        Dict with essence_parameters structure for TAMS
    """
    audio_stream = None
    
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio" and not audio_stream:
            audio_stream = stream
    
    if not audio_stream:
        raise ValueError("No audio stream found in file")
    
    essence_params = {
        "sample_rate": int(audio_stream.get("sample_rate", 0)),
        "channels": int(audio_stream.get("channels", 0))
    }
    
    if "bits_per_sample" in audio_stream:
        essence_params["bit_depth"] = int(audio_stream["bits_per_sample"])
    
    return essence_params


def probe_and_extract_essence_parameters(file_path: str, format_type: str) -> Dict[str, Any]:
    """
    Probe file and extract essence parameters based on format.
    
    Args:
        file_path: Path to media file
        format_type: TAMS format URN (e.g., "urn:x-nmos:format:video")
        
    Returns:
        Dict with essence_parameters for the flow
    """
    probe_data = probe_file(file_path)
    
    if "urn:x-nmos:format:video" in format_type:
        return extract_video_essence_parameters(probe_data)
    elif "urn:x-nmos:format:audio" in format_type:
        return extract_audio_essence_parameters(probe_data)
    else:
        raise ValueError(f"Unsupported format for auto-probe: {format_type}")

