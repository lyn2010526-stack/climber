"""TAOR 主循环引擎端到端确定性测试（不依赖真实 LLM/DB）。

用 mock LLM 驱动引擎跑完整流程：
  1. AUTO 模式：工具调用轮 → 总结轮 → DONE，验证外层循环终止、报告、快照、事件
  2. HITL 模式：高风险写工具触发人机接力暂停（YIELD），验证里程碑快照与状态
  3. 观察复盘 OBSERVE 模式：写工具被拦截，验证三态控制器权限过滤
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest
from agent_system.base_deps.mem_fts5_sqlite import Fts5Store
from agent_system.core_models import (
    RunMode,
    SystemEventType,
    TAORPhase,
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


@dataclass
class FakeChatResult:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    finish_reason: str | None = None


def make_tool_call(name: str, args: dict[str, Any], tc_id: str = "tc_1") -> dict[str, Any]:
    return {
        "id": tc_id,
        "type": "function",
        "function": {"name": name, "arguments": args},
    }


async def fake_tool_executor(call: ToolCall) -> ToolResult:
    if call.name == "query_db":
        return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                          content="mock 查询结果: 找到 3 条记录", is_error=False)
    if call.name == "write_file":
        return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                          content="file written", is_error=False)
    return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                      content=None, is_error=True, error="unknown tool")


def make_tools() -> list[ToolDescriptor]:
    return [
        ToolDescriptor(name="query_db", description="只读查询数据库", tool_class=ToolClass.READ, read_only=True),
        ToolDescriptor(name="write_file", description="写入文件", tool_class=ToolClass.WRITE),
    ]


def make_components(tmpdir: str):
    fts = Fts5Store(os.path.join(tmpdir, "mem.db"))
    router = AdaptiveRetrievalRouter(fts_store=fts)
    snapshot_mgr = SnapshotManager(os.path.join(tmpdir, "snap.db"))
    refiner = BackgroundMemoryRefiner(store=fts)
    compressor = AdaptiveCompressionScheduler()
    return fts, router, snapshot_mgr, refiner, compressor


@pytest.mark.asyncio
async def test_auto_mode_tool_then_done(tmp_path):
    """AUTO 模式：mock LLM 第一轮调用工具，第二轮输出总结 → DONE。"""
    _fts, router, snapshot_mgr, refiner, compressor = make_components(str(tmp_path))
    calls = []
    events: list[tuple[SystemEventType, dict[str, Any]]] = []

    async def mock_llm(messages, tools):
        calls.append(len(messages))
        # 第 1 轮：调用 query_db；之后：输出最终总结
        if len(messages) <= 2:
            return FakeChatResult(content="先查询数据库", tool_calls=[make_tool_call("query_db", {"sql": "SELECT 1"})])
        return FakeChatResult(content="任务完成总结: 已查出 3 条记录并完成分析。")

    async def emit(event_type, data):
        events.append((event_type, data))

    engine = TAOREngine(
        llm_call=mock_llm,
        tool_executor=fake_tool_executor,
        router=router,
        snapshot_mgr=snapshot_mgr,
        refiner=refiner,
        compressor=compressor,
        tool_descriptors=make_tools(),
        emit=emit,
        options=TAOROptions(max_outer_rounds=5, max_stall_rounds=2),
    )

    report = await engine.run("test-session", "查询数据库并分析")

    assert report.status == "completed"
    assert report.tool_calls == 1
    assert report.outer_rounds >= 2
    assert report.inner_turns >= 2
    assert "完成总结" in report.result_summary
    assert report.completed_tasks
    # 快照已保存（每轮增量）
    assert snapshot_mgr.count("test-session") == report.outer_rounds
    # 事件流包含关键阶段
    event_types = {e for e, _ in events}
    assert SystemEventType.PHASE_CHANGED in event_types
    assert SystemEventType.TOOL_CALL in event_types
    assert SystemEventType.TOOL_RESULT in event_types
    assert SystemEventType.OBSERVATION in event_types
    assert SystemEventType.DONE in event_types
    # 后台精炼已启动并完成（收尾触发），产出审计日志
    await refiner.wait_all()
    assert refiner.last_results()
    # LLM 收到完整上下文（system + 历史 assistant/tool 消息）
    assert len(calls) >= 2


@pytest.mark.asyncio
async def test_hitl_yield_on_high_risk_tool(tmp_path):
    """HITL 模式：每次调用写文件工具 → 触发人机接力暂停（YIELD）+ 里程碑快照。"""
    _fts, router, snapshot_mgr, _refiner, _compressor = make_components(str(tmp_path))

    async def mock_llm(messages, tools):
        return FakeChatResult(content="写入配置", tool_calls=[make_tool_call("write_file", {"path": "x.py"})])

    controller = ThreeStateController(mode=RunMode.HITL)

    engine = TAOREngine(
        llm_call=mock_llm,
        tool_executor=fake_tool_executor,
        router=router,
        snapshot_mgr=snapshot_mgr,
        controller=controller,
        tool_descriptors=make_tools(),
        options=TAOROptions(max_outer_rounds=4),
    )

    report = await engine.run("hitl-session", "写配置文件")

    assert report.status == "yielded"
    # 里程碑快照在 YIELD 时保存
    milestones = snapshot_mgr.list_snapshots("hitl-session")
    assert any(s["kind"] == "milestone" for s in milestones)


@pytest.mark.asyncio
async def test_observe_mode_blocks_write_tools(tmp_path):
    """OBSERVE 模式：写工具被三态控制器拦截，返回错误结果而不执行。"""
    _fts, router, snapshot_mgr, _refiner, _compressor = make_components(str(tmp_path))
    executed: list[str] = []

    async def mock_llm(messages, tools):
        return FakeChatResult(content="写入文件", tool_calls=[make_tool_call("write_file", {"path": "x.py"})])

    async def spy_tool_executor(call: ToolCall) -> ToolResult:
        executed.append(call.name)
        return await fake_tool_executor(call)

    controller = ThreeStateController(mode=RunMode.OBSERVE)
    engine = TAOREngine(
        llm_call=mock_llm,
        tool_executor=spy_tool_executor,
        router=router,
        snapshot_mgr=snapshot_mgr,
        controller=controller,
        tool_descriptors=make_tools(),
        options=TAOROptions(max_outer_rounds=3, max_stall_rounds=1),
    )

    await engine.run("observe-session", "检查配置")

    # 写工具未真正执行（被拦截为错误结果）
    assert executed == []


@pytest.mark.asyncio
async def test_rollback_on_stall_after_milestone(tmp_path):
    """连续无进展（工具报错且无输出）→ 触发 ROLLBACK 分支，回滚到最近里程碑。"""
    _fts, router, snapshot_mgr, _refiner, _compressor = make_components(str(tmp_path))

    async def fail_executor(call: ToolCall) -> ToolResult:
        return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                          content=None, is_error=True, error="boom")

    async def mock_llm(messages, tools):
        # 每次都要工具调用且都失败 → 连续无进展
        return FakeChatResult(content="重试写入", tool_calls=[make_tool_call("write_file", {"path": "x.py"})])

    # 先存一个里程碑快照作为回滚点
    snapshot_mgr.save_milestone("stall-session", TAORPhase.PLAN, state={"step": 1}, messages=[], label="plan")

    engine = TAOREngine(
        llm_call=mock_llm,
        tool_executor=fail_executor,
        router=router,
        snapshot_mgr=snapshot_mgr,
        tool_descriptors=make_tools(),
        options=TAOROptions(max_outer_rounds=5, max_stall_rounds=1),
    )

    report = await engine.run("stall-session", "写文件")

    # 触发回滚（rollbacks > 0），并停在该会话（无有效恢复则终止）
    assert report.rollbacks >= 1
    assert snapshot_mgr.load_milestone("stall-session") is not None
