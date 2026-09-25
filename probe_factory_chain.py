"""Empirical verification of the software-factory demo chain."""
import os
os.environ.setdefault("APP_TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/probe_factory.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:///./data/probe_factory.db")
os.environ.setdefault("ENABLE_AUTH", "false")

from fastapi.testclient import TestClient
from app.main import app

results = []


def check(name, status, expected, body=None):
    ok = status == expected
    results.append((name, ok, status, body))


with TestClient(app) as client:
    # 1. POST /api/v1/api-keys (no auth) - should succeed
    r = client.post("/api/v1/api-keys", json={
        "provider": "openai", "name": "demo", "api_key": "sk-test-fake-1234",
    })
    check("POST /api-keys (no auth)", r.status_code, 200, r.json())

    # 2. GET /api/v1/api-keys - list
    r = client.get("/api/v1/api-keys")
    keys = r.json() if r.status_code == 200 else None
    check("GET /api-keys list", r.status_code, 200, keys)
    key_id = keys[0]["id"] if keys else None

    # 3. GET /api/v1/auth/keys - should 400 when auth disabled
    r = client.get("/api/v1/auth/keys")
    check("GET /auth/keys (no auth) -> 400", r.status_code, 400, r.text[:120])

    # 4. DELETE /api/v1/api-keys/{id}
    if key_id:
        r = client.delete(f"/api/v1/api-keys/{key_id}")
        check("DELETE /api-keys/{id}", r.status_code, 200, r.json())

    # 5. factory run WITHOUT key -> 409
    r = client.post("/api/v1/skills/autonomous/run", json={"goal": "test"})
    check("factory run no key -> 409", r.status_code, 409, r.text[:120])

    # 6. factory run WITH key stored -> passes 409 (should enter task queue / SSE)
    client.post("/api/v1/api-keys", json={
        "provider": "openai", "name": "demo2", "api_key": "sk-test-fake-5678",
    })
    r = client.post("/api/v1/skills/autonomous/run", json={"goal": "test"})
    check("factory run with key -> not 409", r.status_code, 200, r.text[:200])

print("=== PROBE RESULTS ===")
for name, ok, status, body in results:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  (status={status})")
    if not ok:
        print(f"      body={body}")
