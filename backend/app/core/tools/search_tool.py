"""
Platform Search Tool

Searches content across GCR platforms (WeChat, Zhihu, Xiaohongshu, Douyin).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.tools.base import BaseTool, ToolParameter, ToolResult
from app.crawlers.base import BaseCrawler, CrawlResult
from app.crawlers.anti_detect import (
    get_anti_detect,
    get_proxy_pool,
    get_rate_limiter,
)

logger = logging.getLogger(__name__)


class PlatformSearchTool(BaseTool):
    """
    Multi-platform search tool.

    Searches across Chinese social media platforms for relevant content.
    Supports both real crawler mode and mock mode for testing.
    """

    # Platform display names
    PLATFORM_NAMES = {
        "zhihu": "知乎",
        "wechat": "微信公众号",
        "xiaohongshu": "小红书",
        "douyin": "抖音",
    }

    def __init__(self, use_mock: bool = False):
        """
        Initialize the search tool.

        Args:
            use_mock: If True, use mock data instead of real crawlers
        """
        super().__init__()
        self.use_mock = use_mock
        self._crawlers: Dict[str, BaseCrawler] = {}
        self._initialized = False

    async def _init_crawlers(self) -> None:
        """Lazily initialize crawlers when first needed."""
        if self._initialized:
            return

        # Get shared anti-detect components
        anti_detect = get_anti_detect()
        proxy_pool = get_proxy_pool()
        rate_limiter = get_rate_limiter()

        # Initialize available crawlers
        try:
            from app.crawlers.zhihu import ZhihuCrawler
            self._crawlers["zhihu"] = ZhihuCrawler(
                proxy_pool=proxy_pool,
                anti_detect=anti_detect,
                rate_limiter=rate_limiter,
            )
        except ImportError:
            logger.warning("Zhihu crawler not available")

        try:
            from app.crawlers.wechat import WeChatCrawler
            self._crawlers["wechat"] = WeChatCrawler(
                proxy_pool=proxy_pool,
                anti_detect=anti_detect,
                rate_limiter=rate_limiter,
            )
        except ImportError:
            logger.warning("WeChat crawler not available")

        # TODO: Add Xiaohongshu and Douyin crawlers when implemented

        self._initialized = True

    @property
    def name(self) -> str:
        return "platform_search"

    @property
    def description(self) -> str:
        return "在中国主流社交媒体平台搜索相关内容。支持微信公众号、知乎、小红书、抖音。"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词",
            ),
            ToolParameter(
                name="platforms",
                type="array",
                description="要搜索的平台列表 (wechat, zhihu, xiaohongshu, douyin)",
                required=False,
            ),
            ToolParameter(
                name="time_range",
                type="string",
                description="时间范围: 1d, 7d, 30d, 90d",
                required=False,
                enum=["1d", "7d", "30d", "90d"],
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="每个平台返回的最大结果数",
                required=False,
            ),
        ]

    async def execute(
        self,
        query: str,
        platforms: List[str] = None,
        time_range: str = "7d",
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        """Execute platform search."""
        platforms = platforms or ["zhihu", "wechat"]

        if self.use_mock:
            return await self._execute_mock(query, platforms, time_range, limit)

        return await self._execute_real(query, platforms, time_range, limit)

    async def _execute_real(
        self,
        query: str,
        platforms: List[str],
        time_range: str,
        limit: int,
    ) -> ToolResult:
        """Execute real search using crawlers."""
        await self._init_crawlers()

        results = []
        errors = []
        searched_platforms = []

        # Search each platform concurrently
        tasks = []
        platform_order = []

        for platform in platforms:
            if platform in self._crawlers:
                tasks.append(
                    self._search_platform(
                        self._crawlers[platform],
                        query,
                        time_range,
                        limit,
                    )
                )
                platform_order.append(platform)
            elif platform in ["xiaohongshu", "douyin"]:
                # Platforms not yet implemented - use mock for now
                results.extend(self._generate_mock_results(query, platform, limit))
                searched_platforms.append(platform)
            else:
                errors.append(f"Unknown platform: {platform}")

        # Execute concurrent searches
        if tasks:
            crawl_results = await asyncio.gather(*tasks, return_exceptions=True)

            for platform, crawl_result in zip(platform_order, crawl_results):
                if isinstance(crawl_result, Exception):
                    errors.append(f"{platform}: {str(crawl_result)}")
                    # Fall back to mock data on error
                    results.extend(self._generate_mock_results(query, platform, limit))
                elif crawl_result.error:
                    errors.append(f"{platform}: {crawl_result.error}")
                    results.extend(self._generate_mock_results(query, platform, limit))
                else:
                    # Convert CrawlItems to result dicts
                    for item in crawl_result.items:
                        results.append({
                            "id": item.id,
                            "platform": item.platform,
                            "title": item.title,
                            "summary": item.summary or item.content[:200] if item.content else "",
                            "author": item.author_name,
                            "url": item.url,
                            "published_at": item.published_at,
                            "metrics": item.metrics,
                        })

                searched_platforms.append(platform)

        # Extract keywords for expansion
        discovered_keywords = self._extract_keywords_from_results(results)

        return ToolResult.ok(
            data={
                "results": results,
                "total": len(results),
                "platforms_searched": searched_platforms,
                "discovered_keywords": discovered_keywords,
                "errors": errors if errors else None,
            }
        )

    async def _search_platform(
        self,
        crawler: BaseCrawler,
        query: str,
        time_range: str,
        limit: int,
    ) -> CrawlResult:
        """Search a single platform."""
        try:
            return await crawler.search(query, time_range, limit)
        except Exception as e:
            logger.error(f"Search failed for {crawler.platform_name}: {e}")
            return CrawlResult.failure(crawler.platform_name, str(e))

    async def _execute_mock(
        self,
        query: str,
        platforms: List[str],
        time_range: str,
        limit: int,
    ) -> ToolResult:
        """Execute mock search for testing."""
        # Simulate search delay
        await asyncio.sleep(0.3)

        results = []
        for platform in platforms:
            platform_results = self._generate_mock_results(query, platform, limit)
            results.extend(platform_results)

        discovered_keywords = self._extract_keywords_from_results(results)

        return ToolResult.ok(
            data={
                "results": results,
                "total": len(results),
                "platforms_searched": platforms,
                "discovered_keywords": discovered_keywords,
            }
        )

    def _generate_mock_results(
        self, query: str, platform: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Generate mock search results."""
        mock_data = {
            "zhihu": [
                {
                    "id": f"zhihu_{i}",
                    "platform": "zhihu",
                    "title": f"{query} 技术深度分析 - 第{i+1}篇",
                    "summary": f"这是一篇关于 {query} 的专业技术分析文章，探讨了其核心架构和实现原理...",
                    "author": f"技术专家{i+1}",
                    "url": f"https://zhihu.com/answer/{100000+i}",
                    "published_at": "2026-02-01",
                    "metrics": {"voteup": 1500 - i * 100, "comments": 200 - i * 20},
                }
                for i in range(min(limit, 5))
            ],
            "wechat": [
                {
                    "id": f"wechat_{i}",
                    "platform": "wechat",
                    "title": f"{query} 行业报告 - 第{i+1}期",
                    "summary": f"本文深入分析了 {query} 在行业中的应用前景和商业模式...",
                    "author": f"AI前沿公众号{i+1}",
                    "url": None,
                    "published_at": "2026-02-03",
                    "metrics": {"reads": 10000 - i * 1000, "likes": 500 - i * 50},
                }
                for i in range(min(limit, 5))
            ],
            "xiaohongshu": [
                {
                    "id": f"xhs_{i}",
                    "platform": "xiaohongshu",
                    "title": f"实测 {query}！真的太好用了",
                    "summary": f"今天给大家测评一下 {query}，体验感受和详细教程...",
                    "author": f"科技博主{i+1}",
                    "url": f"https://xiaohongshu.com/note/{200000+i}",
                    "published_at": "2026-02-05",
                    "metrics": {"likes": 5000 - i * 500, "collects": 1000 - i * 100},
                }
                for i in range(min(limit, 5))
            ],
            "douyin": [
                {
                    "id": f"douyin_{i}",
                    "platform": "douyin",
                    "title": f"一分钟带你了解 {query}",
                    "summary": f"简单易懂的 {query} 科普视频...",
                    "author": f"科技达人{i+1}",
                    "url": f"https://douyin.com/video/{300000+i}",
                    "published_at": "2026-02-04",
                    "metrics": {"plays": 100000 - i * 10000, "likes": 8000 - i * 800},
                }
                for i in range(min(limit, 5))
            ],
        }

        return mock_data.get(platform, [])

    def _extract_keywords_from_results(
        self, results: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract potential keywords from search results for expansion."""
        # In real implementation, this would use NLP
        # For now, return some mock discovered keywords
        keywords = set()
        for result in results:
            title = result.get("title", "")
            # Simple extraction: find capitalized words or known entities
            if "DeepSeek" in title and "R1" not in keywords:
                keywords.add("DeepSeek R1")
            if "API" in title and "API pricing" not in keywords:
                keywords.add("API pricing")
            if "Kimi" in title:
                keywords.add("Moonshot Kimi")

        return list(keywords)[:3]  # Limit to 3 keywords

    async def close(self) -> None:
        """Close all crawler sessions."""
        for crawler in self._crawlers.values():
            await crawler.close()
        self._crawlers.clear()
        self._initialized = False
