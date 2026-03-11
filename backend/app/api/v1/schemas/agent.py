"""
Agent API Schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentPhase(str, Enum):
    """Agent execution phases."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    SEARCHING = "searching"
    SCRAPING = "scraping"
    EXPANDING = "expanding"
    CRITIQUING = "critiquing"
    SYNTHESIZING = "synthesizing"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentCommandRequest(BaseModel):
    """Request schema for agent command execution."""

    command: str = Field(..., description="The command for the agent to execute")
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional execution parameters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "command": "Monitor DeepSeek's latest developments",
                "options": {"platforms": ["zhihu", "wechat"], "time_range": "7d"},
            }
        }


class ThoughtStepResponse(BaseModel):
    """Response schema for a single thought step."""

    step_id: str
    phase: AgentPhase
    timestamp: datetime
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    tokens_used: int = 0


class AgentTaskResponse(BaseModel):
    """Response schema for a complete agent task."""

    task_id: str
    command: str
    status: str
    thought_chain: List[ThoughtStepResponse] = []
    result_summary: Optional[str] = None
    intelligence_count: int = 0
    total_tokens: int = 0
    duration_ms: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None


# 搜索结果相关 Schema
class SearchResultMetrics(BaseModel):
    """搜索结果的指标数据"""
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None


class SearchResultResponse(BaseModel):
    """单个搜索结果的响应"""
    id: str
    title: str
    url: str
    source: str  # weixin, zhihu, weibo, xhs, douyin, web
    snippet: str
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    metrics: Optional[SearchResultMetrics] = None
    relevance_score: int = Field(ge=0, le=100)
    sentiment: Optional[str] = None  # positive, neutral, negative
    tags: List[str] = []
    scraped_at: datetime


class TaskResultsResponse(BaseModel):
    """任务搜索结果的响应"""
    task_id: str
    query: str
    results: List[SearchResultResponse]
    total_count: int
    facets: Optional[Dict[str, Dict[str, int]]] = None  # 按来源/情感分组统计
