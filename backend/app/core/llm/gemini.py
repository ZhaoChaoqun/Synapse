"""
Gemini API Client
"""

from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import settings


class GeminiClient:
    """Client for Google Gemini API."""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize Gemini client.

        Args:
            model_name: Model to use (gemini-2.0-flash or gemini-2.0-pro)
        """
        self.model_name = model_name
        self._model: Optional[genai.GenerativeModel] = None

        # Configure API key
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)

    @property
    def model(self) -> genai.GenerativeModel:
        """Get or create the model instance."""
        if self._model is None:
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
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
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # Create model with system instruction if provided
        if system_instruction:
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_instruction,
            )
        else:
            model = self.model

        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config,
        )

        # Extract token counts
        usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
        }

        return {
            "text": response.text,
            "usage": usage,
        }

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate content with function calling tools.

        Args:
            prompt: User prompt
            tools: List of tool definitions
            system_instruction: System instruction

        Returns:
            Dict with response and potential function calls
        """
        # Convert tools to Gemini format
        gemini_tools = []
        for tool in tools:
            gemini_tools.append(
                genai.protos.Tool(
                    function_declarations=[
                        genai.protos.FunctionDeclaration(
                            name=tool["name"],
                            description=tool["description"],
                            parameters=tool.get("parameters"),
                        )
                    ]
                )
            )

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_instruction,
            tools=gemini_tools,
        )

        response = await model.generate_content_async(prompt)

        # Check for function calls
        function_calls = []
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    function_calls.append({
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args),
                    })

        return {
            "text": response.text if not function_calls else None,
            "function_calls": function_calls,
            "usage": {
                "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            },
        }


# Singleton instances for light and heavy models
_light_client: Optional[GeminiClient] = None
_heavy_client: Optional[GeminiClient] = None


def get_light_client() -> GeminiClient:
    """Get light model client (Gemini Flash - fast, low cost)."""
    global _light_client
    if _light_client is None:
        _light_client = GeminiClient("gemini-2.0-flash")
    return _light_client


def get_heavy_client() -> GeminiClient:
    """Get heavy model client (Gemini Pro - high quality)."""
    global _heavy_client
    if _heavy_client is None:
        _heavy_client = GeminiClient("gemini-2.0-pro")
    return _heavy_client
