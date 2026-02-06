"""
Task Database Models
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentTask(Base):
    """Agent task model - stores task execution records."""

    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    command: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Execution process
    thought_chain: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    tools_used: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Results
    result_summary: Mapped[Optional[str]] = mapped_column(Text)
    intelligence_ids: Mapped[Optional[list]] = mapped_column(ARRAY(UUID(as_uuid=True)))

    # Statistics
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class TimelineEvent(Base):
    """Timeline event model - for cross-time analysis."""

    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    subject_name: Mapped[Optional[str]] = mapped_column(String(255))

    description: Mapped[Optional[str]] = mapped_column(Text)
    significance_score: Mapped[Optional[float]] = mapped_column()

    source_intelligence_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True))
    )

    # For detecting "return" changes (e.g., feature restored)
    related_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
