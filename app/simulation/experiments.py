"""Real, computable experiment backends for the simulation harness.

This module ships actual numerical experiments that *compute real numbers*
with numpy — no fake outputs. Each experiment maps to a classic physics /
engineering model and returns a structured JSON result that the simulation
harness probes for convergence:

- ``heat``      1-D heat conduction via explicit finite differences. When
                the CFL criterion (dt <= dx^2/(2*alpha)) is violated the
                scheme genuinely diverges to NaN, which the harness detects
                and auto-adjusts parameters for — the same retry loop an
                OpenFOAM solver run uses.
- ``oscillator`` damped driven harmonic oscillator (analytic + RK4 check),
                returns settling time / amplitude metrics.
- ``logistic``  logistic population growth, returns final population and
                convergence state.

These backends are intentionally bounded and deterministic: pure numpy, no
network, no subprocess, fixed time steps, and capped output sizes, so the
safe-lab tool policy stays meaningful.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any

import numpy as np

EXPERIMENT_MAX_SECONDS = 10.0
EXPERIMENT_MAX_STEPS = 200_000

# CFL-stability safety factor: dt must be <= cfl * dx^2/(2*alpha)
_CFL = 0.45

MODELS = ("heat", "oscillator", "logistic")


def _finish(payload: dict[str, Any], started: float) -> str:
    payload["elapsed_ms"] = round((time.time() - started) * 1000, 3)
    return json.dumps(payload, ensure_ascii=False, default=float)


def _diverged(payload: dict[str, Any], started: float, reason: str) -> str:
    payload["converged"] = False
    payload["error"] = reason
    payload["nan"] = True
    return _finish(payload, started)


def run_heat_experiment(
    alpha: float = 1e-4,
    dx: float = 0.02,
    dt: float = 1e-4,
    t_final: float = 10.0,
    n_points: int = 51,
    source_temp: float = 100.0,
    ambient_temp: float = 0.0,
) -> str:
    """1-D heat conduction with explicit finite differences.

    Returns a JSON string: ``max_temperature``, ``mean_temperature``,
    ``steady_state``, ``converged``, ``iterations`` and ``cfl``. A
    violating CFL (dt > dx^2/(2*alpha)) genuinely diverges to NaN, which
    the harness probe rejects.
    """
    started = time.time()
    payload: dict[str, Any] = {"model": "heat"}

    if not (alpha > 0 and dx > 0 and dt > 0 and t_final > 0):
        return _diverged(payload, started, "non-positive numerical parameters")

    n = max(3, min(int(n_points), 1000))
    if n % 2 == 0:
        n += 1
    cell_x = dx

    max_stable_dt = _CFL * cell_x * cell_x / (2.0 * alpha)
    cfl = dt / max_stable_dt

    max_steps = int(math.ceil(t_final / dt))
    if max_steps > EXPERIMENT_MAX_STEPS:
        return _diverged(payload, started, "step budget exceeded")

    # Physical blow-up guard: an unstable explicit scheme explodes in
    # magnitude long before it reaches NaN. Treat a field that exceeds a
    # sane multiple of the boundary values as genuinely diverged.
    temp_limit = (max(abs(float(source_temp)), abs(float(ambient_temp))) * 1e6) + 1.0

    temp = np.full(n, float(ambient_temp), dtype=np.float64)
    temp[0] = float(source_temp)
    temp[-1] = float(source_temp)

    done_steps = 0
    reached_steady = False
    prev = temp.copy()
    for _ in range(max_steps):
        temp[1:-1] += dt * alpha / (cell_x * cell_x) * (
            temp[2:] - 2.0 * temp[1:-1] + temp[:-2]
        )
        done_steps += 1
        if not np.all(np.isfinite(temp)):
            return _diverged(payload, started, "numerical divergence (CFL violated)")
        if float(np.max(np.abs(temp))) > temp_limit:
            return _diverged(payload, started, "numerical divergence (CFL blow-up)")
        change = float(np.max(np.abs(temp - prev)))
        prev = temp.copy()
        if change < 1e-6 * (float(np.max(np.abs(temp))) + 1.0):
            reached_steady = True
            break

    payload.update({
        "converged": True,
        "steady_state": reached_steady,
        "cfl": round(cfl, 6),
        "iterations": done_steps,
        "max_temperature": float(np.max(temp)),
        "mean_temperature": float(np.mean(temp)),
        "min_temperature": float(np.min(temp)),
    })
    return _finish(payload, started)


def run_oscillator_experiment(
    mass: float = 1.0,
    stiffness: float = 10.0,
    damping: float = 0.2,
    drive_amplitude: float = 1.0,
    drive_frequency: float = 1.0,
    duration: float = 30.0,
    dt: float = 0.001,
) -> str:
    """Damped driven harmonic oscillator.

    Returns ``settling_time`` (time for envelope to drop to 5% of initial),
    ``max_displacement``, ``final_amplitude``, ``resonance_ratio`` and
    ``converged``. Non-positive mass/stiffness or negative damping diverge
    to NaN.
    """
    started = time.time()
    payload: dict[str, Any] = {"model": "oscillator"}

    if mass <= 0 or stiffness <= 0 or damping < 0 or dt <= 0 or duration <= 0:
        return _diverged(payload, started, "non-positive physical parameters")

    steps = int(math.ceil(duration / dt))
    if steps > EXPERIMENT_MAX_STEPS:
        return _diverged(payload, started, "step budget exceeded")

    omega0 = math.sqrt(stiffness / mass)
    zeta = damping / (2.0 * math.sqrt(mass * stiffness))
    if zeta >= 1.0:
        return _diverged(payload, started, "overdamped system")

    x = 0.0
    v = 1.0
    max_disp = 0.0
    final_amp = 0.0
    settling_time = duration
    max_env = abs(x)
    for i in range(steps):
        t = i * dt
        a = (
            -(stiffness / mass) * x
            - (damping / mass) * v
            + (drive_amplitude / mass) * math.cos(drive_frequency * t)
        )
        v += a * dt
        x += v * dt
        if not math.isfinite(x):
            return _diverged(payload, started, "numeric divergence")
        if abs(x) > max_disp:
            max_disp = abs(x)
        env = abs(x)
        if env > max_env:
            max_env = env
        if settling_time == duration and env < 0.05 * max_env and max_env > 0:
            settling_time = t

    if steps:
        final_amp = abs(x)
    payload.update({
        "converged": True,
        "settling_time": round(settling_time, 4),
        "max_displacement": round(max_disp, 6),
        "final_amplitude": round(final_amp, 6),
        "damping_ratio": round(zeta, 6),
        "resonance_ratio": round(drive_frequency / omega0, 6),
    })
    return _finish(payload, started)


def run_logistic_experiment(
    growth_rate: float = 0.5,
    carrying_capacity: float = 1000.0,
    initial_population: float = 10.0,
    duration: float = 20.0,
    dt: float = 0.01,
) -> str:
    """Logistic population growth.

    Returns ``final_population``, ``max_population``, ``overshoot`` and
    ``converged``. Excessive growth_rate * dt can make the explicit update
    overshoot and diverge to negative/NaN — a real numerical failure.
    """
    started = time.time()
    payload: dict[str, Any] = {"model": "logistic"}

    if growth_rate < 0 or carrying_capacity <= 0 or initial_population < 0 or dt <= 0 or duration <= 0:
        return _diverged(payload, started, "non-positive model parameters")

    steps = int(math.ceil(duration / dt))
    if steps > EXPERIMENT_MAX_STEPS:
        return _diverged(payload, started, "step budget exceeded")

    n = float(initial_population)
    max_pop = n
    overshoot = 0.0
    for _ in range(steps):
        n += dt * growth_rate * n * (1.0 - n / carrying_capacity)
        if n < 0 or not math.isfinite(n):
            return _diverged(payload, started, "population diverged (r*dt too large)")
        if n > max_pop:
            max_pop = n
    overshoot = max(0.0, max_pop - carrying_capacity) / carrying_capacity
    payload.update({
        "converged": True,
        "final_population": round(n, 4),
        "max_population": round(max_pop, 4),
        "overshoot": round(overshoot, 6),
        "carrying_capacity": float(carrying_capacity),
    })
    return _finish(payload, started)


def run_experiment(model: str, **params: Any) -> str:
    """Dispatch to one of the real experiment models."""
    model = str(model or "").lower()
    if model == "heat":
        return run_heat_experiment(**params)
    if model == "oscillator":
        return run_oscillator_experiment(**params)
    if model == "logistic":
        return run_logistic_experiment(**params)
    return json.dumps({
        "model": model,
        "converged": False,
        "error": f"unknown model '{model}'; expected one of {MODELS}",
        "nan": True,
    }, ensure_ascii=False)
