"""Graph-builder regression: visual simulation node must map to SIMULATION type."""

from __future__ import annotations

from app.core.workflow_executor import build_workflow_from_graph
from app.workflow import NodeType


def test_build_workflow_from_graph_maps_simulation_node():
    nodes = [
        {"id": "a", "type": "input", "data": {"label": "In"}},
        {
            "id": "sim",
            "type": "simulation",
            "data": {
                "label": "Sim",
                "tool_name": "simulate_experiment",
                "goal": "Find a dt that converges",
                "schema_(json)": '{"sweep":{"dt":{"values":[0.0001]}},"base":{"model":"heat"}}',
                "max_rounds": "3",
            },
        },
        {"id": "b", "type": "output", "data": {"label": "Out"}},
    ]
    edges = [{"source": "a", "target": "sim"}, {"source": "sim", "target": "b"}]

    wf = build_workflow_from_graph(nodes, edges)

    sim = next(n for n in wf.nodes if n.id == "sim")
    assert sim.type is NodeType.SIMULATION
    assert sim.config["tool_name"] == "simulate_experiment"
    assert sim.config["goal"] == "Find a dt that converges"
    assert sim.config["max_rounds"] == 3
    assert sim.config["schema"] == {
        "sweep": {"dt": {"values": [0.0001]}},
        "base": {"model": "heat"},
    }


def test_build_workflow_from_graph_defaults_simulation_config():
    nodes = [
        {"id": "sim", "type": "simulation", "data": {"label": "Sim"}},
    ]
    edges: list[dict] = []

    wf = build_workflow_from_graph(nodes, edges)

    sim = next(n for n in wf.nodes if n.id == "sim")
    assert sim.type is NodeType.SIMULATION
    assert sim.config["tool_name"] == "simulate_experiment"
    assert sim.config["max_rounds"] == 8
    assert sim.config["schema"] == {}