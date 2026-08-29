"""Module B: Meta-Agent — subscribes to metrics, proposes meta improvements.

The MetaAgent is a read-only observer during monitoring: it consumes
EventBus metric events (tool_result, tool_error, iteration_start,
session_complete, session_error) and detects failure patterns. It NEVER
mutates anything on its own — every change it suggests becomes a
`MetaProposal` that only takes effect after explicit user confirmation.
Application is snapshot-first and passed through the hard security guard;
rollback restores the previous state.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.security.hard_guard import get_hard_guard

logger = structlog.get_logger()


@dataclass
class MetaProposal:
    """A user-confirmable meta-improvement proposal."""
    summary: str
    kind: str  # "graph_patch" | "config_tweak" | "loop_guard" | "token_guard"
    detail: dict[str, Any]
    created_at: str = ""
    approved: bool = False
    applied: bool = False
    snapshot_id: str | None = None


# Event types the MetaAgent subscribes to.
WATCHED_EVENTS: tuple[str, ...] = (
    "tool_result",
    "tool_error",
    "tool_batch_start",
    "iteration_start",
    "session_complete",
    "session_error",
)


class MetaAgent:
    """Consumes metric events and proposes (never auto-applies) changes."""

    def __init__(
        self,
        event_bus: Any | None = None,
        snapshot_fn: Callable[[], Any] | None = None,
        apply_fn: Callable[[MetaProposal], Any] | None = None,
        rollback_fn: Callable[[str], Any] | None = None,
        window_size: int = 50,
    ):
        self.event_bus = event_bus
        self.snapshot_fn = snapshot_fn
        self.apply_fn = apply_fn
        self.rollback_fn = rollback_fn
        self.window_size = window_size
        self._events: list[dict[str, Any]] = []
        self._proposals: list[MetaProposal] = []
        self._running = False

    def set_event_bus(self, bus: Any) -> None:
        self.event_bus = bus

    def set_hooks(
        self,
        snapshot_fn: Callable[[], Any] | None = None,
        apply_fn: Callable[[MetaProposal], Any] | None = None,
        rollback_fn: Callable[[str], Any] | None = None,
    ) -> None:
        if snapshot_fn is not None:
            self.snapshot_fn = snapshot_fn
        if apply_fn is not None:
            self.apply_fn = apply_fn
        if rollback_fn is not None:
            self.rollback_fn = rollback_fn

    async def start_monitoring(self) -> None:
        """Subscribe to metric events."""
        if self._running:
            return
        if self.event_bus is None:
            raise RuntimeError("MetaAgent requires an event bus")
        self._running = True
        for evt in WATCHED_EVENTS:
            self.event_bus.subscribe(evt, self._on_event)
        logger.info("meta_agent.monitoring_started")

    async def stop_monitoring(self) -> None:
        if not self._running:
            return
        if self.event_bus is not None:
            for evt in WATCHED_EVENTS:
                self.event_bus.unsubscribe(evt, self._on_event)
        self._running = False
        logger.info("meta_agent.monitoring_stopped")

    async def _on_event(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        if len(self._events) > self.window_size:
            self._events = self._events[-self.window_size:]

    def list_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def analyze(self) -> list[MetaProposal]:
        """Detect failure patterns from the recent event window."""
        proposals: list[MetaProposal] = []
        if not self._events:
            return proposals

        # 1. High tool failure rate -> tool reliability warning
        tool_events = [e for e in self._events if e.get("type") == "tool_error"]
        tool_total = len([e for e in self._events if e.get("type") in ("tool_result", "tool_error")])
        if tool_total >= 3 and len(tool_events) / tool_total >= 0.5:
            proposals.append(MetaProposal(
                summary=f"High tool failure rate: {len(tool_events)}/{tool_total} failed",
                kind="loop_guard",
                detail={"failures": len(tool_events), "total": tool_total},
            ))

        # 2. Repeated failing tool -> consider retry backoff / drop
        fail_counts: dict[str, int] = {}
        for e in self._events:
            if e.get("type") == "tool_error":
                tool = e.get("tool") or e.get("tool_name") or "unknown"
                fail_counts[tool] = fail_counts.get(tool, 0) + 1
        for tool, cnt in fail_counts.items():
            if cnt >= 3:
                proposals.append(MetaProposal(
                    summary=f"Tool '{tool}' failed {cnt} times consecutively",
                    kind="loop_guard",
                    detail={"tool": tool, "failures": cnt},
                ))

        # 3. No session_complete but session_error present -> session stability
        has_error = any(e.get("type") == "session_error" for e in self._events)
        has_complete = any(e.get("type") == "session_complete" for e in self._events)
        if has_error and not has_complete:
            proposals.append(MetaProposal(
                summary="Session ended in error without completing",
                kind="config_tweak",
                detail={"reason": "session_error without session_complete"},
            ))

        return proposals

    async def propose(self) -> MetaProposal | None:
        """Analyze and register a proposal (does NOT apply anything)."""
        found = self.analyze()
        if not found:
            return None
        proposal = found[0]
        self._proposals.append(proposal)
        logger.info("meta_agent.proposal", summary=proposal.summary, kind=proposal.kind)
        if self.event_bus is not None:
            await self.event_bus.publish("meta_proposal", {
                "summary": proposal.summary, "kind": proposal.kind,
            })
        return proposal

    def approve(self, proposal: MetaProposal | None) -> bool:
        if proposal is None or proposal.approved:
            return False
        proposal.approved = True
        logger.info("meta_agent.approved", summary=proposal.summary)
        return True

    async def apply(self, proposal: MetaProposal | None) -> bool:
        """Apply an approved proposal, snapshot-first, guard-filtered."""
        if proposal is None or not proposal.approved:
            return False
        if proposal.applied:
            return False
        if self.apply_fn is None:
            return False
        guard = get_hard_guard()
        snap = await guard.require_snapshot_before(proposal.summary, self._snap)
        if not snap.allowed:
            logger.warning("meta_agent.apply_aborted", reason=snap.reason)
            return False
        await self.apply_fn(proposal)
        proposal.applied = True
        proposal.snapshot_id = snap.snapshot_id
        logger.info("meta_agent.applied", snapshot_id=snap.snapshot_id)
        return True

    async def rollback(self, snapshot_id: str) -> bool:
        """Roll back to a prior snapshot."""
        if self.rollback_fn is None:
            return False
        await self.rollback_fn(snapshot_id)
        logger.info("meta_agent.rollback", snapshot_id=snapshot_id)
        return True

    async def _snap(self) -> str | None:
        if self.snapshot_fn is None:
            return "meta_agent-noop"
        return await self.snapshot_fn()

    def list_proposals(self) -> list[MetaProposal]:
        return list(self._proposals)
