"""Progress tracking and sub-agent task tree for group collaboration.

Provides two pieces of the unified collaboration protocol:

- ``ProgressTracker``: per sub-agent counters (latest input tokens,
  cumulative output tokens, tool use count, recent activity ring buffer,
  last activity time) plus stall detection that raises an alarm when no
  activity is recorded above a configurable threshold.
- ``TaskTree``: a per-group sub-agent task tree whose node lifecycle
  (task start, node added, node status change) broadcasts structured
  ``tree_node_added`` / ``tree_node_updated`` events over the group
  WebSocket hub, carrying task name, status and elapsed time.

Both registries expose synchronous snapshot query functions so a
reconnecting client can pull authoritative state after a disconnect;
a client disconnect never stops a running task.
"""

from __future__ import annotations

import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.group_ws_hub import group_ws_hub

logger = structlog.get_logger(__name__)

# No-activity duration after which a tracker is considered stalled.
STALL_THRESHOLD_SECONDS = 120.0

# Recent activity ring buffer size (mirrors the upstream reference design).
RECENT_ACTIVITY_LIMIT = 5

# Node statuses that end elapsed-time accumulation for a tree node.
TERMINAL_NODE_STATUSES = {"completed", "failed", "stopped", "partial"}

_MAX_TRACKERS = 512
_MAX_TREES = 256
_MAX_TREE_NODES = 100


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ProgressTracker:
    """Track sub-agent progress: tokens, tool calls, activity, stalls.

    All time-based helpers accept an explicit ``now`` (monotonic seconds)
    so callers and tests can drive the clock deterministically.
    """

    tracker_id: str
    group_id: str = ""
    agent_id: str = ""
    role: str = ""
    stall_threshold_seconds: float = STALL_THRESHOLD_SECONDS
    started_at: float = field(default_factory=time.monotonic)
    last_activity_at: float = field(default_factory=time.monotonic)
    latest_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    tool_use_count: int = 0
    recent_activities: deque = field(default_factory=lambda: deque(maxlen=RECENT_ACTIVITY_LIMIT))
    stalled_warned: bool = False

    def record_activity(self, label: str, now: float | None = None) -> None:
        """Record an activity label and refresh the last-activity time."""
        moment = time.monotonic() if now is None else now
        self.last_activity_at = moment
        self.stalled_warned = False
        self.recent_activities.append({"label": label, "at": _utc_now_iso()})

    def record_input_tokens(self, count: int) -> None:
        """Record the latest input token count for the current turn."""
        self.latest_input_tokens = max(0, int(count))

    def record_output_tokens(self, count: int) -> None:
        """Accumulate output tokens produced so far."""
        self.cumulative_output_tokens += max(0, int(count))

    def record_tool_call(self, tool_name: str | None = None, now: float | None = None) -> None:
        """Count a tool invocation and register it as activity."""
        self.tool_use_count += 1
        self.record_activity(f"tool_call:{tool_name}" if tool_name else "tool_call", now=now)

    def idle_seconds(self, now: float | None = None) -> float:
        """Seconds elapsed since the last recorded activity."""
        moment = time.monotonic() if now is None else now
        return max(0.0, moment - self.last_activity_at)

    def is_stalled(self, threshold_seconds: float | None = None, now: float | None = None) -> bool:
        """True when no activity was recorded above the stall threshold."""
        threshold = self.stall_threshold_seconds if threshold_seconds is None else threshold_seconds
        return self.idle_seconds(now=now) > threshold

    def stall_warning(self, now: float | None = None) -> dict[str, Any] | None:
        """Return a stall alarm once per stall period, or None when healthy."""
        if not self.is_stalled(now=now) or self.stalled_warned:
            return None
        self.stalled_warned = True
        return {
            "tracker_id": self.tracker_id,
            "group_id": self.group_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "idle_seconds": round(self.idle_seconds(now=now), 3),
            "threshold_seconds": self.stall_threshold_seconds,
        }

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        """Synchronous snapshot of the tracker for reconnection sync."""
        moment = time.monotonic() if now is None else now
        return {
            "tracker_id": self.tracker_id,
            "group_id": self.group_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "latest_input_tokens": self.latest_input_tokens,
            "cumulative_output_tokens": self.cumulative_output_tokens,
            "total_tokens": self.latest_input_tokens + self.cumulative_output_tokens,
            "tool_use_count": self.tool_use_count,
            "recent_activities": list(self.recent_activities),
            "idle_seconds": round(self.idle_seconds(now=moment), 3),
            "elapsed_seconds": round(max(0.0, moment - self.started_at), 3),
            "stalled": self.is_stalled(now=moment),
        }


# Registry of live trackers keyed by tracker id (insertion ordered for
# bounded FIFO eviction) so the task tree and snapshot APIs can consume
# progress without holding references.
_progress_trackers: OrderedDict[str, ProgressTracker] = OrderedDict()


def get_progress_tracker(
    tracker_id: str,
    group_id: str = "",
    agent_id: str = "",
    role: str = "",
    stall_threshold_seconds: float = STALL_THRESHOLD_SECONDS,
    create: bool = True,
) -> ProgressTracker | None:
    """Return the tracker for ``tracker_id``, optionally creating it."""
    tracker = _progress_trackers.get(tracker_id)
    if tracker is not None or not create:
        return tracker
    if len(_progress_trackers) >= _MAX_TRACKERS:
        _progress_trackers.popitem(last=False)
    tracker = ProgressTracker(
        tracker_id=tracker_id,
        group_id=group_id,
        agent_id=agent_id,
        role=role,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    _progress_trackers[tracker_id] = tracker
    return tracker


def drop_progress_tracker(tracker_id: str) -> None:
    """Forget a finished tracker so the registry stays bounded."""
    _progress_trackers.pop(tracker_id, None)


def get_progress_snapshots(group_id: str | None = None) -> dict[str, dict[str, Any]]:
    """Synchronous snapshot of live trackers, optionally per group."""
    return {
        tracker_id: tracker.snapshot()
        for tracker_id, tracker in _progress_trackers.items()
        if group_id is None or tracker.group_id == group_id
    }


async def broadcast_stall_warnings(group_id: str | None = None) -> list[dict[str, Any]]:
    """Scan trackers and broadcast one ``progress_warning`` per new stall."""
    warnings: list[dict[str, Any]] = []
    for tracker in list(_progress_trackers.values()):
        if group_id is not None and tracker.group_id != group_id:
            continue
        warning = tracker.stall_warning()
        if warning is None:
            continue
        warnings.append(warning)
        await group_ws_hub.broadcast_canonical(
            tracker.group_id or group_id or "",
            "status",
            {**warning, "warning": "stalled"},
            kind="progress_warning",
        )
    return warnings


@dataclass
class TaskNode:
    """A node in the sub-agent task tree."""

    node_id: str
    task_name: str
    parent_id: str | None = None
    status: str = "running"
    started_at: float = field(default_factory=time.monotonic)
    ended_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self, now: float | None = None) -> int:
        """Milliseconds spent on this node so far (frozen once terminal)."""
        if self.ended_at is not None:
            end = self.ended_at
        else:
            end = time.monotonic() if now is None else now
        return max(0, int((end - self.started_at) * 1000))

    def as_dict(self, now: float | None = None) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "task_name": self.task_name,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "elapsed_ms": self.elapsed_ms(now=now),
            "metadata": dict(self.metadata),
        }


class TaskTree:
    """Per-group sub-agent task tree with structured WS event broadcast.

    Lifecycle events (all carrying ``task_name``, ``status`` and, on
    updates, ``elapsed_ms``):

    - ``tree_node_added``: task start / subtask node added;
    - ``tree_node_updated``: node status change (running -> completed etc.).
    """

    def __init__(self, group_id: str, task_id: str = "") -> None:
        self.group_id = group_id
        self.task_id = task_id
        self.nodes: OrderedDict[str, TaskNode] = OrderedDict()

    async def add_root(self, task_name: str, node_id: str | None = None, metadata: dict[str, Any] | None = None) -> TaskNode:
        """Add the root node for a task start."""
        return await self._add_node(task_name, parent_id=None, node_id=node_id, metadata=metadata)

    async def add_node(
        self,
        parent_id: str | None,
        task_name: str,
        node_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskNode:
        """Add a subtask node under ``parent_id``."""
        return await self._add_node(task_name, parent_id=parent_id, node_id=node_id, metadata=metadata)

    async def _add_node(
        self,
        task_name: str,
        parent_id: str | None,
        node_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> TaskNode:
        if parent_id is not None and parent_id not in self.nodes:
            raise KeyError(f"unknown parent node: {parent_id}")
        while len(self.nodes) >= _MAX_TREE_NODES:
            self.nodes.popitem(last=False)
        node = TaskNode(
            node_id=node_id or uuid.uuid4().hex,
            task_name=task_name,
            parent_id=parent_id,
            metadata=dict(metadata or {}),
        )
        self.nodes[node.node_id] = node
        await group_ws_hub.broadcast(self.group_id, {
            "type": "tree_node_added",
            "data": {
                "event": "tree_node_added",
                "node_id": node.node_id,
                "parent_id": node.parent_id,
                "task_id": self.task_id,
                "task_name": node.task_name,
                "status": node.status,
                "started_at": _utc_now_iso(),
                "metadata": dict(node.metadata),
            },
        })
        return node

    async def ensure_root(self, task_name: str) -> TaskNode:
        """Return the existing root or create one for the task start."""
        root = next((n for n in self.nodes.values() if n.parent_id is None), None)
        if root is not None:
            return root
        return await self.add_root(task_name)

    async def update_status(self, node_id: str, status: str, metadata: dict[str, Any] | None = None) -> TaskNode | None:
        """Update a node status and broadcast the structured change event."""
        node = self.nodes.get(node_id)
        if node is None:
            return None
        node.status = status
        if status in TERMINAL_NODE_STATUSES and node.ended_at is None:
            node.ended_at = time.monotonic()
        if metadata:
            node.metadata.update(metadata)
        await group_ws_hub.broadcast(self.group_id, {
            "type": "tree_node_updated",
            "data": {
                "event": "tree_node_updated",
                "node_id": node.node_id,
                "parent_id": node.parent_id,
                "task_id": self.task_id,
                "task_name": node.task_name,
                "status": node.status,
                "elapsed_ms": node.elapsed_ms(),
                "metadata": dict(node.metadata),
            },
        })
        return node

    def snapshot(self) -> dict[str, Any]:
        """Synchronous snapshot of the tree for reconnection sync."""
        return {
            "group_id": self.group_id,
            "task_id": self.task_id,
            "nodes": [node.as_dict() for node in self.nodes.values()],
        }


# Live trees keyed by group id so reconnecting clients can pull state.
_task_trees: OrderedDict[str, TaskTree] = OrderedDict()


def get_task_tree(group_id: str, task_id: str = "", create: bool = True) -> TaskTree | None:
    """Return the live tree for ``group_id``, optionally creating it."""
    tree = _task_trees.get(group_id)
    if tree is not None or not create:
        return tree
    if len(_task_trees) >= _MAX_TREES:
        _task_trees.popitem(last=False)
    tree = TaskTree(group_id=group_id, task_id=task_id)
    _task_trees[group_id] = tree
    return tree


def drop_task_tree(group_id: str) -> None:
    """Forget the tree for ``group_id`` once its task is finished."""
    _task_trees.pop(group_id, None)


def get_task_tree_snapshot(group_id: str) -> dict[str, Any]:
    """Synchronous snapshot query used after a client reconnects."""
    tree = _task_trees.get(group_id)
    if tree is None:
        return {"group_id": group_id, "task_id": "", "nodes": []}
    return tree.snapshot()
