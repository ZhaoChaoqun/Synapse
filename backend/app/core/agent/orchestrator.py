"""
Agent Orchestrator

The central coordinator for the Agentic Loop.
Manages the complete execution flow from command to final report.
"""

import logging
from typing import AsyncGenerator, Callable, List, Optional

from app.core.agent.state import AgentState, AgentPhase, ThoughtStep
from app.core.agent.planner import Planner
from app.core.agent.executor import Executor
from app.core.agent.critic import Critic, CritiqueResult, get_critic
from app.core.agent.expander import SearchExpander, get_search_expander
from app.core.agent.self_healer import SelfHealer, ErrorContext, get_self_healer
from app.core.llm.router import LLMRouter, get_llm_router
from app.core.tools.registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent Orchestrator - Coordinates the entire Agentic Loop.

    Execution flow:
    1. PLANNING: Decompose command into subtasks
    2. EXECUTING: Execute each subtask
    3. CRITIQUING: Evaluate data quality (NEW)
    4. EXPANDING: Recursively search discovered keywords
    5. SYNTHESIZING: Generate final report

    Advanced features:
    - Critical evaluation of collected data
    - Intelligent search expansion
    - Error self-healing

    The orchestrator yields ThoughtStep objects that can be streamed
    to the frontend for real-time display.
    """

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        tool_registry: Optional[ToolRegistry] = None,
        critic: Optional[Critic] = None,
        expander: Optional[SearchExpander] = None,
        self_healer: Optional[SelfHealer] = None,
    ):
        self.llm = llm_router or get_llm_router()
        self.tools = tool_registry or get_tool_registry(self.llm)
        self.planner = Planner(self.llm)
        self.executor = Executor(self.tools)
        self.critic = critic or get_critic()
        self.expander = expander or get_search_expander()
        self.self_healer = self_healer or get_self_healer()

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

            # Phase 3: Critical evaluation
            async for step in self._critique(state):
                if on_step:
                    on_step(step)
                yield step

            # Phase 4: Intelligent expansion (based on critique)
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
            # Attempt self-healing
            async for step in self._handle_error(state, e):
                if on_step:
                    on_step(step)
                yield step

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
        """Execute all planned subtasks with error handling."""
        while state.can_continue():
            subtask = state.get_current_subtask()
            if not subtask:
                break

            try:
                # Execute the subtask
                step = await self.executor.execute_subtask(state, subtask)
                yield step

                # Check if we should stop on error
                if subtask.status == "failed" and state.error_count >= 3:
                    break

            except Exception as e:
                # Classify and attempt recovery
                error_context = self.self_healer.classify_error(e, subtask.task_type)
                state.error_count += 1

                # Try to recover
                recovery_action = self.self_healer.get_recovery_action(
                    error_context,
                    available_platforms=["zhihu", "wechat", "xiaohongshu", "douyin"],
                )

                recovery_step = state.add_thought(
                    phase=AgentPhase.RECOVERING,
                    thought=f"执行出错: {error_context.message}",
                    action="error_recovery",
                    observation=f"恢复策略: {recovery_action.description}",
                )
                yield recovery_step

                # Attempt recovery
                result = await self.self_healer.attempt_recovery(
                    error_context,
                    recovery_action,
                )

                if not result.success:
                    # Mark subtask as failed and continue
                    subtask.status = "failed"
                    state.complete_current_subtask()

    async def _critique(self, state: AgentState) -> AsyncGenerator[ThoughtStep, None]:
        """Execute critical evaluation phase."""
        if not state.collected_data:
            return

        state.current_phase = AgentPhase.CRITIQUING

        critique_start = state.add_thought(
            phase=AgentPhase.CRITIQUING,
            thought="开始评估收集的数据质量",
            action="start_critique",
        )
        yield critique_start

        # Perform evaluation
        critique_result = await self.critic.evaluate(
            data=state.collected_data,
            original_query=state.original_command,
        )

        # Store critique result in state
        state.credibility_scores["overall"] = critique_result.overall_score
        state.credibility_scores["credibility"] = critique_result.credibility_score
        state.credibility_scores["coverage"] = critique_result.coverage_score

        # Report critique results
        critique_step = state.add_thought(
            phase=AgentPhase.CRITIQUING,
            thought=critique_result.summary,
            action="critique_complete",
            observation=self._format_critique_observation(critique_result),
        )
        yield critique_step

        # If quality is low, add suggestions to pending searches
        if critique_result.needs_improvement:
            for search in critique_result.recommended_searches[:2]:
                if state.add_discovered_keyword(search):
                    logger.info(f"Added critique-recommended search: {search}")

        # Log issues if any
        if critique_result.issues:
            issue_step = state.add_thought(
                phase=AgentPhase.CRITIQUING,
                thought=f"发现 {len(critique_result.issues)} 个数据质量问题",
                action="log_issues",
                observation="; ".join(
                    issue.get("message", "") for issue in critique_result.issues[:3]
                ),
            )
            yield issue_step

    async def _expand_searches(
        self, state: AgentState
    ) -> AsyncGenerator[ThoughtStep, None]:
        """Execute intelligent search expansion."""
        # First, analyze for expansion candidates
        if state.collected_data and state.expansion_count < state.max_expansions:
            expansion_plan = await self.expander.analyze(
                data=state.collected_data,
                original_query=state.original_command,
                already_searched=list(state.discovered_keywords) + [state.original_command],
            )

            # Add priority keywords to pending searches
            for keyword in expansion_plan.priority_keywords:
                if keyword not in state.pending_searches:
                    state.pending_searches.append(keyword)

            if expansion_plan.priority_keywords:
                expansion_step = state.add_thought(
                    phase=AgentPhase.EXPANDING,
                    thought=expansion_plan.reason,
                    action="analyze_expansion",
                    observation=f"建议搜索: {', '.join(expansion_plan.priority_keywords[:3])}",
                )
                yield expansion_step

        # Execute pending searches
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
                thought=f"追加搜索关键词: '{keyword}'",
                action="recursive_expand",
            )
            yield expand_step

            # Execute expansion search
            search_tool = self.tools.get("platform_search")
            if search_tool:
                try:
                    result = await search_tool.safe_execute(
                        query=keyword,
                        platforms=["zhihu", "wechat"],
                        limit=5,
                    )

                    if result.success and result.data:
                        # Add results to collected data
                        new_results = result.data.get("results", [])
                        state.collected_data.extend(new_results)

                        # Track this keyword as searched
                        state.discovered_keywords.append(keyword)

                        result_step = state.add_thought(
                            phase=AgentPhase.EXPANDING,
                            thought=f"追加搜索 '{keyword}' 完成",
                            action="expand_search",
                            observation=f"新增 {len(new_results)} 条结果",
                            tokens_used=result.tokens_used,
                        )
                        yield result_step
                    else:
                        fail_step = state.add_thought(
                            phase=AgentPhase.EXPANDING,
                            thought=f"追加搜索 '{keyword}' 无结果",
                            action="expand_no_result",
                        )
                        yield fail_step

                except Exception as e:
                    # Handle expansion error gracefully
                    error_step = state.add_thought(
                        phase=AgentPhase.EXPANDING,
                        thought=f"追加搜索 '{keyword}' 失败: {str(e)[:50]}",
                        action="expand_error",
                    )
                    yield error_step

    async def _handle_error(
        self, state: AgentState, error: Exception
    ) -> AsyncGenerator[ThoughtStep, None]:
        """Handle fatal errors with self-healing."""
        state.current_phase = AgentPhase.RECOVERING

        # Classify error
        error_context = self.self_healer.classify_error(error, "orchestrator")

        error_step = state.add_thought(
            phase=AgentPhase.RECOVERING,
            thought=f"执行遇到严重错误: {str(error)[:100]}",
            action="fatal_error",
            observation=f"错误类型: {error_context.error_type.value}",
        )
        yield error_step

        # Get recovery action
        recovery_action = self.self_healer.get_recovery_action(error_context)

        # Attempt recovery
        result = await self.self_healer.attempt_recovery(error_context, recovery_action)

        if result.success:
            recovery_step = state.add_thought(
                phase=AgentPhase.RECOVERING,
                thought="错误恢复成功",
                action="recovery_success",
                observation=result.message,
            )
            yield recovery_step
        else:
            # Mark as failed
            state.mark_failed(str(error))
            fail_step = state.thought_chain[-1] if state.thought_chain else ThoughtStep(
                phase=AgentPhase.FAILED,
                thought=f"执行失败: {str(error)}",
                action="fatal_error",
            )
            yield fail_step

    def _format_critique_observation(self, critique: CritiqueResult) -> str:
        """Format critique result for observation."""
        parts = [
            f"综合评分: {critique.overall_score:.0%}",
            f"可信度: {critique.credibility_score:.0%}",
            f"覆盖度: {critique.coverage_score:.0%}",
        ]

        if critique.missing_aspects:
            parts.append(f"缺失: {', '.join(critique.missing_aspects[:2])}")

        if critique.suggestions:
            parts.append(f"建议: {critique.suggestions[0]}")

        return " | ".join(parts)

    def _create_summary_step(self, state: AgentState) -> ThoughtStep:
        """Create final summary step."""
        summary = state.to_summary()

        # Add critique scores to summary
        quality_info = ""
        if "overall" in state.credibility_scores:
            quality_info = f"数据质量: {state.credibility_scores['overall']:.0%}, "

        return ThoughtStep(
            phase=AgentPhase.COMPLETED,
            thought="任务执行完成",
            action="complete",
            observation=(
                f"共执行 {summary['total_steps']} 步，"
                f"收集 {summary['data_collected']} 条数据，"
                f"{quality_info}"
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
            "quality_scores": state.credibility_scores,
            "error_stats": self.self_healer.get_error_stats(),
            "summary": state.to_summary(),
        }


# Factory function for creating orchestrator instances
def create_orchestrator() -> AgentOrchestrator:
    """Create a new AgentOrchestrator instance with default dependencies."""
    llm_router = get_llm_router()
    tool_registry = get_tool_registry(llm_router)
    return AgentOrchestrator(llm_router, tool_registry)
