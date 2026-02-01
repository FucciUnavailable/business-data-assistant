"""
Redis cache configuration for performance optimization.
"""

import os
import redis
import json
import hashlib
from typing import Any, Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class CacheConfig:
    """Centralized cache management using Redis"""

    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', '6379'))
        self.password = os.getenv('REDIS_PASSWORD', None)
        self.default_ttl = int(os.getenv('CACHE_TTL_SECONDS', '300'))

        self._client = self._create_client()

    def _create_client(self) -> redis.Redis:
        """Create Redis client with connection pooling"""
        try:
            client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            client.ping()
            logger.info("Redis connection established")
            return client

        except redis.ConnectionError as e:
            logger.warning(f"Redis unavailable: {str(e)}. Running without cache.")
            return None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._client:
            return None

        try:
            value = self._client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)

            logger.debug(f"Cache MISS: {key}")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self._client:
            return False

        try:
            ttl = ttl or self.default_ttl
            self._client.setex(
                key,
                ttl,
                json.dumps(value, default=str)  # Handle datetime, etc.
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._client:
            return False

        try:
            self._client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (e.g., 'client:*')"""
        if not self._client:
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                deleted = self._client.delete(*keys)
                logger.info(f"Cache cleared: {deleted} keys matching '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return 0

    def generate_cache_key(self, *args, **kwargs) -> str:
        """Generate deterministic cache key from arguments"""
        # Sort kwargs for consistency
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{args}:{sorted_kwargs}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter (for rate limiting)"""
        if not self._client:
            return 0

        try:
            return self._client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {str(e)}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on existing key"""
        if not self._client:
            return False

        try:
            return self._client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Cache expire error: {str(e)}")
            return False


# Singleton instance
cache = CacheConfig()
