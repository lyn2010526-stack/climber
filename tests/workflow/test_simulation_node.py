"""End-to-end tests for the SIMULATION workflow node type."""

from __future__ import annotations

import asyncio

from app.core.engine.tool_capabilities import DEFAULT_ALLOWED_TOOLS, build_workflow_tool_validator
from app.simulation.review import HarnessReviewer
from app.tools import ToolRegistry
from app.workflow import NodeStatus, NodeType, Workflow, WorkflowEdge, WorkflowNode
from app.workflow.engine import WorkflowEngine


class _FakeEngine:
    """Minimal fake AgentEngine: exposes sandbox/permission attrs only."""

    def __init__(self):
        self.sandbox = None
        self.permission_overlay = None


def _registry_with_sim() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "simulate",
        "Fake simulation tool",
        {
            "type": "object",
            "properties": {"rate": {"type": "number"}},
            "required": ["rate"],
        },
        _sim_ok,
    )
    return registry


async def _sim_ok(**kwargs) -> str:
    rate = float(kwargs.get("rate", 1.0))
    return f"Simulation ok. throughput={rate * 2:.2f}"


def test_simulation_node_runs_and_accepts():
    """A SIMULATION node with an opted-in tool should dispatch and accept."""

    async def go():
        registry = _registry_with_sim()
        engine = WorkflowEngine(_FakeEngine(), tool_registry=registry)
        sim_node = WorkflowNode(
            id="sim", type=NodeType.SIMULATION, name="Simulate",
            config={
                "tool_name": "simulate",
                "schema": {"sweep": {"rate": {"values": [1.0, 2.0]}}},
                "max_rounds": 3,
                "tool_capabilities": ["+simulate"],
            },
        )
        end_node = WorkflowNode(id="end", type=NodeType.END, name="End")
        wf = Workflow(
            id="w1", name="Test Sim", nodes=[sim_node, end_node],
            edges=[WorkflowEdge(source="sim", target="end")],
        )
        result = await engine.execute(wf, user_inputs={"goal": "tune rate"})
        return result, sim_node

    result, node = asyncio.run(go())
    assert result.status == "completed"
    assert node.status == NodeStatus.COMPLETED
    output = node.output
    assert output["accepted"] == 2
    assert output["rejected"] == 0
    assert len(output["reports"]) == 2
    assert output["reports"][0]["accepted_attempt"]["parameters"]["rate"] == 1.0


def test_simulation_node_default_denied_tool():
    """Without an explicit capability opt-in, the tool is never dispatched."""

    async def go():
        registry = ToolRegistry()
        fired = []

        async def shell_tool(**kwargs):
            fired.append(kwargs)
            return "ok"

        registry.register("run_command", "shell", {}, shell_tool)
        engine = WorkflowEngine(_FakeEngine(), tool_registry=registry)
        sim_node = WorkflowNode(
            id="sim", type=NodeType.SIMULATION, name="Simulate",
            config={
                "tool_name": "run_command",
                "schema": {"sweep": {"cmd": {"values": ["ls"]}}},
                "max_rounds": 2,
            },
        )
        end_node = WorkflowNode(id="end", type=NodeType.END, name="End")
        wf = Workflow(
            id="w2", name="Test Denied", nodes=[sim_node, end_node],
            edges=[WorkflowEdge(source="sim", target="end")],
        )
        result = await engine.execute(wf, user_inputs={"goal": "x"})
        return result, sim_node, fired

    result, node, fired = asyncio.run(go())
    assert node.status == NodeStatus.COMPLETED
    assert node.output["rejected"] == 1
    assert node.output["accepted"] == 0
    assert fired == []
    # The attempt error records the allowlist block reason
    attempt = node.output["reports"][0]["attempts"][0]
    assert "disabled by default" in attempt["error"]


def test_simulation_node_capability_allowlist():
    """Explicit +tool_capabilities should permit an otherwise-denied tool."""

    async def go():
        registry = _registry_with_sim()
        engine = WorkflowEngine(_FakeEngine(), tool_registry=registry)
        sim_node = WorkflowNode(
            id="sim", type=NodeType.SIMULATION, name="Simulate",
            config={
                "tool_name": "simulate",
                "schema": {"sweep": {"rate": {"values": [5.0]}}},
                "max_rounds": 2,
                "tool_capabilities": ["+simulate", "-shell"],
            },
        )
        end_node = WorkflowNode(id="end", type=NodeType.END, name="End")
        wf = Workflow(
            id="w3", name="Test Allow", nodes=[sim_node, end_node],
            edges=[WorkflowEdge(source="sim", target="end")],
        )
        result = await engine.execute(wf, user_inputs={"goal": "allow"})
        return result, sim_node

    result, node = asyncio.run(go())
    assert node.status == NodeStatus.COMPLETED
    assert node.output["reports"][0]["accepted_attempt"]["parameters"]["rate"] == 5.0


def test_flow_template_resolves_simulation_experiment():
    """Flow(name='simulation_experiment') should build the template."""
    from app.multi_agent.flow import Flow

    flow = asyncio.run(Flow("simulation_experiment")._resolve_workflow({}))
    assert flow is not None
    types = [n.type for n in flow.nodes]
    assert NodeType.SIMULATION in types
    assert NodeType.LLM in types
    sim_config = next(n.config for n in flow.nodes if n.type == NodeType.SIMULATION)
    assert "tool_name" in sim_config


class _LlmEngine(_FakeEngine):
    """Fake AgentEngine that also answers one-shot LLM calls with a plan."""

    def __init__(self, plan_json: str):
        super().__init__()
        self._plan_json = plan_json
        self.sessions = []

    def create_session(self, **kwargs):
        self.sessions.append(kwargs)
        return object()

    async def run_agent(self, session, message):
        return {"output": self._plan_json, "tokens_used": 0}


def test_simulation_node_llm_mode_plans_and_runs():
    """llm_mode: the node plans from a natural-language goal via LLM sub-agent."""

    async def go():
        registry = _registry_with_sim()
        engine = WorkflowEngine(_LlmEngine(
            '{"objective":"tune throughput",'
            '"sweep":{"rate":{"values":[1.0,3.0]}},'
            '"base":{}}'
        ), tool_registry=registry)
        sim_node = WorkflowNode(
            id="sim", type=NodeType.SIMULATION, name="Simulate",
            config={
                "tool_name": "simulate",
                "llm_mode": True,
                "provider": "openai",
                "model_id": "gpt-4",
                "api_key": "test-key",
                "max_rounds": 3,
                "tool_capabilities": ["+simulate"],
                "goal": "Find the rate that maximizes throughput",
            },
        )
        end_node = WorkflowNode(id="end", type=NodeType.END, name="End")
        wf = Workflow(
            id="w4", name="Test LLM Sim", nodes=[sim_node, end_node],
            edges=[WorkflowEdge(source="sim", target="end")],
        )
        result = await engine.execute(wf, user_inputs={})
        return result, sim_node

    result, node = asyncio.run(go())
    assert result.status == "completed"
    assert node.status == NodeStatus.COMPLETED
    assert node.output["accepted"] == 2
    assert sorted(
        r["accepted_attempt"]["parameters"]["rate"]
        for r in node.output["reports"]
    ) == [1.0, 3.0]


class _OrchLlmEngine(_FakeEngine):
    """Fake engine answering LLM calls for orchestrator mode."""

    def __init__(self, plan_json: str):
        super().__init__()
        self._plan_json = plan_json
        self.sessions = []

    def create_session(self, **kwargs):
        self.sessions.append(kwargs)
        return object()

    async def run_agent(self, session, message):
        return {"output": self._plan_json, "tokens_used": 0}


def test_simulation_node_orchestrator_mode():
    """orchestrator_mode: the 总指挥 close-loop runs through the node."""

    async def go():
        registry = _registry_with_sim()
        engine = WorkflowEngine(_OrchLlmEngine(
            '{"objective":"tune throughput",'
            '"sweep":{"rate":{"values":[1.0,2.0]}},'
            '"base":{}}'
        ), tool_registry=registry)
        sim_node = WorkflowNode(
            id="sim", type=NodeType.SIMULATION, name="Simulate",
            config={
                "tool_name": "simulate",
                "orchestrator_mode": True,
                "provider": "openai",
                "model_id": "gpt-4",
                "api_key": "test-key",
                "max_rounds": 3,
                "plan_rounds": 2,
                "tool_capabilities": ["+simulate"],
                "goal": "Find the rate that maximizes throughput",
            },
        )
        end_node = WorkflowNode(id="end", type=NodeType.END, name="End")
        wf = Workflow(
            id="w5", name="Test Orch Sim", nodes=[sim_node, end_node],
            edges=[WorkflowEdge(source="sim", target="end")],
        )
        result = await engine.execute(wf, user_inputs={})
        return result, sim_node

    result, node = asyncio.run(go())
    assert result.status == "completed"
    assert node.status == NodeStatus.COMPLETED
    output = node.output
    assert output["satisfied"] is True
    assert output["accepted"] == 2
    assert output["rounds"] == 1
    assert output["final_report"]["satisfied"] is True
    assert output["final_report"]["best_parameters"]["parameters"]["rate"] in (1.0, 2.0)


def test_simulation_node_uses_global_registry_when_not_injected():
    """A SIMULATION node must resolve the app-wide tool registry (the one
    register_builtins fills) when the engine gets no explicit registry, so
    the real simulate_experiment tool reaches the harness in Flow/API runs.
    """

    async def go():
        from app.tools import register_builtins
        from app.tools import tool_registry as global_registry

        register_builtins()
        engine = WorkflowEngine(_FakeEngine(), tool_registry=None)
        resolved = engine._resolve_registry()
        return (
            resolved is global_registry,
            resolved.get_tool("simulate_experiment") is not None,
        )

    same_global, has_real_tool = asyncio.run(go())
    assert same_global
    assert has_real_tool


def test_simulation_experiment_template_wires_real_tool():
    """The simulation_experiment template must expose a SIMULATION node
    whose tool_name defaults to the real simulate_experiment and stays in
    the default allowlist so Flow/API runs reach the harness."""

    from app.core.engine.tool_capabilities import DEFAULT_ALLOWED_TOOLS
    from app.workflow import NodeType
    from app.workflow.templates import WorkflowTemplates

    workflow = WorkflowTemplates.simulation_experiment(
        provider="openai", model_id="gpt-4o", api_key="",
        tool_name="simulate_experiment",
        schema={"sweep": {"dt": {"values": [1e-4, 2e-4, 5e-4]}}},
        max_rounds=4,
    )
    sim = next(n for n in workflow.nodes if n.type == NodeType.SIMULATION)
    assert sim.config["tool_name"] == "simulate_experiment"
    assert sim.config["max_rounds"] == 4
    assert "simulate_experiment" in DEFAULT_ALLOWED_TOOLS
    assert any(
        t["id"] == "simulation_experiment"
        for t in WorkflowTemplates.list_templates()
    )
