"""End-to-end: visual workflow with simulation node via HTTP API."""
import os
os.environ.setdefault("APP_TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/probe_e2e.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:///./data/probe_e2e.db")
os.environ.setdefault("ENABLE_AUTH", "false")

import json
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    # 1. Store an API key via the live /api-keys route (frontend now points here)
    r = client.post("/api/v1/api-keys", json={
        "provider": "openai", "name": "demo", "api_key": "sk-test-fake-9999",
    })
    print("POST /api-keys:", r.status_code)

    # 2. Create an agent (required by /run)
    r = client.post("/api/v1/agents", json={
        "name": "demo-agent",
        "provider": "openai",
        "model_id": "gpt-4o-mini",
    })
    print("POST /agents:", r.status_code)

    # 3. Create a workflow with a simulation node (exact frontend data shape)
    workflow = {
        "name": "Heat Convergence Demo",
        "nodes": [
            {"id": "a", "type": "input", "data": {"label": "In"}},
            {"id": "sim", "type": "simulation", "data": {
                "label": "Sim",
                "tool_name": "simulate_experiment",
                "goal": "Find a dt that converges",
                "schema_(json)": json.dumps({
                    "sweep": {"dt": {"values": [0.0001, 0.0005]}},
                    "base": {"model": "heat", "dx": 0.02, "t_final": 5,
                             "source_temp": 100, "ambient_temp": 0},
                }),
                "max_rounds": "3",
            }},
            {"id": "b", "type": "output", "data": {"label": "Out"}},
        ],
        "edges": [
            {"source": "a", "target": "sim"},
            {"source": "sim", "target": "b"},
        ],
    }
    r = client.post("/api/v1/workflows", json=workflow)
    print("POST /workflows:", r.status_code, r.json().get("id") if r.status_code == 200 else r.text[:120])
    wf_id = r.json().get("id") if r.status_code == 200 else None

    # 4. Run it
    if wf_id:
        r = client.post(f"/api/v1/workflows/{wf_id}/run", json={"inputs": {}})
        print("POST /workflows/{id}/run:", r.status_code)
        body = r.json()
        print("  status:", body.get("status"))
        outputs = body.get("outputs", {})
        print("  outputs:", json.dumps(outputs, default=str)[:800])
        print("  node_results keys:", list(body.get("node_results", {}).keys()))

print("DONE")
