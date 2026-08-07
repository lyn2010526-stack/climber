"""Search: user - Search and indexing."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UserSearchQuery:
    """Search query."""
    query: str = ''
    filters: dict[str, Any] = field(default_factory=dict)
    sort_by: str = 'relevance'
    page: int = 1
    page_size: int = 20


@dataclass
class UserSearchResult:
    """Search result."""
    items: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    took_ms: float = 0.0


@dataclass
class UserIndexEntry:
    """Index entry."""
    id: str = ''
    title: str = ''
    content: str = ''
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    indexed_at: datetime = field(default_factory=datetime.utcnow)


class UserSearchEngine:
    """Search engine."""

    def __init__(self):
        self._index: dict[str, UserIndexEntry] = {}
        self._inverted_index: dict[str, set[str]] = defaultdict(set)
        self._search_history: list[UserSearchQuery] = []

    def index(self, entry: UserIndexEntry) -> None:
        """Add entry to index."""
        self._index[entry.id] = entry
        words = self._tokenize(entry.title + ' ' + entry.content)
        for word in words:
            self._inverted_index[word].add(entry.id)

    def remove(self, entry_id: str) -> bool:
        """Remove from index."""
        if entry_id in self._index:
            del self._index[entry_id]
            return True
        return False

    def search(self, query: UserSearchQuery) -> UserSearchResult:
        """Search index."""
        start = datetime.utcnow()
        self._search_history.append(query)

        words = self._tokenize(query.query)
        if not words:
            return UserSearchResult()

        matching_ids = set()
        for word in words:
            if word in self._inverted_index:
                matching_ids.update(self._inverted_index[word])

        items = [self._index[eid] for eid in matching_ids if eid in self._index]
        items = [{'id': e.id, 'title': e.title, 'content': e.content} for e in items]

        total = len(items)
        start_idx = (query.page - 1) * query.page_size
        items = items[start_idx:start_idx + query.page_size]

        took = (datetime.utcnow() - start).total_seconds() * 1000

        return UserSearchResult(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            took_ms=took,
        )

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text."""
        return [w.lower() for w in re.findall(r'\w+', text) if len(w) > 1]

    def get_stats(self) -> dict[str, Any]:
        """Get index stats."""
        return {
            'total_documents': len(self._index),
            'unique_terms': len(self._inverted_index),
            'total_searches': len(self._search_history),
        }
