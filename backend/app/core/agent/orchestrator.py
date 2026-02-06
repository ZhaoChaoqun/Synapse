"""
Agent Orchestrator

The central coordinator for the Agentic Loop.
Manages the complete execution flow from command to final report.
"""

from typing import AsyncGenerator, Callable, Optional

from app.core.agent.state import AgentState, AgentPhase, ThoughtStep
from app.core.agent.planner import Planner
from app.core.agent.executor import Executor
from app.core.llm.router import LLMRouter, get_llm_router
from app.core.tools.registry import ToolRegistry, get_tool_registry


class AgentOrchestrator:
    """
    Agent Orchestrator - Coordinates the entire Agentic Loop.

    Execution flow:
    1. PLANNING: Decompose command into subtasks
    2. EXECUTING: Execute each subtask
    3. EXPANDING: Recursively search discovered keywords
    4. SYNTHESIZING: Generate final report

    The orchestrator yields ThoughtStep objects that can be streamed
    to the frontend for real-time display.
    """

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.llm = llm_router or get_llm_router()
        self.tools = tool_registry or get_tool_registry(self.llm)
        self.planner = Planner(self.llm)
        self.executor = Executor(self.tools)

    async def run(
        self,
        command: str,
        on_step: Optional[Callable[[ThoughtStep], None]] = None,
    ) -> AsyncGenerator[ThoughtStep, None]:
        """
        Execute the Agentic Loop for a command.

        Args:
            command: User command to execute
            on_step: Optional callback for each step (for real-time updates)

        Yields:
            ThoughtStep objects representing each step of execution
        """
        # Initialize state
        state = AgentState(original_command=command)
        state.mark_started()

        try:
            # Phase 1: Planning
            async for step in self._plan(state):
                if on_step:
                    on_step(step)
                yield step

            # Phase 2: Execute subtasks
            async for step in self._execute_subtasks(state):
                if on_step:
                    on_step(step)
                yield step

            # Phase 3: Recursive expansion (if any discovered keywords)
            async for step in self._expand_searches(state):
                if on_step:
                    on_step(step)
                yield step

            # Mark as completed
            state.mark_completed()

            # Yield final summary step
            summary_step = self._create_summary_step(state)
            if on_step:
                on_step(summary_step)
            yield summary_step

        except Exception as e:
            # Handle fatal errors
            state.mark_failed(str(e))
            error_step = state.thought_chain[-1] if state.thought_chain else ThoughtStep(
                phase=AgentPhase.FAILED,
                thought=f"执行失败: {str(e)}",
                action="fatal_error",
            )
            if on_step:
                on_step(error_step)
            yield error_step

    async def _plan(self, state: AgentState) -> AsyncGenerator[ThoughtStep, None]:
        """Execute planning phase."""
        state.current_phase = AgentPhase.PLANNING

        # Initial thought
        init_step = state.add_thought(
            phase=AgentPhase.PLANNING,
            thought=f"收到任务: {state.original_command}",
            action="receive_command",
            observation="开始分析任务...",
        )
        yield init_step

        # Execute planning
        await self.planner.plan(state)

        # Yield the planning result step
        if state.thought_chain and len(state.thought_chain) > 1:
            yield state.thought_chain[-1]

    async def _execute_subtasks(
        self, state: AgentState
    ) -> AsyncGenerator[ThoughtStep, None]:
        """Execute all planned subtasks."""
        while state.can_continue():
            subtask = state.get_current_subtask()
            if not subtask:
                break

            # Execute the subtask
            step = await self.executor.execute_subtask(state, subtask)
            yield step

            # Check if we should stop on error
            if subtask.status == "failed" and state.error_count >= 3:
                break

    async def _expand_searches(
        self, state: AgentState
    ) -> AsyncGenerator[ThoughtStep, None]:
        """Execute recursive search expansion for discovered keywords."""
        while state.pending_searches and state.can_continue():
            # Check expansion limit
            if state.expansion_count >= state.max_expansions:
                break

            keyword = state.pending_searches.pop(0)
            state.expansion_count += 1
            state.current_phase = AgentPhase.EXPANDING

            # Create expansion thought
            expand_step = state.add_thought(
                phase=AgentPhase.EXPANDING,
                thought=f"发现新关键词 '{keyword}'，进行追加搜索",
                action="recursive_expand",
            )
            yield expand_step

            # Execute expansion search
            search_tool = self.tools.get("platform_search")
            if search_tool:
                result = await search_tool.safe_execute(
                    query=keyword,
                    platforms=["zhihu", "wechat"],
                    limit=5,
                )

                if result.success and result.data:
                    # Add results to collected data
                    new_results = result.data.get("results", [])
                    state.collected_data.extend(new_results)

                    result_step = state.add_thought(
                        phase=AgentPhase.EXPANDING,
                        thought=f"追加搜索 '{keyword}' 完成",
                        action="expand_search",
                        observation=f"新增 {len(new_results)} 条结果",
                        tokens_used=result.tokens_used,
                    )
                    yield result_step

    def _create_summary_step(self, state: AgentState) -> ThoughtStep:
        """Create final summary step."""
        summary = state.to_summary()

        return ThoughtStep(
            phase=AgentPhase.COMPLETED,
            thought="任务执行完成",
            action="complete",
            observation=(
                f"共执行 {summary['total_steps']} 步，"
                f"收集 {summary['data_collected']} 条数据，"
                f"发现 {summary['keywords_discovered']} 个新关键词，"
                f"消耗 {summary['total_tokens']} tokens"
            ),
            tokens_used=0,
        )

    def get_state_summary(self, state: AgentState) -> dict:
        """Get a summary of the current state for API response."""
        return {
            "task_id": state.task_id,
            "command": state.original_command,
            "status": state.current_phase.value,
            "thought_chain": [step.to_log_dict() for step in state.thought_chain],
            "collected_data_count": len(state.collected_data),
            "discovered_keywords": state.discovered_keywords,
            "total_tokens": state.total_tokens,
            "summary": state.to_summary(),
        }


# Factory function for creating orchestrator instances
def create_orchestrator() -> AgentOrchestrator:
    """Create a new AgentOrchestrator instance with default dependencies."""
    llm_router = get_llm_router()
    tool_registry = get_tool_registry(llm_router)
    return AgentOrchestrator(llm_router, tool_registry)
