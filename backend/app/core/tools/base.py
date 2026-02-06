"""
Tool Base Classes and Interfaces

Defines the base class and interfaces for Agent tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str
    type: str  # string, integer, number, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Definition of a tool for LLM function calling."""

    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)


class ToolResult(BaseModel):
    """Result of a tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    tokens_used: int = 0
    duration_ms: int = 0

    @classmethod
    def ok(cls, data: Any, tokens_used: int = 0, duration_ms: int = 0) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data, tokens_used=tokens_used, duration_ms=duration_ms)

    @classmethod
    def fail(cls, error: str, duration_ms: int = 0) -> "ToolResult":
        """Create a failed result."""
        return cls(success=False, error=error, duration_ms=duration_ms)


class BaseTool(ABC):
    """
    Base class for all Agent tools.

    Tools are the "hands" of the Agent - they perform actual work
    like searching, scraping, analyzing, etc.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (unique identifier)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass

    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters. Override to define parameters."""
        return []

    @property
    def definition(self) -> ToolDefinition:
        """Get the complete tool definition."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with success/failure and data
        """
        pass

    def to_function_schema(self) -> Dict[str, Any]:
        """Convert to Gemini Function Calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def validate_params(self, **kwargs) -> Optional[str]:
        """
        Validate input parameters.

        Returns None if valid, error message if invalid.
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return f"Missing required parameter: {param.name}"

            if param.name in kwargs:
                value = kwargs[param.name]
                # Basic type checking
                if param.type == "string" and not isinstance(value, str):
                    return f"Parameter {param.name} must be a string"
                elif param.type == "integer" and not isinstance(value, int):
                    return f"Parameter {param.name} must be an integer"
                elif param.type == "array" and not isinstance(value, list):
                    return f"Parameter {param.name} must be an array"
                elif param.enum and value not in param.enum:
                    return f"Parameter {param.name} must be one of: {param.enum}"

        return None

    async def safe_execute(self, **kwargs) -> ToolResult:
        """Execute with validation and error handling."""
        # Validate parameters
        if error := self.validate_params(**kwargs):
            return ToolResult.fail(error)

        try:
            return await self.execute(**kwargs)
        except Exception as e:
            return ToolResult.fail(f"Tool execution failed: {str(e)}")
