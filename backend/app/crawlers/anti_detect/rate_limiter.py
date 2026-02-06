"""
Rate Limiter

Controls request rate to avoid triggering platform rate limits.
"""

import asyncio
import time
from typing import Dict, Optional


class RateLimiter:
    """
    Rate limiter for crawler requests.

    Uses token bucket algorithm to control request rate.
    Supports per-platform rate limits.
    """

    # Default rate limits (requests per second)
    DEFAULT_LIMITS: Dict[str, float] = {
        "zhihu": 0.5,       # 1 request per 2 seconds
        "wechat": 0.33,     # 1 request per 3 seconds
        "xiaohongshu": 0.5,  # 1 request per 2 seconds
        "douyin": 0.5,      # 1 request per 2 seconds
        "default": 1.0,     # 1 request per second
    }

    def __init__(
        self,
        limits: Optional[Dict[str, float]] = None,
        redis_client=None,
    ):
        """
        Initialize rate limiter.

        Args:
            limits: Custom rate limits per platform
            redis_client: Optional Redis client for distributed limiting
        """
        self.limits = {**self.DEFAULT_LIMITS, **(limits or {})}
        self.redis = redis_client
        self._last_request: Dict[str, float] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, platform: str) -> asyncio.Lock:
        """Get or create lock for a platform."""
        if platform not in self._locks:
            self._locks[platform] = asyncio.Lock()
        return self._locks[platform]

    def _get_interval(self, platform: str) -> float:
        """Get the minimum interval between requests for a platform."""
        rate = self.limits.get(platform, self.limits["default"])
        return 1.0 / rate if rate > 0 else 0

    async def wait(self, platform: str) -> None:
        """
        Wait until a request can be made.

        Args:
            platform: Platform name
        """
        if self.redis:
            await self._wait_redis(platform)
        else:
            await self._wait_local(platform)

    async def _wait_local(self, platform: str) -> None:
        """Local (in-memory) rate limiting."""
        async with self._get_lock(platform):
            interval = self._get_interval(platform)
            last = self._last_request.get(platform, 0)
            now = time.time()

            elapsed = now - last
            if elapsed < interval:
                wait_time = interval - elapsed
                await asyncio.sleep(wait_time)

            self._last_request[platform] = time.time()

    async def _wait_redis(self, platform: str) -> None:
        """Redis-based distributed rate limiting."""
        key = f"crawler:rate_limit:{platform}"
        interval = self._get_interval(platform)

        while True:
            # Try to set the key with expiration
            # If set successfully, we can proceed
            result = await self.redis.set(
                key, "1",
                ex=max(1, int(interval)),
                nx=True,
            )

            if result:
                return

            # Key exists, wait and retry
            await asyncio.sleep(0.1)

    async def acquire(self, platform: str) -> bool:
        """
        Try to acquire rate limit token without blocking.

        Args:
            platform: Platform name

        Returns:
            True if acquired, False if rate limited
        """
        if self.redis:
            key = f"crawler:rate_limit:{platform}"
            interval = self._get_interval(platform)
            result = await self.redis.set(key, "1", ex=max(1, int(interval)), nx=True)
            return bool(result)
        else:
            interval = self._get_interval(platform)
            last = self._last_request.get(platform, 0)
            now = time.time()

            if now - last >= interval:
                self._last_request[platform] = now
                return True
            return False

    def set_limit(self, platform: str, requests_per_second: float) -> None:
        """
        Set rate limit for a platform.

        Args:
            platform: Platform name
            requests_per_second: Maximum requests per second
        """
        self.limits[platform] = requests_per_second

    def get_limit(self, platform: str) -> float:
        """Get rate limit for a platform."""
        return self.limits.get(platform, self.limits["default"])


# Global instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(redis_client=None) -> RateLimiter:
    """Get the global RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(redis_client=redis_client)
    return _rate_limiter
