"""Layer 3 — long-term (permanent) memory.

Two files:
  MEMORY.md — device environment facts, installed apps, rules, historical
              lessons. Max ~2000 chars.
  USER.md   — user preferences, habits, contacts, addresses. Max ~1500 chars.

Both are injected as a frozen snapshot at session start. The agent can propose
updates, but the diff must be shown to the user for confirmation before any
write happens.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LongTermMemoryProposal:
    """A proposed update to MEMORY.md or USER.md with a visible diff."""

    target: str  # "MEMORY.md" | "USER.md"
    current_content: str
    proposed_content: str
    reason: str = ""
    approved: bool = False

    @property
    def diff(self) -> str:
        return "\n".join(
            difflib.unified_diff(
                self.current_content.splitlines(keepends=True),
                self.proposed_content.splitlines(keepends=True),
                fromfile=f"current_{self.target}",
                tofile=f"proposed_{self.target}",
                lineterm="",
            )
        )

    @property
    def has_changes(self) -> bool:
        return self.current_content != self.proposed_content


MEMORY_MAX_CHARS = 2000
USER_MAX_CHARS = 1500


class LongTermMemory:
    """Manages MEMORY.md and USER.md with frozen-snapshot injection."""

    def __init__(self, base_dir: str | Path = "data/long_term") -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._memory_path = self._base_dir / "MEMORY.md"
        self._user_path = self._base_dir / "USER.md"
        self._init_file(self._memory_path, "# MEMORY.md\n\nSession-independent facts about the environment.\n")
        self._init_file(self._user_path, "# USER.md\n\nUser preferences and habits.\n")

    @staticmethod
    def _init_file(path: Path, default: str) -> None:
        if not path.exists():
            path.write_text(default, encoding="utf-8")

    # ── read ──

    def read_memory(self) -> str:
        return self._memory_path.read_text(encoding="utf-8")

    def read_user(self) -> str:
        return self._user_path.read_text(encoding="utf-8")

    def snapshot(self) -> str:
        """Return the frozen snapshot for system prompt injection."""
        mem = self.read_memory()[:MEMORY_MAX_CHARS]
        usr = self.read_user()[:USER_MAX_CHARS]
        parts = []
        if mem.strip():
            parts.append(f"<MEMORY.md>\n{mem}\n</MEMORY.md>")
        if usr.strip():
            parts.append(f"<USER.md>\n{usr}\n</USER.md>")
        return "\n\n".join(parts)

    # ── propose update ──

    def propose_memory_update(self, new_content: str, reason: str = "") -> LongTermMemoryProposal:
        return LongTermMemoryProposal(
            target="MEMORY.md",
            current_content=self.read_memory(),
            proposed_content=new_content[:MEMORY_MAX_CHARS],
            reason=reason,
        )

    def propose_user_update(self, new_content: str, reason: str = "") -> LongTermMemoryProposal:
        return LongTermMemoryProposal(
            target="USER.md",
            current_content=self.read_user(),
            proposed_content=new_content[:USER_MAX_CHARS],
            reason=reason,
        )

    # ── apply (after user approval) ──

    def apply_proposal(self, proposal: LongTermMemoryProposal) -> bool:
        if not proposal.approved:
            return False
        if not proposal.has_changes:
            return False
        path = self._memory_path if proposal.target == "MEMORY.md" else self._user_path
        path.write_text(proposal.proposed_content, encoding="utf-8")
        return True

    # ── stats ──

    def stats(self) -> dict[str, Any]:
        return {
            "memory_chars": len(self.read_memory()),
            "user_chars": len(self.read_user()),
            "memory_path": str(self._memory_path),
            "user_path": str(self._user_path),
        }


_default_long_term: LongTermMemory | None = None


def get_long_term_memory(base_dir: str | Path = "data/long_term") -> LongTermMemory:
    global _default_long_term
    if _default_long_term is None:
        _default_long_term = LongTermMemory(base_dir=base_dir)
    return _default_long_term
