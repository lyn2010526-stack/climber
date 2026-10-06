"""TAOR 智能体体系 - 核心数据模型与共享契约。

本模块定义 agent-system 全部新增组件共享的类型、枚举与协议，
供 innovation_layer 与 base_deps 引用。学习自 Claude-Code 泄露资料
的「7 阶段 TAOR 状态机」思路（仅参考概念，代码为原创）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex}"


class TAORPhase(StrEnum):
    """TAOR 七阶段主循环状态机（学 Claude-Code 泄露资料概念，原创实现）。

    状态转换：
      TASKIFY -> PLAN -> THINK -> ACT -> OBSERVE -> BRANCH -> (LOOP|DONE|YIELD|ROLLBACK)
    """

    SYSBOOT = "sysboot"          # 0 预检：加载项目 skill/规则文档与长期记忆
    TASKIFY = "taskify"          # 1 解析任务，产出目标与验收标准
    PLAN = "plan"                # 2 生成初始任务规划（子任务清单）
    THINK = "think"              # 3 结合上下文/记忆/工具列表产出下一步行动决策
    ACT = "act"                  # 4 执行工具调用，捕获结果与异常
    OBSERVE = "observe"          # 5 工具结果写会话日志，评估进度与风险等级
    BRANCH = "branch"            # 6 状态分支判断：DONE/ROLLBACK/YIELD/LOOP
    DONE = "done"                # 终止：输出完整任务总结报告
    ROLLBACK = "rollback"        # 回滚：加载最近里程碑快照重试
    YIELD = "yield"              # 人机接力：保存里程碑快照，暂停交还控制权


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RunMode(StrEnum):
    """三态运行控制器模式。"""

    AUTO = "auto"                # 全自动：持续跑 TAOR，直到结束或触发终止
    OBSERVE = "observe"          # 观察复盘：禁用写改工具，只读评估
    HITL = "hitl"                # 人机接力：每轮自动评估，高风险/多分支/连续失败暂停


class ToolClass(StrEnum):
    """工具分类，用于三态控制器的写权限拦截。"""

    READ = "read"
    WRITE = "write"
    EXEC = "exec"
    NETWORK = "network"
    MEMORY = "memory"
    CONTROL = "control"


class MemoryKind(StrEnum):
    """记忆类型标记。"""

    FACT = "fact"                # 抽取的结构化事实
    EPISODE = "episode"          # 会话事件
    SKILL = "skill"              # skill/规则文档（短文档）
    RULE = "rule"
    CODE = "code"                # 长代码文档
    TEXT = "text"                # 长自然文本
    FAILURE = "failure"          # 失败案例
    REFLECTION = "reflection"    # 精炼后的反思


@dataclass
class ToolDescriptor:
    """工具描述，供 TAOR 决策与三态控制器使用。"""

    name: str
    description: str
    tool_class: ToolClass
    read_only: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """一次工具调用请求。"""

    name: str
    arguments: dict[str, Any]
    tool_call_id: str = field(default_factory=lambda: new_id("tc_"))


@dataclass
class ToolResult:
    """一次工具执行结果。"""

    tool_call_id: str
    name: str
    content: Any
    is_error: bool = False
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class MemoryItem:
    """单条记忆（记忆库核心数据模型，mem0 长期记忆模型思路）。"""

    id: str = field(default_factory=lambda: new_id("mem_"))
    kind: MemoryKind = MemoryKind.FACT
    text: str = ""
    doc_type: str | None = None          # skill|rule|code|text|conversation
    doc_length: int = 0                  # 字符长度
    title: str = ""                      # 标题（zeyi 标题加权用）
    metadata: dict[str, Any] = field(default_factory=dict)
    trust_score: float = 0.5             # 可信度权重（Hermes 思路）
    decay: float = 1.0                   # 时间衰减权重（Hermes/mnemosyne）
    created_at: datetime = field(default_factory=now_utc)
    last_accessed_at: datetime | None = None
    accessed_count: int = 0
    ttl_seconds: int | None = None       # TTL 过期（前身：mnemosyne TTL）
    source_session: str | None = None    # 来源会话
    structured: dict[str, Any] = field(default_factory=dict)  # 事实三元组等


@dataclass
class RetrievedMemory:
    """检索召回的一条记忆 + 打分。"""

    item: MemoryItem
    route: str                        # fts|chinese|vector|hybrid
    score: float                      # 融合后得分
    keyword_score: float = 0.0
    vector_score: float = 0.0
    profile_boost: float = 0.0
    reason: str = ""


@dataclass
class Snapshot:
    """双层快照中的一档快照。

    incremental: True 为增量 diff 快照，False 为里程碑全量快照。
    """

    id: str = field(default_factory=lambda: new_id("snap_"))
    kind: str = "incremental"          # incremental | milestone
    session_id: str = ""
    phase: TAORPhase | None = None
    base_on: str | None = None         # 增量快照的基准快照 id
    state: dict[str, Any] = field(default_factory=dict)   # 全量状态（milestone）
    diff: dict[str, Any] = field(default_factory=dict)    # 增量差异（incremental）
    messages_delta: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    milestone_label: str | None = None # YIELD/关键业务节点标记


@dataclass
class LoopDecision:
    """状态分支判断的结果。"""

    next_phase: TAORPhase
    done: bool = False
    rollback: bool = False
    yield_control: bool = False
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class LoopReport:
    """每轮循环输出（用户规范：进度/已完成/Follow-up 队列）。"""

    session_id: str = ""
    outer_round: int = 0
    inner_turn: int = 0
    phase: TAORPhase = TAORPhase.SYSBOOT
    progress: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    followup_queue: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    tokens_used: int = 0
    checksum: str = ""                 # 记忆审计输出用


# ---- 记忆审计输出契约（用户要求：输出记忆审计日志） ----


@dataclass
class MemoryAuditEntry:
    """一条记忆审计记录。"""

    action: str                        # add|refine|merge|expire|downgrade|kept_below_trust
    memory_id: str = ""
    kind: MemoryKind | None = None
    text_preview: str = ""
    score_before: float | None = None
    score_after: float | None = None
    reason: str = ""
    timestamp: datetime = field(default_factory=now_utc)


# ---- 任务报告契约（用户要求：任务报告） ----


@dataclass
class TaskReport:
    """完整任务总结报告。"""

    task_id: str
    objective: str
    mode: RunMode
    status: str                        # completed|yielded|failed|rollbacked|stopped
    outer_rounds: int = 0
    inner_turns: int = 0
    tokens_used: int = 0
    tool_calls: int = 0
    result_summary: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    risk_events: list[dict[str, Any]] = field(default_factory=list)
    retries: int = 0
    rollbacks: int = 0
    snapshots_taken: int = 0
    memory_added: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=now_utc)
    finished_at: datetime | None = None


# ---- 事件协议（供 SDK / HTTP / CLI 共用） ----


class SystemEventType(StrEnum):
    TURN_STARTED = "turn_started"
    TURN_DONE = "turn_done"
    PHASE_CHANGED = "phase_changed"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    OBSERVATION = "observation"
    LOOP_STATUS = "loop_status"
    MILESTONE_SAVED = "milestone_saved"
    SNAPSHOT_SAVED = "snapshot_saved"
    MEMORY_REFINED = "memory_refined"
    YIELD_PENDING = "yield_pending"
    YIELD_RESUMED = "yield_resumed"
    CONTEXT_COMPRESSED = "context_compressed"
    DONE = "done"
    ERROR = "error"


class AgentTick(StrEnum):
    """后台子 Agent 记忆精炼的触发时机。"""

    AFTER_EVERY_TWO_TO_THREE_ROUNDS = "every_2_3_rounds"
    AFTER_MANUAL_TRIGGER = "manual"
    AT_END = "at_end"
