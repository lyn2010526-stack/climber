"""Registry for workflow canvas node metadata and custom executors."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

NodeExecutor = Callable[[Any, dict[str, Any], dict[str, Any]], Any | Awaitable[Any]]


class NodePort(BaseModel):
    """A typed connection point exposed by a workflow node."""

    id: str
    label: str = ""
    data_type: str = "any"
    required: bool = False


class NodeTypeDefinition(BaseModel):
    """Serializable metadata used by both the engine and visual editor."""

    type: str
    label: str
    description: str = ""
    category: str = "core"
    color: str = "#64748b"
    inputs: list[NodePort] = Field(default_factory=list)
    outputs: list[NodePort] = Field(default_factory=list)
    runtime_type: str | None = None
    builtin: bool = False


class NodeRegistry:
    """Stores node metadata and optional execution callbacks."""

    def __init__(self) -> None:
        self._definitions: dict[str, NodeTypeDefinition] = {}
        self._executors: dict[str, NodeExecutor] = {}

    def register(
        self,
        definition: NodeTypeDefinition,
        executor: NodeExecutor | None = None,
    ) -> None:
        self._definitions[definition.type] = definition
        if executor is not None:
            self._executors[definition.type] = executor

    def unregister(self, node_type: str) -> None:
        self._definitions.pop(node_type, None)
        self._executors.pop(node_type, None)

    def get(self, node_type: str) -> NodeTypeDefinition | None:
        return self._definitions.get(node_type)

    def list_types(self) -> list[NodeTypeDefinition]:
        return list(self._definitions.values())

    def get_executor(self, node_type: str) -> NodeExecutor | None:
        return self._executors.get(node_type)

    def runtime_type(self, canvas_type: str) -> str:
        definition = self.get(canvas_type)
        return definition.runtime_type or canvas_type if definition else canvas_type

    def check_connection(
        self,
        source_type: str,
        source_handle: str,
        target_type: str,
        target_handle: str,
    ) -> str | None:
        source = self.get(source_type)
        target = self.get(target_type)
        if source is None or target is None:
            return None

        output = next((port for port in source.outputs if port.id == source_handle), None)
        if output is None:
            return f"Unknown source port '{source_handle}' on node type '{source_type}'"
        input_port = next((port for port in target.inputs if port.id == target_handle), None)
        if input_port is None:
            return f"Unknown target port '{target_handle}' on node type '{target_type}'"
        if "any" not in {output.data_type, input_port.data_type} and output.data_type != input_port.data_type:
            return (
                f"Incompatible ports: {source_type}.{source_handle} ({output.data_type}) -> "
                f"{target_type}.{target_handle} ({input_port.data_type})"
            )
        return None


def _port(port_id: str, label: str, data_type: str = "any", *, required: bool = False) -> NodePort:
    return NodePort(id=port_id, label=label, data_type=data_type, required=required)


node_registry = NodeRegistry()

for _definition in (
    NodeTypeDefinition(
        type="input", label="Input", description="Workflow input values", color="#2563eb",
        outputs=[_port("value", "Value")], runtime_type="start", builtin=True,
    ),
    NodeTypeDefinition(
        type="llm", label="LLM", description="Call a language model", category="ai", color="#9333ea",
        inputs=[_port("prompt", "Prompt", "string")], outputs=[_port("response", "Response", "string")],
        builtin=True,
    ),
    NodeTypeDefinition(
        type="tool", label="Tool", description="Execute a registered tool", category="actions", color="#16a34a",
        inputs=[_port("input", "Input")], outputs=[_port("result", "Result")], builtin=True,
    ),
    NodeTypeDefinition(
        type="condition", label="Condition", description="Branch by condition", category="logic", color="#d97706",
        inputs=[_port("value", "Value")],
        outputs=[_port("true", "True"), _port("false", "False")], builtin=True,
    ),
    NodeTypeDefinition(
        type="code", label="Code", description="Run sandboxed workflow code", category="logic", color="#0d9488",
        inputs=[_port("input", "Input")], outputs=[_port("result", "Result")], builtin=True,
    ),
    NodeTypeDefinition(
        type="iterator", label="Iterator", description="Iterate over a list", category="logic", color="#db2777",
        inputs=[_port("items", "Items", "list", required=True)],
        outputs=[_port("results", "Results", "list")], builtin=True,
    ),
    NodeTypeDefinition(
        type="output", label="Output", description="Return workflow results", color="#0284c7",
        inputs=[_port("value", "Value")], runtime_type="end", builtin=True,
    ),
):
    node_registry.register(_definition)
