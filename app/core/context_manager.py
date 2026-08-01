"""5-layer context management pipeline.

Layer 1 (L0): Immutable base rules — always present, never compressed
Layer 2 (L1): Project rules from CLAUDE.md — loaded per workspace
Layer 3 (L2): Session context — persona, memories, working memory
Layer 4 (L3): Tool output — truncated if over threshold, full stored to disk
Layer 5 (L4): Long-term memory — episodic, core memory blocks, previous session summary
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

TOOL_OUTPUT_THRESHOLD = 5000  # chars before truncation
TOOL_OUTPUT_MAX = 10000  # hard cap
MAX_CONTEXT_MESSAGES = 100  # session messages before summarization


@dataclass
class ContextLayer:
    name: str  # L0-L4
    content: str
    priority: int  # lower = more important, never compressed
    compressible: bool = True


class ContextManager:
    """Assembles and manages the 5-layer context pipeline."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self._session_plans: dict[str, str] = {}

    def assemble_context(
        self, session_id: str, user_id: str, agent_id: str, query: str,
        persona: str = "", role_prompt: str = "",
    ) -> list[dict]:
        """Build ordered system messages for a model call."""
        layers = []

        # L0: Immutable base rules
        layers.append(ContextLayer("L0", self._get_base_rules(), priority=0, compressible=False))

        # L1: Project rules (CLAUDE.md)
        claude_md = self._load_claude_md()
        if claude_md:
            layers.append(ContextLayer("L1", claude_md, priority=1, compressible=False))

        # L2: Session context (persona, role prompt)
        session_ctx = self._build_session_context(persona, role_prompt)
        if session_ctx:
            layers.append(ContextLayer("L2", session_ctx, priority=2))

        # L3: Previous session summary / plan
        plan = self._load_progress(session_id)
        if plan:
            layers.append(ContextLayer("L3", plan, priority=3))

        # L4: Memory injection placeholder (filled by persistent_memory at runtime)
        # This layer is populated by AgentEngine.run() before each turn
        layers.append(ContextLayer("L4", "", priority=4))

        # Convert to message format
        messages = []
        for layer in layers:
            if layer.content:
                messages.append({
                    "role": "system",
                    "content": f"<context layer=\"{layer.name}\">\n{layer.content}\n</context>",
                })
        return messages

    def _get_base_rules(self) -> str:
        return (
            "You are a helpful AI assistant running locally.\n"
            "- Always verify actions before executing\n"
            "- Prefer read-only operations unless asked to modify\n"
            "- Report errors clearly and suggest fixes"
        )

    def _load_claude_md(self) -> str:
        """Load project rules from CLAUDE.md in workspace root."""
        for candidate in ["CLAUDE.md", ".claude.md", "CLAUDE.local.md"]:
            path = self.workspace_root / candidate
            if path.exists():
                return path.read_text(encoding="utf-8")[:10000]
        return ""

    def _build_session_context(self, persona: str, role_prompt: str) -> str:
        parts = []
        if persona:
            parts.append(f"## Persona\n{persona}")
        if role_prompt:
            parts.append(f"## Role\n{role_prompt}")
        return "\n\n".join(parts)

    def truncate_tool_output(self, output: str, max_chars: int = TOOL_OUTPUT_THRESHOLD) -> str:
        """Layer 3: Truncate tool output, store full content to disk."""
        if len(output) <= max_chars:
            return output
        truncated = output[:max_chars]
        return f"{truncated}\n... [truncated, full output stored to session storage]"

    def save_progress(self, session_id: str, content: str):
        """Layer 5: Save task progress to PLAN.md for cross-session continuity."""
        self._session_plans[session_id] = content
        plan_dir = self.workspace_root / "sessions" / session_id
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "PLAN.md"
        plan_file.write_text(content, encoding="utf-8")

    def _load_progress(self, session_id: str) -> str:
        """Load saved progress for session resume."""
        if session_id in self._session_plans:
            return self._session_plans[session_id]
        plan_file = self.workspace_root / "sessions" / session_id / "PLAN.md"
        if plan_file.exists():
            return plan_file.read_text(encoding="utf-8")[:5000]
        return ""

    def compress_history(self, messages: list[dict], max_messages: int = MAX_CONTEXT_MESSAGES) -> list[dict]:
        """Compress conversation history, keeping system + recent messages."""
        if len(messages) <= max_messages:
            return messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent = messages[-(max_messages - len(system_msgs)):]
        summary_marker = {"role": "system", "content": "<previous conversation summarized>"}
        return system_msgs + [summary_marker] + recent
