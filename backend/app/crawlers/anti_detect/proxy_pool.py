"""
Proxy Pool Management

Manages a pool of proxies with health tracking.
"""

import asyncio
from typing import Dict, List, Optional, Set

from app.config import settings


class ProxyPool:
    """
    Proxy pool manager.

    Features:
    - Proxy health tracking (success/failure rates)
    - Automatic rotation
    - Failed proxy removal
    - Optional Redis-backed persistence
    """

    def __init__(self, redis_client=None):
        """
        Initialize proxy pool.

        Args:
            redis_client: Optional Redis client for persistence
        """
        self.redis = redis_client
        self._proxies: Dict[str, float] = {}  # proxy -> score
        self._failed_count: Dict[str, int] = {}  # proxy -> failure count
        self._in_use: Set[str] = set()

        # Configuration
        self.max_failures = 5  # Remove proxy after this many failures
        self.min_score = -10  # Remove proxy if score drops below this

    async def add(self, proxy: str, initial_score: float = 1.0) -> None:
        """
        Add a proxy to the pool.

        Args:
            proxy: Proxy URL (e.g., 'http://host:port')
            initial_score: Initial health score
        """
        if self.redis:
            await self.redis.zadd("crawler:proxy_pool", {proxy: initial_score})
        else:
            self._proxies[proxy] = initial_score
            self._failed_count[proxy] = 0

    async def add_many(self, proxies: List[str], initial_score: float = 1.0) -> None:
        """Add multiple proxies to the pool."""
        for proxy in proxies:
            await self.add(proxy, initial_score)

    async def get(self) -> Optional[str]:
        """
        Get the best available proxy.

        Returns:
            Proxy URL, or None if pool is empty
        """
        if self.redis:
            # Get highest-scoring proxy from Redis
            result = await self.redis.zrevrange(
                "crawler:proxy_pool", 0, 0, withscores=True
            )
            if result:
                return result[0][0]
            return None
        else:
            if not self._proxies:
                return None

            # Get proxy with highest score that's not in use
            available = [
                (p, s) for p, s in self._proxies.items()
                if p not in self._in_use
            ]

            if not available:
                # All proxies in use, return best one anyway
                available = list(self._proxies.items())

            # Sort by score descending
            available.sort(key=lambda x: x[1], reverse=True)
            proxy = available[0][0]
            self._in_use.add(proxy)
            return proxy

    async def release(self, proxy: str) -> None:
        """Release a proxy back to the pool."""
        self._in_use.discard(proxy)

    async def mark_success(self, proxy: str) -> None:
        """
        Mark a proxy as successful (increase score).

        Args:
            proxy: Proxy URL
        """
        if self.redis:
            await self.redis.zincrby("crawler:proxy_pool", 1, proxy)
            # Reset failure count
            await self.redis.hdel("crawler:proxy_failed", proxy)
        else:
            if proxy in self._proxies:
                self._proxies[proxy] = min(self._proxies[proxy] + 1, 10)
                self._failed_count[proxy] = 0
            self._in_use.discard(proxy)

    async def mark_failed(self, proxy: str) -> None:
        """
        Mark a proxy as failed (decrease score).

        Args:
            proxy: Proxy URL
        """
        if self.redis:
            await self.redis.zincrby("crawler:proxy_pool", -2, proxy)
            failures = await self.redis.hincrby("crawler:proxy_failed", proxy, 1)

            # Remove if too many failures
            if failures > self.max_failures:
                await self.redis.zrem("crawler:proxy_pool", proxy)
                await self.redis.hdel("crawler:proxy_failed", proxy)
        else:
            if proxy in self._proxies:
                self._proxies[proxy] -= 2
                self._failed_count[proxy] = self._failed_count.get(proxy, 0) + 1

                # Remove if too many failures or score too low
                if (
                    self._failed_count[proxy] > self.max_failures
                    or self._proxies[proxy] < self.min_score
                ):
                    del self._proxies[proxy]
                    del self._failed_count[proxy]

            self._in_use.discard(proxy)

    async def remove(self, proxy: str) -> None:
        """Remove a proxy from the pool."""
        if self.redis:
            await self.redis.zrem("crawler:proxy_pool", proxy)
            await self.redis.hdel("crawler:proxy_failed", proxy)
        else:
            self._proxies.pop(proxy, None)
            self._failed_count.pop(proxy, None)
            self._in_use.discard(proxy)

    async def get_stats(self) -> Dict:
        """Get pool statistics."""
        if self.redis:
            total = await self.redis.zcard("crawler:proxy_pool")
            return {"total": total, "source": "redis"}
        else:
            return {
                "total": len(self._proxies),
                "in_use": len(self._in_use),
                "available": len(self._proxies) - len(self._in_use),
                "source": "memory",
            }

    async def clear(self) -> None:
        """Clear all proxies from the pool."""
        if self.redis:
            await self.redis.delete("crawler:proxy_pool")
            await self.redis.delete("crawler:proxy_failed")
        else:
            self._proxies.clear()
            self._failed_count.clear()
            self._in_use.clear()

    def is_empty(self) -> bool:
        """Check if the proxy pool is empty."""
        return len(self._proxies) == 0


# Global instance (without Redis by default)
_proxy_pool: Optional[ProxyPool] = None


def get_proxy_pool(redis_client=None) -> ProxyPool:
    """Get the global ProxyPool instance."""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool(redis_client)
    return _proxy_pool
