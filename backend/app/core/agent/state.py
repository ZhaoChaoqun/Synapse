"""
Agent State Management

Defines the state machine and data structures for Agent execution.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentPhase(str, Enum):
    """Agent execution phases."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    SEARCHING = "searching"
    SCRAPING = "scraping"
    EXPANDING = "expanding"  # Recursive search expansion
    CRITIQUING = "critiquing"  # Critical evaluation
    SYNTHESIZING = "synthesizing"
    RECOVERING = "recovering"  # Error recovery
    COMPLETED = "completed"
    FAILED = "failed"


class ThoughtStep(BaseModel):
    """
    Single thought step record for displaying to frontend.

    Each step represents one action in the Agent's reasoning chain.
    """

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    phase: AgentPhase
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    thought: str  # Agent's "thinking" - what it's considering
    action: Optional[str] = None  # Action being taken
    observation: Optional[str] = None  # Result observed
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dict for SSE streaming."""
        return {
            "step_id": self.step_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
            "progress": self._calculate_progress(),
            "tokens_used": self.tokens_used,
        }

    def _calculate_progress(self) -> int:
        """Calculate progress percentage based on phase."""
        phase_progress = {
            AgentPhase.IDLE: 0,
            AgentPhase.PLANNING: 10,
            AgentPhase.EXECUTING: 30,
            AgentPhase.SEARCHING: 40,
            AgentPhase.SCRAPING: 50,
            AgentPhase.EXPANDING: 60,
            AgentPhase.CRITIQUING: 80,
            AgentPhase.SYNTHESIZING: 90,
            AgentPhase.COMPLETED: 100,
            AgentPhase.FAILED: 100,
            AgentPhase.RECOVERING: 70,
        }
        return phase_progress.get(self.phase, 50)


class SubTask(BaseModel):
    """A sub-task decomposed from the main command."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    task_type: str  # search, scrape, analyze, etc.
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None


class AgentState(BaseModel):
    """
    Agent runtime state.

    Tracks all aspects of an Agent's execution including:
    - Task information
    - Execution progress
    - Collected data
    - Error handling
    """

    # Task identification
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    original_command: str
    current_phase: AgentPhase = AgentPhase.IDLE

    # Task decomposition
    subtasks: List[SubTask] = Field(default_factory=list)
    current_subtask_index: int = 0

    # Thought chain (for frontend display)
    thought_chain: List[ThoughtStep] = Field(default_factory=list)

    # Discovery and expansion
    discovered_keywords: List[str] = Field(default_factory=list)
    pending_searches: List[str] = Field(default_factory=list)  # Queue for recursive search

    # Collected data
    collected_data: List[Dict[str, Any]] = Field(default_factory=list)
    credibility_scores: Dict[str, float] = Field(default_factory=dict)

    # Statistics
    total_tokens: int = 0
    total_duration_ms: int = 0
    error_count: int = 0

    # Execution limits
    max_steps: int = 15
    max_expansions: int = 3  # Max recursive search expansions
    current_step: int = 0
    expansion_count: int = 0

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_thought(
        self,
        phase: AgentPhase,
        thought: str,
        action: Optional[str] = None,
        observation: Optional[str] = None,
        tokens_used: int = 0,
    ) -> ThoughtStep:
        """Add a thought step to the chain."""
        step = ThoughtStep(
            phase=phase,
            thought=thought,
            action=action,
            observation=observation,
            tokens_used=tokens_used,
        )
        self.thought_chain.append(step)
        self.total_tokens += tokens_used
        self.current_step += 1
        return step

    def add_subtask(
        self,
        description: str,
        task_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SubTask:
        """Add a subtask to the plan."""
        subtask = SubTask(
            description=description,
            task_type=task_type,
            parameters=parameters or {},
        )
        self.subtasks.append(subtask)
        return subtask

    def get_current_subtask(self) -> Optional[SubTask]:
        """Get the current subtask being executed."""
        if self.current_subtask_index < len(self.subtasks):
            return self.subtasks[self.current_subtask_index]
        return None

    def complete_current_subtask(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark current subtask as completed and move to next."""
        if subtask := self.get_current_subtask():
            subtask.status = "completed"
            subtask.result = result
            self.current_subtask_index += 1

    def add_discovered_keyword(self, keyword: str) -> bool:
        """
        Add a discovered keyword for potential expansion.

        Returns True if keyword was added (not seen before).
        """
        if keyword not in self.discovered_keywords:
            self.discovered_keywords.append(keyword)
            if self.expansion_count < self.max_expansions:
                self.pending_searches.append(keyword)
            return True
        return False

    def can_continue(self) -> bool:
        """Check if execution can continue."""
        return (
            self.current_step < self.max_steps
            and self.current_phase not in (AgentPhase.COMPLETED, AgentPhase.FAILED)
            and self.error_count < 3
        )

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.started_at = datetime.utcnow()
        self.current_phase = AgentPhase.PLANNING

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        self.completed_at = datetime.utcnow()
        self.current_phase = AgentPhase.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Mark execution as failed."""
        self.completed_at = datetime.utcnow()
        self.current_phase = AgentPhase.FAILED
        self.add_thought(
            phase=AgentPhase.FAILED,
            thought=f"任务失败: {error}",
            action="fail",
        )

    def to_summary(self) -> Dict[str, Any]:
        """Generate execution summary."""
        return {
            "task_id": self.task_id,
            "command": self.original_command,
            "status": self.current_phase.value,
            "total_steps": self.current_step,
            "total_tokens": self.total_tokens,
            "data_collected": len(self.collected_data),
            "keywords_discovered": len(self.discovered_keywords),
            "duration_ms": (
                int((self.completed_at - self.started_at).total_seconds() * 1000)
                if self.completed_at and self.started_at
                else self.total_duration_ms
            ),
        }
