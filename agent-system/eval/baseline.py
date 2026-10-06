"""评测基线描述：原版 claw-code 与原版 Hermes-Agent 的循环特性常量。

对比基线的取值来源：
  - claw-code：取自本地参考仓库 `/tmp/opencode/cc-haha/src/QueryEngine.ts`
    （主查询循环 `maxTurns` / `maxBudgetUsd` 上限、结构化输出重试
     `MAX_STRUCTURED_OUTPUT_RETRIES=5`、工具结果回写 transcript 后继续循环）。
  - Hermes-Agent：取自参考上游描述（planner/sub-agents/executor 三层拆解、
    工具调用循环、向量记忆 recall），本环境未落地其代码，取值按文档化特征记录，
    标注为参考描述而非实测。

用法：`baseline.describe("claw-code")` / `baseline.describe("hermes-agent")`，
评测报告据此输出「参考对照」列。

重要：Hermes-Agent 为文档化参考，测量列见 `run`（本引擎实测）；对照列仅用于
说明基线循环在同等场景下的预期特征，不做数值等价断言。
"""

from __future__ import annotations

from dataclasses import dataclass

BASELINE_CLAW_CODE = {
    "name": "claw-code",
    "loop_model": "外层 while(工具结果回写) + maxTurns/maxBudgetUsd 上限；单内层工具循环",
    "max_turns": "外部配置（未豁免即视为无限，预算保护）",
    "max_retries_structured_output": 5,
    "memory": "对话附带（sessionMessage + attachment），无独立长期记忆库",
    "persist": "transcript/快照同程记录，无回滚到里程碑语义",
    "stall_guard": "无（依赖 maxTurns/maxBudget 兜底）",
}

BASELINE_HERMES_AGENT = {
    "name": "hermes-agent",
    "loop_model": "planner(分拆子任务) → 子 agents 执行 → 结果回写；任务级递归",
    "tool_loop": "工具调用循环后评估是否继续/终止",
    "memory": "向量 / 关系记忆召回辅助规划",
    "persist": "无双层快照与里程碑回滚语义",
    "stall_guard": "高层决策兜底（无外轮连续无进展检测）",
}


@dataclass(frozen=True)
class LoopCharacteristic:
    """单条参考特征，用于报告对照列。"""

    key: str
    claw_code: str
    hermes_agent: str


def characteristics() -> list[LoopCharacteristic]:
    """逐维度基线对照（不同循环体系的区别点）。"""
    return [
        LoopCharacteristic("循环上限", "maxTurns/maxBudgetUsd 外部预算", "planner 递归任务数上限"),
        LoopCharacteristic("工具循环", "同程 while（结果回写后继续）", "工具调用循环 + 评估"),
        LoopCharacteristic("无进展守卫", "依赖预算兜底", "高层决策兜底"),
        LoopCharacteristic("记忆持久化", "transcript 附带", "向量/关系记忆召回"),
        LoopCharacteristic("回滚语义", "无里程碑回滚", "无里程碑回滚"),
        LoopCharacteristic("结构化输出重试", "≤5 次（MAX_STRUCTURED_OUTPUT_RETRIES）", "未固定"),
    ]


def describe(name: str) -> dict:
    if name == "claw-code":
        return dict(BASELINE_CLAW_CODE)
    if name == "hermes-agent":
        return dict(BASELINE_HERMES_AGENT)
    raise ValueError(f"未知基线: {name}")


def summary() -> str:
    """Markdown 块：基线对照表。"""
    rows = ["| 维度 | 原版 claw-code | 原版 Hermes-Agent | 本引擎(TAOR) |", "|---|---|---|---|"]
    rows.extend(
        f"| {c.key} | {c.claw_code} | {c.hermes_agent} | 见 run 度量 |" for c in characteristics()
    )
    return "\n".join(rows)
