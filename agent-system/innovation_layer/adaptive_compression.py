"""自适应多级上下文压缩调度（innovation_layer，创新点 5）。

复用 OpenHands 摘要相关函数思路（base_deps/summarize_conversation.py）；
增加调度层：根据任务类型、剩余 token 预算动态改变压缩强度，
不使用固定轮次强制摘要。

创新点：区别于 OpenHands 固定间隔摘要，根据当前任务负载动态调节压缩程度，
简单任务保留更多细节，复杂任务主动收紧上下文。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_system.core_models import RiskLevel

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class CompressionDecision:
    """一次压缩决策。"""

    should_compress: bool = False
    strength: float = 0.0            # 0..1 压缩强度
    target_tokens: int | None = None
    strategy: str = "none"           # none|summarize|truncate|full_rewrite
    reason: str = ""


class AdaptiveCompressionScheduler:
    """动态上下文压缩调度器。

    输入：
      - 当前消息 token 数（context_tokens）
      - 剩余 token 预算（budget_remaining = max - used）
      - 任务类型（task_type: simple|complex）
      - 无进展轮次（stall_rounds）
      - 风险等级
    输出：
      - 是否压缩 + 压缩强度 + 策略
    """

    # 预算占比阈值：上下文占用预算越高，压缩越强
    BUDGET_RATIO_LOW = 0.5
    BUDGET_RATIO_HIGH = 0.75

    def __init__(self, summarize_fn: Callable[[list[dict[str, Any]], dict[str, Any]], str] | None = None) -> None:
        self.summarize_fn = summarize_fn

    def decide(
        self,
        context_tokens: int,
        max_tokens: int,
        task_type: str = "general",      # simple|general|complex
        stall_rounds: int = 0,
        risk_level: RiskLevel = RiskLevel.LOW,
        round_number: int = 0,
    ) -> CompressionDecision:
        """根据任务负载动态决定压缩强度（创新点 5）。"""
        if max_tokens <= 0:
            return CompressionDecision(should_compress=False)

        ratio = context_tokens / max_tokens

        # 简单任务：保留更多细节，高水位才压缩
        if task_type == "simple":
            if ratio < self.BUDGET_RATIO_HIGH:
                return CompressionDecision(should_compress=False,
                                           reason=f"simple 任务 ratio={ratio:.2f} 低于高水位，保留细节")
            strength = 0.4
            strategy = "summarize"
            reason = f"simple 任务触顶 ratio={ratio:.2f}，轻度摘要"
        # 复杂任务：主动收紧
        elif task_type == "complex":
            if ratio < self.BUDGET_RATIO_LOW:
                return CompressionDecision(should_compress=False,
                                           reason=f"complex 任务 ratio={ratio:.2f} 仍充裕")
            strength = 0.7 if ratio < self.BUDGET_RATIO_HIGH else 0.9
            strategy = "full_rewrite" if ratio >= self.BUDGET_RATIO_HIGH else "summarize"
            reason = f"complex 任务 ratio={ratio:.2f}，收紧上下文"
        else:
            # 通用：渐进
            if ratio < self.BUDGET_RATIO_LOW:
                return CompressionDecision(should_compress=False,
                                           reason=f"general 任务 ratio={ratio:.2f} 低于低水位")
            strength = 0.5 if ratio < self.BUDGET_RATIO_HIGH else 0.8
            strategy = "summarize" if ratio < self.BUDGET_RATIO_HIGH else "full_rewrite"
            reason = f"general 任务 ratio={ratio:.2f}，{strategy}"

        # 叠加：连续无进展/高风险 → 提高强度
        if stall_rounds >= 2:
            strength = min(1.0, strength + 0.1)
            reason += f"，连续 {stall_rounds} 轮无进展"
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            strength = min(1.0, strength + 0.05)
            reason += f"，风险 {risk_level.value}"

        target_tokens = int(max_tokens * (1 - strength)) if max_tokens else None
        return CompressionDecision(
            should_compress=True,
            strength=round(strength, 2),
            target_tokens=target_tokens,
            strategy=strategy,
            reason=reason,
        )

    # ---- 与现有 compressor 对接 ----

    async def compress_messages(self, messages: list[dict[str, Any]], decision: CompressionDecision,
                                summarize_fn: Callable | None = None) -> list[dict[str, Any]]:
        """执行压缩（复用注入的摘要函数）。"""
        if not decision.should_compress:
            return messages
        fn = summarize_fn or self.summarize_fn
        if fn is None:
            # 无摘要函数：退化为截断早期消息（保留最近窗口）
            keep = max(2, int(len(messages) * (1 - decision.strength)))
            return messages[-keep:]
        # 保留 system 首条 + 最近消息，中间摘要
        system = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        if len(non_system) <= 4:
            return messages
        head = non_system[:2]
        tail = non_system[-4:]
        middle = non_system[2:-4]
        summary = fn(middle, {"strength": decision.strength, "task_type": "compression"})
        if isinstance(summary, str):
            summary = [{"role": "system", "content": f"[上下文摘要] {summary}"}]
        return [*system, *head, *summary, *tail]

    def estimate_saved_tokens(self, messages: list[dict[str, Any]], decision: CompressionDecision) -> int:
        """估算压缩节省的 token（评估报告用）。"""
        if not decision.should_compress:
            return 0
        return int(len(messages) * decision.strength * 20)  # 粗估 20 tok/条
