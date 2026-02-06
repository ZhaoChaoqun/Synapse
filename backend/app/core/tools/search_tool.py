"""
Platform Search Tool

Searches content across GCR platforms (WeChat, Zhihu, Xiaohongshu, Douyin).
"""

import asyncio
from typing import Any, Dict, List

from app.core.tools.base import BaseTool, ToolParameter, ToolResult


class PlatformSearchTool(BaseTool):
    """
    Multi-platform search tool.

    Searches across Chinese social media platforms for relevant content.
    Currently uses mock data - will be replaced with actual crawlers.
    """

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

        # Simulate search delay
        await asyncio.sleep(0.5)

        # TODO: Replace with actual crawler calls
        results = []
        for platform in platforms:
            platform_results = self._generate_mock_results(
                query, platform, limit
            )
            results.extend(platform_results)

        # Extract discovered keywords for potential expansion
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
