"""Pydantic-AI integration for structured agent execution.

Leverages pydantic-ai for type-safe agent outputs, tool calling,
and structured responses with validation.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from pydantic_ai import Agent

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentResponse(BaseModel):
    """Standard agent response format."""
    content: str = Field(description="Response content")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result from a tool execution."""
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None


class PydanticAIAgent:
    """Wrapper around pydantic-ai Agent with custom tool registration."""

    def __init__(
        self,
        system_prompt: str = "You are a helpful AI assistant.",
        model: str = "gpt-4",
    ):
        self._system_prompt = system_prompt
        self._model = model
        self._agent: Agent | None = None
        self._tools: dict[str, Any] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
    ) -> None:
        """Register a tool function."""
        self._tools[name] = {"description": description, "func": func}
        logger.debug("tool_registered", name=name)

    async def run(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Run the agent with a prompt."""
        try:
            if self._agent is None:
                self._agent = Agent(
                    self._model,
                    system_prompt=self._system_prompt,
                    result_type=AgentResponse,
                )

            result = await self._agent.run(prompt)
            return result.data if hasattr(result, "data") else AgentResponse(content=str(result))
        except Exception as exc:
            logger.warning("agent_run_failed", error=str(exc))
            return AgentResponse(
                content=f"Error: {exc}",
                confidence=0.0,
                metadata={"error": str(exc)},
            )

    async def run_stream(self, prompt: str):
        """Run the agent with streaming output."""
        try:
            if self._agent is None:
                self._agent = Agent(
                    self._model,
                    system_prompt=self._system_prompt,
                )

            async with self._agent.run_stream(prompt) as result:
                async for chunk in result.stream():
                    yield chunk
        except Exception as exc:
            logger.warning("agent_stream_failed", error=str(exc))
            yield f"Error: {exc}"


def create_agent(
    system_prompt: str = "You are a helpful AI assistant.",
    model: str = "gpt-4",
) -> PydanticAIAgent:
    """Factory function to create a new agent."""
    return PydanticAIAgent(system_prompt=system_prompt, model=model)
