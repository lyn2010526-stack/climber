"""Four-layer memory architecture.

Layer 1  short_term  — current session message history, sliding window.
Layer 2  medium_term — current task operation history / intermediate state.
Layer 3  long_term   — MEMORY.md (environment facts) + USER.md (preferences),
                       frozen-snapshot injected at session start; updates
                       require a user-confirmed diff.
Layer 4  skill_library — procedural memory managed by the skill subsystem
                       (see app.core.self_learning / skill store).
"""

from app.core.four_layer_memory.fts5_index import (
    FTS5MemoryIndex,
    get_fts5_index,
    search_memory,
)
from app.core.four_layer_memory.long_term import (
    LongTermMemory,
    LongTermMemoryProposal,
    get_long_term_memory,
)
from app.core.four_layer_memory.medium_term import MediumTermMemory
from app.core.four_layer_memory.short_term import ShortTermMemory

__all__ = [
    "FTS5MemoryIndex",
    "LongTermMemory",
    "LongTermMemoryProposal",
    "MediumTermMemory",
    "ShortTermMemory",
    "get_fts5_index",
    "get_long_term_memory",
    "search_memory",
]
