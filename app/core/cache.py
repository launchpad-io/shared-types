# app/core/cache.py
"""
Enhanced cache module with Redis support and fallback
"""

from typing import Any, Optional, Callable, Union, TypeVar, Generic, List
from functools import wraps
import json
import pickle
import hashlib
from datetime import timedelta
from contextlib import asynccontextmanager
import asyncio
import secrets
import time

# Redis is optional - will work without it
try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    try:
        import aioredis as redis
        HAS_REDIS = True
    except ImportError:
        redis = None
        HAS_REDIS = False

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class CacheBackend:
    """Base cache backend interface"""
    
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        raise NotImplementedError
    
    async def delete(self, key: str) -> None:
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        raise NotImplementedError
    
    async def expire(self, key: str, seconds: int) -> None:
        raise NotImplementedError
    
    async def clear_pattern(self, pattern: str) -> int:
        raise NotImplementedError


class RedisBackend(CacheBackend):
    """Redis cache backend"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            # Try to deserialize
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Try pickle for complex objects
                try:
                    return pickle.loads(value)
                except:
                    # Return as string
                    return value.decode() if isinstance(value, bytes) else value
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        try:
            # Serialize value
            if isinstance(value, (str, int, float)):
                serialized = str(value)
            else:
                try:
                    serialized = json.dumps(value)
                except (TypeError, ValueError):
                    # Use pickle for complex objects
                    serialized = pickle.dumps(value)
            
            if expire:
                await self.redis.setex(key, expire, serialized)
            else:
                await self.redis.set(key, serialized)
                
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
    
    async def delete(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> None:
        try:
            await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {e}")
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.error(f"Redis clear pattern error for {pattern}: {e}")
            return 0


class MemoryBackend(CacheBackend):
    """In-memory cache backend (fallback)"""
    
    def __init__(self):
        self._cache = {}
        self._expires = {}
    
    async def get(self, key: str) -> Optional[Any]:
        # Check expiration
        if key in self._expires and self._expires[key] < time.time():
            await self.delete(key)
            return None
        
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        self._cache[key] = value
        
        if expire:
            self._expires[key] = time.time() + expire
    
    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        self._expires.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        return key in self._cache
    
    async def expire(self, key: str, seconds: int) -> None:
        if key in self._cache:
            self._expires[key] = time.time() + seconds
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (simple glob matching)"""
        import fnmatch
        keys_to_delete = [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            await self.delete(key)
        return len(keys_to_delete)


class CacheManager:
    """
    Enhanced cache manager with Redis and fallback support
    """
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or MemoryBackend()
        self._prefix = getattr(settings, 'CACHE_KEY_PREFIX', 'tsc')
    
    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create namespaced cache key"""
        parts = [self._prefix]
        if namespace:
            parts.append(namespace)
        parts.append(key)
        return ":".join(parts)
    
    async def get(
        self, 
        key: str, 
        namespace: Optional[str] = None,
        default: Optional[T] = None
    ) -> Optional[T]:
        """Get value from cache"""
        full_key = self._make_key(key, namespace)
        value = await self.backend.get(full_key)
        return value if value is not None else default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[Union[int, timedelta]] = None,
        namespace: Optional[str] = None
    ) -> None:
        """Set value in cache"""
        full_key = self._make_key(key, namespace)
        
        if isinstance(expire, timedelta):
            expire = int(expire.total_seconds())
        
        await self.backend.set(full_key, value, expire)
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> None:
        """Delete value from cache"""
        full_key = self._make_key(key, namespace)
        await self.backend.delete(full_key)
    
    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """Check if key exists"""
        full_key = self._make_key(key, namespace)
        return await self.backend.exists(full_key)
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace"""
        pattern = f"{self._prefix}:{namespace}:*"
        return await self.backend.clear_pattern(pattern)
    
    async def get_or_set(
        self,
        key: str,
        func: Callable,
        expire: Optional[Union[int, timedelta]] = None,
        namespace: Optional[str] = None
    ) -> Any:
        """Get from cache or compute and set"""
        value = await self.get(key, namespace)
        if value is not None:
            return value
        
        # Compute value
        value = await func() if asyncio.iscoroutinefunction(func) else func()
        
        # Cache it
        await self.set(key, value, expire, namespace)
        
        return value
    
    @asynccontextmanager
    async def lock(
        self,
        key: str,
        timeout: int = 10,
        namespace: str = "locks"
    ):
        """Distributed lock using cache"""
        lock_key = self._make_key(key, namespace)
        lock_value = secrets.token_urlsafe(16)
        
        # Try to acquire lock
        if isinstance(self.backend, RedisBackend):
            acquired = await self.backend.redis.set(
                lock_key, lock_value, nx=True, ex=timeout
            )
        else:
            # Memory backend
            if not await self.backend.exists(lock_key):
                await self.backend.set(lock_key, lock_value, timeout)
                acquired = True
            else:
                acquired = False
        
        if not acquired:
            raise RuntimeError(f"Could not acquire lock for {key}")
        
        try:
            yield
        finally:
            # Release lock only if we own it
            current_value = await self.backend.get(lock_key)
            if current_value == lock_value:
                await self.backend.delete(lock_key)


# Global cache instance
_cache_instance: Optional[CacheManager] = None


async def get_cache() -> CacheManager:
    """Get or create cache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        # For now, use memory backend
        # Redis can be added later when available
        _cache_instance = CacheManager(MemoryBackend())
        logger.info("Cache initialized with memory backend")
    
    return _cache_instance


# Cache key builder
def cache_key(*args, **kwargs) -> str:
    """Build cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    
    # Create hash for long keys
    key_str = ":".join(key_parts)
    if len(key_str) > 200:
        key_str = hashlib.md5(key_str.encode()).hexdigest()
    
    return key_str


# Decorator for caching function results
def cached(
    expire: Union[int, timedelta] = 300,
    namespace: Optional[str] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching async function results
    
    Args:
        expire: Cache expiration in seconds or timedelta
        namespace: Cache namespace
        key_builder: Custom key builder function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get cache instance
            cache = await get_cache()
            
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key = cache_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache.get(key, namespace)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(key, result, expire, namespace)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in async context
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Tag-based cache invalidation
class TaggedCache:
    """Cache with tag-based invalidation"""
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self.tag_namespace = "tags"
    
    async def set_with_tags(
        self,
        key: str,
        value: Any,
        tags: List[str],
        expire: Optional[Union[int, timedelta]] = None,
        namespace: Optional[str] = None
    ):
        """Set value with tags"""
        # Set the value
        await self.cache.set(key, value, expire, namespace)
        
        # Store tags
        for tag in tags:
            tag_key = f"{self.tag_namespace}:{tag}"
            tagged_keys = await self.cache.get(tag_key, default=[])
            if key not in tagged_keys:
                tagged_keys.append(key)
                await self.cache.set(tag_key, tagged_keys)
    
    async def invalidate_tag(self, tag: str):
        """Invalidate all keys with a tag"""
        tag_key = f"{self.tag_namespace}:{tag}"
        tagged_keys = await self.cache.get(tag_key, default=[])
        
        # Delete all tagged keys
        for key in tagged_keys:
            await self.cache.delete(key)
        
        # Delete the tag list
        await self.cache.delete(tag_key)
        
        return len(tagged_keys)


# Export main components
__all__ = [
    "CacheManager",
    "get_cache",
    "cached",
    "cache_key",
    "TaggedCache",
    "CacheBackend",
    "RedisBackend",
    "MemoryBackend"
]

# Backward compatibility
cache_key_wrapper = cached  # Old name
cache = cached  # Alias for decorator usage in routers