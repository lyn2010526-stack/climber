"""Command primitive for combined state update + routing.

A Command allows a node to simultaneously update state and specify
the next node(s) to execute, replacing the need for separate return values.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class Command:
    """Combined state update + routing instruction.

    Attributes:
        update: Partial state dict to merge into current state.
        goto: Next node(s) to execute. Can be a single node name,
              a list of node names (parallel), or None to continue
              with default routing.
        resume: Value to inject when resuming from an interrupt.
        metadata: Additional metadata attached to this command.
    """

    def __init__(
        self,
        update: dict[str, Any] | None = None,
        goto: str | list[str] | None = None,
        resume: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.update = update
        self.goto = goto
        self.resume = resume
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        parts = []
        if self.update:
            parts.append(f"update={list(self.update.keys())}")
        if self.goto:
            parts.append(f"goto={self.goto}")
        if self.resume is not None:
            parts.append("resume=<value>")
        return f"Command({', '.join(parts)})"

    @classmethod
    def PARENT(cls, update: dict[str, Any] | None = None) -> Command:
        """Create a command that navigates from subgraph to parent graph."""
        return cls(update=update, goto="__parent__")

    @property
    def is_interrupt(self) -> bool:
        """Check if this command represents an interrupt request."""
        return self.metadata.get("interrupt", False)

    @property
    def is_end(self) -> bool:
        """Check if this command signals graph termination."""
        return self.goto == "__end__"


def is_command(obj: Any) -> bool:
    """Check if an object is a Command instance."""
    return isinstance(obj, Command)


def parse_node_output(output: Any) -> tuple[dict[str, Any] | None, str | list[str] | None, Any]:
    """Parse a node's output into (update, goto, resume) components.

    Handles multiple output formats:
    - dict: treated as state update, no routing
    - Command: extract update, goto, resume
    - str: treated as goto target
    - tuple(dict, str): (update, goto)
    """
    if isinstance(output, Command):
        return output.update, output.goto, output.resume
    if isinstance(output, dict):
        return output, None, None
    if isinstance(output, str):
        return None, output, None
    if isinstance(output, tuple) and len(output) == 2:
        update, goto = output
        if isinstance(update, dict) and isinstance(goto, (str, list)):
            return update, goto, None
    return None, None, None
