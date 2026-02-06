"""
Agent Executor

Responsible for executing subtasks using the appropriate tools.
"""

import time
from typing import Any, Dict, Optional

from app.core.agent.state import AgentState, AgentPhase, SubTask, ThoughtStep
from app.core.tools.registry import ToolRegistry
from app.core.tools.base import ToolResult


class Executor:
    """
    Task Executor - Executes subtasks using tools.

    Maps task types to tools and handles execution flow.
    """

    # Mapping from task types to tool names
    TASK_TOOL_MAPPING = {
        "search": "platform_search",
        "analyze": "analyze",
        "memory_search": "memory_search",
        "synthesize": "synthesize",
    }

    # Mapping from task types to agent phases
    TASK_PHASE_MAPPING = {
        "search": AgentPhase.SEARCHING,
        "analyze": AgentPhase.EXECUTING,
        "memory_search": AgentPhase.SEARCHING,
        "synthesize": AgentPhase.SYNTHESIZING,
    }

    def __init__(self, tool_registry: ToolRegistry):
        self.tools = tool_registry

    async def execute_subtask(
        self, state: AgentState, subtask: SubTask
    ) -> ThoughtStep:
        """
        Execute a single subtask.

        Args:
            state: Current agent state
            subtask: Subtask to execute

        Returns:
            ThoughtStep recording the execution
        """
        start_time = time.time()

        # Get tool for this task type
        tool_name = self.TASK_TOOL_MAPPING.get(subtask.task_type)
        if not tool_name:
            return self._create_error_step(
                state, subtask, f"Unknown task type: {subtask.task_type}"
            )

        tool = self.tools.get(tool_name)
        if not tool:
            return self._create_error_step(
                state, subtask, f"Tool not found: {tool_name}"
            )

        # Update phase
        phase = self.TASK_PHASE_MAPPING.get(subtask.task_type, AgentPhase.EXECUTING)
        state.current_phase = phase

        # Mark subtask as running
        subtask.status = "running"

        # Prepare parameters
        params = self._prepare_tool_params(state, subtask)

        # Execute tool
        try:
            result = await tool.safe_execute(**params)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.success:
                return self._handle_success(state, subtask, result, phase, duration_ms)
            else:
                return self._handle_failure(state, subtask, result, phase, duration_ms)

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return self._handle_exception(state, subtask, e, phase, duration_ms)

    def _prepare_tool_params(
        self, state: AgentState, subtask: SubTask
    ) -> Dict[str, Any]:
        """Prepare parameters for tool execution."""
        params = subtask.parameters.copy()

        # Add context-specific parameters
        if subtask.task_type == "search":
            # Use command as query if not specified
            if "query" not in params:
                params["query"] = state.original_command

        elif subtask.task_type == "analyze":
            # Pass collected data
            if "data" not in params:
                params["data"] = state.collected_data

        elif subtask.task_type == "synthesize":
            # Pass all context
            params["collected_data"] = state.collected_data
            params["original_command"] = state.original_command
            # Gather analysis results from previous subtasks
            analysis_results = {}
            for st in state.subtasks:
                if st.task_type == "analyze" and st.result:
                    analysis_results.update(st.result)
            params["analysis_results"] = analysis_results

        return params

    def _handle_success(
        self,
        state: AgentState,
        subtask: SubTask,
        result: ToolResult,
        phase: AgentPhase,
        duration_ms: int,
    ) -> ThoughtStep:
        """Handle successful tool execution."""
        data = result.data or {}

        # Process search results
        if subtask.task_type == "search" and "results" in data:
            # Add to collected data
            state.collected_data.extend(data["results"])

            # Process discovered keywords for expansion
            if "discovered_keywords" in data:
                for keyword in data["discovered_keywords"]:
                    if state.add_discovered_keyword(keyword):
                        pass  # Keyword added to pending searches

            observation = f"找到 {data.get('total', 0)} 条结果"
            if data.get("discovered_keywords"):
                observation += f"，发现新关键词: {', '.join(data['discovered_keywords'])}"

        elif subtask.task_type == "analyze":
            observation = "分析完成"
            if "main_points" in data:
                observation += f"，提取了 {len(data['main_points'])} 个要点"

        elif subtask.task_type == "synthesize":
            observation = "情报报告生成完成"
            if "executive_summary" in data:
                observation += f": {data['executive_summary'][:50]}..."

        elif subtask.task_type == "memory_search":
            observation = f"找到 {data.get('total', 0)} 条历史记录"
            if data.get("timeline_changes"):
                observation += f"，检测到 {len(data['timeline_changes'])} 个时间线变化"

        else:
            observation = "执行完成"

        # Complete subtask
        state.complete_current_subtask(result=data)

        # Create thought step
        step = state.add_thought(
            phase=phase,
            thought=f"执行: {subtask.description}",
            action=subtask.task_type,
            observation=observation,
            tokens_used=result.tokens_used,
        )
        step.duration_ms = duration_ms

        return step

    def _handle_failure(
        self,
        state: AgentState,
        subtask: SubTask,
        result: ToolResult,
        phase: AgentPhase,
        duration_ms: int,
    ) -> ThoughtStep:
        """Handle failed tool execution."""
        subtask.status = "failed"
        state.error_count += 1

        step = state.add_thought(
            phase=phase,
            thought=f"执行失败: {subtask.description}",
            action=subtask.task_type,
            observation=f"错误: {result.error}",
        )
        step.duration_ms = duration_ms

        return step

    def _handle_exception(
        self,
        state: AgentState,
        subtask: SubTask,
        exception: Exception,
        phase: AgentPhase,
        duration_ms: int,
    ) -> ThoughtStep:
        """Handle execution exception."""
        subtask.status = "failed"
        state.error_count += 1

        step = state.add_thought(
            phase=phase,
            thought=f"执行异常: {subtask.description}",
            action=subtask.task_type,
            observation=f"异常: {str(exception)}",
        )
        step.duration_ms = duration_ms

        return step

    def _create_error_step(
        self, state: AgentState, subtask: SubTask, error: str
    ) -> ThoughtStep:
        """Create an error thought step."""
        subtask.status = "failed"
        state.error_count += 1

        return state.add_thought(
            phase=AgentPhase.FAILED,
            thought=f"无法执行: {subtask.description}",
            action="error",
            observation=error,
        )
