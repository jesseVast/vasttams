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
from typing import Optional
from datetime import datetime, timezone, timedelta

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
    from vasttamsserver.core.config import get_settings
    settings = get_settings()
    BASE_URL = f"http://{settings.host}:{settings.port}"
except Exception:
    BASE_URL = "http://localhost:8000"


def _get_token_cache_path():
    """Get path to token cache file (shared across all test processes)"""
    import tempfile
    import os
    cache_dir = os.path.join(tempfile.gettempdir(), "vasttamsserver_test_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "auth_token.json")


def _is_token_valid(token: str) -> bool:
    """Check if JWT token is still valid (not expired)"""
    try:
        import jwt
        
        # Decode without verification to check expiration
        # We don't need to verify signature for expiration check
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Check expiration
        exp = decoded.get("exp")
        if exp:
            exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            # Consider token valid if it expires in more than 5 minutes
            # This gives us a buffer to avoid using tokens that expire mid-test
            return exp_time > (now + timedelta(minutes=5))
        
        return False
    except Exception:
        return False


def _load_cached_token() -> Optional[str]:
    """Load cached token from file if it exists and is valid"""
    import json
    import os
    
    cache_path = _get_token_cache_path()
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
            token = cache_data.get("token")
            if token and _is_token_valid(token):
                return token
    except Exception:
        pass
    
    return None


def _save_cached_token(token: str):
    """Save token to cache file with file locking to prevent race conditions"""
    import json
    import os
    
    cache_path = _get_token_cache_path()
    
    try:
        # Use file locking to prevent race conditions when multiple processes write
        # fcntl is Unix-only, but works on macOS and Linux
        try:
            import fcntl
            with open(cache_path, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump({"token": token, "cached_at": datetime.now(timezone.utc).isoformat()}, f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except ImportError:
            # Windows doesn't have fcntl, but that's okay - just write without locking
            # Worst case: multiple processes write the same token, which is fine
            with open(cache_path, 'w') as f:
                json.dump({"token": token, "cached_at": datetime.now(timezone.utc).isoformat()}, f)
    except Exception:
        # If we can't save cache, that's okay - we'll just re-authenticate
        pass


def _get_auth_headers_internal():
    """
    Internal function to get auth headers with automatic token refresh.
    This function checks token validity and refreshes if needed.
    """
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Try to load cached token first
    cached_token = _load_cached_token()
    if cached_token:
        # Check if token is still valid (with 5-minute buffer)
        if _is_token_valid(cached_token):
            logger.debug("Using cached authentication token")
            return {"Authorization": f"Bearer {cached_token}"}
        else:
            logger.debug("Cached token expired or expiring soon, re-authenticating")
    
    # Need to authenticate (either no cache or expired)
    max_retries = 5
    base_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # Exponential backoff: 0.5s, 1s, 2s, 4s, 8s
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logger.debug(f"Waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
            
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"username": "admin", "password": "vastdata"},
                timeout=10  # Increased timeout for parallel execution
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                if token:
                    # Save token to cache for future use
                    _save_cached_token(token)
                    headers = {"Authorization": f"Bearer {token}"}
                    logger.info(f"Authentication successful on attempt {attempt + 1}")
                    return headers
                else:
                    logger.warning(f"Login returned 200 but no token in response (attempt {attempt + 1})")
            else:
                logger.warning(f"Login failed with status {response.status_code} on attempt {attempt + 1}: {response.text[:200]}")
            
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
        except requests.exceptions.Timeout as e:
            logger.warning(f"Timeout error on attempt {attempt + 1}: {e}")
        except Exception as e:
            logger.warning(f"Exception during login on attempt {attempt + 1}: {e}")
    
    # If all retries fail, raise an error instead of returning empty headers
    # This will cause ALL tests that depend on auth_headers to fail immediately with a clear error
    error_msg = f"CRITICAL: Failed to authenticate after {max_retries} attempts. Server may not be running or credentials incorrect. All tests requiring authentication will fail."
    logger.error(error_msg)
    # Use pytest.fail() to ensure all dependent tests fail with a clear message
    pytest.fail(error_msg, pytrace=False)


@pytest.fixture(scope="session")
def auth_headers():
    """
    Fixture that provides authentication headers for test requests.
    Uses token caching to avoid re-authenticating for every test.
    Tokens are cached in a file shared across all test processes.
    Automatically refreshes tokens if they expire during long test runs.
    
    Token cache location: /tmp/vasttams_test_cache/auth_token.json
    Tokens are valid for 30 minutes (JWT default), but we re-authenticate
    if token expires within 5 minutes to avoid mid-test expiration.
    
    For long test runs, the fixture will automatically refresh expired tokens.
    """
    # Return a dict-like object that checks token validity on each access
    # This allows the token to be refreshed during long test runs
    class AuthHeaders:
        def __init__(self):
            self._headers = None
            self._last_check = 0
        
        def _refresh_if_needed(self):
            """Refresh headers if token is expired or expiring soon"""
            import time
            # Check token validity every 5 minutes or if headers not set
            now = time.time()
            if self._headers is None or (now - self._last_check) > 300:  # Check every 5 minutes
                self._headers = _get_auth_headers_internal()
                self._last_check = now
            else:
                # Quick check: verify token is still valid
                token = self._headers.get("Authorization", "").replace("Bearer ", "")
                if token and not _is_token_valid(token):
                    # Token expired, refresh it
                    self._headers = _get_auth_headers_internal()
                    self._last_check = now
        
        def __getitem__(self, key):
            self._refresh_if_needed()
            return self._headers[key]
        
        def get(self, key, default=None):
            self._refresh_if_needed()
            return self._headers.get(key, default)
        
        def keys(self):
            self._refresh_if_needed()
            return self._headers.keys()
        
        def values(self):
            self._refresh_if_needed()
            return self._headers.values()
        
        def items(self):
            self._refresh_if_needed()
            return self._headers.items()
        
        def __contains__(self, key):
            self._refresh_if_needed()
            return key in self._headers
    
    return AuthHeaders()


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
    WARNING: This function will raise an exception if authentication fails.
    Use the auth_headers fixture in tests instead of calling this directly.
    """
    try:
        from vasttamsserver.core.config import get_settings
        settings = get_settings()
        base_url = f"http://{settings.host}:{settings.port}"
    except Exception:
        base_url = "http://localhost:8000"
    
    response = requests.post(
        f"{base_url}/auth/login",
        json={"username": "admin", "password": "vastdata"},
        timeout=5
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to authenticate: {response.status_code} - {response.text}")
    
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Login succeeded but no access_token in response")
    
    return {"Authorization": f"Bearer {token}"}


# Register test tracker plugin (must be at end of file)
# Plugin hooks are now in test_tracker.py
pytest_plugins = ["test_tracker"]
