"""Prefix cache optimization.

Fixed content (system prompt, tool descriptions, skill index) is placed at the
front of the prompt so provider prefix caching (e.g. DeepSeek) hits. Sessions
keep the fixed prefix stable to maximize cache reuse.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(frozen=True)
class CacheEntry:
    """Immutable metadata for one append-only model result."""

    key: str
    blocks: tuple[tuple[str, str], ...]
    value: Any
    input_tokens: int = 0


@dataclass(frozen=True)
class StaleSnip:
    """First block that made a prior cache entry stale."""

    block: str
    reason: str
    expected: str
    actual: str


@dataclass
class PrefixCache:
    """Stable fixed prefix assembled from resident content.

    The fixed block is rendered once and reused across turns/sessions. Only
    stable parts belong here; anything that changes per turn goes in the
    dynamic block after it.
    """

    system_prompt: str = ""
    tool_descriptions: str = ""
    skill_index: str = ""
    long_term_memory: str = ""
    max_entries: int = 256
    max_entry_bytes: int = 16 * 1024 * 1024
    max_stale_snips: int = 256
    _entries: dict[str, CacheEntry] = field(default_factory=dict, init=False, repr=False)
    _entry_sizes: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _total_entry_bytes: int = field(default=0, init=False, repr=False)
    _stale_snips: list[StaleSnip] = field(default_factory=list, init=False, repr=False)

    _STALE_REASONS: ClassVar[dict[str, str]] = {
        "prefix_revision": "prefix revision changed",
        "tool_schema": "tool schema changed",
        "model": "model changed",
        "parameters": "model parameters changed",
        "messages": "message block changed",
    }

    def __post_init__(self) -> None:
        if self.max_entries <= 0:
            raise ValueError("max_entries must be positive")
        if self.max_entry_bytes <= 0:
            raise ValueError("max_entry_bytes must be positive")
        if self.max_stale_snips <= 0:
            raise ValueError("max_stale_snips must be positive")

    def set_fixed(
        self,
        system_prompt: str = "",
        tool_descriptions: str = "",
        skill_index: str = "",
        long_term_memory: str = "",
    ) -> None:
        self.system_prompt = system_prompt
        self.tool_descriptions = tool_descriptions
        self.skill_index = skill_index
        self.long_term_memory = long_term_memory

    def render_fixed_prefix(self) -> str:
        """Assemble the fixed prefix in canonical order.

        Order: system prompt -> long-term memory -> skill index ->
        tool descriptions. Stable across turns to maximize prefix cache hits.
        """
        parts: list[str] = []
        if self.system_prompt:
            parts.append(f"<system>\n{self.system_prompt}\n</system>")
        if self.long_term_memory:
            parts.append(f"<memory>\n{self.long_term_memory}\n</memory>")
        if self.skill_index:
            parts.append(f"<skills>\n{self.skill_index}\n</skills>")
        if self.tool_descriptions:
            parts.append(f"<tools>\n{self.tool_descriptions}\n</tools>")
        return "\n\n".join(parts)

    def assemble(
        self,
        dynamic: dict[str, str],
    ) -> list[dict[str, str]]:
        """Assemble a prompt: fixed prefix first, then dynamic blocks."""
        messages: list[dict[str, str]] = []
        prefix = self.render_fixed_prefix()
        if prefix:
            messages.append({"role": "system", "content": prefix})
        # Dynamic block: summary + recent turns + rag + tool results.
        order = ("summary", "recent_turns", "rag_results", "tool_results")
        for key in order:
            value = dynamic.get(key, "")
            if value:
                messages.append(
                    {"role": "system", "content": f"<{key}>\n{value}\n</{key}>"}
                )
        return messages

    @property
    def entries(self) -> tuple[CacheEntry, ...]:
        return tuple(copy.deepcopy(entry) for entry in self._entries.values())

    @property
    def stale_snips(self) -> tuple[StaleSnip, ...]:
        return tuple(self._stale_snips)

    def lookup(self, key: str) -> CacheEntry | None:
        entry = self._entries.get(key)
        return copy.deepcopy(entry) if entry is not None else None

    def append(self, entry: CacheEntry) -> bool:
        """Append an entry without replacement, evicting the oldest entries."""
        if entry.key in self._entries:
            return False
        stored = copy.deepcopy(entry)
        entry_size = len(repr(stored).encode("utf-8"))
        if entry_size > self.max_entry_bytes:
            return False
        self._entries[entry.key] = stored
        self._entry_sizes[entry.key] = entry_size
        self._total_entry_bytes += entry_size
        while len(self._entries) > self.max_entries or self._total_entry_bytes > self.max_entry_bytes:
            oldest_key = next(iter(self._entries))
            self._entries.pop(oldest_key)
            self._total_entry_bytes -= self._entry_sizes.pop(oldest_key)
        return True

    def _append_stale(self, snip: StaleSnip) -> None:
        self._stale_snips.append(snip)
        if len(self._stale_snips) > self.max_stale_snips:
            del self._stale_snips[: len(self._stale_snips) - self.max_stale_snips]

    def record_stale(self, actual_blocks: tuple[tuple[str, str], ...]) -> StaleSnip | None:
        """Record only the first differing block against the newest entry."""
        if not self._entries:
            return None
        expected_blocks = next(reversed(self._entries.values())).blocks
        for (block, expected), (actual_block, actual) in zip(expected_blocks, actual_blocks, strict=False):
            if block != actual_block or expected != actual:
                differing_block = block if block == actual_block else f"{block}/{actual_block}"
                snip = StaleSnip(
                    block=differing_block,
                    reason=self._STALE_REASONS.get(differing_block, "request block changed"),
                    expected=expected[:160],
                    actual=actual[:160],
                )
                self._append_stale(snip)
                return snip
        if len(expected_blocks) != len(actual_blocks):
            snip = StaleSnip(
                block="request_shape",
                reason="request block count changed",
                expected=str(len(expected_blocks)),
                actual=str(len(actual_blocks)),
            )
            self._append_stale(snip)
            return snip
        return None


_default_prefix_cache: PrefixCache | None = None


def get_prefix_cache() -> PrefixCache:
    global _default_prefix_cache
    if _default_prefix_cache is None:
        _default_prefix_cache = PrefixCache()
    return _default_prefix_cache
