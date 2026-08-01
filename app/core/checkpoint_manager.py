"""Checkpoint management for agent execution.

Wraps CheckpointStore with higher-level operations for tool checkpoints
and final checkpoints, replacing scattered checkpoint creation code.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.checkpoint import CheckpointData
from app.core.checkpoint_store import CheckpointStore

if TYPE_CHECKING:
    from app.core.agent_engine import AgentSession

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint creation and persistence."""

    def __init__(self, store: CheckpointStore) -> None:
        self.store = store

    async def save_tool_checkpoint(
        self,
        session: AgentSession,
        iteration: int,
        tool_calls: list[dict[str, Any]],
        tool_results: list[Any],
        ctx_tokens: int,
    ) -> None:
        """Save checkpoint after tool execution."""
        try:
            cp = CheckpointData(
                session_id=session.session_id,
                messages=session.messages,
                iteration=iteration,
                status=session.state_machine.state.value,
                channel_values={
                    "last_tool_calls": tool_calls,
                    "last_tool_results": [r.result if hasattr(r, 'result') else str(r) for r in tool_results],
                    "context_tokens": ctx_tokens,
                },
                channel_versions={"messages": iteration, "tools": len(tool_calls)},
                versions_seen={"node": {"messages": iteration, "tools": len(tool_calls)}},
            )
            await self.store.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
        except Exception as e:
            logger.warning("checkpoint_manager.tool_checkpoint_failed", error=str(e))

    async def save_final_checkpoint(
        self,
        session: AgentSession,
        iteration: int,
        result: Any,
        ctx_tokens: int,
    ) -> None:
        """Save final checkpoint after loop completion."""
        try:
            content = result.content if result and hasattr(result, 'content') else ""
            cp = CheckpointData(
                session_id=session.session_id,
                messages=session.messages,
                iteration=iteration,
                status=session.state_machine.state.value,
                channel_values={
                    "final_content": content,
                    "total_iterations": iteration,
                    "context_tokens": ctx_tokens,
                },
                channel_versions={"messages": iteration},
                versions_seen={"node": {"messages": iteration}},
            )
            await self.store.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
        except Exception as e:
            logger.warning("checkpoint_manager.final_checkpoint_failed", error=str(e))
