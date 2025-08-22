"""
Shared pytest configuration and fixtures for the TAMS test suite.
This file runs before any tests and sets up the testing environment.
"""

import warnings
import sys
import os
from pathlib import Path

# Set environment variable to suppress warnings at Python level
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add the app directory to the Python path for imports
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Suppress all deprecation warnings before any imports
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# Suppress all warnings to keep test output clean
warnings.simplefilter("ignore")
