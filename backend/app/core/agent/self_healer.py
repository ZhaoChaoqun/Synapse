"""
Self-Healing Module

Provides error recovery and self-healing capabilities for the Agent.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors the Agent can encounter."""

    NETWORK = "network"  # Network/connectivity issues
    RATE_LIMIT = "rate_limit"  # API rate limiting
    BLOCKED = "blocked"  # Platform blocked access
    PARSE = "parse"  # Data parsing errors
    TIMEOUT = "timeout"  # Request timeout
    AUTH = "auth"  # Authentication errors
    TOOL = "tool"  # Tool execution errors
    LLM = "llm"  # LLM API errors
    UNKNOWN = "unknown"  # Unknown errors


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error types."""

    RETRY = "retry"  # Simple retry
    RETRY_WITH_BACKOFF = "retry_backoff"  # Exponential backoff
    SWITCH_PLATFORM = "switch_platform"  # Try different platform
    SWITCH_PROXY = "switch_proxy"  # Try different proxy
    SIMPLIFY_QUERY = "simplify_query"  # Simplify the search query
    SKIP = "skip"  # Skip this task
    FALLBACK = "fallback"  # Use fallback data/method
    ESCALATE = "escalate"  # Escalate to user


@dataclass
class ErrorContext:
    """Context information about an error."""

    error_type: ErrorType
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None  # Tool, platform, etc.
    details: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    recoverable: bool = True


@dataclass
class RecoveryAction:
    """Action to take for recovery."""

    strategy: RecoveryStrategy
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    expected_success_rate: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "parameters": self.parameters,
            "description": self.description,
            "expected_success_rate": round(self.expected_success_rate, 2),
        }


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    success: bool
    action_taken: RecoveryAction
    message: str
    new_result: Optional[Any] = None


class SelfHealer:
    """
    Self-healing module for Agent error recovery.

    Capabilities:
    - Error classification
    - Recovery strategy selection
    - Automatic retry with backoff
    - Platform/proxy switching
    - Query simplification
    - Graceful degradation
    """

    # Maximum retries per error type
    MAX_RETRIES = {
        ErrorType.NETWORK: 3,
        ErrorType.RATE_LIMIT: 2,
        ErrorType.BLOCKED: 1,
        ErrorType.PARSE: 2,
        ErrorType.TIMEOUT: 3,
        ErrorType.AUTH: 1,
        ErrorType.TOOL: 2,
        ErrorType.LLM: 2,
        ErrorType.UNKNOWN: 1,
    }

    # Recovery strategies by error type
    RECOVERY_STRATEGIES = {
        ErrorType.NETWORK: [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.SWITCH_PROXY,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.RATE_LIMIT: [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.SWITCH_PLATFORM,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.BLOCKED: [
            RecoveryStrategy.SWITCH_PROXY,
            RecoveryStrategy.SWITCH_PLATFORM,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.PARSE: [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.FALLBACK,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.TIMEOUT: [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.SIMPLIFY_QUERY,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.AUTH: [
            RecoveryStrategy.ESCALATE,
        ],
        ErrorType.TOOL: [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.FALLBACK,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.LLM: [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.FALLBACK,
            RecoveryStrategy.SKIP,
        ],
        ErrorType.UNKNOWN: [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.SKIP,
        ],
    }

    # Backoff configuration
    INITIAL_BACKOFF_MS = 1000
    MAX_BACKOFF_MS = 30000
    BACKOFF_MULTIPLIER = 2

    def __init__(self):
        self._error_history: List[ErrorContext] = []
        self._recovery_callbacks: Dict[RecoveryStrategy, Callable] = {}
        self._circuit_breaker: Dict[str, datetime] = {}  # source -> cooldown_until

    def classify_error(self, error: Exception, source: Optional[str] = None) -> ErrorContext:
        """
        Classify an error and create context.

        Args:
            error: The exception that occurred
            source: Source of the error (tool name, platform, etc.)

        Returns:
            ErrorContext with classification
        """
        error_str = str(error).lower()

        # Classify based on error message patterns
        if any(kw in error_str for kw in ["connection", "network", "unreachable", "dns"]):
            error_type = ErrorType.NETWORK
        elif any(kw in error_str for kw in ["rate limit", "429", "too many requests", "频率"]):
            error_type = ErrorType.RATE_LIMIT
        elif any(kw in error_str for kw in ["403", "blocked", "forbidden", "access denied", "封禁"]):
            error_type = ErrorType.BLOCKED
        elif any(kw in error_str for kw in ["parse", "json", "decode", "format"]):
            error_type = ErrorType.PARSE
        elif any(kw in error_str for kw in ["timeout", "timed out"]):
            error_type = ErrorType.TIMEOUT
        elif any(kw in error_str for kw in ["401", "auth", "unauthorized", "token"]):
            error_type = ErrorType.AUTH
        elif any(kw in error_str for kw in ["llm", "model", "api key", "quota"]):
            error_type = ErrorType.LLM
        else:
            error_type = ErrorType.UNKNOWN

        # Determine if recoverable
        recoverable = error_type not in [ErrorType.AUTH]

        context = ErrorContext(
            error_type=error_type,
            message=str(error),
            source=source,
            recoverable=recoverable,
            details={"original_type": type(error).__name__},
        )

        self._error_history.append(context)
        return context

    def get_recovery_action(
        self,
        context: ErrorContext,
        available_platforms: Optional[List[str]] = None,
    ) -> RecoveryAction:
        """
        Determine the best recovery action for an error.

        Args:
            context: Error context
            available_platforms: List of available platforms for switching

        Returns:
            RecoveryAction to attempt
        """
        # Check if we've exceeded max retries
        if context.retry_count >= self.MAX_RETRIES.get(context.error_type, 2):
            return RecoveryAction(
                strategy=RecoveryStrategy.SKIP,
                description=f"已达到最大重试次数 ({context.retry_count})",
                expected_success_rate=0.0,
            )

        # Check circuit breaker
        if context.source and context.source in self._circuit_breaker:
            if datetime.utcnow() < self._circuit_breaker[context.source]:
                return RecoveryAction(
                    strategy=RecoveryStrategy.SWITCH_PLATFORM,
                    parameters={"reason": "circuit_breaker"},
                    description=f"{context.source} 处于冷却期",
                    expected_success_rate=0.6,
                )

        # Get strategies for this error type
        strategies = self.RECOVERY_STRATEGIES.get(
            context.error_type,
            [RecoveryStrategy.RETRY, RecoveryStrategy.SKIP]
        )

        # Select best strategy based on context
        for strategy in strategies:
            if strategy == RecoveryStrategy.RETRY:
                return RecoveryAction(
                    strategy=strategy,
                    description="简单重试",
                    expected_success_rate=0.5 - (context.retry_count * 0.1),
                )

            elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                backoff = self._calculate_backoff(context.retry_count)
                return RecoveryAction(
                    strategy=strategy,
                    parameters={"backoff_ms": backoff},
                    description=f"等待 {backoff}ms 后重试",
                    expected_success_rate=0.6 - (context.retry_count * 0.1),
                )

            elif strategy == RecoveryStrategy.SWITCH_PLATFORM:
                if available_platforms and len(available_platforms) > 1:
                    current = context.source
                    alternatives = [p for p in available_platforms if p != current]
                    if alternatives:
                        return RecoveryAction(
                            strategy=strategy,
                            parameters={"new_platform": alternatives[0]},
                            description=f"切换到 {alternatives[0]} 平台",
                            expected_success_rate=0.7,
                        )

            elif strategy == RecoveryStrategy.SWITCH_PROXY:
                return RecoveryAction(
                    strategy=strategy,
                    description="切换代理后重试",
                    expected_success_rate=0.6,
                )

            elif strategy == RecoveryStrategy.SIMPLIFY_QUERY:
                return RecoveryAction(
                    strategy=strategy,
                    description="简化查询后重试",
                    expected_success_rate=0.5,
                )

            elif strategy == RecoveryStrategy.FALLBACK:
                return RecoveryAction(
                    strategy=strategy,
                    description="使用备用数据源",
                    expected_success_rate=0.8,
                )

            elif strategy == RecoveryStrategy.ESCALATE:
                return RecoveryAction(
                    strategy=strategy,
                    description="需要人工介入",
                    expected_success_rate=0.0,
                )

        # Default to skip
        return RecoveryAction(
            strategy=RecoveryStrategy.SKIP,
            description="跳过此任务",
            expected_success_rate=0.0,
        )

    async def attempt_recovery(
        self,
        context: ErrorContext,
        action: RecoveryAction,
        retry_func: Optional[Callable] = None,
    ) -> RecoveryResult:
        """
        Attempt to recover from an error.

        Args:
            context: Error context
            action: Recovery action to attempt
            retry_func: Function to retry if applicable

        Returns:
            RecoveryResult indicating success/failure
        """
        import asyncio

        context.retry_count += 1

        try:
            if action.strategy == RecoveryStrategy.RETRY:
                if retry_func:
                    result = await retry_func()
                    return RecoveryResult(
                        success=True,
                        action_taken=action,
                        message="重试成功",
                        new_result=result,
                    )

            elif action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                backoff_ms = action.parameters.get("backoff_ms", 1000)
                await asyncio.sleep(backoff_ms / 1000)

                if retry_func:
                    result = await retry_func()
                    return RecoveryResult(
                        success=True,
                        action_taken=action,
                        message=f"等待 {backoff_ms}ms 后重试成功",
                        new_result=result,
                    )

            elif action.strategy == RecoveryStrategy.SWITCH_PROXY:
                # Trigger proxy switch (actual implementation in crawler)
                return RecoveryResult(
                    success=True,
                    action_taken=action,
                    message="已切换代理，请重试",
                )

            elif action.strategy == RecoveryStrategy.SWITCH_PLATFORM:
                new_platform = action.parameters.get("new_platform")
                return RecoveryResult(
                    success=True,
                    action_taken=action,
                    message=f"已切换到 {new_platform}",
                    new_result={"new_platform": new_platform},
                )

            elif action.strategy == RecoveryStrategy.SIMPLIFY_QUERY:
                return RecoveryResult(
                    success=True,
                    action_taken=action,
                    message="请使用简化的查询重试",
                )

            elif action.strategy == RecoveryStrategy.FALLBACK:
                return RecoveryResult(
                    success=True,
                    action_taken=action,
                    message="使用备用数据",
                )

            elif action.strategy == RecoveryStrategy.SKIP:
                return RecoveryResult(
                    success=False,
                    action_taken=action,
                    message="已跳过此任务",
                )

            elif action.strategy == RecoveryStrategy.ESCALATE:
                return RecoveryResult(
                    success=False,
                    action_taken=action,
                    message="需要人工介入处理",
                )

        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return RecoveryResult(
                success=False,
                action_taken=action,
                message=f"恢复失败: {str(e)}",
            )

        return RecoveryResult(
            success=False,
            action_taken=action,
            message="恢复操作未完成",
        )

    def _calculate_backoff(self, retry_count: int) -> int:
        """Calculate exponential backoff duration."""
        backoff = self.INITIAL_BACKOFF_MS * (self.BACKOFF_MULTIPLIER ** retry_count)
        return min(backoff, self.MAX_BACKOFF_MS)

    def trip_circuit_breaker(self, source: str, cooldown_seconds: int = 60) -> None:
        """
        Trip the circuit breaker for a source.

        Args:
            source: Source to block
            cooldown_seconds: How long to block
        """
        self._circuit_breaker[source] = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
        logger.warning(f"Circuit breaker tripped for {source}, cooldown: {cooldown_seconds}s")

    def reset_circuit_breaker(self, source: str) -> None:
        """Reset circuit breaker for a source."""
        self._circuit_breaker.pop(source, None)

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        if not self._error_history:
            return {"total_errors": 0, "by_type": {}}

        by_type: Dict[str, int] = {}
        for error in self._error_history:
            type_name = error.error_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "total_errors": len(self._error_history),
            "by_type": by_type,
            "recent_errors": [
                {"type": e.error_type.value, "message": e.message[:100], "source": e.source}
                for e in self._error_history[-5:]
            ],
        }

    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()


# Global instance
_self_healer: Optional[SelfHealer] = None


def get_self_healer() -> SelfHealer:
    """Get the global SelfHealer instance."""
    global _self_healer
    if _self_healer is None:
        _self_healer = SelfHealer()
    return _self_healer
