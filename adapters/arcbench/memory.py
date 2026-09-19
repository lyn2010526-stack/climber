"""Adapter-local persistent memory for ARC-Bench runs.

Records failed-node summaries (node_id, timestamp, failing titles, message)
into a tiny JSON file under ``out_dir/.arc/memory.json`` and injects the
historical constraints back into later runs' node prompts. Kept self-contained
on purpose: the app memory service is async, DB-backed and carries setup
requirements that the sync grading adapter must not depend on. Zero external
dependencies, every failure degrades silently.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

MEMORY_DIR = ".arc"
MEMORY_FILE = "memory.json"
MAX_ENTRIES = 64


def memory_enabled() -> bool:
    return os.environ.get("CLIMBER_ARC_ACCEPTANCE_MEMORY", "").strip() != "0"


def memory_path(out_dir: Path) -> Path:
    return Path(out_dir) / MEMORY_DIR / MEMORY_FILE


def _tail(text, limit: int) -> str:
    text = text or ""
    return text[-limit:]


def record_failed_nodes(out_dir: Path, failed_nodes, acc: dict | None) -> None:
    """Append the run's failed-node summaries to persistent memory (best-effort)."""

    if not memory_enabled():
        return
    failed = sorted({str(n) for n in failed_nodes if n})
    if not failed:
        return
    message = _tail((acc or {}).get("message", ""), 300)
    detail = (acc or {}).get("specs_detail") or []
    entries = []
    for node_id in failed:
        titles = []
        for res in detail:
            if not isinstance(res, dict) or res.get("passed"):
                continue
            haystack = " ".join([res.get("file", ""), *res.get("titles", [])])
            if node_id in haystack:
                titles.append(" - ".join(res.get("titles", [])) or res.get("file", ""))
        entries.append({
            "node_id": node_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "titles": titles[:6],
            "message": message,
        })
    path = memory_path(out_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(payload, list):
                existing = payload
        path.write_text(
            json.dumps((existing + entries)[-MAX_ENTRIES:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, ValueError):
        pass


def acceptance_memory_inject(node_id: str, out_dir) -> str:
    """Historical failure constraints for a node, or '' when none (silent)."""

    if not memory_enabled() or not node_id:
        return ""
    path = memory_path(out_dir)
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return ""
    if not isinstance(payload, list):
        return ""
    hits = [e for e in payload if isinstance(e, dict) and e.get("node_id") == node_id]
    if not hits:
        return ""
    lines = []
    for entry in hits[-3:]:
        stamp = entry.get("timestamp", "")
        msg = _tail(entry.get("message", ""), 200)
        titles = entry.get("titles") or []
        title_note = "; failing cases: " + "; ".join(str(t) for t in titles[:3]) if titles else ""
        lines.append(f"- {stamp} {msg}{title_note}".strip())
    if not lines:
        return ""
    return ("REGRESSION GUARD from previous run(s), these independent acceptance "
            "failures were recorded for this node:\n" + "\n".join(lines))
