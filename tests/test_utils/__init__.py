"""
Test Utilities Module

This module provides shared utilities, mocks, and helpers for all test modules.
"""

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test data storage
test_data = {
    "source_id": None,
    "flow_id": None,
    "object_ids": [],
    "segment_ids": [],
    "collection_ids": []
}

from .mock_vastdbmanager import mock_vastdbmanager, MockVastDBManager
from .mock_s3store import mock_s3store, MockS3Store
from .test_helpers import (
    test_data_factory,
    mock_helper,
    assertion_helper,
    test_setup_helper,
    TestDataFactory,
    MockHelper,
    AssertionHelper,
    TestSetupHelper
)
# Note: Endpoint-specific test utilities are in test_endpoints/test_utils.py

__all__ = [
    'BASE_URL',
    'test_data',
    'mock_vastdbmanager',
    'MockVastDBManager',
    'mock_s3store',
    'MockS3Store',
    'test_data_factory',
    'mock_helper',
    'assertion_helper',
    'test_setup_helper',
    'TestDataFactory',
    'MockHelper',
    'AssertionHelper',
    'TestSetupHelper'
]
