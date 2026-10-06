"""确定性 demo 夹具（SDK / CLI / API 共用离线运行路径）。

在不接真实 LLM 凭据时，用脚本化 mock 跑通整条 TAOR 链路。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_system.core_models import ToolCall, ToolClass, ToolDescriptor, ToolResult

DEMO_TOOLS = [
    ToolDescriptor(name="query_db", description="只读查询数据库", tool_class=ToolClass.READ, read_only=True),
    ToolDescriptor(name="analyze", description="对查询结果做统计分析", tool_class=ToolClass.READ, read_only=True),
    ToolDescriptor(name="write_file", description="写入报告文件", tool_class=ToolClass.WRITE),
]


@dataclass
class FakeChatResult:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0


def deterministic_llm():
    """脚本化 mock：第 1 轮 query_db，第 2 轮 analyze，第 3 轮总结。"""
    counter = {"n": 0}

    async def llm_call(_messages, _tools):
        counter["n"] += 1
        n = counter["n"]
        if n == 1:
            return FakeChatResult(content="先查询数据库", tool_calls=[
                {"id": "tc_1", "type": "function",
                 "function": {"name": "query_db",
                              "arguments": {"sql": "SELECT * FROM orders"}}}])
        if n == 2:
            return FakeChatResult(content="对结果做部门汇总", tool_calls=[
                {"id": "tc_2", "type": "function",
                 "function": {"name": "analyze",
                              "arguments": {"field": "department"}}}])
        return FakeChatResult(content="已完成数据分析，共 3 个部门 128 条记录，汇总结果见附件。")

    return llm_call


async def _query_db(call: ToolCall) -> ToolResult:
    return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                      content="[3 行] 华东:42, 华北:56, 华南:30", is_error=False)


async def _analyze(call: ToolCall) -> ToolResult:
    return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                      content="结果: 华东 42 / 华北 56 / 华南 30，华北占比最高，为当前重点部门",
                      is_error=False)


async def _write_file(call: ToolCall) -> ToolResult:
    return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                      content="报告已写入 report.md", is_error=False)


async def _execute(call: ToolCall) -> ToolResult:
    handlers = {"query_db": _query_db, "analyze": _analyze, "write_file": _write_file}
    handler = handlers.get(call.name)
    if handler is None:
        return ToolResult(tool_call_id=call.tool_call_id, name=call.name,
                          content=None, is_error=True, error=f"未知工具 {call.name}")
    return await handler(call)


DEMO_TOOL_EXECUTOR = _execute
