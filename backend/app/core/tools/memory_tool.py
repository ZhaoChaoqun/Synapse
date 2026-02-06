"""
Memory Search Tool

Searches the intelligence memory database.
"""

import asyncio
from typing import Any, Dict, List

from app.core.tools.base import BaseTool, ToolParameter, ToolResult


class MemorySearchTool(BaseTool):
    """
    Memory search tool.

    Searches historical intelligence data for relevant information
    and can detect temporal changes.
    """

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return "在历史情报库中进行语义搜索，找出相关的历史信息。可以发现跨时间的变化。"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询",
            ),
            ToolParameter(
                name="subject",
                type="string",
                description="关注的主体（公司/产品名）",
                required=False,
            ),
            ToolParameter(
                name="detect_changes",
                type="boolean",
                description="是否检测时间线变化（如功能上下线）",
                required=False,
            ),
            ToolParameter(
                name="time_range_days",
                type="integer",
                description="搜索的时间范围（天数）",
                required=False,
            ),
        ]

    async def execute(
        self,
        query: str,
        subject: str = None,
        detect_changes: bool = False,
        time_range_days: int = 90,
        **kwargs,
    ) -> ToolResult:
        """Execute memory search."""
        # Simulate search delay
        await asyncio.sleep(0.3)

        # TODO: Replace with actual vector database search
        results = self._generate_mock_memory_results(query, subject)

        # Detect changes if requested
        changes = []
        if detect_changes and subject:
            changes = self._detect_mock_changes(subject, time_range_days)

        return ToolResult.ok(
            data={
                "results": results,
                "total": len(results),
                "timeline_changes": changes if detect_changes else None,
            }
        )

    def _generate_mock_memory_results(
        self, query: str, subject: str = None
    ) -> List[Dict[str, Any]]:
        """Generate mock memory search results."""
        mock_results = [
            {
                "id": "mem_001",
                "content": f"历史记录：关于 {query} 的早期报道显示市场反应积极",
                "source": "zhihu",
                "collected_at": "2025-12-15",
                "relevance_score": 0.92,
                "credibility_score": 0.85,
            },
            {
                "id": "mem_002",
                "content": f"历史记录：{query} 在上个月的讨论热度有所下降",
                "source": "wechat",
                "collected_at": "2026-01-20",
                "relevance_score": 0.88,
                "credibility_score": 0.78,
            },
            {
                "id": "mem_003",
                "content": f"历史记录：行业专家对 {query} 的前景表示乐观",
                "source": "zhihu",
                "collected_at": "2026-01-28",
                "relevance_score": 0.85,
                "credibility_score": 0.90,
            },
        ]

        if subject:
            mock_results.append({
                "id": "mem_004",
                "content": f"历史记录：{subject} 曾在2个月前下线某功能，现已恢复",
                "source": "wechat",
                "collected_at": "2025-12-01",
                "relevance_score": 0.95,
                "credibility_score": 0.82,
            })

        return mock_results

    def _detect_mock_changes(
        self, subject: str, time_range_days: int
    ) -> List[Dict[str, Any]]:
        """Detect mock timeline changes."""
        return [
            {
                "change_type": "feature_removed",
                "description": f"{subject} 聊天功能下线",
                "detected_at": "2025-11-15",
                "related_event_id": "change_001",
            },
            {
                "change_type": "feature_restored",
                "description": f"{subject} 聊天功能重新上线（改进版）",
                "detected_at": "2026-01-20",
                "related_event_id": "change_001",
                "insight": "功能在下线2个月后以改进版形式重新上线，可能经过了重大重构",
            },
            {
                "change_type": "pricing_change",
                "description": f"{subject} API 价格下调 50%",
                "detected_at": "2026-02-01",
                "insight": "可能是市场竞争加剧导致的策略性降价",
            },
        ]
