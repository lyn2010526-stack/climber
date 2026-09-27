"""Stress/hammer test for the software-factory + simulation chain."""
import json
import random
import threading
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
key = "sk-loadtest-fake-0000"

results = {"total": 0, "ok": 0, "err": 0, "errors": {}, "methods": {}}
lock = threading.Lock()


def req(method, path, body=None, timeout=120):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            status = resp.status
            payload = resp.read().decode(errors="replace")
        return status, payload, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), time.time() - t0
    except Exception as e:
        return -1, str(e), time.time() - t0


def record(method, path, status, dt, ok_flag):
    with lock:
        results["total"] += 1
        if ok_flag:
            results["ok"] += 1
        else:
            results["err"] += 1
            k = f"{method} {path} -> {status}"
            results["errors"][k] = results["errors"].get(k, 0) + 1
    s = f"{method} {path} -> {status} [{dt*1000:.0f}ms]"
    with open("/tmp/loadtest_rows.log", "a") as f:
        f.write(s + "\n")


def run_experiment_worker(worker_id, n):
    """Create a workflow with a simulation node and run it."""
    for i in range(n):
        dt = random.choice([1e-4, 5e-4, 1e-3, 1e-2, 0.1])
        model = random.choice(["heat", "oscillator", "logistic", "bogus_model"])
        base = {"model": "heat", "dx": 0.02, "t_final": 5, "source_temp": 100, "ambient_temp": 0}
        if model == "oscillator":
            base = {"model": "oscillator", "mass": 1, "stiffness": 2, "damping": 0.1,
                    "drive_amplitude": 0.5, "drive_frequency": 1.2, "duration": 10}
        elif model == "logistic":
            base = {"model": "logistic", "growth_rate": 0.5, "carrying_capacity": 100,
                    "initial_population": 10, "duration": 50}
        schema = json.dumps({"sweep": {"dt": {"values": [dt]}}, "base": base})
        malformed = (i % 5 == 0)
        if malformed:
            schema = "{ not valid json !!"
        workflow = {
            "name": f"lt-{worker_id}-{i}",
            "nodes": [
                {"id": "a", "type": "input", "data": {"label": "In"}},
                {"id": "sim", "type": "simulation", "data": {
                    "label": "Sim", "tool_name": "simulate_experiment",
                    "goal": f"converge dt for {model}",
                    "schema_(json)": schema,
                    "max_rounds": str(random.choice([1, 3, 10])),
                }},
                {"id": "b", "type": "output", "data": {"label": "Out"}},
            ],
            "edges": [{"source": "a", "target": "sim"}, {"source": "sim", "target": "b"}],
        }
        s, body, dt0 = req("POST", "/api/v1/workflows", workflow)
        record("POST", "/workflows", s, dt0, 200 <= s < 300)
        if s != 200:
            continue
        wf_id = json.loads(body).get("id")
        s, body, dt1 = req("POST", f"/api/v1/workflows/{wf_id}/run", {"inputs": {}})
        # completed (200) is success regardless of experiment outcome; error fields recorded separately
        ok_flag = s == 200
        record("POST", f"/workflows/{wf_id}/run", s, dt1, ok_flag)
        if s == 200:
            try:
                data = json.loads(body)
                outs = data.get("outputs", {})
                sim = outs.get("Out") or {}
                tag = f"accepted={sim.get('accepted')} rejected={sim.get('rejected')}"
                with open("/tmp/loadtest_rows.log", "a") as f:
                    f.write(f"  result: {tag}\n")
            except Exception:
                pass


def api_key_stress_worker(worker_id, n):
    for i in range(n):
        s, body, dt0 = req("POST", "/api/v1/api-keys", {
            "provider": random.choice(["openai", "anthropic", "google", "ollama", "stepfun"]),
            "name": f"key-{worker_id}-{i}", "api_key": f"sk-{random.randint(0,10**12)}",
        })
        record("POST", "/api-keys", s, dt0, 200 <= s < 300)
        list_s, _, _ = req("GET", "/api/v1/api-keys")
        record("GET", "/api-keys", list_s, 0.01, list_s == 200)


def agent_stress_worker(worker_id, n):
    for i in range(n):
        s, body, dt0 = req("POST", "/api/v1/agents", {
            "name": f"agent-{worker_id}-{i}", "provider": "openai", "model_id": "gpt-4o-mini",
        })
        record("POST", "/agents", s, dt0, 200 <= s < 300)


def malformed_worker(worker_id, n):
    """Bang on endpoints with garbage to probe 5xx vs 4xx hygiene."""
    garbage = [
        "not-json",
        "[]",
        '{"nodes": "nope"}',
        '{"nodes": [{"id":"a","type":"simulation","data":{}}], "edges": [], "name": 123}',
        '{"nodes": [{"id":"a","type":"input","data":{}}], "edges": [{"source":"missing"}]}',
    ]
    for i in range(n):
        body = garbage[i % len(garbage)]
        try:
            data = json.loads(body) if body not in ("not-json", "[]") else json.loads(body) if body == "[]" else body
        except Exception:
            data = body
        s, resp, dt0 = req("POST", "/api/v1/workflows", data if isinstance(data, dict) else json.loads('{}'))
        record("POST", "/workflows(garbage)", s, dt0, 400 <= s < 500 or s == 200)


def main():
    workers = []
    for w in range(4):
        t = threading.Thread(target=run_experiment_worker, args=(w, 6))
        workers.append(t)
    for w in range(2):
        t = threading.Thread(target=api_key_stress_worker, args=(w, 8))
        workers.append(t)
    t = threading.Thread(target=agent_stress_worker, args=(0, 5))
    workers.append(t)
    t = threading.Thread(target=malformed_worker, args=(0, 6))
    workers.append(t)
    t0 = time.time()
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    dur = time.time() - t0
    print(f"=== LOADTEST SUMMARY ({dur:.1f}s) ===")
    print(f"total={results['total']} ok={results['ok']} err={results['err']}")
    if results["errors"]:
        print("ERROR BREAKDOWN:")
        for k, v in sorted(results["errors"].items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()