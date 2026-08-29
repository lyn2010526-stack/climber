"""Capability adapters — wrap external sources as Capabilities.

- McpCapability: wraps an MCP tool
- SkillCapability: wraps a skill (parses its flow, then calls sub-capabilities)
- HttpCapability: wraps an HTTP endpoint
- SubagentCapability: delegates to an independent sub-agent
- ModelCapability: wraps a model call
- PerceptionCapability: wraps perception (screenshot / ui-tree / voice)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.capability.capability import Capability, CapabilityMeta


class McpCapability(Capability):
    """Adapt an MCP tool into a Capability."""

    def __init__(
        self,
        meta: CapabilityMeta,
        tool_name: str,
        execute_fn: Callable[..., Any],
    ) -> None:
        self._meta = meta
        self._tool_name = tool_name
        self._execute_fn = execute_fn
        self._executable = True

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    @property
    def tool_name(self) -> str:
        return self._tool_name

    async def execute(self, **kwargs: Any) -> Any:
        return await self._execute_fn(name=self._tool_name, arguments=kwargs)

    def is_executable(self) -> bool:
        return self._executable


class SkillCapability(Capability):
    """Adapt a skill into a Capability; the flow is parsed to call sub-capabilities."""

    def __init__(
        self,
        meta: CapabilityMeta,
        skill_id: str,
        runner: Callable[..., Any],
        parse_steps: Callable[[], list[str]] | None = None,
    ) -> None:
        self._meta = meta
        self._skill_id = skill_id
        self._runner = runner
        self._parse_steps = parse_steps or (lambda: [])
        self._steps: list[str] = []

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs: Any) -> Any:
        self._steps = self._parse_steps()
        return await self._runner(skill_id=self._skill_id, **kwargs)

    def is_executable(self) -> bool:
        return True

    def steps(self) -> list[str]:
        return self._steps


class HttpCapability(Capability):
    """Adapt an HTTP API endpoint into a Capability."""

    def __init__(
        self,
        meta: CapabilityMeta,
        endpoint: str,
        method: str = "GET",
        auth_fn: Callable[[], dict[str, str]] | None = None,
        requester: Callable[..., Any] | None = None,
    ) -> None:
        self._meta = meta
        self._endpoint = endpoint
        self._method = method
        self._auth_fn = auth_fn
        self._requester = requester

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs: Any) -> Any:
        if self._requester is not None:
            headers = self._auth_fn() if self._auth_fn else {}
            return await self._requester(
                endpoint=self._endpoint,
                method=self._method,
                headers=headers,
                params=kwargs,
            )
        raise RuntimeError("HttpCapability has no requester configured")

    def is_executable(self) -> bool:
        return self._requester is not None


class SubagentCapability(Capability):
    """Delegate execution to an independent sub-agent; returns a summary."""

    def __init__(
        self,
        meta: CapabilityMeta,
        agent_type: str,
        dispatcher: Callable[..., Any],
    ) -> None:
        self._meta = meta
        self._agent_type = agent_type
        self._dispatcher = dispatcher

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs: Any) -> Any:
        return await self._dispatcher(agent_type=self._agent_type, **kwargs)

    def is_executable(self) -> bool:
        return True


class ModelCapability(Capability):
    """Wrap a model call as a capability."""

    def __init__(
        self,
        meta: CapabilityMeta,
        model_call: Callable[..., Any],
    ) -> None:
        self._meta = meta
        self._model_call = model_call

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs: Any) -> Any:
        return await self._model_call(**kwargs)

    def is_executable(self) -> bool:
        return True


class PerceptionCapability(Capability):
    """Wrap a perception source (screenshot / ui-tree / voice)."""

    def __init__(
        self,
        meta: CapabilityMeta,
        source: str,
        reader: Callable[..., Any],
    ) -> None:
        self._meta = meta
        self._source = source
        self._reader = reader

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs: Any) -> Any:
        return await self._reader(source=self._source, **kwargs)

    def is_executable(self) -> bool:
        return True
