"""MemFS — Git-backed memory file system for agents.

Provides a file-system abstraction over persistent memory storage,
with git versioning for all changes. Memory is organized into
semantic directories (system/, reference/, skills/, conversations/)
and each file is a MemoryBlock with YAML frontmatter metadata.
"""

from app.core.memfs.store import MemFS
from app.core.memfs.memory_block import MemoryBlock

__all__ = ["MemFS", "MemoryBlock"]
