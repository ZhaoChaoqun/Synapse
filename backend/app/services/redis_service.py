"""
Redis Service
"""

from typing import Optional

import redis.asyncio as redis

from app.config import settings


class RedisService:
    """Redis service for caching and pub/sub."""

    _instance: Optional["RedisService"] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            print("✅ Redis connected")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
            print("👋 Redis disconnected")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # Cache operations
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        return await self.client.get(key)

    async def set(
        self, key: str, value: str, expire: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration (seconds)."""
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        return await self.client.delete(key)

    # Hash operations (for token tracking)
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value."""
        return await self.client.hset(name, key, value)

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """Increment hash field by amount."""
        return await self.client.hincrby(name, key, amount)

    async def hgetall(self, name: str) -> dict:
        """Get all hash fields."""
        return await self.client.hgetall(name)

    # Sorted set operations (for proxy pool)
    async def zadd(self, name: str, mapping: dict) -> int:
        """Add members to sorted set."""
        return await self.client.zadd(name, mapping)

    async def zincrby(self, name: str, amount: float, member: str) -> float:
        """Increment sorted set member score."""
        return await self.client.zincrby(name, amount, member)

    async def zrevrange(
        self, name: str, start: int, end: int, withscores: bool = False
    ) -> list:
        """Get sorted set members in descending order."""
        return await self.client.zrevrange(name, start, end, withscores=withscores)

    async def zrem(self, name: str, *members: str) -> int:
        """Remove members from sorted set."""
        return await self.client.zrem(name, *members)


# Global instance
redis_service = RedisService()


async def get_redis() -> RedisService:
    """Dependency for getting Redis service."""
    return redis_service
