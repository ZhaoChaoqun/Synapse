"""
Agent API Endpoints
"""

import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.api.v1.schemas.agent import (
    AgentCommandRequest,
    AgentTaskResponse,
    ThoughtStepResponse,
)
from app.core.agent.orchestrator import AgentOrchestrator, create_orchestrator
from app.core.agent.state import AgentState, ThoughtStep

router = APIRouter(prefix="/agent", tags=["Agent"])

# Store for tracking active and recent tasks
# In production, this should be in Redis or database
_task_store: dict[str, AgentState] = {}


@router.post("/execute")
async def execute_command(request: AgentCommandRequest):
    """
    Execute an Agent command with SSE streaming response.

    Returns Server-Sent Events stream with real-time thought steps.

    The stream emits:
    - `thought` events: Each step of the Agent's reasoning
    - `complete` event: Final summary when execution completes

    Example usage with JavaScript:
    ```javascript
    const eventSource = new EventSource('/api/v1/agent/execute?command=...');
    eventSource.addEventListener('thought', (e) => console.log(JSON.parse(e.data)));
    eventSource.addEventListener('complete', (e) => eventSource.close());
    ```
    """
    orchestrator = create_orchestrator()

    async def event_generator() -> AsyncGenerator[dict, None]:
        state: Optional[AgentState] = None
        total_tokens = 0
        task_id = ""

        try:
            async for step in orchestrator.run(request.command):
                # Get task_id from first step
                if not task_id and hasattr(step, 'step_id'):
                    # Extract task_id from orchestrator state
                    pass

                total_tokens += step.tokens_used

                # Convert step to dict for SSE
                step_data = step.to_log_dict()

                yield {
                    "event": "thought",
                    "data": json.dumps(step_data, ensure_ascii=False),
                }

        except Exception as e:
            # Emit error event
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": str(e), "phase": "execution"},
                    ensure_ascii=False,
                ),
            }

        # Emit completion event
        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "task_id": task_id or "task_unknown",
                    "total_tokens": total_tokens,
                    "status": "completed",
                },
                ensure_ascii=False,
            ),
        }

    return EventSourceResponse(event_generator())


@router.post("/execute/sync")
async def execute_command_sync(request: AgentCommandRequest):
    """
    Execute an Agent command synchronously (non-streaming).

    Returns the complete result after execution finishes.
    Useful for testing or when SSE is not available.
    """
    orchestrator = create_orchestrator()

    thought_chain = []
    total_tokens = 0

    async for step in orchestrator.run(request.command):
        thought_chain.append(step.to_log_dict())
        total_tokens += step.tokens_used

    return {
        "status": "completed",
        "thought_chain": thought_chain,
        "total_steps": len(thought_chain),
        "total_tokens": total_tokens,
    }


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(task_id: str):
    """
    Get task details by ID.

    Returns the full execution history and results for a task.
    """
    # Check in-memory store first
    if task_id in _task_store:
        state = _task_store[task_id]
        return AgentTaskResponse(
            task_id=state.task_id,
            command=state.original_command,
            status=state.current_phase.value,
            thought_chain=[
                ThoughtStepResponse(
                    step_id=step.step_id,
                    phase=step.phase,
                    timestamp=step.timestamp,
                    thought=step.thought,
                    action=step.action,
                    observation=step.observation,
                    progress=step._calculate_progress(),
                    tokens_used=step.tokens_used,
                )
                for step in state.thought_chain
            ],
            result_summary=None,  # TODO: Generate from synthesize result
            intelligence_count=len(state.collected_data),
            total_tokens=state.total_tokens,
            duration_ms=state.total_duration_ms,
            created_at=state.started_at,
            completed_at=state.completed_at,
        )

    # TODO: Query from database
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.get("/tasks")
async def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
):
    """
    List all tasks with pagination.

    Args:
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip
        status: Filter by status (optional)
    """
    # Get from in-memory store
    tasks = list(_task_store.values())

    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t.current_phase.value == status]

    # Sort by start time (newest first)
    tasks.sort(key=lambda t: t.started_at or t.task_id, reverse=True)

    # Apply pagination
    paginated = tasks[offset : offset + limit]

    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "command": t.original_command[:100],  # Truncate for list view
                "status": t.current_phase.value,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "total_tokens": t.total_tokens,
            }
            for t in paginated
        ],
        "total": len(tasks),
        "limit": limit,
        "offset": offset,
    }


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task by ID."""
    if task_id in _task_store:
        del _task_store[task_id]
        return {"message": f"Task {task_id} deleted"}

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
