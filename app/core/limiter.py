from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request, Response
from typing import Optional, Callable
import redis.asyncio as redis
from app.core.config import settings
import hashlib
import json
import time

# Custom key function that uses user ID if authenticated, IP otherwise
async def get_rate_limit_key(request: Request) -> str:
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Fallback to IP address
    return get_remote_address(request)

# Initialize limiter with Redis backend for distributed rate limiting
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=settings.REDIS_URL,
    strategy="moving-window",
    default_limits=[f"{settings.RATE_LIMIT_PER_HOUR}/hour"]
)

class AdvancedRateLimiter:
    """Enterprise rate limiter with tier-based limits and cost-based throttling"""
    
    def __init__(self, redis_url: str):
        self.redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=100,
            decode_responses=True
        )
        
    async def get_redis(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.redis_pool)
    
    async def check_rate_limit(
        self,
        key: str,
        cost: int = 1,
        window_seconds: int = 60,
        max_requests: int = 60,
        tier: str = "default"
    ) -> tuple[bool, dict]:
        """
        Advanced rate limiting with cost-based throttling
        Returns (allowed, metadata)
        """
        redis_client = await self.get_redis()
        
        # Tier-based limits
        tier_limits = {
            "free": {"requests": 60, "burst": 10},
            "pro": {"requests": 600, "burst": 100},
            "enterprise": {"requests": 6000, "burst": 1000},
        }
        
        limits = tier_limits.get(tier, tier_limits["free"])
        max_requests = limits["requests"]
        
        # Create bucket key
        bucket_key = f"rl:{key}:{window_seconds}"
        
        # Lua script for atomic rate limit check
        lua_script = """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local max_requests = tonumber(ARGV[2])
        local cost = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        -- Clean old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
        
        -- Count current requests
        local current = redis.call('ZCARD', key)
        
        if current + cost > max_requests then
            return {0, current, max_requests}
        end
        
        -- Add new request
        redis.call('ZADD', key, now, now .. ':' .. cost)
        redis.call('EXPIRE', key, window)
        
        return {1, current + cost, max_requests}
        """
        
        result = await redis_client.eval(
            lua_script,
            1,
            bucket_key,
            window_seconds,
            max_requests,
            cost,
            int(time.time())
        )
        
        allowed = bool(result[0])
        current_requests = result[1]
        limit = result[2]
        
        # Calculate reset time
        reset_time = int(time.time()) + window_seconds
        
        metadata = {
            "limit": limit,
            "remaining": max(0, limit - current_requests),
            "reset": reset_time,
            "retry_after": window_seconds if not allowed else None,
            "tier": tier,
            "cost": cost
        }
        
        return allowed, metadata
    
    async def get_user_tier(self, user_id: str) -> str:
        """Get user's rate limit tier from cache/database"""
        redis_client = await self.get_redis()
        tier = await redis_client.get(f"user:tier:{user_id}")
        return tier or "free"

# Global advanced rate limiter instance
advanced_limiter = AdvancedRateLimiter(settings.REDIS_URL)

# Decorator for custom rate limits
def rate_limit(
    requests: int = 60,
    window: int = 60,
    cost: int = 1,
    key_func: Optional[Callable] = None
):
    """
    Custom rate limit decorator for specific endpoints
    
    Usage:
        @rate_limit(requests=10, window=60, cost=1)
        async def expensive_endpoint():
            pass
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            key = await (key_func(request) if key_func else get_rate_limit_key(request))
            
            # Get user tier if authenticated
            tier = "free"
            if hasattr(request.state, "user") and request.state.user:
                tier = await advanced_limiter.get_user_tier(str(request.state.user.id))
            
            allowed, metadata = await advanced_limiter.check_rate_limit(
                key=key,
                cost=cost,
                window_seconds=window,
                max_requests=requests,
                tier=tier
            )
            
            # Set rate limit headers
            response = Response()
            response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
            response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
            response.headers["X-RateLimit-Reset"] = str(metadata["reset"])
            
            if not allowed:
                response.status_code = 429
                response.headers["Retry-After"] = str(metadata["retry_after"])
                return response
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator