"""
Loop Recorder Module for TAMS

Automatically deletes old segments when flows exceed their loop_recorder_duration.
"""

from .manager import LoopRecorderManager

__all__ = ['LoopRecorderManager']

