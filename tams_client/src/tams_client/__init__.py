"""
TAMS Client Library

Python client library for TAMS (Time-addressable Media Store) API.
"""

from .client import TAMSClient
from .domain.source import TAMSSource
from .domain.flow import TAMSFlow
from .domain.segment import TAMSSegment
from .exceptions import (
    TAMSClientError,
    TAMSAuthenticationError,
    TAMSAPIError,
    TAMSConnectionError
)

__version__ = "1.0.0"

__all__ = [
    "TAMSClient",
    "TAMSSource",
    "TAMSFlow",
    "TAMSSegment",
    "TAMSClientError",
    "TAMSAuthenticationError",
    "TAMSAPIError",
    "TAMSConnectionError",
]

