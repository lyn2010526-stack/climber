"""Memory-archive subsystem — L0/L1 sidecars, session archives and retrieval.

Implements the three-layer context model on top of the existing memory stack:

- :mod:`~app.core.memory_archive.layers` generates and persists L0/L1
  directory summaries (a.k.a. ``.abstract``/``.overview``) for memory scopes.
- :mod:`~app.core.memory_archive.archive` archives sessions and extracts
  long-term memories on commit.
- :mod:`~app.core.memory_archive.retrieval` performs directory-scoped
  semantic retrieval instead of scanning the whole index.
- :mod:`~app.core.memory_archive.context` assembles a token-cheap bypass
  bundle that injects only summaries into a conversation.
"""

from __future__ import annotations

from app.core.memory_archive.archive import SessionArchiveService, session_archive
from app.core.memory_archive.context import (
    DEFAULT_SCOPES,
    MemoryContextBypass,
    memory_context_bypass,
)
from app.core.memory_archive.extraction import (
    MEMORY_SCOPE,
    MEMORY_TYPES,
    ExtractedMemory,
    MemoryExtractor,
    memory_extractor,
)
from app.core.memory_archive.index import SemanticIndex, semantic_index
from app.core.memory_archive.layers import (
    MemorySidecarService,
    SidecarBundle,
    sidecar_service,
)
from app.core.memory_archive.retrieval import (
    LEVEL_NAMES,
    DirectoryRetriever,
    normalize_scope,
)
from app.core.memory_archive.summarizer import (
    L0_MAX_CHARS,
    L1_MAX_CHARS,
    TextSummarizer,
    llm_completion,
    llm_enabled,
)

__all__ = [
    "DEFAULT_SCOPES",
    "L0_MAX_CHARS",
    "L1_MAX_CHARS",
    "LEVEL_NAMES",
    "MEMORY_SCOPE",
    "MEMORY_TYPES",
    "DirectoryRetriever",
    "ExtractedMemory",
    "MemoryContextBypass",
    "MemoryExtractor",
    "MemorySidecarService",
    "SemanticIndex",
    "SessionArchiveService",
    "SidecarBundle",
    "TextSummarizer",
    "llm_completion",
    "llm_enabled",
    "memory_context_bypass",
    "memory_extractor",
    "normalize_scope",
    "semantic_index",
    "session_archive",
    "sidecar_service",
]
