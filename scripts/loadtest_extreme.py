"""Extreme-input hammer: single-user demo simulation, no rate-limit trigger.

Deliberately paces below the 30/min limit to isolate functional robustness
from the (already confirmed) rate-limit behaviour.
"""
import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
results = {"total": 0, "ok": 0, "err": 0, "errors": {}, "lat": []}


def req(method, path, body=None, timeout=180):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace"), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), time.time() - t0
    except Exception as e:
        return -1, str(e), time.time() - t0


def rec(method, path, s, dt, ok):
    results["total"] += 1
    results["lat"].append(dt)
    if ok:
        results["ok"] += 1
    else:
        results["err"] += 1
        k = f"{method} {path} -> {s}"
        results["errors"][k] = results["errors"].get(k, 0) + 1
    print(f"{method} {path} -> {s} [{dt*1000:.0f}ms]")


def create_agent():
    s, b, _ = req("POST", "/api/v1/agents", {"name": "demo-agent", "provider": "openai", "model_id": "gpt-4o-mini"})
    rec("POST", "/agents", s, 0, 200 <= s < 300)


def mk_workflow(name, schema_str, rounds, goal):
    return {
        "name": name,
        "nodes": [
            {"id": "a", "type": "input", "data": {"label": "In"}},
            {"id": "sim", "type": "simulation", "data": {
                "label": "Sim", "tool_name": "simulate_experiment",
                "goal": goal, "schema_(json)": schema_str, "max_rounds": str(rounds),
            }},
            {"id": "b", "type": "output", "data": {"label": "Out"}},
        ],
        "edges": [{"source": "a", "target": "sim"}, {"source": "sim", "target": "b"}],
    }


def run_and_report(name, schema, rounds, goal, expect=200):
    s, b, dt = req("POST", "/api/v1/workflows", mk_workflow(name, schema, rounds, goal))
    rec("POST", "/workflows", s, dt, s == 200)
    if s != 200:
        return
    wf_id = json.loads(b).get("id")
    s2, b2, dt2 = req("POST", f"/api/v1/workflows/{wf_id}/run", {"inputs": {}})
    ok = s2 == expect
    rec(f"POST /workflows/{wf_id}/run", "", s2, dt2, ok)
    if s2 == 200:
        try:
            data = json.loads(b2)
            out = (data.get("outputs") or {}).get("Out") or {}
            print(f"    => status={data.get('status')} accepted={out.get('accepted')} rejected={out.get('rejected')} err={data.get('error','')[:80]}")
        except Exception:
            pass
    time.sleep(1.2)


def main():
    create_agent()
    base_heat = {"model": "heat", "dx": 0.02, "t_final": 5, "source_temp": 100, "ambient_temp": 0}

    # 1. dt way above stability limit (should reject and adjust, not hang/crash)
    run_and_report("big-dt", json.dumps({"sweep": {"dt": {"values": [1.0]}}, "base": base_heat}), 4,
                   "Find dt that converges")

    # 2. dt tiny -> very long integration (50000+ steps)
    run_and_report("tiny-dt", json.dumps({"sweep": {"dt": {"values": [1e-6]}}, "base": base_heat}), 3,
                   "Converge heat")

    # 3. negative / zero dt (invalid physics)
    run_and_report("neg-dt", json.dumps({"sweep": {"dt": {"values": [-0.01, 0]}}, "base": base_heat}), 3,
                   "Run experiment")

    # 4. unknown model name in base
    run_and_report("bad-model", json.dumps({"sweep": {"dt": {"values": [1e-4]}}, "base": {"model": "quantum_cfd", "dx": 0.02}}), 3,
                   "Run experiment")

    # 5. garbage schema JSON
    run_and_report("garbage-schema", "{ definitely not json !!", 3, "Run experiment")

    # 6. empty schema string
    run_and_report("empty-schema", "", 3, "Run experiment")

    # 7. schema as plain JSON dict (not the sweep/base envelope) - does planner cope?
    run_and_report("flat-schema", json.dumps({"model": "heat", "dt": 0.001, "dx": 0.02}), 3,
                   "Run experiment")

    # 8. huge max_rounds
    run_and_report("huge-rounds", json.dumps({"sweep": {"dt": {"values": [1e-4]}}, "base": base_heat}), 100,
                   "Converge")

    # 9. max_rounds = 0 / non-numeric
    run_and_report("zero-rounds", json.dumps({"sweep": {"dt": {"values": [1e-4]}}, "base": base_heat}), 0,
                   "Converge")

    # 10. long goal text
    run_and_report("long-goal", json.dumps({"sweep": {"dt": {"values": [1e-4]}}, "base": base_heat}), 3,
                   "please sweep the timestep dt over a few values and find one that keeps the numerical integration stable and converged while preserving physical accuracy of the heat diffusion profile at the boundary source temperature of one hundred celsius over five seconds duration with a spatial resolution of twenty millimetres") 

    # 11. malformed workflow: node without id
    s, b, dt = req("POST", "/api/v1/workflows", {
        "name": "no-id", "nodes": [{"type": "simulation", "data": {"label": "x"}}], "edges": []})
    rec("POST /workflows(no-id)", "", s, dt, s in (200, 422))

    # 12. concurrent duplicate runs of the same workflow (5x parallel)
    s, b, dt = req("POST", "/api/v1/workflows",
                   mk_workflow("repeat", json.dumps({"sweep": {"dt": {"values": [1e-4]}}, "base": base_heat}), 2,
                               "Converge"))
    wf_id = json.loads(b).get("id")
    import threading
    out = []
    def run_one():
        st, bd, _ = req("POST", f"/api/v1/workflows/{wf_id}/run", {"inputs": {}})
        out.append(st)
    ts = [threading.Thread(target=run_one) for _ in range(5)]
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"    parallel same-workflow statuses: {sorted(out)}")

    print(f"=== EXTREME SUMMARY ===")
    print(f"total={results['total']} ok={results['ok']} err={results['err']}")
    lat = sorted(results["lat"])
    n = len(lat)
    if n:
        print(f"latency p50={lat[n//2]*1000:.0f}ms p90={lat[int(n*0.9)]*1000:.0f}ms max={lat[-1]*1000:.0f}ms")
    if results["errors"]:
        print("ERROR BREAKDOWN:")
        for k, v in sorted(results["errors"].items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()