"""
Tool Registry

Central registry for all available tools.
"""

from typing import Dict, List, Optional, TYPE_CHECKING

from app.core.tools.base import BaseTool, ToolDefinition

if TYPE_CHECKING:
    from app.core.llm.router import LLMRouter


class ToolRegistry:
    """
    Central registry for Agent tools.

    Manages tool registration, lookup, and provides tool schemas
    for LLM function calling.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_names(self) -> List[str]:
        """Get all tool names."""
        return list(self._tools.keys())

    def get_definitions(self) -> List[ToolDefinition]:
        """Get definitions of all tools."""
        return [tool.definition for tool in self._tools.values()]

    def get_function_schemas(self) -> List[Dict]:
        """Get all tools as function schemas for LLM."""
        return [tool.to_function_schema() for tool in self._tools.values()]

    def get_tools_by_type(self, tool_type: str) -> List[BaseTool]:
        """Get tools filtered by type (based on name prefix)."""
        return [
            tool for tool in self._tools.values()
            if tool.name.startswith(tool_type)
        ]

    @classmethod
    def create_default(cls, llm_router: "LLMRouter") -> "ToolRegistry":
        """
        Create a registry with default tools.

        Args:
            llm_router: LLM router for tools that need LLM access

        Returns:
            ToolRegistry with all default tools registered
        """
        from app.core.tools.search_tool import PlatformSearchTool
        from app.core.tools.analyze_tool import AnalyzeTool
        from app.core.tools.memory_tool import MemorySearchTool
        from app.core.tools.synthesize_tool import SynthesizeTool

        registry = cls()

        # Register all tools
        registry.register(PlatformSearchTool())
        registry.register(AnalyzeTool(llm_router))
        registry.register(MemorySearchTool())
        registry.register(SynthesizeTool(llm_router))

        return registry


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry(llm_router: Optional["LLMRouter"] = None) -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        if llm_router is None:
            from app.core.llm.router import get_llm_router
            llm_router = get_llm_router()
        _registry = ToolRegistry.create_default(llm_router)
    return _registry
