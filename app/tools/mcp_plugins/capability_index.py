"""MCP Plugin: Capability Index — semantic skill/capability retrieval.

Matches task goals to the most appropriate skill or capability
using semantic similarity, not keyword search.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityEntry:
    name: str
    description: str
    entry_type: str  # "skill", "tool", "composed_capability"
    tags: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    use_count: int = 0


@dataclass
class MatchResult:
    entry: CapabilityEntry
    score: float
    match_reason: str


class CapabilityIndex:
    """Semantic capability retrieval engine."""

    def __init__(self, storage_path: str = "data/capability_index.json"):
        self._storage_path = storage_path
        self._entries: dict[str, CapabilityEntry] = {}
        self._load()

    def register(
        self,
        name: str,
        description: str,
        entry_type: str,
        tags: list[str] | None = None,
    ) -> CapabilityEntry:
        entry = CapabilityEntry(
            name=name,
            description=description,
            entry_type=entry_type,
            tags=tags or [],
        )
        self._entries[name] = entry
        self._save()
        return entry

    def search(
        self,
        query: str,
        entry_type: str | None = None,
        limit: int = 5,
    ) -> list[MatchResult]:
        """Search capabilities by semantic similarity to query."""
        results = []
        query_words = self._tokenize(query)

        for _, entry in self._entries.items():
            if entry_type and entry.entry_type != entry_type:
                continue

            score, reason = self._compute_similarity(query_words, entry)
            if score > 0.05:
                results.append(MatchResult(
                    entry=entry,
                    score=score,
                    match_reason=reason,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def find_best(self, query: str) -> MatchResult | None:
        """Find the single best matching capability."""
        results = self.search(query, limit=1)
        return results[0] if results else None

    def _tokenize(self, text: str) -> dict[str, float]:
        """Convert text to weighted word frequencies."""
        words = re.findall(r"[a-zA-Z_]+", text.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "be", "to", "for",
            "of", "in", "on", "and", "or", "it", "this", "that",
        }
        freq: dict[str, float] = {}
        for word in words:
            if word in stop_words:
                continue
            freq[word] = freq.get(word, 0) + 1

        # TF-IDF-like weighting: rare words get higher weight
        total = sum(freq.values())
        if total > 0:
            for word in freq:
                freq[word] = freq[word] / total
        return freq

    def _compute_similarity(
        self,
        query_words: dict[str, float],
        entry: CapabilityEntry,
    ) -> tuple[float, str]:
        """Compute cosine-like similarity between query and entry."""
        entry_text = f"{entry.name} {entry.description} {' '.join(entry.tags)}"
        entry_words = self._tokenize(entry_text)

        if not query_words or not entry_words:
            return 0.0, ""

        # Dot product
        common_words = set(query_words) & set(entry_words)
        if not common_words:
            return 0.0, ""

        score = sum(query_words[w] * entry_words[w] for w in common_words)

        # Normalize
        query_norm = math.sqrt(sum(v ** 2 for v in query_words.values()))
        entry_norm = math.sqrt(sum(v ** 2 for v in entry_words.values()))
        if query_norm == 0 or entry_norm == 0:
            return 0.0, ""
        score /= (query_norm * entry_norm)

        # Boost by success rate
        score *= (0.5 + 0.5 * entry.success_rate)

        reason = f"Matched on: {', '.join(sorted(common_words)[:5])}"
        return score, reason

    def update_stats(self, name: str, success: bool) -> None:
        entry = self._entries.get(name)
        if entry:
            entry.use_count += 1
            if success:
                # Running average
                entry.success_rate = (
                    entry.success_rate * (entry.use_count - 1) + 1
                ) / entry.use_count
            else:
                entry.success_rate = (
                    entry.success_rate * (entry.use_count - 1)
                ) / entry.use_count
            self._save()

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "name": e.name,
                "description": e.description[:60],
                "type": e.entry_type,
                "tags": e.tags,
                "success_rate": e.success_rate,
                "uses": e.use_count,
            }
            for e in self._entries.values()
        ]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "capability_search",
                "description": "Search for the best matching capability for a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Task description or goal"},
                        "type_filter": {
                            "type": "string",
                            "enum": ["skill", "tool", "composed_capability"],
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "capability_register",
                "description": "Register a new capability in the index",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "entry_type": {
                            "type": "string",
                            "enum": ["skill", "tool", "composed_capability"],
                        },
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "description", "entry_type"],
                },
            },
        ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            name: {
                "name": e.name,
                "description": e.description,
                "entry_type": e.entry_type,
                "tags": e.tags,
                "success_rate": e.success_rate,
                "use_count": e.use_count,
            }
            for name, e in self._entries.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for name, e in data.items():
                self._entries[name] = CapabilityEntry(
                    name=e["name"],
                    description=e["description"],
                    entry_type=e["entry_type"],
                    tags=e.get("tags", []),
                    success_rate=e.get("success_rate", 0.0),
                    use_count=e.get("use_count", 0),
                )
        except (json.JSONDecodeError, KeyError):
            pass
