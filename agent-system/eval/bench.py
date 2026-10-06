"""TAOR 引擎评测脚本：确定性场景基准 + 任务报告 + 记忆审计 + 基线对照。

用法（Climber 仓库根目录，离线可复现）：

    python3 agent-system/eval/bench.py [--out DIR] [--only linear_complete,hitl_yield]

产出：
  - `<out>/manifest.json`  每次场景的完整指标（TaskReport/记忆审计/快照/事件）
  - `<out>/report.md`      对照原版 claw-code 与原版 Hermes-Agent 的评测报告
  - 控制台：每场景 PASS/FAIL 汇总

场景均使用确定性 mock（不依赖 LLM 凭据），可直接跑通全链路。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_bootstrap  # noqa: F401
from agent_system import demo
from agent_system.core_models import RunMode, TAORPhase, ToolCall, ToolResult
from agent_system.eval import baseline
from agent_system.sdk import TAORClient, TAORConfig


def _llm_plan(*steps):
    """按步骤返回的工具调用脚本：None 表示本轮输出总结。"""
    counter = {"n": 0}

    async def llm_call(_messages, _tools):
        counter["n"] += 1
        step = steps[min(counter["n"] - 1, len(steps) - 1)]
        if step is None:
            return demo.FakeChatResult(content="任务完成，输出最终总结。")
        if isinstance(step, tuple):
            step = [step]
        calls = [{
            "id": f"tc_{counter['n']}_{i}",
            "type": "function",
            "function": {"name": name, "arguments": args},
        } for i, (name, args) in enumerate(step)]
        return demo.FakeChatResult(content="执行工具调用", tool_calls=calls)

    return llm_call


def _llm_always_tool(name: str, args: dict):
    return _llm_plan([(name, args)])


def _ok_tool_executor(executed: list[str]):
    async def exec_tool(call: ToolCall) -> ToolResult:
        executed.append(call.name)
        return demo.DEMO_TOOL_EXECUTOR(call)

    return exec_tool


def _fail_tool_executor(call: ToolCall) -> ToolResult:
    return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                      content=None, is_error=True, error="boom")


SCENARIOS = {
    "linear_complete": {
        "objective": "查询数据库并按部门汇总生成报告",
        "mode": RunMode.AUTO,
        "llm": _llm_plan(("query_db", {"sql": "SELECT * FROM orders"}),
                         ("analyze", {"field": "department"}),
                         None),
        "expect": {"status": "completed", "tool_calls_min": 2, "audits_min": 1,
                   "snapshots_min": 2, "rollbacks": 0},
        "note": "线性任务：2 次工具调用后输出总结 → DONE",
    },
    "hitl_yield": {
        "objective": "把配置写入 x.py 后总结",
        "mode": RunMode.HITL,
        "llm": _llm_always_tool("write_file", {"path": "x.py"}),
        "expect": {"status": "yielded", "milestones_min": 1},
        "note": "HITL 模式：写工具触发人机接力暂停（YIELD）+ 里程碑快照",
    },
    "observe_block": {
        "objective": "检查配置（写工具应被拦截）",
        "mode": RunMode.OBSERVE,
        "llm": _llm_always_tool("write_file", {"path": "x.py"}),
        "spy_executor": True,
        "expect": {"executed": 0, "no_execute": True},
        "note": "OBSERVE 模式：写工具被三态控制器拦截，不真正执行",
    },
    "stall_rollback": {
        "objective": "写入后总结（工具持续报错）",
        "mode": RunMode.AUTO,
        "llm": _llm_always_tool("write_file", {"path": "x.py"}),
        "fail_executor": True,
        "pre_seed_milestone": True,
        "expect": {"rollbacks_min": 1},
        "note": "连续无进展 → ROLLBACK 到最近里程碑",
    },
    "long_milestones": {
        "objective": "分五步完成数据分析并汇报",
        "mode": RunMode.AUTO,
        "llm": _llm_plan(("query_db", {"sql": "s1"}), ("query_db", {"sql": "s2"}),
                         ("analyze", {"field": "a"}), ("analyze", {"field": "b"}),
                         ("write_file", {"path": "r.md"}), None),
        "expect": {"status": "completed", "tool_calls_min": 4,
                   "snapshots_min": 5, "audits_min": 1},
        "note": "长任务：多轮工具调用 + 每轮增量快照 + 中途后台精炼",
    },
}


def run_scenario(name: str, spec: dict) -> dict:
    import tempfile

    started = time.monotonic()
    workdir = os.path.join(tempfile.gettempdir(), "taor_eval")
    os.makedirs(workdir, exist_ok=True)
    cfg = TAORConfig(data_dir=os.path.join(workdir, f"eval_{name}"),
                     mode=spec["mode"], max_outer_rounds=8, max_stall_rounds=2,
                     memory_refine_every=2)
    client = TAORClient(cfg)

    if spec.get("pre_seed_milestone"):
        client.snapshot_manager.save_milestone(
            "eval-session", TAORPhase.PLAN, state={"step": 0}, messages=[], label="plan")

    executed: list[str] = []
    execute = demo.DEMO_TOOL_EXECUTOR
    if spec.get("fail_executor"):
        execute = _fail_tool_executor
    elif spec.get("spy_executor"):
        execute = _ok_tool_executor(executed)

    handle = client.run(spec["objective"], mode=spec["mode"], session_id="eval-session",
                        llm_call=spec["llm"], tool_executor=execute, tools=demo.DEMO_TOOLS)

    report = handle.report
    snapshots = handle.snapshots
    audits = handle.audits
    duration_ms = (time.monotonic() - started) * 1000

    kinds = {}
    for s in snapshots:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1

    metrics = {
        "scenario": name,
        "objective": spec["objective"],
        "status": report.status,
        "outer_rounds": report.outer_rounds,
        "inner_turns": report.inner_turns,
        "tool_calls": report.tool_calls,
        "retries": report.retries,
        "rollbacks": report.rollbacks,
        "audits": len(audits),
        "audit_actions": [a.action for a in audits],
        "snapshot_kinds": kinds,
        "executed": executed,
        "duration_ms": round(duration_ms, 1),
        "events": len(handle.events),
        "report": handle.as_dict(),
        "note": spec["note"],
    }
    metrics["pass"] = _check(metrics, spec["expect"])
    metrics["fail_reasons"] = _fail_reasons(metrics, spec["expect"])
    return metrics


def _check(metrics: dict, expect: dict) -> bool:
    return not _fail_reasons(metrics, expect)


def _fail_reasons(metrics: dict, expect: dict) -> list[str]:
    reasons: list[str] = []
    if "status" in expect and metrics["status"] != expect["status"]:
        reasons.append(f"status={metrics['status']} != {expect['status']}")
    if "tool_calls_min" in expect and metrics["tool_calls"] < expect["tool_calls_min"]:
        reasons.append(f"tool_calls={metrics['tool_calls']} < {expect['tool_calls_min']}")
    if "audits_min" in expect and metrics["audits"] < expect["audits_min"]:
        reasons.append(f"audits={metrics['audits']} < {expect['audits_min']}")
    if "snapshots_min" in expect and sum(metrics["snapshot_kinds"].values()) < expect["snapshots_min"]:
        reasons.append(f"snapshots={sum(metrics['snapshot_kinds'].values())} < {expect['snapshots_min']}")
    if "milestones_min" in expect and metrics["snapshot_kinds"].get("milestone", 0) < expect["milestones_min"]:
        reasons.append(f"milestones={metrics['snapshot_kinds'].get('milestone', 0)} < {expect['milestones_min']}")
    if "rollbacks" in expect and metrics["rollbacks"] != expect["rollbacks"]:
        reasons.append(f"rollbacks={metrics['rollbacks']} != {expect['rollbacks']}")
    if "rollbacks_min" in expect and metrics["rollbacks"] < expect["rollbacks_min"]:
        reasons.append(f"rollbacks={metrics['rollbacks']} < {expect['rollbacks_min']}")
    if "no_execute" in expect and metrics["executed"]:
        reasons.append(f"executed={metrics['executed']}（应被拦截）")
    return reasons


def build_report(results: dict[str, dict], _out_dir: str) -> str:
    lines = ["# TAOR 引擎评测报告", "", baseline.summary(), ""]
    lines.append("## 场景结果")
    lines.append("| 场景 | 状态 | rounds | tools | retries | rollbacks | audits | 快照 | 结果 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for name, m in results.items():
        marks = " ".join(f"{k}:{v}" for k, v in m["snapshot_kinds"].items())
        lines.append(f"| {name} | {m['status']} | {m['outer_rounds']} | {m['tool_calls']} "
                     f"| {m['retries']} | {m['rollbacks']} | {m['audits']} | {marks} | "
                     f"{'PASS' if m['pass'] else 'FAIL'} |")
    lines.append("")
    lines.append("## 任务报告摘要")
    for name, m in results.items():
        rep = m["report"]["report"]
        lines.append(f"- `{name}` status={rep['status']} outer_rounds={rep['outer_rounds']} "
                     f"inner_turns={rep['inner_turns']} completed_tasks={len(rep.get('completed_tasks', []))}")
    lines.append("")
    lines.append("## 记忆审计摘要")
    for name, m in results.items():
        lines.append(f"- `{name}` 审计 {m['audits']} 条：" + ", ".join(m["audit_actions"]))
    lines.append("")
    lines.append("## 基线对照说明")
    lines.append("本引擎（TAOR）在同等确定性场景下的实测指标见上表；对照列为参考特征（见 `baseline.py`），")
    lines.append("差异点集中在：本引擎具备『连续无进展→回滚里程碑』守卫、双层快照、后台记忆精炼。")
    return "\n".join(lines)


def main(args: argparse.Namespace) -> int:
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                                       time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)

    names = args.only.split(",") if args.only else sorted(SCENARIOS)
    results: dict[str, dict] = {}
    failed = 0
    for name in names:
        if name not in SCENARIOS:
            print(f"[skip] 未知场景 {name}")
            continue
        m = run_scenario(name, SCENARIOS[name])
        results[name] = m
        tag = "PASS" if m["pass"] else "FAIL"
        if not m["pass"]:
            failed += 1
        print(f"[{tag}] {name:<18} status={m['status']:<10} rounds={m['outer_rounds']} "
              f"tools={m['tool_calls']} audits={m['audits']} ms={m['duration_ms']}")
        if m["fail_reasons"]:
            for r in m["fail_reasons"]:
                print(f"      ! {r}")

    manifest = {name: m for name, m in results.items() if not name.startswith("_")}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, default=str)
    report = build_report(manifest, out_dir)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n汇总: {len(results) - failed}/{len(results)} PASS")
    print(f"产出目录: {out_dir}")

    # JSON 机器模式：输出完整 manifest
    if args.json:
        print("\n== manifest.json ==")
        print(json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
    return 0 if failed == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TAOR 引擎确定性评测")
    p.add_argument("--out", default="", help="结果输出目录（缺省自动生成时间戳目录）")
    p.add_argument("--only", default="", help="逗号分隔的场景子集")
    p.add_argument("--json", action="store_true", help="额外输出完整 manifest")
    return p


if __name__ == "__main__":
    raise SystemExit(main(build_parser().parse_args()))
