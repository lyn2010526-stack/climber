from __future__ import annotations

import importlib.util
from pathlib import Path


def test_runtime_sse_dependency_is_declared_and_importable() -> None:
    requirements = (Path(__file__).parents[2] / "requirements.txt").read_text()

    assert "sse-starlette" in requirements
    assert importlib.util.find_spec("sse_starlette") is not None
