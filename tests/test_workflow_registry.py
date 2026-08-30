"""Tests for extensible workflow node metadata and executors."""

from __future__ import annotations

from app.workflow.registry import NodePort, NodeRegistry, NodeTypeDefinition, node_registry


def test_builtin_registry_exposes_seven_canvas_node_types():
    definitions = node_registry.list_types()

    assert [definition.type for definition in definitions] == [
        "input",
        "llm",
        "tool",
        "condition",
        "code",
        "iterator",
        "output",
    ]
    assert all(definition.label for definition in definitions)
    assert all(definition.color for definition in definitions)


def test_custom_node_type_can_register_an_executor():
    registry = NodeRegistry()

    async def execute(node, inputs, context):
        return {"value": inputs["value"], "node_id": node.id, "user_id": context["user_id"]}

    definition = NodeTypeDefinition(
        type="custom.echo",
        label="Echo",
        inputs=[NodePort(id="value", data_type="string", required=True)],
        outputs=[NodePort(id="result", data_type="string")],
    )
    registry.register(definition, execute)

    assert registry.get("custom.echo") == definition
    assert registry.get_executor("custom.echo") is execute


def test_port_compatibility_accepts_any_and_rejects_mismatched_types():
    registry = NodeRegistry()
    registry.register(NodeTypeDefinition(
        type="source",
        label="Source",
        outputs=[NodePort(id="text", data_type="string"), NodePort(id="value")],
    ))
    registry.register(NodeTypeDefinition(
        type="target",
        label="Target",
        inputs=[NodePort(id="text", data_type="string"), NodePort(id="items", data_type="list")],
    ))

    assert registry.check_connection("source", "text", "target", "text") is None
    assert registry.check_connection("source", "value", "target", "items") is None
    assert "incompatible" in registry.check_connection("source", "text", "target", "items").lower()
    assert "unknown source port" in registry.check_connection("source", "missing", "target", "text").lower()
