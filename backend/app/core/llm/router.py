"""
LLM Router - Routes requests to appropriate model based on task complexity
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.llm.gemini import GeminiClient, get_light_client, get_heavy_client


class ModelTier(str, Enum):
    """Model tier for routing."""

    LIGHT = "light"  # Gemini Flash - fast, low cost
    HEAVY = "heavy"  # Gemini Pro - high quality


class LLMRouter:
    """
    LLM Router - Intelligently routes requests to the appropriate model.

    - Light (Gemini Flash): filtering, classification, simple QA
    - Heavy (Gemini Pro): complex analysis, critical evaluation, synthesis
    """

    # Tasks that should use the light model
    LIGHT_TASKS = {
        "filter",
        "classify",
        "extract_keywords",
        "simple_qa",
        "summarize_short",
        "sentiment_basic",
    }

    # Tasks that should use the heavy model
    HEAVY_TASKS = {
        "critical_review",
        "deep_analysis",
        "synthesis",
        "complex_reasoning",
        "cross_validation",
    }

    # Content length threshold for auto-routing
    CONTENT_LENGTH_THRESHOLD = 5000

    def __init__(self):
        self._light: Optional[GeminiClient] = None
        self._heavy: Optional[GeminiClient] = None

    @property
    def light(self) -> GeminiClient:
        """Get light model client."""
        if self._light is None:
            self._light = get_light_client()
        return self._light

    @property
    def heavy(self) -> GeminiClient:
        """Get heavy model client."""
        if self._heavy is None:
            self._heavy = get_heavy_client()
        return self._heavy

    def get_client(
        self,
        task: Optional[str] = None,
        content_length: Optional[int] = None,
        force_tier: Optional[ModelTier] = None,
    ) -> GeminiClient:
        """
        Get appropriate client based on task or content.

        Args:
            task: Task type (e.g., "filter", "deep_analysis")
            content_length: Length of content to process
            force_tier: Force a specific model tier

        Returns:
            Appropriate GeminiClient instance
        """
        # If tier is forced, use it
        if force_tier:
            return self.light if force_tier == ModelTier.LIGHT else self.heavy

        # Route based on task type
        if task:
            if task in self.LIGHT_TASKS:
                return self.light
            elif task in self.HEAVY_TASKS:
                return self.heavy

        # Route based on content length
        if content_length and content_length > self.CONTENT_LENGTH_THRESHOLD:
            return self.heavy

        # Default to light model for efficiency
        return self.light

    async def generate(
        self,
        prompt: str,
        task: Optional[str] = None,
        system_instruction: Optional[str] = None,
        force_tier: Optional[ModelTier] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate content using the appropriate model.

        Args:
            prompt: User prompt
            task: Task type for routing
            system_instruction: System instruction
            force_tier: Force a specific model tier
            **kwargs: Additional arguments for generation

        Returns:
            Generation result with model info
        """
        client = self.get_client(
            task=task,
            content_length=len(prompt),
            force_tier=force_tier,
        )

        result = await client.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            **kwargs,
        )

        # Add model info to result
        result["model"] = client.model_name
        result["tier"] = "light" if client == self.light else "heavy"

        return result

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        task: Optional[str] = None,
        system_instruction: Optional[str] = None,
        force_tier: Optional[ModelTier] = None,
    ) -> Dict[str, Any]:
        """
        Generate content with function calling.

        Args:
            prompt: User prompt
            tools: List of tool definitions
            task: Task type for routing
            system_instruction: System instruction
            force_tier: Force a specific model tier

        Returns:
            Generation result with potential function calls
        """
        client = self.get_client(
            task=task,
            content_length=len(prompt),
            force_tier=force_tier,
        )

        result = await client.generate_with_tools(
            prompt=prompt,
            tools=tools,
            system_instruction=system_instruction,
        )

        result["model"] = client.model_name
        result["tier"] = "light" if client == self.light else "heavy"

        return result


# Global router instance
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get the global LLM router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
