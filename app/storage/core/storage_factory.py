"""
Storage factory for creating and managing core storage components

This module provides a factory pattern for creating S3Core and VASTCore instances
with proper configuration management.
"""

import logging
from typing import Optional, Dict, Any
from app.core.config import get_settings
from .s3_core import S3Core
from .vast_core import VASTCore

logger = logging.getLogger(__name__)


class StorageFactory:
    """
    Factory for creating core storage components
    
    This class manages the creation and configuration of S3Core and VASTCore
    instances based on application configuration.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize storage factory
        
        Args:
            config: Optional configuration override (uses app config if not provided)
        """
        self.config = config or {}
        self._s3_core = None
        self._vast_core = None
        
        logger.info("StorageFactory initialized")
    
    def get_s3_core(self) -> S3Core:
        """
        Get or create S3Core instance
        
        Returns:
            S3Core: Configured S3 core instance
        """
        if self._s3_core is None:
            settings = get_settings()
            
            # Use config override if provided, otherwise use app settings
            endpoint_url = self.config.get('s3_endpoint_url', settings.s3_endpoint_url)
            access_key_id = self.config.get('s3_access_key_id', settings.s3_access_key_id)
            secret_access_key = self.config.get('s3_secret_access_key', settings.s3_secret_access_key)
            bucket_name = self.config.get('s3_bucket_name', settings.s3_bucket_name)
            use_ssl = self.config.get('s3_use_ssl', getattr(settings, 's3_use_ssl', True))
            
            logger.info("Creating S3Core with endpoint: %s, bucket: %s", endpoint_url, bucket_name)
            
            self._s3_core = S3Core(
                endpoint_url=endpoint_url,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                bucket_name=bucket_name,
                use_ssl=use_ssl,
                region=self.config.get('s3_region', getattr(settings, 's3_region', 'us-east-1'))
            )
            
            logger.info("S3Core created successfully")
        
        return self._s3_core
    
    def get_vast_core(self) -> VASTCore:
        """
        Get or create VASTCore instance
        
        Returns:
            VASTCore: Configured VAST core instance
        """
        if self._vast_core is None:
            settings = get_settings()
            
            # Use config override if provided, otherwise use app settings
            vast_endpoints = self.config.get('vast_endpoints', getattr(settings, 'vast_endpoints', ['http://localhost:42000']))
            auto_connect = self.config.get('vast_auto_connect', getattr(settings, 'vast_auto_connect', True))
            
            logger.info("Creating VASTCore with endpoints: %s", vast_endpoints)
            
            self._vast_core = VASTCore(
                endpoints=vast_endpoints,
                auto_connect=auto_connect
            )
            
            logger.info("VASTCore created successfully")
        
        return self._vast_core
    
    def create_storage_components(self) -> Dict[str, Any]:
        """
        Create all storage components
        
        Returns:
            Dict: Dictionary containing all storage components
        """
        logger.info("Creating all storage components")
        
        components = {
            's3_core': self.get_s3_core(),
            'vast_core': self.get_vast_core()
        }
        
        logger.info("All storage components created successfully")
        return components
    
    def close_all(self):
        """Close all storage connections"""
        logger.info("Closing all storage connections")
        
        if self._vast_core:
            self._vast_core.close()
            self._vast_core = None
        
        # S3 doesn't have persistent connections to close
        self._s3_core = None
        
        logger.info("All storage connections closed")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about all storage components
        
        Returns:
            Dict: Storage component information
        """
        info = {}
        
        # S3 info
        if self._s3_core:
            try:
                info['s3'] = self._s3_core.get_bucket_info()
            except Exception as e:
                info['s3'] = {'error': str(e)}
        else:
            info['s3'] = {'status': 'not_initialized'}
        
        # VAST info
        if self._vast_core:
            try:
                info['vast'] = {
                    'connected': self._vast_core.is_connected(),
                    'endpoints': self._vast_core.endpoints,
                    'tables': self._vast_core.list_tables() if self._vast_core.is_connected() else []
                }
            except Exception as e:
                info['vast'] = {'error': str(e)}
        else:
            info['vast'] = {'status': 'not_initialized'}
        
        return info
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all storage components
        
        Returns:
            Dict: Health check results
        """
        logger.info("Performing storage health check")
        
        health = {
            'timestamp': str(logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))),
            'overall_status': 'unknown',
            'components': {}
        }
        
        # Check S3 health
        try:
            s3_core = self.get_s3_core()
            s3_info = s3_core.get_bucket_info()
            health['components']['s3'] = {
                'status': 'healthy' if s3_info.get('exists') else 'unhealthy',
                'details': s3_info
            }
        except Exception as e:
            health['components']['s3'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check VAST health
        try:
            vast_core = self.get_vast_core()
            health['components']['vast'] = {
                'status': 'healthy' if vast_core.is_connected() else 'unhealthy',
                'connected': vast_core.is_connected(),
                'endpoints': vast_core.endpoints
            }
        except Exception as e:
            health['components']['vast'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Determine overall status
        component_statuses = [comp['status'] for comp in health['components'].values()]
        if all(status == 'healthy' for status in component_statuses):
            health['overall_status'] = 'healthy'
        elif any(status == 'error' for status in component_statuses):
            health['overall_status'] = 'error'
        else:
            health['overall_status'] = 'degraded'
        
        logger.info("Storage health check completed: %s", health['overall_status'])
        return health
