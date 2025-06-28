from typing import Optional, Any, Callable
from functools import wraps
import json
import hashlib
import redis.asyncio as redis
from app.core.config import settings
import pickle
import asyncio

class CacheManager:
    """
    Enterprise cache manager with multiple strategies
    """
    def __init__(self, redis_url: str):
        self.redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=100,
            decode_responses=False  # For binary data
        )
    
    async def get_redis(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.redis_pool)
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        redis_client = await self.get_redis()
        value = await redis_client.get(key)
        
        if value:
            try:
                return pickle.loads(value)
            except:
                return json.loads(value)
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set value in cache with options"""
        redis_client = await self.get_redis()
        
        # Serialize value
        try:
            serialized = pickle.dumps(value)
        except:
            serialized = json.dumps(value).encode()
        
        return await redis_client.set(
            key,
            serialized,
            ex=ttl or settings.CACHE_TTL_SECONDS,
            nx=nx,  # Only set if not exists
            xx=xx   # Only set if exists
        )
    
    async def delete(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        redis_client = await self.get_redis()
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await redis_client.delete(*keys)
        return 0
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache for a specific user"""
        await self.delete(f"*:user:{user_id}:*")
    
    async def invalidate_campaign_cache(self, campaign_id: str):
        """Invalidate all cache for a specific campaign"""
        await self.delete(f"*:campaign:{campaign_id}:*")

# Global cache manager
cache_manager = CacheManager(settings.REDIS_URL)

def cached(
    ttl: int = 300,
    prefix: str = "cache",
    key_builder: Optional[Callable] = None,
    condition: Optional[Callable] = None
):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix
        key_builder: Custom key builder function
        condition: Function to determine if result should be cached
    
    Usage:
        @cached(ttl=3600, prefix="user_profile")
        async def get_user_profile(user_id: str):
            # Expensive operation
            return profile
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_manager._make_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result if condition met
            if condition is None or condition(result):
                await cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        # Add cache invalidation method
        wrapper.invalidate = lambda *args, **kwargs: cache_manager.delete(
            cache_manager._make_key(prefix, *args, **kwargs)
        )
        
        return wrapper
    return decorator

# Specialized cache decorators
cache_user_data = cached(ttl=600, prefix="user")
cache_campaign_data = cached(ttl=300, prefix="campaign")
cache_analytics_data = cached(ttl=3600, prefix="analytics")