"""Tests for the Pregel workflow route path."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.v1.routes.workflows import _execute_workflow


def _agent() -> SimpleNamespace:
    return SimpleNamespace(
        provider="openai",
        model_id="test-model",
        api_key_encrypted="",
        base_url="",
    )


@pytest.mark.asyncio
async def test_pregel_route_branch_runs_input_output_graph() -> None:
    nodes = [
        {"id": "in", "type": "input", "data": {"label": "Input"}},
        {"id": "out", "type": "output", "data": {"label": "Output"}},
    ]
    edges = [{"source": "in", "target": "out"}]

    result = await _execute_workflow(
        None,
        _agent(),
        nodes,
        edges,
        {"pregel": True, "inputs": {"input": "hello"}, "workflow_id": "wf"},
        0.0,
    )

    assert result["status"] == "completed"
    assert result["outputs"]["Output"] == {"input": "hello"}
