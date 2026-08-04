"""StateGraph execution engine with superstep parallelism.

"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from app.core.channels import Channel, LastValue, DeltaChannel, BinaryOperator

logger = logging.getLogger(__name__)


@dataclass
class NodeSpec:
    func: Callable
    input_schema: type | None = None
    retry: int = 0
    timeout: float | None = None
    on_error: Callable | None = None


@dataclass
class Edge:
    source: str
    target: str | list[str]
    condition: Callable | None = None


@dataclass
class StateGraph:
    nodes: dict[str, NodeSpec] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    channels: dict[str, Channel] = field(default_factory=dict)

    def add_node(self, name: str, func: Callable, **kwargs: Any) -> None:
        self.nodes[name] = NodeSpec(func=func, **kwargs)

    def add_edge(self, source: str, target: str | list[str], condition: Callable | None = None) -> None:
        self.edges.append(Edge(source=source, target=target, condition=condition))

    def add_channel(self, key: str, channel: Channel) -> None:
        self.channels[key] = channel

    def get_channel(self, key: str, default: Any = None) -> Any:
        if key in self.channels:
            return self.channels[key].get()
        return default

    def set_channel(self, key: str, value: Any, mode: str = "last_value") -> None:
        if key not in self.channels:
            if mode == "last_value":
                self.channels[key] = LastValue(key=key, default=value)
            elif mode == "delta":
                self.channels[key] = DeltaChannel(key=key, default=value)
            else:
                self.channels[key] = LastValue(key=key, default=value)
        else:
            self.channels[key].update(value)
