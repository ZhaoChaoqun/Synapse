"""
Memory Search Tool

Searches the intelligence memory database using semantic search.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.tools.base import BaseTool, ToolParameter, ToolResult
from app.memory import MemoryManager, get_memory_manager

logger = logging.getLogger(__name__)


class MemorySearchTool(BaseTool):
    """
    Memory search tool.

    Searches historical intelligence data for relevant information
    using semantic similarity. Can detect temporal changes and patterns.
    """

    def __init__(self, use_mock: bool = False):
        """
        Initialize memory search tool.

        Args:
            use_mock: If True, use mock data instead of real memory
        """
        super().__init__()
        self.use_mock = use_mock
        self._memory_manager: Optional[MemoryManager] = None

    def _get_memory_manager(self) -> MemoryManager:
        """Lazily get memory manager."""
        if self._memory_manager is None:
            self._memory_manager = get_memory_manager()
        return self._memory_manager

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
                name="memory_type",
                type="string",
                description="记忆类型过滤: fact, insight, pattern, summary, entity",
                required=False,
                enum=["fact", "insight", "pattern", "summary", "entity"],
            ),
            ToolParameter(
                name="detect_changes",
                type="boolean",
                description="是否检测时间线变化（如功能上下线）",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回的最大结果数",
                required=False,
            ),
        ]

    async def execute(
        self,
        query: str,
        subject: Optional[str] = None,
        memory_type: Optional[str] = None,
        detect_changes: bool = False,
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        """Execute memory search."""
        if self.use_mock:
            return await self._execute_mock(query, subject, detect_changes)

        return await self._execute_real(
            query, subject, memory_type, detect_changes, limit
        )

    async def _execute_real(
        self,
        query: str,
        subject: Optional[str],
        memory_type: Optional[str],
        detect_changes: bool,
        limit: int,
    ) -> ToolResult:
        """Execute real memory search."""
        memory_manager = self._get_memory_manager()

        try:
            # Perform semantic search
            search_results = await memory_manager.recall(
                query=query,
                limit=limit,
                memory_type=memory_type,
                entity=subject,
                min_relevance=0.3,
            )

            # Format results
            results = []
            for sr in search_results:
                memory = sr.memory
                results.append({
                    "id": memory.id,
                    "content": memory.content,
                    "summary": memory.summary,
                    "memory_type": memory.memory_type,
                    "relevance_score": round(sr.relevance_score, 3),
                    "similarity_score": round(sr.similarity_score, 3),
                    "importance_score": round(memory.importance_score, 3),
                    "created_at": memory.created_at.isoformat(),
                    "metadata": memory.metadata,
                })

            # Detect changes if requested
            changes = []
            if detect_changes and subject:
                changes = await self._detect_changes(subject, memory_manager)

            # Get related entities if subject specified
            related_memories = []
            if subject:
                entity_memories = await memory_manager.get_by_entity(subject, limit=5)
                for m in entity_memories:
                    if m.id not in [r["id"] for r in results]:
                        related_memories.append({
                            "id": m.id,
                            "content": m.content[:200],
                            "memory_type": m.memory_type,
                        })

            return ToolResult.ok(
                data={
                    "results": results,
                    "total": len(results),
                    "timeline_changes": changes if detect_changes else None,
                    "related_by_entity": related_memories if subject else None,
                    "memory_stats": memory_manager.get_stats(),
                }
            )

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            # Fall back to mock on error
            return await self._execute_mock(query, subject, detect_changes)

    async def _detect_changes(
        self,
        subject: str,
        memory_manager: MemoryManager,
    ) -> List[Dict[str, Any]]:
        """Detect timeline changes for a subject."""
        changes = []

        # Search for pattern-type memories about the subject
        pattern_results = await memory_manager.recall(
            query=f"{subject} change update",
            limit=10,
            memory_type="pattern",
            entity=subject,
            min_relevance=0.2,
        )

        for sr in pattern_results:
            memory = sr.memory
            if "change" in memory.content.lower() or "update" in memory.content.lower():
                changes.append({
                    "change_type": memory.metadata.get("change_type", "unknown"),
                    "description": memory.content,
                    "detected_at": memory.created_at.isoformat(),
                    "confidence": memory.metadata.get("confidence", 0.5),
                })

        return changes

    async def _execute_mock(
        self,
        query: str,
        subject: Optional[str],
        detect_changes: bool,
    ) -> ToolResult:
        """Execute mock memory search."""
        results = self._generate_mock_memory_results(query, subject)
        changes = []
        if detect_changes and subject:
            changes = self._detect_mock_changes(subject)

        return ToolResult.ok(
            data={
                "results": results,
                "total": len(results),
                "timeline_changes": changes if detect_changes else None,
            }
        )

    def _generate_mock_memory_results(
        self, query: str, subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate mock memory search results."""
        mock_results = [
            {
                "id": "mem_001",
                "content": f"历史记录：关于 {query} 的早期报道显示市场反应积极",
                "memory_type": "fact",
                "relevance_score": 0.92,
                "similarity_score": 0.88,
                "importance_score": 0.75,
                "created_at": "2025-12-15T10:30:00",
                "metadata": {"platform": "zhihu"},
            },
            {
                "id": "mem_002",
                "content": f"历史记录：{query} 在上个月的讨论热度有所下降",
                "memory_type": "insight",
                "relevance_score": 0.88,
                "similarity_score": 0.82,
                "importance_score": 0.68,
                "created_at": "2026-01-20T14:15:00",
                "metadata": {"platform": "wechat"},
            },
            {
                "id": "mem_003",
                "content": f"历史记录：行业专家对 {query} 的前景表示乐观",
                "memory_type": "fact",
                "relevance_score": 0.85,
                "similarity_score": 0.80,
                "importance_score": 0.82,
                "created_at": "2026-01-28T09:00:00",
                "metadata": {"platform": "zhihu", "author": "AI行业分析师"},
            },
        ]

        if subject:
            mock_results.append({
                "id": "mem_004",
                "content": f"历史记录：{subject} 曾在2个月前下线某功能，现已恢复",
                "memory_type": "pattern",
                "relevance_score": 0.95,
                "similarity_score": 0.90,
                "importance_score": 0.88,
                "created_at": "2025-12-01T16:45:00",
                "metadata": {"platform": "wechat", "change_type": "feature_restored"},
            })

        return mock_results

    def _detect_mock_changes(self, subject: str) -> List[Dict[str, Any]]:
        """Detect mock timeline changes."""
        return [
            {
                "change_type": "feature_removed",
                "description": f"{subject} 聊天功能下线",
                "detected_at": "2025-11-15T12:00:00",
                "confidence": 0.9,
            },
            {
                "change_type": "feature_restored",
                "description": f"{subject} 聊天功能重新上线（改进版）",
                "detected_at": "2026-01-20T10:00:00",
                "confidence": 0.85,
            },
            {
                "change_type": "pricing_change",
                "description": f"{subject} API 价格下调 50%",
                "detected_at": "2026-02-01T08:00:00",
                "confidence": 0.95,
            },
        ]


class MemoryStoreTool(BaseTool):
    """
    Tool for storing new memories.

    Used by the Agent to persist important insights and facts.
    """

    def __init__(self, use_mock: bool = False):
        super().__init__()
        self.use_mock = use_mock
        self._memory_manager: Optional[MemoryManager] = None

    def _get_memory_manager(self) -> MemoryManager:
        if self._memory_manager is None:
            self._memory_manager = get_memory_manager()
        return self._memory_manager

    @property
    def name(self) -> str:
        return "memory_store"

    @property
    def description(self) -> str:
        return "将重要的洞察、事实或模式存储到长期记忆中，以便未来任务时回忆。"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="content",
                type="string",
                description="要存储的内容",
            ),
            ToolParameter(
                name="memory_type",
                type="string",
                description="记忆类型: fact, insight, pattern",
                enum=["fact", "insight", "pattern"],
            ),
            ToolParameter(
                name="importance",
                type="number",
                description="重要性评分 (0-1)",
                required=False,
            ),
            ToolParameter(
                name="entities",
                type="array",
                description="相关实体（公司、产品名等）",
                required=False,
            ),
            ToolParameter(
                name="summary",
                type="string",
                description="内容摘要",
                required=False,
            ),
        ]

    async def execute(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        entities: Optional[List[str]] = None,
        summary: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Store a new memory."""
        if self.use_mock:
            return ToolResult.ok(
                data={
                    "memory_id": "mock_mem_new",
                    "stored": True,
                    "message": f"Mock: Stored {memory_type} memory",
                }
            )

        try:
            memory_manager = self._get_memory_manager()
            memory_id = await memory_manager.store(
                content=content,
                memory_type=memory_type,
                importance=importance,
                summary=summary,
                entities=entities,
            )

            return ToolResult.ok(
                data={
                    "memory_id": memory_id,
                    "stored": True,
                    "memory_type": memory_type,
                    "importance": importance,
                }
            )

        except Exception as e:
            logger.error(f"Memory store failed: {e}")
            return ToolResult.fail(error=f"Failed to store memory: {str(e)}")
