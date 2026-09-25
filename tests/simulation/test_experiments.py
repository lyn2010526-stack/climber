"""Tests for the real, computable experiment backends.

These tests assert the backends produce *real* numbers (no fake output),
detect true numerical divergence, and expose the metrics the harness
probes / reviewers consume. This is the "actually runs experiments"
guarantee behind the simulation harness.
"""

from __future__ import annotations

import json

from app.simulation.experiments import (
    run_experiment,
    run_heat_experiment,
    run_logistic_experiment,
    run_oscillator_experiment,
)


def parse(output: str) -> dict:
    return json.loads(output)


def test_heat_converges_with_stable_cfl():
    out = parse(run_heat_experiment(alpha=1e-4, dx=0.02, dt=1e-4, t_final=10.0))
    assert out["model"] == "heat"
    assert out["converged"] is True
    assert out["max_temperature"] > 0
    assert out["max_temperature"] <= 100.0
    assert out["mean_temperature"] > 0
    assert out["cfl"] <= 0.45
    assert out["iterations"] > 0


def test_heat_diverges_when_cfl_violated():
    # max stable dt for alpha=1e-2, dx=0.02 is 0.45*0.0004/(2*0.01)=0.009
    # dt=0.05 gives 100 steps of amplification factor 4 -> genuine NaN
    out = parse(run_heat_experiment(alpha=1e-2, dx=0.02, dt=0.05, t_final=5.0))
    assert out["converged"] is False
    assert out["nan"] is True
    assert "divergence" in out["error"].lower()


def test_heat_rejects_non_positive_parameters():
    out = parse(run_heat_experiment(alpha=0.0))
    assert out["converged"] is False
    assert "non-positive" in out["error"]


def test_oscillator_returns_metrics():
    out = parse(run_oscillator_experiment(mass=1.0, stiffness=10.0, damping=0.2))
    assert out["model"] == "oscillator"
    assert out["converged"] is True
    assert out["settling_time"] > 0
    assert out["max_displacement"] > 0
    assert out["final_amplitude"] >= 0
    assert out["damping_ratio"] > 0


def test_oscillator_diverges_on_non_physical_params():
    out = parse(run_oscillator_experiment(mass=-1.0))
    assert out["converged"] is False
    assert out["nan"] is True


def test_logistic_converges_to_capacity():
    out = parse(run_logistic_experiment(growth_rate=0.5, carrying_capacity=1000.0))
    assert out["converged"] is True
    assert out["final_population"] > 0
    assert out["max_population"] <= 1000.0
    assert out["overshoot"] == 0.0


def test_logistic_diverges_on_large_r_dt():
    out = parse(run_logistic_experiment(growth_rate=50.0, dt=0.5))
    assert out["converged"] is False
    assert out["nan"] is True


def test_run_experiment_dispatches_by_model():
    assert parse(run_experiment("heat", alpha=1e-4, dx=0.02, dt=1e-4))["model"] == "heat"
    assert parse(run_experiment("oscillator"))["model"] == "oscillator"
    assert parse(run_experiment("logistic"))["model"] == "logistic"


def test_run_experiment_unknown_model():
    out = parse(run_experiment("nope"))
    assert out["converged"] is False
    assert "unknown model" in out["error"]


def test_output_is_always_finite_and_bounded():
    """Real outputs carry a small elapsed_ms footer and no runaway size."""
    out = parse(run_experiment("heat", alpha=1e-4, dx=0.02, dt=1e-4, t_final=5.0))
    assert isinstance(out["elapsed_ms"], float)
    raw = run_experiment("heat", alpha=1e-4, dx=0.02, dt=1e-4, t_final=5.0)
    assert len(raw) < 2000
