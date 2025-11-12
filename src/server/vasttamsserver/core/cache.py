"""
Redis Cache Service with Graceful Degradation

Provides caching functionality with automatic TTL expiration.
If Redis is unavailable, all operations silently fail and the application
continues without caching.
"""

import json
import logging
import asyncio
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta

try:
    import redis.asyncio as aioredis
    from redis.asyncio import ConnectionPool, Redis
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
        TimeoutError as RedisTimeoutError,
        RedisError,
        AuthenticationError as RedisAuthenticationError
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None
    ConnectionPool = None
    Redis = None
    RedisConnectionError = None
    RedisTimeoutError = None
    RedisAuthenticationError = None

from .config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis cache service with graceful degradation.
    
    All operations are safe - they never raise exceptions.
    If Redis is unavailable, operations return None or do nothing.
    """
    
    def __init__(self):
        """Initialize cache service."""
        self.settings = get_settings()
        self._redis: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self._enabled = False
        self._available = False
        self._consecutive_failures = 0
        self._last_health_check: Optional[datetime] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_count = 0
        self._health_check_success_count = 0
        self._health_check_failure_count = 0
        self._key_prefix = "tams"
        
        if REDIS_AVAILABLE and self.settings.redis_enabled:
            self._enabled = True
            logger.info("Redis cache initialization enabled")
            logger.info(f"Redis configuration: host={self.settings.redis_host}, port={self.settings.redis_port}, "
                       f"db={self.settings.redis_db}, ssl={self.settings.redis_ssl}, "
                       f"max_connections={self.settings.redis_max_connections}")
            # Note: _initialize will be called asynchronously
            # We can't await here in __init__, so connection happens lazily
        else:
            if not REDIS_AVAILABLE:
                logger.warning("Redis library not available, caching disabled")
            elif not self.settings.redis_enabled:
                logger.info("Redis caching disabled via configuration")
    
    async def _ensure_initialized(self):
        """Ensure Redis connection is initialized (lazy initialization)."""
        if self._enabled and not self._redis and not self._health_check_task:
            logger.debug("Redis not initialized yet, attempting initialization...")
            await self._initialize()
        elif self._enabled and not self._redis and self._health_check_task:
            logger.debug("Redis initialization in progress or failed, health check task exists")
    
    async def _initialize(self):
        """Initialize Redis connection."""
        logger.info("Initializing Redis cache connection...")
        try:
            await self._connect()
            # Start health check task only if connection succeeded
            if self._available:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                logger.info("Redis cache initialization completed successfully")
            else:
                logger.warning("Redis connection failed during initialization, health check task not started")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}. Application will continue without caching.", exc_info=True)
            self._available = False
    
    async def _connect(self):
        """Connect to Redis."""
        if not self._enabled:
            return
        
        logger.info(f"Connecting to Redis at {self.settings.redis_host}:{self.settings.redis_port} (db={self.settings.redis_db})...")
        
        try:
            # Build connection parameters
            connection_params = {
                "host": self.settings.redis_host,
                "port": self.settings.redis_port,
                "db": self.settings.redis_db,
                "socket_timeout": self.settings.redis_socket_timeout,
                "socket_connect_timeout": self.settings.redis_socket_connect_timeout,
                "decode_responses": False,  # We'll handle encoding/decoding ourselves
            }
            
            # Handle password - check for both None and empty string
            if self.settings.redis_password and self.settings.redis_password.strip():
                connection_params["password"] = self.settings.redis_password
                logger.debug("Redis password authentication enabled")
            else:
                logger.debug("Redis password not set (using no authentication)")
            
            if self.settings.redis_ssl:
                connection_params["ssl"] = True
                logger.debug("Redis SSL/TLS enabled")
            
            logger.debug(f"Creating Redis connection pool (max_connections={self.settings.redis_max_connections})...")
            # Create connection pool
            self._pool = ConnectionPool(
                **connection_params,
                max_connections=self.settings.redis_max_connections
            )
            
            logger.debug("Creating Redis client...")
            # Create Redis client
            self._redis = Redis(connection_pool=self._pool)
            
            # Test connection
            logger.debug("Testing Redis connection (ping)...")
            await self._redis.ping()
            
            self._available = True
            self._consecutive_failures = 0
            logger.info(f"✅ Redis cache connected successfully to {self.settings.redis_host}:{self.settings.redis_port} (db={self.settings.redis_db})")
            
        except Exception as e:
            # Check if it's a Redis-specific exception
            if REDIS_AVAILABLE and isinstance(e, (RedisConnectionError, RedisTimeoutError, RedisAuthenticationError)):
                logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
                logger.warning(f"Connection attempt was to {self.settings.redis_host}:{self.settings.redis_port} (db={self.settings.redis_db})")
                logger.warning(f"Exception type: {type(e).__name__}")
            else:
                logger.error(f"Unexpected error connecting to Redis: {e}", exc_info=True)
                logger.error(f"Connection attempt was to {self.settings.redis_host}:{self.settings.redis_port} (db={self.settings.redis_db})")
                logger.error(f"Exception type: {type(e).__name__}")
            self._available = False
            self._consecutive_failures += 1
    
    async def _health_check_loop(self):
        """Periodic health check and reconnection."""
        logger.info(f"Redis health check loop started (interval: {self.settings.redis_health_check_interval}s)")
        
        while self._enabled:
            try:
                await asyncio.sleep(self.settings.redis_health_check_interval)
                
                self._health_check_count += 1
                self._last_health_check = datetime.now()
                
                if not self._available:
                    # Try to reconnect
                    logger.info(f"Redis health check #{self._health_check_count}: Not available, attempting to reconnect...")
                    await self._connect()
                    if self._available:
                        self._health_check_success_count += 1
                        logger.info(f"✅ Redis health check #{self._health_check_count}: Reconnection successful")
                    else:
                        self._health_check_failure_count += 1
                        logger.warning(f"❌ Redis health check #{self._health_check_count}: Reconnection failed (consecutive failures: {self._consecutive_failures})")
                else:
                    # Check if still connected
                    try:
                        start_time = datetime.now()
                        await self._redis.ping()
                        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                        
                        self._consecutive_failures = 0
                        self._health_check_success_count += 1
                        logger.info(f"✅ Redis health check #{self._health_check_count}: Ping successful ({elapsed_ms:.1f}ms) - "
                                   f"Stats: {self._health_check_success_count} success, {self._health_check_failure_count} failures")
                    except Exception as e:
                        self._available = False
                        self._consecutive_failures += 1
                        self._health_check_failure_count += 1
                        logger.warning(f"❌ Redis health check #{self._health_check_count}: Ping failed - {type(e).__name__}: {e} "
                                     f"(consecutive failures: {self._consecutive_failures})")
                        
            except asyncio.CancelledError:
                logger.info("Redis health check loop cancelled")
                break
            except Exception as e:
                self._health_check_failure_count += 1
                logger.error(f"Error in Redis health check loop: {e}", exc_info=True)
    
    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self._key_prefix}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes for Redis."""
        try:
            if isinstance(value, (str, int, float, bool)):
                # Simple types - store as JSON string
                return json.dumps(value).encode('utf-8')
            elif isinstance(value, (dict, list)):
                # Complex types - JSON encode
                return json.dumps(value, default=str).encode('utf-8')
            else:
                # Fallback: convert to string and JSON encode
                return json.dumps(str(value), default=str).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize cache value: {e}")
            raise
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from Redis bytes."""
        try:
            if value is None:
                return None
            decoded = value.decode('utf-8')
            return json.loads(decoded)
        except Exception as e:
            logger.error(f"Failed to deserialize cache value: {e}")
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (without prefix)
            
        Returns:
            Cached value or None if not found/unavailable
        """
        await self._ensure_initialized()
        
        if not self._available:
            return None
        
        try:
            full_key = self._make_key(key)
            value = await self._redis.get(full_key)
            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None
            
            deserialized = self._deserialize(value)
            logger.debug(f"Cache hit: {key}")
            return deserialized
            
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache get failed (connection error): {key} - {e}")
            self._available = False
            self._consecutive_failures += 1
            return None
        except Exception as e:
            logger.debug(f"Cache get failed: {key} - {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key (without prefix)
            value: Value to cache
            ttl: Time to live in seconds (uses default from settings if None)
            
        Returns:
            True if successful, False otherwise (never raises)
        """
        await self._ensure_initialized()
        
        if not self._available:
            return False
        
        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            
            if ttl is None:
                ttl = self.settings.tams_cache_ttl
            
            await self._redis.setex(full_key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            self._consecutive_failures = 0
            return True
            
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache set failed (connection error): {key} - {e}")
            self._available = False
            self._consecutive_failures += 1
            return False
        except Exception as e:
            logger.debug(f"Cache set failed: {key} - {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key (without prefix)
            
        Returns:
            True if successful, False otherwise (never raises)
        """
        await self._ensure_initialized()
        
        if not self._available:
            return False
        
        try:
            full_key = self._make_key(key)
            result = await self._redis.delete(full_key)
            logger.debug(f"Cache delete: {key}")
            return bool(result)
            
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache delete failed (connection error): {key} - {e}")
            self._available = False
            self._consecutive_failures += 1
            return False
        except Exception as e:
            logger.debug(f"Cache delete failed: {key} - {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key (without prefix)
            
        Returns:
            True if exists, False otherwise
        """
        await self._ensure_initialized()
        
        if not self._available:
            return False
        
        try:
            full_key = self._make_key(key)
            result = await self._redis.exists(full_key)
            return bool(result)
            
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache exists check failed (connection error): {key} - {e}")
            self._available = False
            self._consecutive_failures += 1
            return False
        except Exception as e:
            logger.debug(f"Cache exists check failed: {key} - {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "flow:*" or "flows:source:123*")
            
        Returns:
            Number of keys deleted (0 if unavailable)
        """
        await self._ensure_initialized()
        
        if not self._available:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            # Use SCAN to find matching keys (safer than KEYS for large datasets)
            deleted_count = 0
            async for key in self._redis.scan_iter(match=full_pattern):
                await self._redis.delete(key)
                deleted_count += 1
            
            logger.debug(f"Cache clear pattern: {pattern} ({deleted_count} keys deleted)")
            return deleted_count
            
        except (ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache clear pattern failed (connection error): {pattern} - {e}")
            self._available = False
            self._consecutive_failures += 1
            return 0
        except Exception as e:
            logger.debug(f"Cache clear pattern failed: {pattern} - {e}")
            return 0
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get cache service status.
        
        Returns:
            Dict with status information
        """
        # Ensure Redis is initialized before checking status
        if self._enabled:
            try:
                await self._ensure_initialized()
            except Exception as e:
                logger.warning(f"Failed to ensure Redis initialization during status check: {e}")
        
        status = {
            "enabled": self._enabled,
            "available": self._available,
            "redis_connected": False,
            "consecutive_failures": self._consecutive_failures,
            "health_check_interval_seconds": self.settings.redis_health_check_interval,
            "health_check_count": self._health_check_count,
            "health_check_success_count": self._health_check_success_count,
            "health_check_failure_count": self._health_check_failure_count,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }
        
        if self._available and self._redis:
            try:
                start_time = datetime.now()
                await self._redis.ping()
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                status["redis_connected"] = True
                status["ping_latency_ms"] = round(elapsed_ms, 2)
            except Exception as e:
                logger.debug(f"Redis ping failed during status check: {e}")
                status["redis_connected"] = False
                status["available"] = False
                status["last_error"] = str(e)
        elif self._enabled and not self._available:
            # Redis is enabled but not available - log why
            logger.debug(f"Redis is enabled but not available. Redis client exists: {self._redis is not None}, "
                        f"consecutive failures: {self._consecutive_failures}")
            status["last_error"] = f"Not connected (consecutive failures: {self._consecutive_failures})"
        
        return status
    
    async def close(self):
        """Close Redis connections."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.debug(f"Error closing Redis connection: {e}")
        
        if self._pool:
            try:
                await self._pool.aclose()
            except Exception as e:
                logger.debug(f"Error closing Redis pool: {e}")
        
        self._available = False
        logger.info("Redis cache service closed")

