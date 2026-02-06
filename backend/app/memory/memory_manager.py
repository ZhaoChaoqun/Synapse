"""
Memory Manager

High-level interface for the Agent's long-term memory system.
Handles storing, retrieving, and managing memories with decay.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.memory.vector_store import VectorStore, SearchResult, get_vector_store
from app.memory.embedding_service import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """A single memory entry."""

    id: str
    memory_type: str  # "fact", "insight", "pattern", "summary", "entity"
    content: str
    summary: Optional[str] = None
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "memory_type": self.memory_type,
            "content": self.content,
            "summary": self.summary,
            "importance_score": self.importance_score,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class MemorySearchResult:
    """Result from memory search."""

    memory: Memory
    relevance_score: float  # Combined score (similarity + importance)
    similarity_score: float


class MemoryManager:
    """
    Agent's long-term memory manager.

    Features:
    - Store different types of memories (facts, insights, patterns)
    - Semantic search with importance weighting
    - Memory decay over time
    - Automatic consolidation of similar memories
    - Context-aware recall
    """

    # Memory type weights for importance calculation
    TYPE_WEIGHTS = {
        "fact": 1.0,
        "insight": 1.2,
        "pattern": 1.3,
        "summary": 0.8,
        "entity": 1.0,
    }

    # Decay rate per day
    DEFAULT_DECAY_RATE = 0.05

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        Initialize memory manager.

        Args:
            vector_store: Vector store for embeddings
            embedding_service: Service for generating embeddings
        """
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = embedding_service or get_embedding_service()

        # In-memory cache of memories (id -> Memory)
        self._memories: Dict[str, Memory] = {}

        # Index by type
        self._type_index: Dict[str, List[str]] = {}

        # Index by entity (for entity-related memories)
        self._entity_index: Dict[str, List[str]] = {}

    async def store(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        summary: Optional[str] = None,
        entities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a new memory.

        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Initial importance score (0-1)
            summary: Optional summary
            entities: Related entities
            metadata: Additional metadata

        Returns:
            Memory ID
        """
        memory_id = str(uuid.uuid4())

        # Apply type weight to importance
        type_weight = self.TYPE_WEIGHTS.get(memory_type, 1.0)
        adjusted_importance = min(importance * type_weight, 1.0)

        # Create memory object
        memory = Memory(
            id=memory_id,
            memory_type=memory_type,
            content=content,
            summary=summary,
            importance_score=adjusted_importance,
            metadata=metadata or {},
        )

        # Store in memory cache
        self._memories[memory_id] = memory

        # Update type index
        if memory_type not in self._type_index:
            self._type_index[memory_type] = []
        self._type_index[memory_type].append(memory_id)

        # Update entity index
        if entities:
            for entity in entities:
                entity_lower = entity.lower()
                if entity_lower not in self._entity_index:
                    self._entity_index[entity_lower] = []
                self._entity_index[entity_lower].append(memory_id)
            memory.metadata["entities"] = entities

        # Store embedding in vector store
        await self.vector_store.add(
            content=content,
            source_type="memory",
            source_id=memory_id,
            metadata={
                "memory_type": memory_type,
                "importance": adjusted_importance,
                "summary": summary,
                **(metadata or {}),
            },
        )

        logger.debug(f"Stored memory {memory_id} of type {memory_type}")
        return memory_id

    async def recall(
        self,
        query: str,
        limit: int = 5,
        memory_type: Optional[str] = None,
        entity: Optional[str] = None,
        min_relevance: float = 0.3,
        include_decayed: bool = False,
    ) -> List[MemorySearchResult]:
        """
        Recall relevant memories.

        Args:
            query: Search query
            limit: Maximum number of results
            memory_type: Filter by memory type
            entity: Filter by related entity
            min_relevance: Minimum relevance score
            include_decayed: Include memories that have decayed

        Returns:
            List of MemorySearchResult objects
        """
        # Search vector store
        search_results = await self.vector_store.search(
            query=query,
            limit=limit * 2,  # Get more to filter
            source_type="memory",
            min_score=min_relevance * 0.5,  # Lower threshold for initial search
            metadata_filter={"memory_type": memory_type} if memory_type else None,
        )

        # Process results
        results = []
        for sr in search_results:
            memory_id = sr.source_id
            if not memory_id or memory_id not in self._memories:
                continue

            memory = self._memories[memory_id]

            # Filter by entity if specified
            if entity:
                memory_entities = memory.metadata.get("entities", [])
                if not any(e.lower() == entity.lower() for e in memory_entities):
                    continue

            # Calculate decayed importance
            decayed_importance = self._calculate_decayed_importance(memory)

            # Skip if too decayed (unless include_decayed)
            if not include_decayed and decayed_importance < 0.1:
                continue

            # Calculate combined relevance score
            # Relevance = similarity * (importance_weight + recency_weight)
            recency_bonus = self._calculate_recency_bonus(memory)
            relevance = sr.score * (0.6 + decayed_importance * 0.3 + recency_bonus * 0.1)

            if relevance >= min_relevance:
                results.append(
                    MemorySearchResult(
                        memory=memory,
                        relevance_score=relevance,
                        similarity_score=sr.score,
                    )
                )

            # Update access stats
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()

        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:limit]

    async def store_intelligence(
        self,
        intelligence_id: str,
        content: str,
        platform: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        entities: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> str:
        """
        Store intelligence item as a memory.

        Args:
            intelligence_id: Source intelligence ID
            content: Intelligence content
            platform: Source platform
            title: Title
            author: Author name
            entities: Extracted entities
            importance: Importance score

        Returns:
            Memory ID
        """
        # Create summary from title and content
        summary = title or content[:200]

        metadata = {
            "intelligence_id": intelligence_id,
            "platform": platform,
            "title": title,
            "author": author,
        }

        return await self.store(
            content=content,
            memory_type="fact",
            importance=importance,
            summary=summary,
            entities=entities,
            metadata=metadata,
        )

    async def store_insight(
        self,
        insight: str,
        source_memories: List[str],
        entities: Optional[List[str]] = None,
        importance: float = 0.7,
    ) -> str:
        """
        Store a derived insight.

        Args:
            insight: Insight content
            source_memories: IDs of source memories
            entities: Related entities
            importance: Importance score

        Returns:
            Memory ID
        """
        return await self.store(
            content=insight,
            memory_type="insight",
            importance=importance,
            entities=entities,
            metadata={"source_memories": source_memories},
        )

    async def store_pattern(
        self,
        pattern: str,
        examples: List[str],
        confidence: float = 0.5,
    ) -> str:
        """
        Store a recognized pattern.

        Args:
            pattern: Pattern description
            examples: Example memory IDs
            confidence: Pattern confidence

        Returns:
            Memory ID
        """
        return await self.store(
            content=pattern,
            memory_type="pattern",
            importance=confidence,
            metadata={"examples": examples, "confidence": confidence},
        )

    async def get_by_entity(
        self,
        entity: str,
        limit: int = 10,
    ) -> List[Memory]:
        """Get all memories related to an entity."""
        entity_lower = entity.lower()
        memory_ids = self._entity_index.get(entity_lower, [])

        memories = []
        for mid in memory_ids[:limit]:
            if mid in self._memories:
                memories.append(self._memories[mid])

        return memories

    async def get_recent(
        self,
        limit: int = 10,
        memory_type: Optional[str] = None,
    ) -> List[Memory]:
        """Get most recently accessed memories."""
        candidates = list(self._memories.values())

        if memory_type:
            candidates = [m for m in candidates if m.memory_type == memory_type]

        # Sort by last access time (most recent first)
        candidates.sort(
            key=lambda m: m.last_accessed_at or m.created_at,
            reverse=True,
        )

        return candidates[:limit]

    async def forget(self, memory_id: str) -> bool:
        """
        Remove a memory.

        Args:
            memory_id: Memory ID to remove

        Returns:
            True if removed, False if not found
        """
        if memory_id not in self._memories:
            return False

        memory = self._memories[memory_id]

        # Remove from type index
        if memory.memory_type in self._type_index:
            self._type_index[memory.memory_type] = [
                i for i in self._type_index[memory.memory_type] if i != memory_id
            ]

        # Remove from entity index
        for entity in memory.metadata.get("entities", []):
            entity_lower = entity.lower()
            if entity_lower in self._entity_index:
                self._entity_index[entity_lower] = [
                    i for i in self._entity_index[entity_lower] if i != memory_id
                ]

        # Remove from vector store
        await self.vector_store.delete(memory_id)

        # Remove from cache
        del self._memories[memory_id]

        return True

    async def consolidate(self) -> int:
        """
        Consolidate similar memories to reduce redundancy.

        Returns:
            Number of memories consolidated
        """
        # TODO: Implement memory consolidation
        # This would involve:
        # 1. Finding similar memories (high cosine similarity)
        # 2. Merging them into summaries
        # 3. Creating new "summary" type memories
        return 0

    async def decay_all(self) -> int:
        """
        Apply decay to all memories.

        Returns:
            Number of memories that fell below threshold
        """
        decayed_count = 0

        for memory in list(self._memories.values()):
            decayed_importance = self._calculate_decayed_importance(memory)

            # Update importance
            memory.importance_score = decayed_importance

            # Mark if fallen below threshold
            if decayed_importance < 0.1:
                decayed_count += 1

        return decayed_count

    def _calculate_decayed_importance(self, memory: Memory) -> float:
        """Calculate importance with time decay."""
        now = datetime.utcnow()
        created = memory.created_at
        days_old = (now - created).days

        # Exponential decay
        decay_factor = (1 - self.DEFAULT_DECAY_RATE) ** days_old

        # Access bonus (memories accessed recently decay slower)
        access_bonus = 1.0
        if memory.last_accessed_at:
            days_since_access = (now - memory.last_accessed_at).days
            access_bonus = 1.0 + (0.5 / (1 + days_since_access))

        return memory.importance_score * decay_factor * min(access_bonus, 1.5)

    def _calculate_recency_bonus(self, memory: Memory) -> float:
        """Calculate recency bonus (0-1)."""
        now = datetime.utcnow()

        if memory.last_accessed_at:
            ref_time = memory.last_accessed_at
        else:
            ref_time = memory.created_at

        hours_ago = (now - ref_time).total_seconds() / 3600

        # Bonus decreases exponentially
        return max(0, 1.0 - (hours_ago / 168))  # 168 hours = 1 week

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        type_counts = {k: len(v) for k, v in self._type_index.items()}
        entity_counts = len(self._entity_index)

        avg_importance = 0
        if self._memories:
            avg_importance = sum(m.importance_score for m in self._memories.values()) / len(self._memories)

        return {
            "total_memories": len(self._memories),
            "by_type": type_counts,
            "unique_entities": entity_counts,
            "average_importance": round(avg_importance, 3),
            "vector_store_stats": self.vector_store.get_stats(),
        }


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
