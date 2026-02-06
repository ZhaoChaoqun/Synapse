"""
Agent API Endpoints
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.v1.schemas.agent import (
    AgentCommandRequest,
    AgentTaskResponse,
    ThoughtStepResponse,
)

router = APIRouter(prefix="/agent", tags=["Agent"])


async def mock_thought_stream(command: str) -> AsyncGenerator[dict, None]:
    """
    Mock thought stream for development.
    TODO: Replace with actual AgentOrchestrator.run()
    """
    import asyncio
    from datetime import datetime

    steps = [
        {
            "step_id": "step_1",
            "phase": "planning",
            "timestamp": datetime.now().isoformat(),
            "thought": f"分析任务: {command}",
            "action": "decompose_task",
            "observation": "分解为 3 个子任务",
            "progress": 20,
            "tokens_used": 150,
        },
        {
            "step_id": "step_2",
            "phase": "searching",
            "timestamp": datetime.now().isoformat(),
            "thought": "正在搜索知乎相关内容...",
            "action": "platform_search",
            "observation": "找到 15 条相关结果",
            "progress": 40,
            "tokens_used": 200,
        },
        {
            "step_id": "step_3",
            "phase": "expanding",
            "timestamp": datetime.now().isoformat(),
            "thought": "发现新关键词 'DeepSeek R1'，追加搜索...",
            "action": "recursive_search",
            "observation": "追加搜索完成，新增 8 条结果",
            "progress": 60,
            "tokens_used": 180,
        },
        {
            "step_id": "step_4",
            "phase": "critiquing",
            "timestamp": datetime.now().isoformat(),
            "thought": "正在交叉验证信息可信度...",
            "action": "critical_evaluation",
            "observation": "23 条高可信度，5 条需复核",
            "progress": 80,
            "tokens_used": 300,
        },
        {
            "step_id": "step_5",
            "phase": "synthesizing",
            "timestamp": datetime.now().isoformat(),
            "thought": "生成情报摘要...",
            "action": "synthesize",
            "observation": "情报摘要生成完成",
            "progress": 100,
            "tokens_used": 250,
        },
    ]

    for step in steps:
        await asyncio.sleep(0.8)  # Simulate processing time
        yield step


@router.post("/execute")
async def execute_command(request: AgentCommandRequest):
    """
    Execute an Agent command with SSE streaming response.

    Returns Server-Sent Events stream with real-time thought steps.
    """

    async def event_generator():
        total_tokens = 0
        async for step in mock_thought_stream(request.command):
            total_tokens += step.get("tokens_used", 0)
            yield {
                "event": "thought",
                "data": json.dumps(step, ensure_ascii=False),
            }
        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "task_id": "task_mock_001",
                    "intelligence_count": 28,
                    "total_tokens": total_tokens,
                },
                ensure_ascii=False,
            ),
        }

    return EventSourceResponse(event_generator())


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(task_id: str):
    """Get task details by ID."""
    # TODO: Implement database query
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/tasks")
async def list_tasks(limit: int = 20, offset: int = 0):
    """List all tasks with pagination."""
    # TODO: Implement database query
    return {"tasks": [], "total": 0, "limit": limit, "offset": offset}
