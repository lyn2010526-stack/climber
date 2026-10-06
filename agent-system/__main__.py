"""TAOR 智能体引擎 CLI（agent-system 可执行入口）。

在 Climber 仓库根目录运行：

    python3 -m agent_system.cli --objective "查询数据库并按部门汇总" --max-rounds 6

默认使用内置脚本化 mock LLM（确定性，可离线复现全链路）；接入真实模型时
用 `--llm-provider env` 并在环境变量提供凭据。输出包含：
  - 每轮主循环状态（进度/已完成/Follow-up 队列）
  - 最终任务报告（TaskReport）
  - 记忆审计日志（后台精炼产出）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import UTC

import agent_bootstrap  # noqa: F401
from agent_system.base_deps.mem_fts5_sqlite import Fts5Store
from agent_system.core_models import (
    RunMode,
    SystemEventType,
    ToolCall,
    ToolClass,
    ToolDescriptor,
    ToolResult,
)
from agent_system.innovation_layer.adaptive_compression import AdaptiveCompressionScheduler
from agent_system.innovation_layer.adaptive_retrieval import AdaptiveRetrievalRouter
from agent_system.innovation_layer.background_refine import BackgroundMemoryRefiner
from agent_system.innovation_layer.dual_snapshot import SnapshotManager
from agent_system.innovation_layer.taor_engine import TAOREngine, TAOROptions
from agent_system.innovation_layer.three_state_controller import ThreeStateController

TOOLS = [
    ToolDescriptor(
        name="query_db", description="只读查询数据库", tool_class=ToolClass.READ, read_only=True
    ),
    ToolDescriptor(
        name="analyze",
        description="对查询结果做统计分析",
        tool_class=ToolClass.READ,
        read_only=True,
    ),
    ToolDescriptor(name="write_file", description="写入报告文件", tool_class=ToolClass.WRITE),
]


@dataclass
class FakeChatResult:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0


def _now_str() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def scripted_llm_factory():
    """确定性 mock：第 1 轮调 query_db，第 2 轮调 analyze，第 3 轮总结。"""
    counter = {"n": 0}

    async def llm_call(_messages, _tools):
        counter["n"] += 1
        n = counter["n"]
        if n == 1:
            return FakeChatResult(
                content="先查询数据库",
                tool_calls=[
                    {
                        "id": "tc_1",
                        "type": "function",
                        "function": {
                            "name": "query_db",
                            "arguments": {"sql": "SELECT * FROM orders"},
                        },
                    }
                ],
            )
        if n == 2:
            return FakeChatResult(
                content="对结果做部门汇总",
                tool_calls=[
                    {
                        "id": "tc_2",
                        "type": "function",
                        "function": {"name": "analyze", "arguments": {"field": "department"}},
                    }
                ],
            )
        return FakeChatResult(content="已完成数据分析，共 3 个部门 128 条记录，汇总结果见附件。")

    return llm_call


async def query_db(call: ToolCall) -> ToolResult:
    return ToolResult(
        tool_call_id=call.tool_call_id,
        name=call.name,
        content="[3 行] 华东:42, 华北:56, 华南:30",
        is_error=False,
    )


async def analyze(call: ToolCall) -> ToolResult:
    return ToolResult(
        tool_call_id=call.tool_call_id,
        name=call.name,
        content="结果: 华东 42 / 华北 56 / 华南 30，华北占比最高，为当前重点部门",
        is_error=False,
    )


async def write_file(call: ToolCall) -> ToolResult:
    return ToolResult(
        tool_call_id=call.tool_call_id,
        name=call.name,
        content="报告已写入 report.md",
        is_error=False,
    )


async def tool_executor(call: ToolCall) -> ToolResult:
    handlers = {"query_db": query_db, "analyze": analyze, "write_file": write_file}
    handler = handlers.get(call.name)
    if handler is None:
        return ToolResult(
            tool_call_id=call.tool_call_id,
            name=call.name,
            content=None,
            is_error=True,
            error=f"未知工具 {call.name}",
        )
    return await handler(call)


async def main(args: argparse.Namespace) -> int:
    workdir = args.workdir or tempfile.mkdtemp(prefix="taor_")
    fts = Fts5Store(os.path.join(workdir, "memory.db"))
    snapshot_mgr = SnapshotManager(os.path.join(workdir, "snapshots.db"))
    refiner = BackgroundMemoryRefiner(store=fts)
    router = AdaptiveRetrievalRouter(fts_store=fts)
    compressor = AdaptiveCompressionScheduler()

    # 预置一条项目规则记忆（验证 SYSBOOT 检索）
    from agent_system.core_models import MemoryItem, MemoryKind

    fts.upsert(
        MemoryItem(
            kind=MemoryKind.RULE,
            text="报告需包含部门维度的汇总数字并标注占比最高的部门",
            title="报告规则",
            doc_type="rule",
            doc_length=30,
            trust_score=0.9,
        )
    )

    mode = RunMode(args.mode) if args.mode else RunMode.AUTO
    controller = ThreeStateController(mode=mode)
    llm = scripted_llm_factory()

    events: list[dict[str, Any]] = []

    async def emit(event_type, data):
        events.append({"event": event_type.value, "data": data})
        if not args.json and event_type in (
            SystemEventType.PHASE_CHANGED,
            SystemEventType.TOOL_CALL,
            SystemEventType.YIELD_PENDING,
            SystemEventType.DONE,
        ):
            _print_event(event_type, data)

    engine = TAOREngine(
        llm_call=llm,
        tool_executor=tool_executor,
        router=router,
        snapshot_mgr=snapshot_mgr,
        refiner=refiner,
        compressor=compressor,
        controller=controller,
        tool_descriptors=TOOLS,
        options=TAOROptions(max_outer_rounds=args.max_rounds, mode=mode),
        emit=emit,
    )

    if not args.json:
        print(f"[{_now_str()}] objective        : {args.objective}")
        print(f"[{_now_str()}] mode             : {mode.value}")
        print(f"[{_now_str()}] max_outer_rounds : {args.max_rounds}")
        print(f"[{_now_str()}] workdir          : {workdir}")
        print("-" * 72)

    report = await engine.run(args.session_id, args.objective, context={"max_tokens": 16000})

    # 等后台精炼收尾
    await refiner.wait_all()

    audits = _collect_audits(refiner)

    if args.json:
        out = {
            "objective": args.objective,
            "session_id": args.session_id,
            "report": _asdict_safe(report),
            "events": events,
            "audits": audits,
            "snapshots": snapshot_mgr.list_snapshots(args.session_id),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0 if report.status == "completed" else 2

    print("-" * 72)
    print("== 任务报告 (TaskReport) ==")
    _print_report(report)

    print("-" * 72)
    print("== 记忆审计日志 (MemoryAudit) ==")
    if audits:
        for entry in audits:
            print(
                f"  [{entry['action']}] mem={entry['memory_id'][-8:]:>8} "
                + f'text="{entry["text_preview"][:34]}" reason={entry["reason"]}'
            )
    else:
        print("  (本轮无审计记录会话日志，未触发抽取)")

    return 0 if report.status == "completed" else 2


def _print_event(event_type: SystemEventType, data: dict[str, Any]) -> None:
    if event_type == SystemEventType.PHASE_CHANGED:
        print(f"  -> PHASE {data.get('phase'):<9} (round={data.get('round', '-')})")
    elif event_type == SystemEventType.TOOL_CALL:
        print(
            f"  -> TOOL   {data.get('name')} args={json.dumps(data.get('arguments', {}), ensure_ascii=False)[:60]}"
        )
    elif event_type == SystemEventType.YIELD_PENDING:
        print(f"  -> YIELD  {data.get('reason')}")
    elif event_type == SystemEventType.DONE:
        print(f"  -> DONE   status={data.get('status')} rounds={data.get('rounds')}")


def _print_report(report) -> None:
    print(f"  task_id        : {report.task_id}")
    print(f"  status         : {report.status}")
    print(f"  outer_rounds   : {report.outer_rounds}")
    print(f"  inner_turns    : {report.inner_turns}")
    print(f"  tool_calls     : {report.tool_calls}")
    print(f"  retries        : {report.retries}")
    print(f"  rollbacks      : {report.rollbacks}")
    print(f"  completed      : {len(report.completed_tasks)} 项")
    for task in report.completed_tasks:
        print(f"    - {task}")
    if report.result_summary:
        print(f"  result_summary : {report.result_summary[:160]}")


def _collect_audits(refiner) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for result in refiner.last_results():
        out.extend(
            {
                "action": entry.action,
                "memory_id": entry.memory_id,
                "text_preview": entry.text_preview,
                "reason": entry.reason,
            }
            for entry in result.audits
        )
    return out


def _asdict_safe(obj):
    return asdict(obj)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TAOR 智能体主循环 CLI")
    parser.add_argument("--objective", default="查询数据库并按部门汇总生成报告", help="任务目标")
    parser.add_argument("--session-id", default="cli-session-1")
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--mode", choices=["auto", "observe", "hitl"], default=None)
    parser.add_argument("--workdir", default=None, help="数据目录（缺省用临时目录）")
    parser.add_argument("--llm-provider", choices=["scripted", "env"], default="scripted")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    sys.exit(asyncio.run(main(args)))
