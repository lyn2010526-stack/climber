"""ReasoningPipeline — 三维推理引擎核心数据模型与抽象基类。

- Tree of Thoughts (Princeton, NeurIPS 2023): 多路径探索 + 评估选择
- Self-Refine (Google, 2023): Init→Feedback→Iterate 垂直迭代
- Reflexion (MIT, NeurIPS 2023): 持久自省 + 跨轮次学习
- Constitutional AI (Anthropic, 2022): 原则驱动的覆盖率检查
- NeMo Guardrails (NVIDIA): 结构化验证 + 风险矩阵
- LangGraph (LangChain): 图式编排 + 状态管理
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ReasoningMode(StrEnum):
    """推理模式枚举。"""

    AUTO = "auto"
    TREE_OF_THOUGHT = "tree"
    DEEP_REFINE = "deep"
    DEBATE = "debate"


class IssueSeverity(StrEnum):
    """问题严重级别 — 与 review_models.py 的 ReviewIssueModel 一致。"""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class Issue(BaseModel):
    """单条批判发现的问题。"""

    severity: IssueSeverity
    description: str = Field(min_length=10, max_length=1000)
    location: str = Field(default="", max_length=200)
    fix_suggestion: str = Field(default="", max_length=1000)


class CritiqueResult(BaseModel):
    """批判结果 — 多维度评估。

    参考 Self-Refine 的多维度评分 (1-5 分制) 和
    ReviewOutputModel 的结构化输出。
    """

    passed: bool = False
    issues: list[Issue] = Field(default_factory=list)
    summary: str = Field(default="", max_length=500)
    scores: dict[str, float] = Field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)

    @property
    def major_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.MAJOR)

    @property
    def average_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)

    def to_feedback_string(self) -> str:
        """生成供 Worker 使用的反馈字符串。"""
        if self.passed or not self.issues:
            return ""
        lines: list[str] = []
        if self.summary:
            lines.append(f"Summary: {self.summary}")
        for i, issue in enumerate(self.issues, 1):
            lines.append(f"{i}. [{issue.severity.value.upper()}] {issue.description}")
            if issue.location:
                lines.append(f"   Location: {issue.location}")
            if issue.fix_suggestion:
                lines.append(f"   Fix: {issue.fix_suggestion}")
        return "\n".join(lines)


class Candidate(BaseModel):
    """推理候选 — 单条路径的最终输出。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    strategy: str = ""
    path_type: str = ""
    content: str = ""
    reasoning_chain: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    critique: CritiqueResult | None = None
    refined_from: str | None = None
    round_created: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EdgeCase(BaseModel):
    """边界情况 — 参考 NeMo Guardrails 的场景枚举。"""

    description: str
    category: str
    tested: bool = False
    result: str = ""


class Risk(BaseModel):
    """潜在风险 — 概率 × 影响矩阵。

    参考 NeMo Guardrails 的风险评估模型。
    """

    description: str
    probability: str = "low"
    impact: str = "low"
    mitigation: str = ""

    @property
    def risk_score(self) -> int:
        """风险分数 = probability × impact (1-9)。"""
        prob_map = {"low": 1, "medium": 2, "high": 3}
        imp_map = {"low": 1, "medium": 2, "high": 3}
        return prob_map.get(self.probability, 1) * imp_map.get(self.impact, 1)


class Assumption(BaseModel):
    """隐藏假设 — 显式化和验证。

    参考 Constitutional AI 的 "identify assumptions" 原则。
    """

    statement: str
    validated: bool = False
    evidence: str = ""
    risk_if_wrong: str = ""


class CoverageReport(BaseModel):
    """覆盖率报告 — 推理输出的全面验证。

    参考 Constitutional AI 原则驱动验证 +
    NeMo Guardrails 的结构化检查清单。
    """

    edge_cases: list[EdgeCase] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    score: float = 0.0
    checklist: dict[str, bool] = Field(default_factory=dict)

    @property
    def high_risks(self) -> list[Risk]:
        return [r for r in self.risks if r.risk_score >= 6]

    @property
    def unvalidated_assumptions(self) -> list[Assumption]:
        return [a for a in self.assumptions if not a.validated]

    def summary(self) -> str:
        parts = [f"Coverage: {self.score:.0%}"]
        if self.edge_cases:
            tested = sum(1 for e in self.edge_cases if e.tested)
            parts.append(f"Edge cases: {tested}/{len(self.edge_cases)} tested")
        if self.high_risks:
            parts.append(f"High risks: {len(self.high_risks)}")
        if self.blind_spots:
            parts.append(f"Blind spots: {len(self.blind_spots)}")
        return " | ".join(parts)


class ReasoningRequest(BaseModel):
    """推理请求。"""

    task: str = Field(..., min_length=1, max_length=10000)
    mode: ReasoningMode = ReasoningMode.AUTO
    max_paths: int = Field(default=3, ge=1, le=5)
    max_refine_rounds: int = Field(default=3, ge=1, le=5)
    coverage_enabled: bool = True
    context: dict[str, Any] = Field(default_factory=dict)
    model_override: str | None = None
    max_tokens: int = Field(default=8000, ge=100, le=128000)
    timeout_seconds: int = Field(default=120, ge=10, le=600)


class RoundTrace(BaseModel):
    """单轮推理轨迹。"""

    round_num: int
    action: str
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0


class PathTrace(BaseModel):
    """单条路径的完整轨迹。"""

    candidate_id: str
    path_type: str
    rounds: list[RoundTrace] = Field(default_factory=list)
    final_confidence: float = 0.0


class ReasoningTrace(BaseModel):
    """完整推理轨迹 — 可审计。"""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    request_task: str = ""
    strategy_selected: str = ""
    path_traces: list[PathTrace] = Field(default_factory=list)
    coverage_checks: list[dict[str, Any]] = Field(default_factory=list)
    final_selection_reason: str = ""
    total_duration_ms: float = 0.0
    created_at: float = Field(default_factory=time.time)


class ReasoningResult(BaseModel):
    """推理结果 — 最终输出。"""

    answer: str
    mode_used: ReasoningMode
    candidates: list[Candidate] = Field(default_factory=list)
    coverage: CoverageReport | None = None
    rounds: int = 0
    total_duration_ms: float = 0.0
    trace: ReasoningTrace | None = None
    total_tokens: int = 0
    estimated_cost: float = 0.0


class ReasoningFeedback(BaseModel):
    """推理质量反馈 — 用户对推理结果的评价。"""

    trace_id: str
    user_id: str
    rating: int = Field(ge=1, le=5, description="总体评分 1-5")
    thumbs: str | None = Field(default=None, description="up / down / None")
    comment: str = Field(default="", max_length=1000)
    selected_candidate_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class Strategy(Protocol):
    """策略协议 — 所有推理策略必须实现。"""

    name: str

    async def execute(
        self,
        request: ReasoningRequest,
        self_refine: Any,
        model_registry: Any,
    ) -> list[Candidate]:
        """执行推理，返回候选列表。"""
        ...


def generate_id() -> str:
    """生成短 ID。"""
    return str(uuid.uuid4())[:8]
