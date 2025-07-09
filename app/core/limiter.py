# shared-types/app/core/limiter.py
"""
Rate limiting module with Redis support
"""

from typing import Optional, Callable, Dict, Tuple, List
from fastapi import Request, Response
import time
import hashlib

try:
    import redis.asyncio as redis
except ImportError:
    try:
        import aioredis as redis
    except ImportError:
        redis = None

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key from request
    Uses user ID if authenticated, IP otherwise
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Try to get real IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")
    
    return f"ip:{ip}"


class RateLimiter:
    """Simple rate limiter implementation"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        self.default_limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 100)
        self.default_window = 60  # seconds
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int = None,
        window: int = None,
        redis_client: Optional[redis.Redis] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if rate limit is exceeded
        Returns (allowed, metadata)
        """
        if not self.enabled:
            return True, {"limit": limit or self.default_limit, "remaining": -1, "reset": 0}
        
        limit = limit or self.default_limit
        window = window or self.default_window
        
        # If no Redis, always allow (with warning)
        if not redis_client:
            logger.warning("Rate limiting requested but Redis not available")
            return True, {"limit": limit, "remaining": -1, "reset": 0}
        
        try:
            now = int(time.time())
            window_start = now - window
            key = f"rate_limit:{key}:{window}"
            
            # Use simple counter approach
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()
            
            current_count = results[0]
            
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            reset = now + window
            
            metadata = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset,
                "retry_after": window if not allowed else None
            }
            
            return allowed, metadata
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow the request
            return True, {"limit": limit, "remaining": -1, "reset": 0}


class AdvancedRateLimiter:
    """Advanced rate limiter with tier support"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client = None
        self.tier_limits = {
            "free": {"requests": 60, "burst": 10},
            "pro": {"requests": 600, "burst": 100},
            "enterprise": {"requests": 6000, "burst": 1000},
        }
    
    async def get_redis(self) -> Optional[redis.Redis]:
        """Get Redis client"""
        if not redis:
            return None
            
        if not self._redis_client:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Failed to create Redis client: {e}")
                return None
        
        return self._redis_client
    
    async def check_rate_limit(
        self,
        key: str,
        cost: int = 1,
        window_seconds: int = 60,
        max_requests: int = 60,
        tier: str = "free"
    ) -> Tuple[bool, Dict]:
        """
        Check rate limit with tier support
        Returns (allowed, metadata)
        """
        redis_client = await self.get_redis()
        if not redis_client:
            # No Redis, allow but warn
            logger.warning("Advanced rate limiting requested but Redis not available")
            return True, {
                "limit": max_requests,
                "remaining": -1,
                "reset": 0,
                "tier": tier,
                "cost": cost
            }
        
        try:
            # Get tier limits
            limits = self.tier_limits.get(tier, self.tier_limits["free"])
            max_requests = limits["requests"]
            
            now = int(time.time())
            bucket_key = f"rl:{key}:{window_seconds}"
            
            # Simple sliding window implementation
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(bucket_key, 0, now - window_seconds)
            
            # Count current entries
            pipe.zcard(bucket_key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if allowed
            if current_count + cost > max_requests:
                allowed = False
            else:
                # Add new entry
                await redis_client.zadd(bucket_key, {f"{now}:{cost}": now})
                await redis_client.expire(bucket_key, window_seconds)
                allowed = True
            
            # Calculate metadata
            remaining = max(0, max_requests - current_count - (cost if allowed else 0))
            reset_time = now + window_seconds
            
            metadata = {
                "limit": max_requests,
                "remaining": remaining,
                "reset": reset_time,
                "retry_after": window_seconds if not allowed else None,
                "tier": tier,
                "cost": cost
            }
            
            return allowed, metadata
            
        except Exception as e:
            logger.error(f"Advanced rate limit check error: {e}")
            # On error, allow the request
            return True, {
                "limit": max_requests,
                "remaining": -1,
                "reset": 0,
                "tier": tier,
                "cost": cost
            }
    
    async def get_user_tier(self, user_id: str) -> str:
        """Get user's rate limit tier"""
        redis_client = await self.get_redis()
        if not redis_client:
            return "free"
        
        try:
            tier = await redis_client.get(f"user:tier:{user_id}")
            return tier or "free"
        except Exception as e:
            logger.error(f"Error getting user tier: {e}")
            return "free"


# Create instances
limiter = RateLimiter()
advanced_limiter = AdvancedRateLimiter()


# Decorator for rate limiting
def rate_limit(
    requests: int = 60,
    window: int = 60,
    cost: int = 1,
    key_func: Optional[Callable] = None
):
    """
    Rate limit decorator for endpoints
    
    Usage:
        @rate_limit(requests=10, window=60)
        async def my_endpoint():
            pass
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Skip if rate limiting is disabled
            if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
                return await func(request, *args, **kwargs)
            
            # Get rate limit key
            if key_func:
                key = await key_func(request) if asyncio.iscoroutinefunction(key_func) else key_func(request)
            else:
                key = await get_rate_limit_key(request)
            
            # Get user tier if available
            tier = "free"
            if hasattr(request.state, "user") and request.state.user:
                tier = await advanced_limiter.get_user_tier(str(request.state.user.id))
            
            # Check rate limit
            allowed, metadata = await advanced_limiter.check_rate_limit(
                key=key,
                cost=cost,
                window_seconds=window,
                max_requests=requests,
                tier=tier
            )
            
            # Add headers to response
            response = Response()
            response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
            response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
            response.headers["X-RateLimit-Reset"] = str(metadata["reset"])
            
            if not allowed:
                response.status_code = 429
                response.headers["Retry-After"] = str(metadata["retry_after"])
                response.content = b'{"detail": "Rate limit exceeded"}'
                response.media_type = "application/json"
                return response
            
            # Call the actual function
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Export everything
__all__ = [
    "limiter",
    "advanced_limiter",
    "rate_limit",
    "get_rate_limit_key",
    "RateLimiter",
    "AdvancedRateLimiter"
]

import asyncio