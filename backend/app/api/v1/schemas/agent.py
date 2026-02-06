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
