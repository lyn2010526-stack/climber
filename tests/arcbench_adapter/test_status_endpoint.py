"""Read-only ARC-Bench status endpoint contract tests."""

from __future__ import annotations

import json


def _write(run_dir, relative: str, content: str) -> None:
    path = run_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def test_arcbench_status_reports_not_run_when_no_output(client, monkeypatch) -> None:
    import app.api.v1.routes.arcbench as arcbench

    monkeypatch.setattr(arcbench, "_RUN_DIR", arcbench._PROJECT_ROOT / "workspace-does-not-exist")
    resp = await client.get("/api/v1/arcbench/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["phase"] == "idle"
    assert "尚未" in body["message"]


async def test_arcbench_status_reports_completed_run(client, tmp_path, monkeypatch) -> None:
    import app.api.v1.routes.arcbench as arcbench

    run_dir = tmp_path / "run-1"
    _write(run_dir, ".arc/runner-events.jsonl", "\n".join([
        json.dumps({"type": "runner_state", "state": "running", "timestamp": "2026-09-18 10:00:00", "message": "started"}),
        json.dumps({"type": "requirement_state", "node_id": "REQ-1", "phase": "design", "status": "completed", "timestamp": "2026-09-18 10:01:00", "message": "designed"}),
        json.dumps({"type": "requirement_state", "node_id": "REQ-1", "phase": "implement", "status": "completed", "timestamp": "2026-09-18 10:02:00", "message": "implemented"}),
        json.dumps({"type": "requirement_state", "node_id": "REQ-1", "phase": "test", "status": "passed", "timestamp": "2026-09-18 10:03:00", "message": "spec green"}),
        json.dumps({"type": "requirement_state", "node_id": "REQ-2", "phase": "test", "status": "failed", "timestamp": "2026-09-18 10:04:00", "message": "spec red"}),
        json.dumps({"type": "runner_state", "state": "completed", "timestamp": "2026-09-18 10:05:00", "message": "completed 1/2 nodes"}),
    ]))
    _write(run_dir, "run_summary.json", json.dumps({
        "nodes_completed": 1, "nodes_total": 2, "acceptance": "1 passed, 1 failed",
        "rehearsal_error": False,
    }))
    (run_dir / ".arc" / "traceability").mkdir(parents=True)

    pack_dir = tmp_path / "dist"
    pack_dir.mkdir()
    (pack_dir / "climber-arcbench-20260918.zip").write_bytes(b"PK")

    monkeypatch.setattr(arcbench, "_RUN_DIR", tmp_path)
    monkeypatch.setattr(arcbench, "_PACK_DIR", pack_dir)

    resp = await client.get("/api/v1/arcbench/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["phase"] == "acceptance"
    assert "1 passed, 1 failed" in body["phase_detail"]
    assert body["trace_exists"] is True
    assert body["acceptance"]["ran"] is True
    assert body["acceptance"]["passed"] == 1
    assert body["acceptance"]["failed"] == 1
    assert body["pack_exists"] is True
    assert body["pack_artifact"].endswith("climber-arcbench-20260918.zip")
    assert body["updated_at"] == "2026-09-18 10:05:00"
    assert body["last_events"][-1]["type"] == "runner_state"


async def test_arcbench_status_reports_mid_run_phase(client, tmp_path, monkeypatch) -> None:
    import app.api.v1.routes.arcbench as arcbench

    run_dir = tmp_path / "run-2"
    _write(run_dir, ".arc/runner-events.jsonl", "\n".join([
        json.dumps({"type": "runner_state", "state": "running", "timestamp": "2026-09-18 09:00:00", "message": "started"}),
        json.dumps({"type": "requirement_state", "node_id": "REQ-1", "phase": "design", "status": "completed", "timestamp": "2026-09-18 09:01:00", "message": "designed"}),
        json.dumps({"type": "requirement_state", "node_id": "REQ-1", "phase": "implement", "status": "running", "timestamp": "2026-09-18 09:02:00", "message": "coding"}),
    ]))
    monkeypatch.setattr(arcbench, "_RUN_DIR", tmp_path)
    monkeypatch.setattr(arcbench, "_PACK_DIR", tmp_path / "empty-dist")

    resp = await client.get("/api/v1/arcbench/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["phase"] == "implementation"
    assert body["trace_exists"] is False
    assert body["pack_exists"] is False


async def test_arcbench_status_reports_failed_runner(client, tmp_path, monkeypatch) -> None:
    import app.api.v1.routes.arcbench as arcbench

    run_dir = tmp_path / "run-3"
    _write(run_dir, ".arc/runner-events.jsonl", "\n".join([
        json.dumps({"type": "runner_state", "state": "running", "timestamp": "2026-09-18 08:00:00", "message": "started"}),
        json.dumps({"type": "runner_state", "state": "failed", "timestamp": "2026-09-18 08:01:00", "message": "requirements parse failed: boom"}),
    ]))
    monkeypatch.setattr(arcbench, "_RUN_DIR", tmp_path)
    monkeypatch.setattr(arcbench, "_PACK_DIR", tmp_path / "empty-dist")

    resp = await client.get("/api/v1/arcbench/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["phase"] == "failed"
    assert "boom" in body["phase_detail"]
