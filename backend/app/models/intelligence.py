"""
Intelligence Database Models
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IntelligenceItem(Base):
    """Intelligence item model - stores collected intelligence data."""

    __tablename__ = "intelligence_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_id: Mapped[Optional[str]] = mapped_column(String(255))

    title: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    author_name: Mapped[Optional[str]] = mapped_column(String(255))
    author_id: Mapped[Optional[str]] = mapped_column(String(255))
    author_followers: Mapped[Optional[int]] = mapped_column(Integer)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    sentiment: Mapped[Optional[float]] = mapped_column(Float)
    credibility_score: Mapped[Optional[float]] = mapped_column(Float)
    importance_score: Mapped[Optional[float]] = mapped_column(Float)

    # Related entities (JSON arrays)
    mentioned_companies: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    mentioned_products: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    mentioned_persons: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    keywords: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Vector embedding reference
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Metadata
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    processing_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Competitor(Base):
    """Competitor model - stores competitor information."""

    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    aliases: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Basic info
    company_type: Mapped[Optional[str]] = mapped_column(String(100))
    founded_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    headquarters: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(Text)

    # Product info
    products: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    tech_stack: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Funding info
    funding_rounds: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    total_funding: Mapped[Optional[float]] = mapped_column(Float)
    valuation: Mapped[Optional[float]] = mapped_column(Float)

    # Team info
    key_people: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Dynamic tracking
    last_news_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    news_frequency: Mapped[Optional[float]] = mapped_column(Float)
    sentiment_trend: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    features: Mapped[List["ProductFeature"]] = relationship(back_populates="competitor")


class ProductFeature(Base):
    """Product feature model - tracks feature changes over time."""

    __tablename__ = "product_features"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitors.id")
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    feature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_description: Mapped[Optional[str]] = mapped_column(Text)
    feature_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status change history
    status_history: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    source_intelligence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelligence_items.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship(back_populates="features")
