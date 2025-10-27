"""
Load TAMS 8.0 example data for use in tests.

This module provides functions to load example data from the tams-8.0/api/examples
directory for use in tests.
"""

import json
from pathlib import Path
from typing import Dict, Any, List


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


def get_examples_dir() -> Path:
    """Get the path to the TAMS 8.0 examples directory"""
    return get_project_root() / "tams-8.0" / "api" / "examples"


def load_example(example_name: str) -> Dict[str, Any]:
    """
    Load an example JSON file from tams-8.0/api/examples/
    
    Args:
        example_name: Name of the example file (e.g., "source-get-200-basic.json")
    
    Returns:
        Parsed JSON data from the example file
    
    Example:
        >>> example = load_example("source-get-200-basic.json")
        >>> print(example["id"])
    """
    examples_dir = get_examples_dir()
    example_path = examples_dir / example_name
    
    if not example_path.exists():
        raise FileNotFoundError(f"Example file not found: {example_path}")
    
    with open(example_path, 'r') as f:
        return json.load(f)


def load_example_list(example_name: str) -> List[Dict[str, Any]]:
    """
    Load an example JSON file that contains a list
    
    Args:
        example_name: Name of the example file
    
    Returns:
        List of parsed JSON objects
    
    Example:
        >>> sources = load_example_list("sources-get-200.json")
        >>> print(len(sources))
    """
    data = load_example(example_name)
    
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "data" in data:
        return data["data"]
    else:
        return [data]


# Convenience functions for common examples
def get_source_example() -> Dict[str, Any]:
    """Get a basic source example"""
    return load_example("source-get-200-basic.json")


def get_video_flow_example() -> Dict[str, Any]:
    """Get a video flow example with fixed frame rate"""
    return load_example("flow-get-200-video-h264.json")


def get_vfr_flow_example() -> Dict[str, Any]:
    """Get a video flow example with variable frame rate (VFR)"""
    return load_example("flow-get-200-video-h264-vfr.json")


def get_objects_example() -> Dict[str, Any]:
    """Get an objects example"""
    return load_example("objects-get-200.json")


def get_segments_example() -> List[Dict[str, Any]]:
    """Get flow segments example"""
    return load_example_list("flow-segments-get-200.json")

