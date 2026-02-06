"""
LLM Router - Routes requests to appropriate model based on task complexity

Supports multiple LLM providers:
- Anthropic Claude (via Agent Maestro proxy - free with GitHub Copilot)
- Google Gemini (direct API)
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from app.config import settings


class ModelTier(str, Enum):
    """Model tier for routing."""

    LIGHT = "light"  # Fast, lower cost
    HEAVY = "heavy"  # High quality, more expensive


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients."""

    model_name: str

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        ...

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class LLMRouter:
    """
    LLM Router - Intelligently routes requests to the appropriate model.

    Supports:
    - Anthropic Claude via Agent Maestro (free with GitHub Copilot)
    - Google Gemini (direct API)

    Model tiers:
    - Light: Fast responses for filtering, classification, simple tasks
    - Heavy: High quality for complex analysis, synthesis, reasoning
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

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM Router.

        Args:
            provider: LLM provider to use ("anthropic" or "gemini").
                     Defaults to settings.llm_provider
        """
        self.provider = provider or settings.llm_provider
        self._light: Optional[LLMClient] = None
        self._heavy: Optional[LLMClient] = None

    @property
    def light(self) -> LLMClient:
        """Get light model client."""
        if self._light is None:
            self._light = self._create_client(ModelTier.LIGHT)
        return self._light

    @property
    def heavy(self) -> LLMClient:
        """Get heavy model client."""
        if self._heavy is None:
            self._heavy = self._create_client(ModelTier.HEAVY)
        return self._heavy

    def _create_client(self, tier: ModelTier) -> LLMClient:
        """Create an LLM client based on provider and tier."""
        if self.provider == "anthropic":
            from app.core.llm.anthropic import AnthropicClient

            model = (
                settings.claude_model_light
                if tier == ModelTier.LIGHT
                else settings.claude_model_heavy
            )
            return AnthropicClient(
                model_name=model,
                base_url=settings.agent_maestro_url,
            )
        else:
            # Default to Gemini
            from app.core.llm.gemini import GeminiClient

            model = (
                "gemini-2.0-flash" if tier == ModelTier.LIGHT else "gemini-2.0-pro"
            )
            return GeminiClient(model_name=model)

    def get_client(
        self,
        task: Optional[str] = None,
        content_length: Optional[int] = None,
        force_tier: Optional[ModelTier] = None,
    ) -> LLMClient:
        """
        Get appropriate client based on task or content.

        Args:
            task: Task type (e.g., "filter", "deep_analysis")
            content_length: Length of content to process
            force_tier: Force a specific model tier

        Returns:
            Appropriate LLM client instance
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
        result["provider"] = self.provider

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
        result["provider"] = self.provider

        return result


# Global router instance
_router: Optional[LLMRouter] = None


def get_llm_router(provider: Optional[str] = None) -> LLMRouter:
    """
    Get the global LLM router instance.

    Args:
        provider: Optional provider override. If specified and different
                 from current router, creates a new router.

    Returns:
        LLMRouter instance
    """
    global _router

    if _router is None:
        _router = LLMRouter(provider=provider)
    elif provider and provider != _router.provider:
        # Provider changed, create new router
        _router = LLMRouter(provider=provider)

    return _router


async def check_llm_availability() -> Dict[str, Any]:
    """
    Check availability of configured LLM provider.

    Returns:
        Dict with availability status and details
    """
    provider = settings.llm_provider

    if provider == "anthropic":
        from app.core.llm.anthropic import check_agent_maestro_health

        is_available = await check_agent_maestro_health(
            settings.agent_maestro_url.replace("/api/anthropic", "")
        )
        return {
            "provider": "anthropic",
            "available": is_available,
            "endpoint": settings.agent_maestro_url,
            "message": (
                "Agent Maestro proxy is available"
                if is_available
                else "Agent Maestro proxy not found. Make sure VS Code with Agent Maestro extension is running."
            ),
        }
    else:
        # Gemini - check if API key is configured
        is_available = bool(settings.gemini_api_key)
        return {
            "provider": "gemini",
            "available": is_available,
            "message": (
                "Gemini API key is configured"
                if is_available
                else "Gemini API key not configured. Set GEMINI_API_KEY in .env"
            ),
        }
