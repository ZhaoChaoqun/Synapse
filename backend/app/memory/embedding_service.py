"""
Embedding Service

Generates vector embeddings using Gemini's embedding API.
"""

import hashlib
import logging
from typing import List, Optional

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using Gemini API.

    Uses text-embedding-004 model for high-quality embeddings
    suitable for semantic search.
    """

    # Embedding model configuration
    DEFAULT_MODEL = "text-embedding-004"
    EMBEDDING_DIM = 768  # text-embedding-004 output dimension

    # Task types for different use cases
    TASK_RETRIEVAL_DOCUMENT = "retrieval_document"
    TASK_RETRIEVAL_QUERY = "retrieval_query"
    TASK_SEMANTIC_SIMILARITY = "semantic_similarity"
    TASK_CLASSIFICATION = "classification"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            api_key: Gemini API key (defaults to settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_name = self.DEFAULT_MODEL

    async def embed_text(
        self,
        text: str,
        task_type: str = TASK_RETRIEVAL_DOCUMENT,
        title: Optional[str] = None,
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            task_type: Type of embedding task (affects optimization)
            title: Optional title for document embeddings

        Returns:
            List of floats representing the embedding vector
        """
        if not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            # Prepare content with optional title
            content = text
            if title and task_type == self.TASK_RETRIEVAL_DOCUMENT:
                content = f"{title}\n\n{text}"

            # Truncate if too long (Gemini has token limits)
            max_chars = 25000  # Approximate limit
            if len(content) > max_chars:
                content = content[:max_chars]

            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=content,
                task_type=task_type,
            )

            return result["embedding"]

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def embed_texts(
        self,
        texts: List[str],
        task_type: str = TASK_RETRIEVAL_DOCUMENT,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            task_type: Type of embedding task

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            # Filter empty texts
            valid_texts = [t for t in texts if t.strip()]
            if not valid_texts:
                return []

            # Truncate each text
            max_chars = 25000
            truncated_texts = [t[:max_chars] for t in valid_texts]

            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=truncated_texts,
                task_type=task_type,
            )

            return result["embedding"]

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Uses TASK_RETRIEVAL_QUERY for optimized query embeddings.

        Args:
            query: Search query

        Returns:
            Query embedding vector
        """
        return await self.embed_text(query, task_type=self.TASK_RETRIEVAL_QUERY)

    async def embed_document(
        self,
        content: str,
        title: Optional[str] = None,
    ) -> List[float]:
        """
        Generate embedding for a document.

        Uses TASK_RETRIEVAL_DOCUMENT for optimized document embeddings.

        Args:
            content: Document content
            title: Document title (optional)

        Returns:
            Document embedding vector
        """
        return await self.embed_text(
            content,
            task_type=self.TASK_RETRIEVAL_DOCUMENT,
            title=title,
        )

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """
        Compute SHA-256 hash of content for deduplication.

        Args:
            content: Text content

        Returns:
            Hex string of SHA-256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same dimension")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# Global instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the global EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
