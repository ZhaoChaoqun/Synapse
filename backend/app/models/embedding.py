"""
Embedding Database Models

Stores vector embeddings for semantic search using pgvector.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Float, Integer, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# pgvector extension support
# Note: Requires pgvector extension to be installed in PostgreSQL
# CREATE EXTENSION IF NOT EXISTS vector;

# We'll use ARRAY(Float) as a fallback if pgvector is not available
# In production, use the actual vector type from pgvector


class Embedding(Base):
    """
    Vector embedding model for semantic search.

    Stores text embeddings generated from intelligence items,
    enabling semantic similarity search.
    """

    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Source reference
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "intelligence", "summary", "query"
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), index=True
    )

    # Content
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # SHA-256 hash for deduplication
    content_preview: Mapped[Optional[str]] = mapped_column(
        Text
    )  # First 500 chars for debugging

    # Embedding vector
    # Using ARRAY(Float) for compatibility; in production use pgvector's vector type
    embedding: Mapped[List[float]] = mapped_column(
        ARRAY(Float), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "text-embedding-004"
    embedding_dim: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # e.g., 768, 1536

    # Metadata for filtering
    platform: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    keywords: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Timestamps
    content_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_embeddings_source", "source_type", "source_id"),
        Index("ix_embeddings_platform_category", "platform", "category"),
    )


class MemoryEntry(Base):
    """
    Memory entry for the Agent's long-term memory.

    Stores processed insights, summaries, and learned patterns
    that the Agent can recall during future tasks.
    """

    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Memory type
    memory_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "fact", "insight", "pattern", "summary", "entity"

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Importance and decay
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    access_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    decay_rate: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.1
    )

    # Associations
    related_entities: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=list
    )  # Companies, products, people mentioned
    related_memories: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=list
    )  # UUIDs of related memory entries
    source_intelligence_ids: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=list
    )  # Source intelligence item IDs

    # Embedding reference
    embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), index=True
    )

    # Context
    context_tags: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=list
    )  # Tags for categorization
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )  # When this memory became valid
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )  # When this memory expires (if applicable)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_memory_type_importance", "memory_type", "importance_score"),
    )


class QueryCache(Base):
    """
    Query cache for frequently asked questions.

    Caches semantic search results to improve response time
    for similar queries.
    """

    __tablename__ = "query_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Query info
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )  # SHA-256 hash
    query_embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True)
    )

    # Cached results
    result_ids: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # List of result embedding/memory IDs
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cache metadata
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_hit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
