"""Model adapter layer - unified interface for all LLM providers."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from pydantic import BaseModel

from app.core import ChatResult


class ModelCapability(BaseModel):
    """What a model can do."""
    chat: bool = True
    streaming: bool = False
    tools: bool = False
    vision: bool = False
    embedding: bool = False
    max_tokens: int = 4096


@runtime_checkable
class ModelAdapter(Protocol):
    """Unified interface that every model provider must implement."""

    @property
    def provider(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def api_key(self) -> str: ...

    @api_key.setter
    def api_key(self, value: str) -> None: ...

    @property
    def capabilities(self) -> ModelCapability: ...

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Send messages and get a complete response with optional tool calls."""
        ...

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Stream chat completion - yields ChatResult chunks with partial content.
        
        Each yielded ChatResult has:
        - content: incremental text delta
        - tool_calls: complete tool calls (only in final chunk)
        - finish_reason: null for intermediate, "stop"/"tool_calls" for final
        - tokens_used: cumulative token count
        """
        ...
