"""
Vector Store

Manages vector embeddings storage and similarity search.
Supports both PostgreSQL (pgvector) and in-memory fallback.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.memory.embedding_service import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a vector similarity search."""

    id: str
    content: str
    score: float  # Similarity score (0-1)
    metadata: Dict[str, Any]
    source_type: str
    source_id: Optional[str] = None


class VectorStore:
    """
    Vector storage and search engine.

    Provides:
    - Vector embedding storage
    - Semantic similarity search
    - Metadata filtering
    - Hybrid search (semantic + keyword)

    Currently uses in-memory storage with numpy-based similarity.
    Can be extended to use pgvector for production.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        use_db: bool = False,
    ):
        """
        Initialize vector store.

        Args:
            embedding_service: Service for generating embeddings
            use_db: If True, use PostgreSQL with pgvector (not yet implemented)
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.use_db = use_db

        # In-memory storage
        self._vectors: Dict[str, Dict[str, Any]] = {}
        # Index by source_type for faster filtering
        self._type_index: Dict[str, List[str]] = {}
        # Index by platform
        self._platform_index: Dict[str, List[str]] = {}

    async def add(
        self,
        content: str,
        source_type: str,
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        Add a document to the vector store.

        Args:
            content: Text content to store
            source_type: Type of source (e.g., "intelligence", "memory")
            source_id: Optional source identifier
            metadata: Optional metadata dict
            embedding: Pre-computed embedding (if None, will be generated)

        Returns:
            ID of the stored document
        """
        # Generate ID
        doc_id = str(uuid.uuid4())

        # Generate embedding if not provided
        if embedding is None:
            title = metadata.get("title") if metadata else None
            embedding = await self.embedding_service.embed_document(content, title)

        # Compute content hash
        content_hash = self.embedding_service.compute_content_hash(content)

        # Check for duplicates
        for existing_id, existing in self._vectors.items():
            if existing.get("content_hash") == content_hash:
                logger.debug(f"Duplicate content detected, returning existing ID: {existing_id}")
                return existing_id

        # Store document
        self._vectors[doc_id] = {
            "id": doc_id,
            "content": content,
            "content_preview": content[:500] if content else "",
            "content_hash": content_hash,
            "embedding": embedding,
            "source_type": source_type,
            "source_id": source_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        # Update indices
        if source_type not in self._type_index:
            self._type_index[source_type] = []
        self._type_index[source_type].append(doc_id)

        platform = (metadata or {}).get("platform")
        if platform:
            if platform not in self._platform_index:
                self._platform_index[platform] = []
            self._platform_index[platform].append(doc_id)

        return doc_id

    async def add_many(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Add multiple documents to the vector store.

        Args:
            documents: List of dicts with keys: content, source_type, source_id, metadata

        Returns:
            List of document IDs
        """
        # Extract contents for batch embedding
        contents = [doc["content"] for doc in documents]
        titles = [doc.get("metadata", {}).get("title") for doc in documents]

        # Generate embeddings in batch
        embeddings = await self.embedding_service.embed_texts(contents)

        # Add each document
        ids = []
        for doc, embedding in zip(documents, embeddings):
            doc_id = await self.add(
                content=doc["content"],
                source_type=doc["source_type"],
                source_id=doc.get("source_id"),
                metadata=doc.get("metadata"),
                embedding=embedding,
            )
            ids.append(doc_id)

        return ids

    async def search(
        self,
        query: str,
        limit: int = 10,
        source_type: Optional[str] = None,
        platform: Optional[str] = None,
        min_score: float = 0.5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Args:
            query: Search query
            limit: Maximum number of results
            source_type: Filter by source type
            platform: Filter by platform
            min_score: Minimum similarity score (0-1)
            metadata_filter: Additional metadata filters

        Returns:
            List of SearchResult objects
        """
        if not self._vectors:
            return []

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)

        # Get candidate document IDs
        candidate_ids = self._get_candidates(source_type, platform)

        # Calculate similarities
        scores: List[Tuple[str, float]] = []
        for doc_id in candidate_ids:
            doc = self._vectors.get(doc_id)
            if not doc:
                continue

            # Apply metadata filter
            if metadata_filter:
                doc_metadata = doc.get("metadata", {})
                if not self._matches_filter(doc_metadata, metadata_filter):
                    continue

            # Calculate similarity
            score = self.embedding_service.cosine_similarity(
                query_embedding, doc["embedding"]
            )

            if score >= min_score:
                scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Build results
        results = []
        for doc_id, score in scores[:limit]:
            doc = self._vectors[doc_id]
            results.append(
                SearchResult(
                    id=doc_id,
                    content=doc["content"],
                    score=score,
                    metadata=doc.get("metadata", {}),
                    source_type=doc["source_type"],
                    source_id=doc.get("source_id"),
                )
            )

        return results

    async def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        return self._vectors.get(doc_id)

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        if doc_id not in self._vectors:
            return False

        doc = self._vectors[doc_id]

        # Remove from indices
        source_type = doc["source_type"]
        if source_type in self._type_index:
            self._type_index[source_type] = [
                i for i in self._type_index[source_type] if i != doc_id
            ]

        platform = doc.get("metadata", {}).get("platform")
        if platform and platform in self._platform_index:
            self._platform_index[platform] = [
                i for i in self._platform_index[platform] if i != doc_id
            ]

        # Remove document
        del self._vectors[doc_id]
        return True

    async def update_metadata(
        self, doc_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """Update document metadata."""
        if doc_id not in self._vectors:
            return False

        self._vectors[doc_id]["metadata"].update(metadata)
        return True

    def _get_candidates(
        self,
        source_type: Optional[str],
        platform: Optional[str],
    ) -> List[str]:
        """Get candidate document IDs based on filters."""
        # Start with all IDs
        candidates = set(self._vectors.keys())

        # Filter by source type
        if source_type:
            type_ids = set(self._type_index.get(source_type, []))
            candidates = candidates.intersection(type_ids)

        # Filter by platform
        if platform:
            platform_ids = set(self._platform_index.get(platform, []))
            candidates = candidates.intersection(platform_ids)

        return list(candidates)

    def _matches_filter(
        self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                # List filter: value should be in list
                if metadata[key] not in value:
                    return False
            else:
                # Exact match
                if metadata[key] != value:
                    return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        type_counts = {k: len(v) for k, v in self._type_index.items()}
        platform_counts = {k: len(v) for k, v in self._platform_index.items()}

        return {
            "total_documents": len(self._vectors),
            "by_type": type_counts,
            "by_platform": platform_counts,
        }

    def clear(self) -> None:
        """Clear all documents from the store."""
        self._vectors.clear()
        self._type_index.clear()
        self._platform_index.clear()


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the global VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
