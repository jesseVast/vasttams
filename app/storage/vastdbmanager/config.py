"""Configuration constants for VastDBManager"""

# Configuration Constants - Easy to adjust for troubleshooting
# 
# TROUBLESHOOTING GUIDE:
# - If batch operations are too slow: Increase DEFAULT_BATCH_SIZE (e.g., 200, 500)
# - If you get memory errors: Decrease DEFAULT_BATCH_SIZE (e.g., 50, 25)
# - If parallel processing isn't working: Decrease PARALLEL_THRESHOLD (e.g., 5)
# - If you get too many concurrent connections: Decrease DEFAULT_MAX_WORKERS (e.g., 2)
# - If operations fail intermittently: Increase DEFAULT_MAX_RETRIES (e.g., 5)
# - If VAST connections timeout: Increase VAST_TIMEOUT (e.g., 60)
#
DEFAULT_BATCH_SIZE = 100  # Default batch size for insert operations
DEFAULT_MAX_WORKERS = 4   # Default number of parallel workers for batch operations
PARALLEL_THRESHOLD = 10   # Threshold above which parallel processing is used
VAST_TIMEOUT = 30         # VAST connection timeout in seconds
DEFAULT_MAX_RETRIES = 3   # Default maximum retry attempts for failed operations
