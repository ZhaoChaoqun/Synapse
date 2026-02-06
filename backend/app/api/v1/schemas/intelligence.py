"""
Intelligence API Schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class IntelligenceItem(BaseModel):
    """Schema for a single intelligence item."""

    id: str
    platform: str
    title: Optional[str] = None
    summary: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    sentiment: float = Field(ge=-1.0, le=1.0)
    credibility_score: float = Field(ge=0.0, le=1.0)
    importance_score: float = Field(ge=0.0, le=1.0)
    mentioned_companies: List[str] = []
    keywords: List[str] = []
    source_url: Optional[str] = None


class IntelligenceSearchRequest(BaseModel):
    """Request schema for intelligence search."""

    query: str = Field(..., min_length=1)
    platforms: Optional[List[str]] = None
    time_range: Optional[str] = Field(default="7d")
    category: Optional[str] = None
    min_credibility: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    limit: int = Field(default=20, ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "DeepSeek API pricing",
                "platforms": ["zhihu", "wechat"],
                "time_range": "30d",
                "min_credibility": 0.6,
                "limit": 20,
            }
        }


class IntelligenceSearchResponse(BaseModel):
    """Response schema for intelligence search."""

    items: List[IntelligenceItem]
    total: int
    query_tokens: int


class TimelineEvent(BaseModel):
    """Schema for a timeline event."""

    id: str
    event_type: str
    event_date: str
    subject_name: str
    description: str
    significance_score: float = Field(ge=0.0, le=1.0)
    related_event_id: Optional[str] = None
