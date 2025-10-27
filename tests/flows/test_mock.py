#!/usr/bin/env python3
"""
Mock Tests for Flows

Unit tests for flows using mocked dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.flows.models import VideoFlow, VideoEssenceParameters
from test_examples import get_video_flow_example, get_vfr_flow_example

import logging
logger = logging.getLogger(__name__)


class TestFlowModels:
    """Unit tests for Flow models using TAMS 8.0 example data"""
    
    def test_create_video_flow_from_example(self):
        """Test creating a VideoFlow from TAMS 8.0 example"""
        example = get_video_flow_example()
        
        # Create essence parameters from example
        essence_params = VideoEssenceParameters(**example["essence_parameters"])
        
        # Create flow
        flow = VideoFlow(
            id=example["id"],
            source_id=example["source_id"],
            format=example["format"],
            codec=example["codec"],
            label=example.get("label"),
            essence_parameters=essence_params,
            container=example.get("container"),
            avg_bit_rate=example.get("avg_bit_rate")
        )
        
        assert flow.id == example["id"]
        assert flow.source_id == example["source_id"]
        assert flow.format == "urn:x-nmos:format:video"
        assert essence_params.frame_width == example["essence_parameters"]["frame_width"]
        assert essence_params.frame_height == example["essence_parameters"]["frame_height"]
    
    def test_create_vfr_flow_from_example(self):
        """Test creating a VFR flow from TAMS 8.0 example"""
        example = get_vfr_flow_example()
        
        # Create essence parameters with VFR
        essence_params = VideoEssenceParameters(**example["essence_parameters"])
        
        # Create flow
        flow = VideoFlow(
            id=example["id"],
            source_id=example["source_id"],
            format=example["format"],
            codec=example["codec"],
            label=example.get("label"),
            essence_parameters=essence_params
        )
        
        assert flow.id == example["id"]
        assert essence_params.vfr == True
        assert essence_params.frame_rate is None  # VFR flows don't have frame_rate
    
    def test_vfr_validation(self):
        """Test VFR validation per ADR-0041"""
        # Valid: VFR=true, no frame_rate
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            vfr=True,
            frame_rate=None  # Must be None for VFR
        )
        assert essence_params.vfr == True
        assert essence_params.frame_rate is None
        
        # Valid: VFR=false, frame_rate set
        essence_params = VideoEssenceParameters(
            frame_width=1920,
            frame_height=1080,
            vfr=False,
            frame_rate={
                "numerator": 25,
                "denominator": 1
            }
        )
        assert essence_params.vfr == False
        assert essence_params.frame_rate is not None


# Note: Service layer tests would require extensive mocking of dependencies
# and would create circular import issues. These tests are better suited
# for integration testing (test_database.py) or contract testing.
#
# class TestFlowServiceMock:
#     """Unit tests for Flow storage service using mocks - skipped due to circular imports"""
#     pass

