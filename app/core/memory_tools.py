"""Memory Tools — Agent-callable tools for self-managing memory.

These tools allow agents to manage their own memory during conversation,
following the Letta/MemGPT pattern of LLM self-managed memory.

Tools:
- core_memory_append: Append to a named memory block
- core_memory_replace: Replace content within a memory block
- read_memory: Read a memory file from MemFS
- write_memory: Write a memory file to MemFS
- search_memory: Semantic search across all memories
"""

from __future__ import annotations

import functools
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


def _ensure_async(func: Callable) -> Callable:
    """Ensure a function is async."""
    if asyncio.iscoroutinefunction(func):
        return func

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper


import asyncio


class MemoryToolRegistry:
    """Registry for memory tools that agents can call.

    Provides a unified interface for registering, describing,
    and invoking memory management tools. Tools are registered
    as async callables with metadata for LLM tool descriptions.

    Args:
        memfs: Optional MemFS instance for file-based memory.
        memory_service: Optional core memory service for block operations.
        vector_service: Optional vector memory service for search.
    """

    def __init__(
        self,
        memfs: Any = None,
        memory_service: Any = None,
        vector_service: Any = None,
    ) -> None:
        self._memfs = memfs
        self._memory_service = memory_service
        self._vector_service = vector_service
        self._tools: dict[str, dict[str, Any]] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default set of memory tools."""
        self.register(
            "core_memory_append",
            self._tool_core_memory_append,
            description="Append text to a named core memory block. "
                "Use to add new facts, preferences, or observations to persistent memory.",
            parameters={
                "type": "object",
                "properties": {
                    "block_name": {
                        "type": "string",
                        "description": "Name of the memory block to append to "
                            "(e.g., 'persona', 'user_profile', 'project_notes')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to append to the block",
                    },
                },
                "required": ["block_name", "content"],
            },
        )

        self.register(
            "core_memory_replace",
            self._tool_core_memory_replace,
            description="Replace specific text within a named core memory block. "
                "Use to update existing facts or correct outdated information.",
            parameters={
                "type": "object",
                "properties": {
                    "block_name": {
                        "type": "string",
                        "description": "Name of the memory block to modify",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find and replace",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                },
                "required": ["block_name", "old_text", "new_text"],
            },
        )

        self.register(
            "read_memory",
            self._tool_read_memory,
            description="Read a memory file from the memory filesystem. "
                "Use to retrieve stored memories, notes, or reference information.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the memory file "
                            "(e.g., 'system/persona.md', 'reference/project-notes.md')",
                    },
                },
                "required": ["path"],
            },
        )

        self.register(
            "write_memory",
            self._tool_write_memory,
            description="Write or update a memory file in the memory filesystem. "
                "Use to store new information, update notes, or create reference docs.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path for the memory file "
                            "(e.g., 'reference/architecture.md')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the memory file",
                    },
                },
                "required": ["path", "content"],
            },
        )

        self.register(
            "search_memory",
            self._tool_search_memory,
            description="Search memory files using semantic or keyword search. "
                "Use to find relevant memories, facts, or notes related to a topic.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant memories",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Register a new memory tool.

        Args:
            name: Tool name (used by the LLM to call it).
            handler: Async callable that implements the tool.
            description: Human/LLM-readable description.
            parameters: JSON Schema for the tool parameters.
        """
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "parameters": parameters or {},
        }
        logger.debug("memory_tool_registered", name=name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with their descriptions.

        Returns:
            List of tool definitions suitable for LLM tool descriptions.
        """
        return [
            {
                "name": name,
                "description": info["description"],
                "parameters": info["parameters"],
            }
            for name, info in self._tools.items()
        ]

    async def invoke(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke a registered tool by name.

        Args:
            tool_name: Name of the tool to invoke.
            **kwargs: Tool-specific parameters.

        Returns:
            Dict with 'success' boolean and 'result' or 'error'.

        Raises:
            KeyError: If the tool is not registered.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        try:
            result = await tool["handler"](**kwargs)
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            logger.error(
                "memory_tool_error",
                tool=tool_name,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def _tool_core_memory_append(
        self,
        block_name: str,
        content: str,
        user_id: str = "default",
        agent_id: str | None = None,
    ) -> str:
        """Append text to a core memory block."""
        if self._memory_service is None:
            return "Error: Core memory service not available"

        block = await self._memory_service.append_block(
            user_id=user_id,
            label=block_name,
            text=content,
            agent_id=agent_id,
        )

        if block is None:
            return f"Block '{block_name}' not found. Use core_memory_replace to create it first."

        logger.info(
            "tool_core_memory_append",
            block=block_name,
            user_id=user_id,
        )
        return f"Appended to block '{block_name}' (length: {len(block.value)} chars)"

    async def _tool_core_memory_replace(
        self,
        block_name: str,
        old_text: str,
        new_text: str,
        user_id: str = "default",
        agent_id: str | None = None,
    ) -> str:
        """Replace text within a core memory block."""
        if self._memory_service is None:
            return "Error: Core memory service not available"

        block = await self._memory_service.replace_in_block(
            user_id=user_id,
            label=block_name,
            old_text=old_text,
            new_text=new_text,
            agent_id=agent_id,
        )

        if block is None:
            return f"Block '{block_name}' not found."

        if old_text not in (block.value or ""):
            logger.info(
                "tool_core_memory_replace",
                block=block_name,
                user_id=user_id,
            )
            return f"Replaced text in block '{block_name}'"

        return f"Warning: old text not found in block '{block_name}'. No changes made."

    async def _tool_read_memory(self, path: str) -> str:
        """Read a memory file from MemFS."""
        if self._memfs is None:
            return "Error: MemFS not available"

        try:
            content = await self._memfs.read(path)
            return content
        except FileNotFoundError:
            return f"Memory file not found: {path}"
        except Exception as e:
            return f"Error reading {path}: {e}"

    async def _tool_write_memory(self, path: str, content: str) -> str:
        """Write a memory file to MemFS."""
        if self._memfs is None:
            return "Error: MemFS not available"

        try:
            from app.core.memfs.memory_block import MemoryBlock

            block = MemoryBlock.new(
                path=path,
                content=content,
            )
            await self._memfs.write_block(block)
            logger.info("tool_write_memory", path=path)
            return f"Memory written to {path}"
        except Exception as e:
            return f"Error writing {path}: {e}"

    async def _tool_search_memory(
        self,
        query: str,
        limit: int = 5,
        user_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Search memory using vector or keyword search."""
        results: list[dict[str, Any]] = []

        if self._vector_service is not None:
            try:
                vector_results = await self._vector_service.search(
                    collection="episodic",
                    query=query,
                    top_k=limit,
                    where={"user_id": user_id},
                )
                for r in vector_results:
                    results.append({
                        "source": "vector",
                        "id": r.get("id", ""),
                        "text": r.get("text", ""),
                        "score": r.get("score", 0.0),
                    })
            except Exception as e:
                logger.debug("tool_search_vector_failed", error=str(e))

        if self._memfs is not None and len(results) < limit:
            try:
                file_results = await self._memfs.search(query)
                for r in file_results[: limit - len(results)]:
                    results.append({
                        "source": "memfs",
                        "path": r["path"],
                        "matches": r["matches"][:3],
                    })
            except Exception as e:
                logger.debug("tool_search_memfs_failed", error=str(e))

        return results


def create_default_tool_registry(
    memfs: Any = None,
    memory_service: Any = None,
    vector_service: Any = None,
) -> MemoryToolRegistry:
    """Factory function to create a MemoryToolRegistry with default tools.

    Args:
        memfs: Optional MemFS instance.
        memory_service: Optional CoreMemoryService instance.
        vector_service: Optional VectorMemoryService instance.

    Returns:
        Configured MemoryToolRegistry.
    """
    return MemoryToolRegistry(
        memfs=memfs,
        memory_service=memory_service,
        vector_service=vector_service,
    )
