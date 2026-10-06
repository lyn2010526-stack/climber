"""三态运行控制器（innovation_layer，创新点 3）。

全自动 / 观察复盘 / 人机接力三态。其中人机接力模式是本系统的
**自动触发暂停**（区别于手动 stop/continue）：

  - 出现高风险操作
  - 出现多条可选方案
  - 连续多次失败
  满足任意一项 → 保存里程碑快照，暂停循环，输出当前进度、候选方案、
  风险清单、快照集合。使用者选择继续运行 / 修改规划 / 回滚快照 /
  补充知识库后恢复。

创新点：现有 Agent 要么一口气跑完，要么需要用户手动输入指令暂停；
本系统自动识别风险、多分支、反复失败场景主动停下来交回控制权。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from agent_system.core_models import (
    LoopDecision,
    RiskLevel,
    RunMode,
    TAORPhase,
    ToolClass,
    ToolDescriptor,
)


@dataclass
class YieldContext:
    """人机接力暂停时输出的上下文。"""

    current_progress: str = ""
    candidates: list[str] = field(default_factory=list)   # 候选方案
    risks: list[dict[str, Any]] = field(default_factory=list)  # 风险清单
    snapshot_ids: list[str] = field(default_factory=list)  # 快照集合
    yield_reason: str = ""
    pending_tasks: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)


@dataclass
class PauseDecision:
    """是否应该暂停（人机接力）的决策结果。"""

    should_pause: bool = False
    reason: str = ""
    candidates: list[str] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)


class RiskPolicy:
    """风险判定策略。"""

    HIGH_RISK_CLASSES: ClassVar[set[ToolClass]] = {ToolClass.WRITE, ToolClass.EXEC, ToolClass.NETWORK}
    HIGH_RISK_TOOLS: ClassVar[frozenset[str]] = frozenset({
        "bash", "shell", "exec", "run_command", "delete_file", "rm", "git_push",
        "deploy", "upload", "write_file", "create_file", "edit_file", "install_package",
    })

    def assess_tool(self, tool: ToolDescriptor | str) -> RiskLevel:
        name = tool.name if isinstance(tool, ToolDescriptor) else tool
        if name in self.HIGH_RISK_TOOLS:
            return RiskLevel.HIGH
        if isinstance(tool, ToolDescriptor) and tool.tool_class in self.HIGH_RISK_CLASSES:
            return RiskLevel.HIGH
        return RiskLevel.LOW


class ThreeStateController:
    """三态运行控制器。

    - AUTO：持续跑，直到结束或终止条件
    - OBSERVE：禁用全部写/改/执行/网络工具，只允许读
    - HITL：每轮评估，命中暂停条件则 YIELD
    """

    def __init__(self, mode: RunMode = RunMode.AUTO, risk_policy: RiskPolicy | None = None) -> None:
        self.mode = mode
        self.risk_policy = risk_policy or RiskPolicy()
        self.consecutive_failures = 0
        self.max_failures_before_yield = 2  # 连续失败阈值
        self.risk_threshold = RiskLevel.HIGH

    def set_mode(self, mode: RunMode) -> None:
        self.mode = mode

    def allow_tool(self, tool: ToolDescriptor | str) -> tuple[bool, str | None]:
        """三态控制器的工具权限过滤。

        OBSERVE 模式：只允许 READ/MEMORY 类。
        传入字符串时按名称命中高风险清单即拦截；传入描述符时按类拦截。
        返回 (allowed, reason)。
        """
        if self.mode != RunMode.OBSERVE:
            return True, None
        name = tool.name if isinstance(tool, ToolDescriptor) else tool
        if isinstance(tool, ToolDescriptor):
            cls = tool.tool_class
        else:
            # 无描述符时：高风险工具名按 WRITE/EXEC/NETWORK 处理
            cls = ToolClass.WRITE if name in self.risk_policy.HIGH_RISK_TOOLS else ToolClass.READ
        if cls in (ToolClass.READ, ToolClass.MEMORY, ToolClass.CONTROL):
            return True, None
        return False, f"观察复盘模式禁用 {name}（{cls.value} 类工具）"

    def register_failure(self) -> None:
        self.consecutive_failures += 1

    def register_success(self) -> None:
        self.consecutive_failures = 0

    # ---- 人机接力自动暂停评估 ----

    def evaluate_pause(self, *, risk_level: RiskLevel = RiskLevel.LOW,
                       candidates: list[str] | None = None,
                       tool_class: ToolClass | None = None,
                       tool_name: str | None = None) -> PauseDecision:
        """每轮自动评估是否触发人机接力暂停（创新点 3 核心）。"""
        if self.mode != RunMode.HITL:
            return PauseDecision(should_pause=False)

        risks: list[dict[str, Any]] = []

        # 条件 1：高风险操作
        if risk_level.value in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}:
            risks.append({"type": "high_risk_operation", "detail": f"风险等级 {risk_level.value}"})
        if tool_class and self.risk_policy.HIGH_RISK_CLASSES.intersection({tool_class}):
            risks.append({"type": "high_risk_operation", "detail": f"高风险工具类 {tool_class.value}"})
        if tool_name and tool_name in self.risk_policy.HIGH_RISK_TOOLS:
            risks.append({"type": "high_risk_operation", "detail": f"高风险工具 {tool_name}"})

        # 条件 2：多条可选方案
        cands = candidates or []
        if len(cands) >= 2:
            risks.append({"type": "multiple_candidates", "detail": f"{len(cands)} 条候选方案", "candidates": cands})

        # 条件 3：连续多次失败
        if self.consecutive_failures >= self.max_failures_before_yield:
            risks.append({"type": "repeated_failures",
                          "detail": f"连续 {self.consecutive_failures} 次失败"})

        if not risks:
            return PauseDecision(should_pause=False)

        return PauseDecision(
            should_pause=True,
            reason="; ".join(r["detail"] for r in risks),
            candidates=cands,
            risks=risks,
        )

    def yield_context(self, *, report: Any = None, candidates: list[str] | None = None,
                      risks: list[dict[str, Any]] | None = None,
                      snapshot_ids: list[str] | None = None,
                      reason: str = "") -> YieldContext:
        """构造人机接力暂停输出（进度 + 候选 + 风险 + 快照集合）。"""
        return YieldContext(
            current_progress=report.progress if report else "",
            candidates=candidates or [],
            risks=risks or [],
            snapshot_ids=snapshot_ids or [],
            yield_reason=reason,
            pending_tasks=list(getattr(report, "pending_tasks", []) or []),
            completed_tasks=list(getattr(report, "completed_tasks", []) or []),
        )


def make_decision(phase: TAORPhase, *, done: bool = False, rollback: bool = False,
                  yield_control: bool = False, reason: str = "",
                  risk_level: RiskLevel = RiskLevel.LOW) -> LoopDecision:
    """TAOR 状态分支判断的快捷构造。"""
    if done:
        next_phase = TAORPhase.DONE
    elif rollback:
        next_phase = TAORPhase.ROLLBACK
    elif yield_control:
        next_phase = TAORPhase.YIELD
    else:
        next_phase = phase  # LOOP：继续下一轮（从 THINK 或 PLAN）
    return LoopDecision(next_phase=next_phase, done=done, rollback=rollback,
                        yield_control=yield_control, reason=reason, risk_level=risk_level)
