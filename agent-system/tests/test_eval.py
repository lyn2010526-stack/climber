"""评测脚本测试：对典型场景跑基准并断言全部通过（确定性 mock，离线）。"""

from __future__ import annotations

import agent_bootstrap  # noqa: F401
from agent_system.eval import bench


def test_eval_scenarios_all_pass() -> None:
    for name in ("linear_complete", "hitl_yield", "observe_block"):
        metrics = bench.run_scenario(name, bench.SCENARIOS[name])
        assert metrics["pass"], f"{name} 场景失败: {metrics['fail_reasons']}"


def test_eval_baseline_describe() -> None:
    for name in ("claw-code", "hermes-agent"):
        desc = bench.baseline.describe(name)
        assert desc["name"] == name
        assert "loop_model" in desc
