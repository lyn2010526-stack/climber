"""Structural subtyping protocols for service providers.

These protocols define interfaces for pluggable backends without requiring
inheritance. They break circular dependencies by providing a shared type
layer that both consumers and implementations can reference.
"""

from __future__ import annotations

from typing import Any, Protocol


class MemoryBackend(Protocol):
    """Protocol for memory storage and retrieval backends."""

    async def search(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        """Search memories matching the query."""
        ...

    async def add(self, content: str, metadata: dict[str, Any] | None = None, **kwargs: Any) -> str:
        """Add a memory entry. Returns the entry ID."""
        ...

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry by ID."""
        ...

    async def retrieve(self, key: str, **kwargs: Any) -> Any:
        """Retrieve a specific memory entry by key."""
        ...

    async def format_for_prompt(self, **kwargs: Any) -> str:
        """Format memory entries for prompt injection."""
        ...


class MemoryService(Protocol):
    """Higher-level protocol for memory orchestration services.

    Combines retrieval, formatting, and lifecycle management for
    use in agent context preparation.
    """

    async def retrieve_for_query(
        self, user_id: str, agent_id: str, query: str,
        session_context: list[dict[str, str]] | None = None,
    ) -> Any:
        """Retrieve all relevant memories for a query within token budget."""
        ...

    async def on_session_end(
        self, user_id: str, agent_id: str, session_id: str,
        messages: list[dict[str, str]],
    ) -> None:
        """Extract and store memories when a session ends."""
        ...


class CheckpointStore(Protocol):
    """Protocol for checkpoint persistence backends."""

    async def save(self, session_id: str, step: int, data: dict[str, Any]) -> None:
        """Save a checkpoint for a session."""
        ...

    async def load(self, session_id: str, step: int) -> dict[str, Any] | None:
        """Load a checkpoint for a session."""
        ...

    async def list(self, session_id: str) -> list[int]:
        """List available checkpoint steps for a session."""
        ...


class ToolExecutor(Protocol):
    """Protocol for tool execution backends."""

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool with given arguments."""
        ...

    def validate(self, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Validate a tool call before execution."""
        ...


class ModelProvider(Protocol):
    """Protocol for model inference backends."""

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Send a chat request and return the result."""
        ...

    async def stream(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Stream chat responses."""
        ...
