"""
Agent Planner

Responsible for decomposing user commands into executable subtasks.
"""

import json
from typing import List, Optional

from app.core.agent.state import AgentState, AgentPhase, SubTask
from app.core.llm.router import LLMRouter, ModelTier


PLANNER_SYSTEM_PROMPT = """你是一个专业的 AI 情报分析任务规划器。你的职责是将用户的调研命令分解为具体的可执行子任务。

## 你可以规划的任务类型：
1. **search** - 在平台上搜索内容
   - platforms: 要搜索的平台列表 (wechat, zhihu, xiaohongshu, douyin)
   - query: 搜索关键词
   - time_range: 时间范围 (1d, 7d, 30d)

2. **analyze** - 分析收集到的数据
   - analysis_type: sentiment（情感分析）, summary（摘要）, extract_entities（实体提取）

3. **memory_search** - 搜索历史情报库
   - query: 搜索查询
   - detect_changes: 是否检测时间线变化

4. **synthesize** - 综合所有数据生成报告

## 规划原则：
1. 每个任务应该具体、可执行
2. 搜索任务应覆盖多个相关平台
3. 分析任务应在搜索任务之后
4. 最后一个任务应该是 synthesize（综合）
5. 控制任务数量在 3-6 个之间

请以 JSON 格式返回任务列表。"""

PLANNER_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "string",
            "description": "对用户命令的简要分析"
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "task_type": {"type": "string", "enum": ["search", "analyze", "memory_search", "synthesize"]},
                    "parameters": {"type": "object"}
                },
                "required": ["description", "task_type"]
            }
        }
    },
    "required": ["analysis", "tasks"]
}


class Planner:
    """
    Task Planner - Decomposes commands into subtasks.

    Uses LLM to understand the command and create an execution plan.
    """

    def __init__(self, llm_router: LLMRouter):
        self.llm = llm_router

    async def plan(self, state: AgentState) -> List[SubTask]:
        """
        Create execution plan for the given command.

        Args:
            state: Current agent state with original command

        Returns:
            List of SubTask objects
        """
        command = state.original_command

        # Build prompt
        prompt = f"""请为以下调研命令创建执行计划：

命令: {command}

请分析这个命令，并返回一个 JSON 格式的任务计划。
确保任务计划覆盖信息搜集、分析和综合三个阶段。

返回格式：
{{
    "analysis": "对命令的理解和分析",
    "tasks": [
        {{
            "description": "任务描述",
            "task_type": "search|analyze|memory_search|synthesize",
            "parameters": {{...}}
        }}
    ]
}}"""

        try:
            # Use light model for planning (fast and cost-effective)
            result = await self.llm.generate(
                prompt=prompt,
                task="classify",  # Routing hint for light model
                system_instruction=PLANNER_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent plans
            )

            # Parse response
            plan_data = self._parse_plan_response(result["text"])

            # Convert to SubTask objects
            subtasks = []
            for task_data in plan_data.get("tasks", []):
                subtask = state.add_subtask(
                    description=task_data["description"],
                    task_type=task_data["task_type"],
                    parameters=task_data.get("parameters", {}),
                )
                subtasks.append(subtask)

            # Add thought step
            state.add_thought(
                phase=AgentPhase.PLANNING,
                thought=f"分析任务: {command}",
                action="decompose_task",
                observation=f"分解为 {len(subtasks)} 个子任务: {plan_data.get('analysis', '')}",
                tokens_used=result["usage"]["prompt_tokens"] + result["usage"]["completion_tokens"],
            )

            return subtasks

        except Exception as e:
            # Fallback to default plan
            return self._create_default_plan(state, str(e))

    def _parse_plan_response(self, response_text: str) -> dict:
        """Parse LLM response to extract plan data."""
        # Try to find JSON in response
        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract structured data
            return self._extract_plan_from_text(response_text)

    def _extract_plan_from_text(self, text: str) -> dict:
        """Extract plan from unstructured text (fallback)."""
        # Simple extraction based on keywords
        tasks = []

        # Default tasks based on common patterns
        if any(kw in text.lower() for kw in ["搜索", "search", "查找", "find"]):
            tasks.append({
                "description": "在主流平台搜索相关内容",
                "task_type": "search",
                "parameters": {"platforms": ["zhihu", "wechat"], "time_range": "7d"}
            })

        if any(kw in text.lower() for kw in ["分析", "analyze", "sentiment"]):
            tasks.append({
                "description": "分析收集到的内容",
                "task_type": "analyze",
                "parameters": {"analysis_type": "summary"}
            })

        # Always end with synthesize
        tasks.append({
            "description": "综合所有信息生成报告",
            "task_type": "synthesize",
            "parameters": {}
        })

        return {"analysis": "基于文本提取的默认计划", "tasks": tasks}

    def _create_default_plan(self, state: AgentState, error: str) -> List[SubTask]:
        """Create a default plan when LLM planning fails."""
        command = state.original_command

        # Extract potential keywords from command
        keywords = self._extract_keywords(command)
        query = keywords[0] if keywords else command

        default_tasks = [
            {
                "description": f"在知乎搜索 '{query}' 相关内容",
                "task_type": "search",
                "parameters": {"platforms": ["zhihu"], "query": query, "time_range": "7d"}
            },
            {
                "description": f"在微信公众号搜索 '{query}' 相关内容",
                "task_type": "search",
                "parameters": {"platforms": ["wechat"], "query": query, "time_range": "7d"}
            },
            {
                "description": "分析收集到的内容情感和关键信息",
                "task_type": "analyze",
                "parameters": {"analysis_type": "summary"}
            },
            {
                "description": "综合所有信息生成情报摘要",
                "task_type": "synthesize",
                "parameters": {}
            },
        ]

        subtasks = []
        for task_data in default_tasks:
            subtask = state.add_subtask(
                description=task_data["description"],
                task_type=task_data["task_type"],
                parameters=task_data["parameters"],
            )
            subtasks.append(subtask)

        # Add thought step about fallback
        state.add_thought(
            phase=AgentPhase.PLANNING,
            thought=f"规划任务时遇到问题，使用默认计划",
            action="fallback_plan",
            observation=f"创建了 {len(subtasks)} 个默认子任务",
        )

        return subtasks

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from command text."""
        # Simple keyword extraction (can be enhanced with NLP)
        # Remove common words
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这",
                     "monitor", "analyze", "search", "find", "track", "latest", "recent", "the", "a", "an", "for", "of", "and", "to", "in", "on"}

        words = text.replace("'", " ").replace('"', " ").split()
        keywords = [w for w in words if w.lower() not in stopwords and len(w) > 1]

        return keywords[:5]  # Return top 5 keywords
