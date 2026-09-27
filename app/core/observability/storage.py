"""Storage location helpers for the observability components.

``TraceCollector``, ``AuditChain`` and ``GoalTracker`` each default to
``":memory:"``. Every read endpoint therefore answered with an empty list,
and all recorded history disappeared on restart. They now resolve to files
under ``data/``, which is the same directory ``emergency_stop`` already uses.

Tests should pass an explicit path (usually ``tmp_path``) to stay isolated.
"""

from __future__ import annotations

import os
from pathlib import Path


def observability_dir() -> Path:
    """Return the directory holding observability databases, creating it."""
    base = os.environ.get("CLIMBER_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[3] / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def default_observability_db(filename: str) -> str:
    """Return an absolute path for an observability database file.

    Args:
        filename: The database file name, e.g. ``"traces.db"``.

    Returns:
        A path string suitable for ``sqlite3.connect``.
    """
    return str(observability_dir() / filename)
