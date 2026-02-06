"""
Platforms API Endpoints
"""

from typing import List, Optional

from fastapi import APIRouter

from app.api.v1.schemas.platforms import NetworkGraph, NetworkNode, PlatformStats

router = APIRouter(prefix="/platforms", tags=["Platforms"])


@router.get("/stats", response_model=List[PlatformStats])
async def get_platform_stats():
    """
    Get real-time statistics for GCR platforms.

    Used by StatsGrid component.
    """
    # TODO: Implement actual stats calculation
    return [
        PlatformStats(
            platform="wechat",
            display_name="WeChat Pulse",
            hotness_score=88,
            trend=0.12,
            trend_up=True,
            color_theme="green",
            top_keywords=[
                {"keyword": "DeepSeek", "count": 156},
                {"keyword": "Kimi", "count": 98},
                {"keyword": "AGI", "count": 67},
            ],
        ),
        PlatformStats(
            platform="zhihu",
            display_name="Zhihu Heat",
            hotness_score=76,
            trend=-0.05,
            trend_up=False,
            color_theme="blue",
            top_keywords=[
                {"keyword": "大模型", "count": 234},
                {"keyword": "AI Agent", "count": 189},
                {"keyword": "RAG", "count": 145},
            ],
        ),
        PlatformStats(
            platform="xiaohongshu",
            display_name="XHS Trend",
            hotness_score=92,
            trend=0.23,
            trend_up=True,
            color_theme="red",
            top_keywords=[
                {"keyword": "AI绘画", "count": 567},
                {"keyword": "ChatGPT", "count": 432},
                {"keyword": "效率工具", "count": 321},
            ],
        ),
        PlatformStats(
            platform="douyin",
            display_name="Douyin Vel",
            hotness_score=65,
            trend=0.08,
            trend_up=True,
            color_theme="white",
            top_keywords=[
                {"keyword": "AI换脸", "count": 890},
                {"keyword": "数字人", "count": 654},
                {"keyword": "AI配音", "count": 432},
            ],
        ),
    ]


@router.get("/network", response_model=NetworkGraph)
async def get_network_graph(
    focus: Optional[str] = None,
    depth: int = 2,
):
    """
    Get knowledge graph network for visualization.

    Used by NetworkMap component.
    """
    # TODO: Implement actual graph generation
    nodes = [
        NetworkNode(
            id="node_core",
            label="INSIGHT CORE",
            type="core",
            status="active",
            icon="hub",
            color="#3B82F6",
        ),
        NetworkNode(
            id="node_deepseek",
            label="DeepSeek",
            type="competitor",
            status="velocity",
            icon="business",
            color="#4F46E5",
        ),
        NetworkNode(
            id="node_moonshot",
            label="Moonshot AI",
            type="competitor",
            status="active",
            icon="business",
            color="#10B981",
        ),
        NetworkNode(
            id="node_techbrother",
            label="TechBrother",
            type="kol",
            status="active",
            icon="person",
            color="#F59E0B",
        ),
        NetworkNode(
            id="node_alibaba",
            label="Alibaba Cloud",
            type="cloud",
            status="active",
            icon="cloud",
            color="#6366F1",
        ),
    ]

    edges = [
        {"source": "node_core", "target": "node_deepseek", "relationship": "monitors"},
        {"source": "node_core", "target": "node_moonshot", "relationship": "monitors"},
        {"source": "node_deepseek", "target": "node_moonshot", "relationship": "competes_with"},
        {"source": "node_techbrother", "target": "node_deepseek", "relationship": "covers"},
        {"source": "node_alibaba", "target": "node_deepseek", "relationship": "partners_with"},
    ]

    return NetworkGraph(nodes=nodes, edges=edges)
