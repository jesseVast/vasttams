"""
TAMS API Models

This module provides backward compatibility by re-exporting all models.
For new code, prefer importing directly from the specific model modules.
"""

# Import all models directly from modules
from .core import *
from .sources import *
from .flows import *
from .segments import *
from .service import *
from .webhooks import *
from .storage import *
from .objects import *
from .deletion import *
from .responses import *
from .filters import *
from .legacy import *