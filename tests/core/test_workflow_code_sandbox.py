"""Regression tests for the subprocess-isolated workflow code node sandbox."""

from __future__ import annotations

import pytest

from app.workflow.code_sandbox import run_code_sandboxed
from app.workflow.safe_code import safe_eval, validate_code_ast


async def test_sandbox_runs_legit_python() -> None:
    outcome = await run_code_sandboxed("result = sum(range(10))", {})
    assert outcome["ok"] is True
    assert outcome["result"] == 45


async def test_sandbox_passes_inputs() -> None:
    outcome = await run_code_sandboxed("result = inputs.get('n', 0) * 2", {"n": 21})
    assert outcome["ok"] is True
    assert outcome["result"] == 42


async def test_sandbox_blocks_dunder_escape() -> None:
    outcome = await run_code_sandboxed("x = [].__class__\nresult = 1", {})
    assert outcome["ok"] is False
    assert "attribute" in outcome["error"]


async def test_sandbox_blocks_runtime_import_of_os() -> None:
    outcome = await run_code_sandboxed("m = __import__('os')\nresult = 1", {})
    assert outcome["ok"] is False


async def test_sandbox_blocks_static_dangerous_import() -> None:
    outcome = await run_code_sandboxed("import os\nresult = 1", {})
    assert outcome["ok"] is False
    assert "Unsafe import" in outcome["error"]


async def test_sandbox_allows_allowlisted_imports() -> None:
    outcome = await run_code_sandboxed("import json\nresult = json.dumps({'a': 1})", {})
    assert outcome["ok"] is True
    assert outcome["result"] == '{"a": 1}'


async def test_sandbox_terminates_infinite_loop() -> None:
    outcome = await run_code_sandboxed("while True:\n    pass", {}, timeout_seconds=2)
    assert outcome["ok"] is False
    assert "limit" in outcome["error"].lower() or "terminated" in outcome["error"].lower()


def test_rejects_huge_pow_literal() -> None:
    import ast

    with pytest.raises(ValueError, match="exponent"):
        validate_code_ast(ast.parse("x = 2 ** 100000", mode="exec"))


def test_legit_pow_still_evaluates() -> None:
    assert safe_eval("2 ** 10", {}) == 1024
