"""
Platforms API Schemas
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlatformStats(BaseModel):
    """Schema for platform statistics."""

    platform: str
    display_name: str
    hotness_score: int = Field(ge=0, le=100)
    trend: float
    trend_up: bool
    color_theme: str
    top_keywords: List[Dict[str, Any]] = []


class NetworkNode(BaseModel):
    """Schema for a network graph node."""

    id: str
    label: str
    type: str  # core, competitor, kol, cloud, keyword
    status: str  # active, velocity, inactive
    icon: str
    color: str
    x: Optional[float] = None
    y: Optional[float] = None


class NetworkEdge(BaseModel):
    """Schema for a network graph edge."""

    source: str
    target: str
    relationship: str
    strength: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)


class NetworkGraph(BaseModel):
    """Schema for a complete network graph."""

    nodes: List[NetworkNode]
    edges: List[Dict[str, Any]]
