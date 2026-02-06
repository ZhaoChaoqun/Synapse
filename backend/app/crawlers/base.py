"""
Crawler Base Classes

Defines the base class and interfaces for platform crawlers.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CrawlItem(BaseModel):
    """A single crawled item."""

    id: str
    platform: str
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    author_name: Optional[str] = None
    author_id: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    collected_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    metrics: Dict[str, Any] = Field(default_factory=dict)
    raw_data: Optional[Dict[str, Any]] = None


class CrawlResult(BaseModel):
    """Result of a crawl operation."""

    platform: str
    items: List[CrawlItem] = Field(default_factory=list)
    total_found: int = 0
    has_more: bool = False
    next_cursor: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def success(
        cls,
        platform: str,
        items: List[CrawlItem],
        total_found: int = 0,
        has_more: bool = False,
        next_cursor: Optional[str] = None,
    ) -> "CrawlResult":
        """Create a successful crawl result."""
        return cls(
            platform=platform,
            items=items,
            total_found=total_found or len(items),
            has_more=has_more,
            next_cursor=next_cursor,
        )

    @classmethod
    def failure(cls, platform: str, error: str) -> "CrawlResult":
        """Create a failed crawl result."""
        return cls(platform=platform, error=error)


class CrawlerException(Exception):
    """Base exception for crawler errors."""

    pass


class RateLimitedException(CrawlerException):
    """Raised when rate limited by the platform."""

    pass


class BlockedException(CrawlerException):
    """Raised when blocked by the platform."""

    pass


class CaptchaException(CrawlerException):
    """Raised when captcha is required."""

    pass


class ParseException(CrawlerException):
    """Raised when parsing fails."""

    pass


class BaseCrawler(ABC):
    """
    Base class for all platform crawlers.

    Provides common functionality for:
    - HTTP requests with retry and anti-detection
    - Rate limiting
    - Error handling
    """

    def __init__(
        self,
        proxy_pool: Optional["ProxyPool"] = None,
        anti_detect: Optional["AntiDetect"] = None,
        rate_limiter: Optional["RateLimiter"] = None,
    ):
        self.proxy_pool = proxy_pool
        self.anti_detect = anti_detect
        self.rate_limiter = rate_limiter
        self._session = None

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform identifier (e.g., 'zhihu', 'wechat')."""
        pass

    @property
    def display_name(self) -> str:
        """Human-readable platform name."""
        return self.platform_name.title()

    @abstractmethod
    async def search(
        self,
        query: str,
        time_range: str = "7d",
        limit: int = 10,
    ) -> CrawlResult:
        """
        Search for content on the platform.

        Args:
            query: Search keywords
            time_range: Time range filter (1d, 7d, 30d, 90d)
            limit: Maximum number of results

        Returns:
            CrawlResult with search results
        """
        pass

    @abstractmethod
    async def get_detail(self, item_id: str) -> Optional[CrawlItem]:
        """
        Get detailed content for a specific item.

        Args:
            item_id: Platform-specific item ID

        Returns:
            CrawlItem with full details, or None if not found
        """
        pass

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            import aiohttp

            # Configure session with anti-detection
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
            )
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
        return self._session

    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        url: str,
        method: str = "GET",
        max_retries: int = 3,
        **kwargs,
    ) -> Any:
        """
        Make an HTTP request with retry and anti-detection.

        Args:
            url: Request URL
            method: HTTP method
            max_retries: Maximum retry attempts
            **kwargs: Additional request parameters

        Returns:
            Response data (JSON or text)

        Raises:
            CrawlerException on failure
        """
        session = await self._get_session()

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.wait(self.platform_name)

                # Get anti-detection headers
                headers = kwargs.pop("headers", {})
                if self.anti_detect:
                    headers.update(self.anti_detect.get_headers())

                # Get proxy if available
                proxy = None
                if self.proxy_pool:
                    proxy = await self.proxy_pool.get()

                async with session.request(
                    method,
                    url,
                    headers=headers,
                    proxy=proxy,
                    **kwargs,
                ) as response:
                    # Handle different status codes
                    if response.status == 200:
                        # Mark proxy as successful
                        if self.proxy_pool and proxy:
                            await self.proxy_pool.mark_success(proxy)

                        # Return based on content type
                        content_type = response.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            return await response.json()
                        else:
                            return await response.text()

                    elif response.status == 403:
                        # Blocked - try switching proxy
                        if self.proxy_pool and proxy:
                            await self.proxy_pool.mark_failed(proxy)
                        raise BlockedException(f"Access blocked (403) from {self.platform_name}")

                    elif response.status == 429:
                        # Rate limited
                        raise RateLimitedException(f"Rate limited by {self.platform_name}")

                    else:
                        raise CrawlerException(
                            f"HTTP {response.status} from {self.platform_name}"
                        )

            except (RateLimitedException, BlockedException) as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    continue
                raise CrawlerException(f"Request timeout to {self.platform_name}")

            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise CrawlerException(f"Request failed: {str(e)}")

        raise CrawlerException(f"Max retries exceeded for {self.platform_name}")

    def _parse_time_range(self, time_range: str) -> int:
        """Convert time range string to days."""
        mapping = {
            "1d": 1,
            "7d": 7,
            "30d": 30,
            "90d": 90,
        }
        return mapping.get(time_range, 7)


# Import these here to avoid circular imports
from app.crawlers.anti_detect.proxy_pool import ProxyPool
from app.crawlers.anti_detect.anti_detect import AntiDetect
from app.crawlers.anti_detect.rate_limiter import RateLimiter
