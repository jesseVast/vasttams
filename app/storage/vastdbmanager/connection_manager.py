"""Connection management for VastDBManager"""

import logging
import vastdb
from typing import List, Union, Optional

from .config import VAST_TIMEOUT

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages VAST database connections and endpoints"""
    
    def __init__(self, endpoints: Union[str, List[str]]):
        """
        Initialize connection manager
        
        Args:
            endpoints: Single endpoint string or list of endpoints
        """
        # Convert single endpoint to list for consistency
        if isinstance(endpoints, str):
            self.endpoints = [endpoints]
        else:
            self.endpoints = endpoints
        
        self.connection = None
        self.bucket = None
        self.schema = None
        
        logger.info(f"Initialized ConnectionManager with {len(self.endpoints)} endpoints")
    
    def connect(self):
        """Connect to VAST database using the first available endpoint"""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            
            # Use first endpoint for connection
            endpoint = self.endpoints[0]
            self.connection = vastdb.connect(
                endpoint=endpoint,
                access=settings.vast_access_key,
                secret=settings.vast_secret_key,
                timeout=VAST_TIMEOUT
            )
            
            # Store bucket and schema names
            self.bucket = settings.vast_bucket
            self.schema = settings.vast_schema
            
            # Setup schema
            self._setup_schema()
            logger.info(f"Connected to VAST database at {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to connect to VAST database: {e}")
            raise
    
    def _setup_schema(self):
        """Setup database schema and discover existing tables"""
        try:
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                
                # Ensure schema exists
                schema = bucket.schema(self.schema, fail_if_missing=False)
                if schema is None:
                    schema = bucket.create_schema(self.schema)
                    logger.info(f"Schema '{self.schema}' created")
                else:
                    logger.info(f"Schema '{self.schema}' already exists")
                
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
            raise
    
    def connect_to_endpoint(self, endpoint: Optional[str] = None):
        """Connect to a specific VAST database endpoint"""
        try:
            if endpoint is None:
                endpoint = self.endpoints[0]  # Use first endpoint as fallback
            
            from app.core.config import get_settings
            settings = get_settings()
            
            self.connection = vastdb.connect(
                endpoint=endpoint,
                access=settings.vast_access_key,
                secret=settings.vast_secret_key,
                timeout=30
            )
            
            logger.info(f"Connected to VAST database at {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to connect to VAST database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from VAST database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from VAST database")
    
    def is_connected(self) -> bool:
        """Check if connected to VAST database"""
        return self.connection is not None
    
    def get_connection(self):
        """Get the current VAST connection"""
        return self.connection
    
    def get_bucket(self) -> str:
        """Get the current bucket name"""
        return self.bucket
    
    def get_schema(self) -> str:
        """Get the current schema name"""
        return self.schema
