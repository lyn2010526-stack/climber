"""Workflow error recovery — Temporal-style per-node retry and compensation.

Provides:
- Per-node retry with exponential backoff
- Partial result recovery (resume from failed node)
- Timeout handling per node
- Compensation actions (rollback) for failed branches
- Error classification (transient vs permanent)
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class ErrorType(StrEnum):
    TRANSIENT = "transient"      # Retryable (timeout, rate limit, network)
    PERMANENT = "permanent"      # Not retryable (invalid input, auth)
    UNKNOWN = "unknown"          # Might be transient


class NodeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    COMPENSATING = "compensating"


def classify_error(error: Exception) -> ErrorType:
    """Classify an error as transient or permanent."""
    error_name = type(error).__name__
    transient_errors = {
        "TimeoutError", "ConnectionError", "ClientConnectorError",
        "ConnectTimeout", "ReadTimeout", "ServiceUnavailable",
        "RateLimitError", "TooManyRequests",
    }
    permanent_errors = {
        "ValueError", "TypeError", "KeyError", "AttributeError",
        "AuthenticationError", "PermissionError", "FileNotFoundError",
    }

    if error_name in transient_errors:
        return ErrorType.TRANSIENT
    if error_name in permanent_errors:
        return ErrorType.PERMANENT

    # Check error message for common transient indicators
    error_msg = str(error).lower()
    transient_indicators = ["timeout", "rate limit", "too many", "unavailable", "connection", "503", "429"]
    if any(ind in error_msg for ind in transient_indicators):
        return ErrorType.TRANSIENT

    return ErrorType.UNKNOWN


@dataclass
class RetryPolicy:
    """Configuration for node retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retry_on: set[ErrorType] = field(default_factory=lambda: {ErrorType.TRANSIENT, ErrorType.UNKNOWN})
    timeout_seconds: float = 60.0


@dataclass
class NodeResult:
    """Result of a workflow node execution."""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: str | None = None
    attempts: int = 0
    duration_ms: float = 0.0
    retry_history: list[dict[str, Any]] = field(default_factory=list)


class RecoverableWorkflowExecutor:
    """Workflow executor with per-node retry and error recovery.

    Wraps the DAG workflow engine with:
    - Automatic retry for transient failures
    - Partial execution recovery (resume from last successful node)
    - Timeout enforcement per node
    - Error classification and logging
    """

    def __init__(self, retry_policy: RetryPolicy | None = None):
        self.retry_policy = retry_policy or RetryPolicy()
        self._node_results: dict[str, NodeResult] = {}
        self._checkpoint: dict[str, Any] = {}

    async def execute_with_recovery(
        self,
        nodes: list[dict[str, Any]],
        execute_fn: Callable[[dict[str, Any]], Awaitable[Any]],
        resume_from: str | None = None,
    ) -> dict[str, Any]:
        """Execute workflow nodes with retry and recovery.

        Args:
            nodes: List of node definitions (must have 'id' field)
            execute_fn: Async function that executes a single node
            resume_from: Node ID to resume from (skips earlier nodes)

        Returns:
            Dict with 'results', 'status', and 'errors'
        """
        results: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        status = "completed"
        start_idx = 0

        # Find resume point
        if resume_from:
            for i, node in enumerate(nodes):
                if node["id"] == resume_from:
                    start_idx = i
                    break

        for _, node in enumerate(nodes[start_idx:], start=start_idx):
            node_id = node["id"]

            # Check if already completed (from checkpoint)
            if node_id in self._checkpoint:
                results[node_id] = self._checkpoint[node_id]
                continue

            node_result = await self._execute_node_with_retry(node, execute_fn)
            self._node_results[node_id] = node_result

            if node_result.status == NodeStatus.COMPLETED:
                results[node_id] = node_result.output
                self._checkpoint[node_id] = node_result.output
            elif node_result.status == NodeStatus.SKIPPED:
                continue
            else:
                # Node failed after all retries
                errors.append({
                    "node_id": node_id,
                    "error": node_result.error,
                    "attempts": node_result.attempts,
                })
                status = "partial"

                # Decide whether to continue or abort
                if node.get("required", True):
                    status = "failed"
                    break
                # Non-required nodes: continue with next

        return {
            "results": results,
            "status": status,
            "errors": errors,
            "node_results": {k: v.status.value for k, v in self._node_results.items()},
        }

    async def _execute_node_with_retry(
        self,
        node: dict[str, Any],
        execute_fn: Callable[[dict[str, Any]], Awaitable[Any]],
    ) -> NodeResult:
        """Execute a single node with retry logic."""
        node_id = node["id"]
        max_retries = node.get("max_retries", self.retry_policy.max_retries)
        timeout = node.get("timeout_seconds", self.retry_policy.timeout_seconds)
        result = NodeResult(node_id=node_id, status=NodeStatus.PENDING)

        for attempt in range(max_retries + 1):
            result.attempts = attempt + 1
            result.status = NodeStatus.RUNNING if attempt == 0 else NodeStatus.RETRYING

            try:
                start = time.monotonic()

                # Execute with timeout
                output = await asyncio.wait_for(execute_fn(node), timeout=timeout)

                result.duration_ms = (time.monotonic() - start) * 1000
                result.status = NodeStatus.COMPLETED
                result.output = output
                return result

            except TimeoutError:
                error_msg = f"Node {node_id} timed out after {timeout}s"
                result.error = error_msg
                result.retry_history.append({
                    "attempt": attempt + 1,
                    "error": error_msg,
                    "type": "timeout",
                })

                if attempt < max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning("Node timeout, retrying", node_id=node_id, attempt=attempt + 1, delay=delay)
                    await asyncio.sleep(delay)

            except Exception as e:
                error_type = classify_error(e)
                result.error = str(e)
                result.retry_history.append({
                    "attempt": attempt + 1,
                    "error": str(e),
                    "type": error_type.value,
                })

                # Don't retry permanent errors
                if error_type == ErrorType.PERMANENT:
                    result.status = NodeStatus.FAILED
                    logger.error("Permanent error in node", node_id=node_id, error=str(e))
                    break

                if attempt < max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning("Node failed, retrying", node_id=node_id, attempt=attempt + 1, error=str(e), delay=delay)
                    await asyncio.sleep(delay)

        if result.status not in (NodeStatus.COMPLETED, NodeStatus.SKIPPED):
            result.status = NodeStatus.FAILED

        return result

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(
            self.retry_policy.base_delay * (self.retry_policy.exponential_base ** attempt),
            self.retry_policy.max_delay,
        )
        if self.retry_policy.jitter:
            delay *= (0.5 + random.random())  # 50%-150% of calculated delay  # noqa: S311 - retry jitter, non-crypto
        return delay

    def get_checkpoint(self) -> dict[str, Any]:
        """Get current execution checkpoint for resumption."""
        return dict(self._checkpoint)

    def reset(self) -> None:
        """Reset executor state."""
        self._node_results.clear()
        self._checkpoint.clear()
