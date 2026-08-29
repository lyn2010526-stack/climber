"""Layer 1 — short-term (session-level) memory.

Keeps the most recent ``window_size`` turns of raw conversation in memory;
older turns are moved out to a rolling summary (handled by the long-context
summarizer). This is the smallest, highest-cost layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # user | assistant | tool
    content: str
    seq: int = 0


@dataclass
class ShortTermMemory:
    """Sliding-window session memory.

    Args:
        window_size: number of recent turns kept verbatim.
    """

    window_size: int = 10
    turns: list[Turn] = field(default_factory=list)
    evicted_turns: list[Turn] = field(default_factory=list)
    _seq: int = 0

    def add(self, role: str, content: str) -> Turn:
        self._seq += 1
        turn = Turn(role=role, content=content, seq=self._seq)
        self.turns.append(turn)
        if len(self.turns) > self.window_size:
            removed = self.turns[0]
            self.evicted_turns.append(removed)
            self.turns = self.turns[-self.window_size:]
        return turn

    def recent(self, limit: int | None = None) -> list[Turn]:
        n = limit or self.window_size
        return self.turns[-n:]

    def evicted(self) -> list[Turn]:
        """Return turns evicted from the window (for summarization)."""
        return list(self.evicted_turns)

    def drain_evicted(self) -> list[Turn]:
        evicted = list(self.evicted_turns)
        self.evicted_turns.clear()
        return evicted

    def reset(self) -> None:
        self.turns.clear()
        self.evicted_turns.clear()
        self._seq = 0

    def to_messages(self, limit: int | None = None) -> list[dict[str, str]]:
        return [
            {"role": t.role, "content": t.content}
            for t in self.recent(limit)
        ]
