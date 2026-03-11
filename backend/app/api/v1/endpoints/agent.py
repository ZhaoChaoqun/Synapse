"""
Agent API Endpoints
"""

import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.api.v1.schemas.agent import (
    AgentCommandRequest,
    AgentTaskResponse,
    SearchResultMetrics,
    SearchResultResponse,
    TaskResultsResponse,
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
        task_id = ""
        total_tokens = 0

        try:
            async for step in orchestrator.run(request.command):
                # Get task_id from orchestrator's current state (first time)
                if not task_id and orchestrator.current_state:
                    task_id = orchestrator.current_state.task_id
                    # Save to store immediately
                    _task_store[task_id] = orchestrator.current_state

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

        # Update store with final state (ensures collected_data is current)
        if orchestrator.current_state and task_id:
            _task_store[task_id] = orchestrator.current_state

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


@router.get("/tasks/{task_id}/results", response_model=TaskResultsResponse)
async def get_task_results(
    task_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source: Optional[str] = Query(default=None, description="Filter by source platform"),
    sentiment: Optional[str] = Query(default=None, description="Filter by sentiment"),
):
    """
    Get search results for a specific task.

    Returns the collected intelligence data with filtering and pagination support.

    Args:
        task_id: Task ID to get results for
        limit: Maximum number of results to return
        offset: Number of results to skip
        source: Filter by source platform (weixin, zhihu, weibo, xhs, douyin, web)
        sentiment: Filter by sentiment (positive, neutral, negative)
    """
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    state = _task_store[task_id]

    # Transform collected_data to SearchResultResponse format
    results = []
    facets: dict[str, dict[str, int]] = {
        "sources": defaultdict(int),
        "sentiments": defaultdict(int),
    }

    for item in state.collected_data:
        # Build SearchResultResponse from collected data
        result = _transform_to_search_result(item)
        if result:
            # Update facets
            facets["sources"][result.source] += 1
            if result.sentiment:
                facets["sentiments"][result.sentiment] += 1

            # Apply filters
            if source and result.source != source:
                continue
            if sentiment and result.sentiment != sentiment:
                continue

            results.append(result)

    # Sort by relevance score (descending)
    results.sort(key=lambda r: r.relevance_score, reverse=True)

    # Apply pagination
    total_count = len(results)
    paginated_results = results[offset : offset + limit]

    return TaskResultsResponse(
        task_id=task_id,
        query=state.original_command,
        results=paginated_results,
        total_count=total_count,
        facets=dict(facets) if facets else None,
    )


def _transform_to_search_result(item: dict) -> Optional[SearchResultResponse]:
    """
    Transform a collected data item to SearchResultResponse.

    Handles various data formats from different crawlers.
    """
    try:
        # Generate ID if not present
        result_id = item.get("id") or str(uuid.uuid4())[:12]

        # Extract common fields with fallbacks
        title = item.get("title") or item.get("name") or "无标题"
        url = item.get("url") or item.get("link") or ""
        source = item.get("source") or item.get("platform") or "web"
        snippet = item.get("snippet") or item.get("summary") or item.get("content", "")[:200]

        # Truncate snippet if too long
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."

        # Extract metrics if available
        metrics = None
        if any(k in item for k in ["views", "likes", "comments", "shares"]):
            metrics = SearchResultMetrics(
                views=item.get("views"),
                likes=item.get("likes"),
                comments=item.get("comments"),
                shares=item.get("shares"),
            )

        # Parse dates
        published_at = None
        if pub_date := item.get("published_at") or item.get("publish_time") or item.get("date"):
            if isinstance(pub_date, str):
                try:
                    published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except ValueError:
                    pass
            elif isinstance(pub_date, datetime):
                published_at = pub_date

        scraped_at = datetime.utcnow()
        if scraped := item.get("scraped_at") or item.get("collected_at"):
            if isinstance(scraped, str):
                try:
                    scraped_at = datetime.fromisoformat(scraped.replace("Z", "+00:00"))
                except ValueError:
                    pass
            elif isinstance(scraped, datetime):
                scraped_at = scraped

        # Calculate relevance score
        relevance_score = item.get("relevance_score") or item.get("score") or 50

        # Normalize source name
        source_mapping = {
            "wechat": "weixin",
            "微信": "weixin",
            "知乎": "zhihu",
            "微博": "weibo",
            "小红书": "xhs",
            "抖音": "douyin",
        }
        source = source_mapping.get(source.lower(), source.lower())

        return SearchResultResponse(
            id=result_id,
            title=title,
            url=url,
            source=source,
            snippet=snippet,
            content=item.get("content"),
            published_at=published_at,
            author=item.get("author"),
            metrics=metrics,
            relevance_score=min(100, max(0, int(relevance_score))),
            sentiment=item.get("sentiment"),
            tags=item.get("tags") or [],
            scraped_at=scraped_at,
        )
    except Exception:
        return None


@router.get("/tasks/{task_id}/entity-graph")
async def get_task_entity_graph(task_id: str):
    """
    Get entity relationship graph for a specific task.

    Extracts entities (companies, products, people, concepts) from collected data
    and builds a relationship graph based on co-occurrence analysis.

    Returns:
        Entity graph with nodes (entities) and edges (relationships)
    """
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    state = _task_store[task_id]

    if not state.collected_data:
        return {
            "entities": [],
            "relations": [],
            "centerEntity": None,
            "generatedAt": datetime.utcnow().isoformat(),
        }

    # Generate entity graph from collected data
    from app.core.analysis.entity_graph import generate_entity_graph

    graph = generate_entity_graph(
        data=state.collected_data,
        query=state.original_command,
    )

    return graph
