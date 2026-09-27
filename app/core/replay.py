"""Tool result replay policy.

A checkpoint records the `tool_results` of a run, but resuming a session means
deciding what may be replayed. Re-running a read returns the same bytes;
re-running a write or a command repeats a side effect that may already have
happened, or may now be wrong.

The classification lives in app/core/engine/validation.py, where every
registered tool is already tagged with a read/write mode and a parameter name.
Deriving the policy from that table means a newly classified tool is covered
without a second list to maintain. Tools with no classification are treated as
unsafe, so a missing entry fails closed.

Replay design references:
* https://docs.langchain.com/oss/python/langgraph/persistence
* https://docs.temporal.io/workflow-execution/event
* https://docs.temporal.io/workflow-activity
"""

from __future__ import annotations

from typing import Any


class ToolReplayPolicy:
    """Decide which recorded tool results may be replayed on recovery."""

    def __init__(self) -> None:
        from app.tools import ToolRegistry

        self._allowed: set[str] = set()
        # The registry-level network set is the same list that gates egress, so
        # replay cannot re-open a network call the deployment has disabled.
        self._network_tools = set(ToolRegistry.NETWORK_TOOLS)

    def allow(self, tool_name: str) -> None:
        """Mark a tool as replayable.

        Opting in a tool that the classification marks unsafe has no effect:
        the deny rules win, because the caller is less informed than the
        table that gates execution.

        Args:
            tool_name: Name of the tool to treat as replayable.
        """
        if tool_name in self._unsafe_names():
            return
        self._allowed.add(tool_name)

    def is_replayable(self, tool_name: str) -> bool:
        """Return True when the tool's recorded result may be reused.

        Args:
            tool_name: Name of the tool that produced the result.

        Returns:
            True for read-only tools, False for writes, commands, network
            calls and anything unclassified.
        """
        if not tool_name:
            return False
        if tool_name in self._unsafe_names():
            return False
        if tool_name in self._allowed:
            return True
        return self._mode_of(tool_name) == "read"

    def filter(self, results: list[Any]) -> list[dict[str, Any]]:
        """Keep only the replayable entries of a recorded tool result list.

        Args:
            results: Recorded results, each a dict carrying a tool name.

        Returns:
            The entries that may be replayed, in the original order.
        """
        keep: list[dict[str, Any]] = []
        for entry in results:
            if not isinstance(entry, dict):
                continue
            name = entry.get("tool") or entry.get("tool_name")
            if isinstance(name, str) and self.is_replayable(name):
                keep.append(entry)
        return keep

    @staticmethod
    def _mode_of(tool_name: str) -> str | None:
        """Return the classified mode for a tool, or None when unclassified."""
        from app.core.engine.validation import _FILE_TOOLS

        entry = _FILE_TOOLS.get(tool_name)
        if entry is None:
            return None
        return entry[1] if len(entry) > 1 else None

    @staticmethod
    def _unsafe_names() -> set[str]:
        """Names that can never be replayed regardless of opt-in."""
        from app.core.engine.validation import _COMMAND_TOOLS, _FILE_TOOLS
        from app.tools import ToolRegistry

        unsafe = set(_COMMAND_TOOLS)
        # Every write-classified file tool is unsafe. Without this, a "write"
        # entry would fall through to the opt-in branch and become replayable.
        for name, entry in _FILE_TOOLS.items():
            if len(entry) > 1 and entry[1] == "write":
                unsafe.add(name)
        unsafe |= set(ToolRegistry.NETWORK_TOOLS)
        return unsafe
