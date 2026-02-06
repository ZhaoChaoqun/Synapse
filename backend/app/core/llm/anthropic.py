"""
Anthropic Claude API Client via Agent Maestro Proxy

This client connects to Agent Maestro VS Code extension which provides
free access to Claude models through GitHub Copilot subscription.
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.config import settings


class AnthropicClient:
    """
    Client for Anthropic Claude API via Agent Maestro proxy.

    Agent Maestro runs as a VS Code extension and exposes Claude models
    at http://localhost:23333/api/anthropic/v1/messages
    """

    def __init__(
        self,
        model_name: str = "claude-opus-4.5",
        base_url: str = "http://localhost:23333/api/anthropic",
    ):
        """
        Initialize Anthropic client.

        Args:
            model_name: Claude model to use
            base_url: Agent Maestro proxy URL
        """
        self.model_name = model_name
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Generate content from prompt.

        Args:
            prompt: User prompt
            system_instruction: System instruction for the model
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Dict with text and token usage
        """
        messages = [{"role": "user", "content": prompt}]

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_instruction:
            payload["system"] = system_instruction

        response = await self.client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        return {
            "text": text,
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
        }

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """
        Generate content with streaming.

        Args:
            prompt: User prompt
            system_instruction: System instruction for the model
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Yields:
            Text chunks as they are generated
        """
        messages = [{"role": "user", "content": prompt}]

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if system_instruction:
            payload["system"] = system_instruction

        async with self.client.stream(
            "POST", "/v1/messages", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except json.JSONDecodeError:
                        continue

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Generate content with function calling tools.

        Args:
            prompt: User prompt
            tools: List of tool definitions
            system_instruction: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Dict with response and potential function calls
        """
        messages = [{"role": "user", "content": prompt}]

        # Convert tools to Anthropic format
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {"type": "object", "properties": {}}),
            })

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": anthropic_tools,
        }

        if system_instruction:
            payload["system"] = system_instruction

        response = await self.client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract text and function calls
        text = ""
        function_calls = []

        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use":
                function_calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "args": block.get("input", {}),
                })

        return {
            "text": text if text else None,
            "function_calls": function_calls,
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Multi-turn chat with Claude.

        Args:
            messages: List of message dicts with role and content
            system_instruction: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions
            stream: Whether to stream the response

        Returns:
            Dict with response content and usage
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        if system_instruction:
            payload["system"] = system_instruction

        if tools:
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {"type": "object", "properties": {}}),
                })
            payload["tools"] = anthropic_tools

        response = await self.client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        return data


async def check_agent_maestro_health(
    base_url: str = "http://localhost:23333"
) -> bool:
    """
    Check if Agent Maestro proxy is available.

    Args:
        base_url: Agent Maestro base URL

    Returns:
        True if available, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url}/api/v1/info")
            return response.status_code == 200
    except Exception:
        return False


# Singleton instances
_light_client: Optional[AnthropicClient] = None
_heavy_client: Optional[AnthropicClient] = None


def get_claude_light_client() -> AnthropicClient:
    """Get light Claude client (Claude Opus 4.5)."""
    global _light_client
    if _light_client is None:
        base_url = settings.agent_maestro_url if hasattr(settings, 'agent_maestro_url') else "http://localhost:23333/api/anthropic"
        _light_client = AnthropicClient(
            model_name="claude-opus-4.5",
            base_url=base_url,
        )
    return _light_client


def get_claude_heavy_client() -> AnthropicClient:
    """Get heavy Claude client (Claude Opus 4.5)."""
    global _heavy_client
    if _heavy_client is None:
        base_url = settings.agent_maestro_url if hasattr(settings, 'agent_maestro_url') else "http://localhost:23333/api/anthropic"
        _heavy_client = AnthropicClient(
            model_name="claude-opus-4.5",
            base_url=base_url,
        )
    return _heavy_client
