"""
Shared pytest configuration and fixtures for the TAMS test suite.
This file runs before any tests and sets up the testing environment.
"""

import warnings
import sys
import os
import requests
import pytest
from pathlib import Path

# Set environment variable to suppress warnings at Python level
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add the app directory to the Python path for imports
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Suppress all deprecation warnings before any imports
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# Suppress all warnings to keep test output clean
warnings.simplefilter("ignore")

# Import settings for BASE_URL
try:
    from vasttams.core.config import get_settings
    settings = get_settings()
    BASE_URL = f"http://{settings.host}:{settings.port}"
except Exception:
    BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def auth_headers():
    """
    Fixture that provides authentication headers for test requests.
    Logs in as admin and returns Bearer token headers.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin", "password": "vastdata"},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                return {"Authorization": f"Bearer {token}"}
        # Fallback to empty headers if login fails
        return {}
    except Exception as e:
        # If login fails, return empty headers (tests will fail with 401)
        return {}


@pytest.fixture(scope="session")
def auth_token(auth_headers):
    """Extract just the token from auth_headers for convenience"""
    auth_header = auth_headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    return None


def get_auth_headers():
    """
    Helper function to get auth headers (for use in test fixtures).
    Returns empty dict if login fails.
    """
    try:
        from vasttams.core.config import get_settings
        settings = get_settings()
        base_url = f"http://{settings.host}:{settings.port}"
    except Exception:
        base_url = "http://localhost:8000"
    
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json={"username": "admin", "password": "vastdata"},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                return {"Authorization": f"Bearer {token}"}
    except Exception:
        pass
    return {}
