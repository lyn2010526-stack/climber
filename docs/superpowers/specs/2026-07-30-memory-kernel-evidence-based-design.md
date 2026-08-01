# 记忆系统与执行内核深化设计（证据版）

> 本文档所有现状判断均由可复现脚本或代码行号验证。凡未验证的推测一律不写入。
> 修订日期：2026-07-30

---

## 零、为什么需要这份文档

已存在 `2026-07-30-memory-execution-kernel-deep-dive.md`（919 行）描述四层记忆愿景。
本文档不重复愿景，只补三件它没做的事：

1. **用可执行证据定位真实故障点**（而非"部分接入""未接入"这类模糊描述）
2. **修正原文档与现有代码不符的判断**
3. **给出 L1/L4 与 TurnState 这三个真正缺失件的落地设计**

---

## 一、现状：记忆系统四层全部静默失效

### 1.1 实测证据

复现方法：按 `agent_engine.py:125-127` 的真实接线方式装配 orchestrator，
写入一条 importance=0.9 的记忆，再走检索链路。

```
BUG 1: core memory service never wired
  _core_memory_service   = None
  _vector_memory_service = None
  _reflection_service    = None
  -> SILENT LAYERS: ['core', 'vector/archival', 'reflection']

BUG 2: retrieve_memories returns ORM objects, code calls .get()
  retrieve_memories -> 1 item(s), type=EpisodicMemory
  has .get() method? False
  .get('content') raises -> AttributeError: 'EpisodicMemory' object has no attribute 'get'
  _retrieve_episodic() -> text='' tokens=0
  -> DATA LOST (swallowed)

BUG 3: _retrieve_user_profile calls a method that does not exist
  hasattr(svc, 'get_user_profile')      = False
  hasattr(svc, 'get_or_create_profile') = True
  direct call raises -> AttributeError

BUG 4: end-to-end retrieval returns nothing despite stored memory
  core_memory / user_profile / episodic / archival / reflection : 全部 False
  total_tokens : 0
  format_for_prompt() -> ''
  VERDICT: memory injected into prompt = NOTHING (all 4 layers dead)
```

**结论**：不是"检索质量差"，是**检索结果为空**。存进去的记忆一条都到不了 prompt。

### 1.2 四个根因（精确到行）

| # | 位置 | 缺陷 | 后果 |
|---|------|------|------|
| 1 | `agent_engine.py:125-127` | `wire_services()` 只传 `persistent_memory`，另外 3 个参数默认 `None` | L1/L3/L4 三层检索方法首行 `if ... is None: return ""` 直接返回 |
| 2 | `hierarchical_memory.py:216` | `mem.get("content", "")`，但 `retrieve_memories()` 返回 `list[EpisodicMemory]` ORM 对象 | 抛 `AttributeError`，被 224 行 `except Exception` 吞掉，L2 永远空 |
| 3 | `hierarchical_memory.py:189` | 调 `get_user_profile()`，该方法在代码库中不存在（真实名 `get_or_create_profile`） | 抛 `AttributeError`，被 194 行吞掉，用户画像永远空 |
| 4 | `agent_engine.py:131` | `core_memory_service=None` 且注释写 "lazy import in prepare()"，但 `prepare()` 内无任何 lazy import | `context_preparer.py:54` 的 `if is not None` 恒假，核心记忆注入代码永不执行 |

### 1.3 加剧问题的设计缺陷

`hierarchical_memory.py` 四个 `_retrieve_*` 方法全部采用
`try: ... except Exception: logger.debug(...)` 模式。

`logger.debug` 在生产日志级别下不输出。**这是四个 bug 能长期存活的直接原因**：
故障完全无声。修复必须同时改掉这个静默模式，否则下一个 bug 依旧隐形。

### 1.4 对原始批评的一处修正

原文档称检索是"关键词匹配，不是语义理解"。

实际 `persistent_memory.py:85` 已优先走 `vector_memory.search(collection="episodic")`
向量检索，关键词仅作 fallback。**语义检索能力已存在**，只是结果在上层被
第 2 号 bug 摧毁。修复方向因此不是"实现语义检索"，而是"修好数据通路"，
工作量显著小于原判断。

---

## 二、记忆系统目标设计

### 2.1 分层职责与现有代码映射

| 层 | 职责 | 生命周期 | 现有载体 | 缺口 |
|----|------|---------|---------|------|
| L1 Working | 当前任务目标/观察/假设 | 单任务，结束即清 | `AgentSession.messages` | 无结构化 goals/observations/hypotheses |
| L2 Episodic | 过去事件与经验 | 写入→衰减→遗忘 | `PersistentMemoryService` + `EpisodicMemory` 表 | 通路断（bug 2），衰减未调度 |
| L3 Semantic | 知识与事实 | 程序化更新，少删 | `VectorMemoryService`(archival) + `KnowledgeGraph` | 未接线（bug 1） |
| L4 Identity | 人格/价值观/准则 | 持久，极少变更 | `CoreMemoryService` | 未接线（bug 1+4），无 values/principles 概念 |

**设计原则**：L2/L3 的存储层已完备，只修通路，不重写。L1/L4 需新增结构。

### 2.2 统一后端协议

```python
# app/core/memory/protocol.py
from typing import Protocol

class MemoryBackend(Protocol):
    """四层记忆的统一后端契约，便于替换实现与测试。"""

    async def store(self, event: MemoryEvent) -> MemoryItem: ...
    async def recall(self, query: str, ctx: RecallContext) -> list[MemoryItem]: ...
    async def forget(self, memory_id: str, reason: str) -> None: ...
```

`MemoryItem` 统一为 dataclass 而非 ORM 对象，从类型层面根除 bug 2：

```python
@dataclass
class MemoryItem:
    id: str
    content: str
    importance: float
    created_at: datetime
    last_accessed_at: datetime | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_orm(cls, row: Any) -> "MemoryItem":
        """唯一的 ORM -> dict 边界，防止 ORM 对象泄漏到上层。"""
        return cls(
            id=row.id,
            content=row.content,
            importance=row.importance,
            created_at=row.created_at,
            last_accessed_at=getattr(row, "last_accessed_at", None),
            tags=list(getattr(row, "tags", []) or []),
        )
```

### 2.3 L1 Working Memory（新增）

原文档只说"复用 session.messages"，未给结构。补齐：

```python
# app/core/memory/working.py

class GoalStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"

@dataclass
class Goal:
    id: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    parent_id: str | None = None      # 支持子目标树

@dataclass
class Observation:
    content: str
    source: str                        # tool_name / llm / user
    iteration: int

@dataclass
class Hypothesis:
    statement: str
    confidence: float
    verified: bool | None = None       # None=待验证

class WorkingMemory:
    """任务级工作内存。执行过程中实时更新，任务结束归档到 L2。"""

    MAX_OBSERVATIONS = 50              # 硬上限，防上下文膨胀
    MAX_HYPOTHESES = 3                 # 对齐"假设路径最多 3 条"约束

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.goals: list[Goal] = []
        self.observations: list[Observation] = []
        self.hypotheses: list[Hypothesis] = []

    def add_observation(self, obs: Observation) -> None:
        self.observations.append(obs)
        if len(self.observations) > self.MAX_OBSERVATIONS:
            self.observations = self.observations[-self.MAX_OBSERVATIONS:]

    def format_for_prompt(self) -> str:
        """仅输出活跃目标与最近观察，控制 token 占用。"""
        parts: list[str] = []
        active = [g for g in self.goals if g.status == GoalStatus.ACTIVE]
        if active:
            parts.append("[CURRENT GOALS]")
            parts.extend(f"- {g.description}" for g in active)
        if self.observations:
            parts.append("[RECENT OBSERVATIONS]")
            parts.extend(f"- [{o.source}] {o.content}" for o in self.observations[-5:])
        if self.hypotheses:
            parts.append("[WORKING HYPOTHESES]")
            parts.extend(
                f"- ({h.confidence:.0%}) {h.statement}"
                for h in self.hypotheses if h.verified is not True
            )
        return "\n".join(parts)
```

**关键决策**：`WorkingMemory` 纯内存、不落库。任务结束时由 L2 归档，
避免为短生命周期数据增加数据库写压力。

### 2.4 L4 Identity Memory（新增）

```python
# app/core/memory/identity.py

@dataclass
class Principle:
    statement: str
    inviolable: bool = False           # 不可覆盖的硬准则

@dataclass
class Persona:
    role: str                          # "代码安全专家"
    expertise: list[str]
    tone: str = "concise"

class IdentityMemory:
    """Agent 人格。持久存在，仅显式操作可改。"""

    def __init__(self, persona: Persona, principles: list[Principle]) -> None:
        self.persona = persona
        self.principles = principles

    def format_for_prompt(self) -> str:
        parts = [
            "[IDENTITY]",
            f"Role: {self.persona.role}",
            f"Expertise: {', '.join(self.persona.expertise)}",
        ]
        inviolable = [p for p in self.principles if p.inviolable]
        if inviolable:
            parts.append("[INVIOLABLE PRINCIPLES]")
            parts.extend(f"- {p.statement}" for p in inviolable)
        return "\n".join(parts)
```

**与提示词引擎的边界**：`IdentityMemory` 输出注入 PromptEngine 的
**Layer 0（不可覆盖层）**，复用既有三层提示词架构，不新建注入机制。
`inviolable=True` 的准则不允许被 Layer 1 用户提示词覆盖。

### 2.5 注入顺序与 token 预算

```
最终 prompt 组装顺序（由外到内）：
  L4 Identity   -> PromptEngine Layer 0    预算  400 tokens（固定）
  L3 Semantic   -> system message           预算  800 tokens
  L2 Episodic   -> system message           预算 1500 tokens
  L1 Working    -> system message（贴近对话）预算  600 tokens
  核心对话                                   剩余全部
```

沿用 `MemoryRetrievalConfig` 现有预算字段，仅新增 `working_memory_tokens: int = 600`
与 `identity_tokens: int = 400`。

### 2.6 记忆生命周期与衰减

沿用原文档衰减公式，补上缺失的**触发机制**：

```
effective_importance = base_importance × e^(-λ × days_since_last_access)
```

| importance | 保留策略 | 归属 |
|-----------|---------|------|
| > 0.8 | 永久 | L3/L4 |
| 0.5-0.8 | 30 天后开始衰减 | L2 |
| 0.3-0.5 | 7 天 | L2 |
| < 0.3 | 不写入 | 丢弃 |

**触发点**（原文档缺失，这是衰减从未生效的原因）：
`decay_recency_scores()` 与 `decay_recency_by_access()` 已实现但**从未被调用**。
接入方案：注册到既有 `app/core/cleanup.py` 的周期任务，与 Session TTL 清理同一调度器，
不新增后台任务框架。

### 2.7 Agent 自主记忆操作

`MemoryToolSet`（remember/recall/forget）已实现于 `app/tools/memory_toolset.py`，
但**未注册进 ToolRegistry**，Agent 拿不到。修复为在 `register_builtins()` 中注册，
无需重写工具。

---

## 三、执行内核：修正现状判断

### 3.1 原文档与实际代码的偏差

| 原文档说法 | 实测 | 修正 |
|-----------|------|------|
| `_run_locked()` 200+ 行 | 该方法**不存在** | 实际是 `_react_loop()`，**149 行** |
| 混合 9 项职责无法拆分 | `run()` 已拆为 `_initialize`/`_react_loop`/`_finalize` | 阶段拆分**已完成** |
| 需新建 TaskState | `task_state_machine.py:17-23` 已有 7 态 | 已存在，但用 `PROCESSING` 非 `RUNNING`，另有 `RETRYING` |
| 需新建 TurnState | 代码库中**不存在** | **这是真实缺口** |

`agent_engine.py` 全文 544 行，已提取 `ContextPreparer`、`ToolExecutionPipeline`、
`CheckpointManager`、`MemoryLifecycleManager` 四个组件。执行内核重构的
Phase 1（阶段提取）与 Phase 2（组件提取）**实际已完成**。

### 3.2 真实剩余缺口：TurnState

现状：`AgentEvent` 用 `THINKING`/`CHECKPOINT` 等事件类型隐式表达轮次阶段，
但无显式状态机，导致：

- 无法查询"某轮当前卡在哪个阶段"
- `AWAITING`（等待人工审批）无状态表达，审批中断后无法精确恢复
- 前端只能靠事件流猜测阶段

设计：

```python
# app/core/turn_state.py

class TurnState(str, Enum):
    IDLE = "idle"
    PREPARING = "preparing"        # 组装 context
    THINKING = "thinking"          # 调用 LLM
    EXECUTING = "executing"        # 执行工具
    AWAITING = "awaiting"          # 等待人工决策
    CHECKPOINTING = "checkpointing"
    DONE = "done"

TURN_TRANSITIONS: dict[TurnState, set[TurnState]] = {
    TurnState.IDLE:          {TurnState.PREPARING},
    TurnState.PREPARING:     {TurnState.THINKING, TurnState.DONE},
    TurnState.THINKING:      {TurnState.EXECUTING, TurnState.CHECKPOINTING, TurnState.DONE},
    TurnState.EXECUTING:     {TurnState.AWAITING, TurnState.CHECKPOINTING, TurnState.THINKING},
    TurnState.AWAITING:      {TurnState.EXECUTING, TurnState.DONE},   # 批准/拒绝
    TurnState.CHECKPOINTING: {TurnState.THINKING, TurnState.DONE},
    TurnState.DONE:          set(),
}
```

**接入方式（最小侵入）**：`TurnState` 挂在既有 `Turn` 实体上，
新增 `turn_state` 列。`_react_loop` 在现有 yield 事件处同步转换状态，
不改循环结构、不改 `run()` 签名、不改 SSE 响应格式。

### 3.3 一处必须保留的既有修复

`run()` 会截获 `_react_loop` 的 DONE 事件并改由 `_finalize` 产出终态。
`final_status` 参数（`agent_engine.py` 的 `run`/`_finalize`）确保
`max_iterations_reached` 不被 `session.status.value` 覆盖成 `failed`。
引入 TurnState 时不得回退该行为，否则 `test_max_iterations` 重新失败。

---

## 四、实施顺序

按"先通路、再结构"排序，每步独立可测、可回滚。

| 阶段 | 内容 | 验收 |
|-----|------|------|
| P0-1 | 修 4 个 wiring bug；`_retrieve_*` 的 `logger.debug` 改 `logger.warning` | 复现脚本 `format_for_prompt()` 非空 |
| P0-2 | `MemoryItem.from_orm` 统一边界，消除 ORM 泄漏 | 类型层面不再出现 `.get()` on ORM |
| P0-3 | `MemoryToolSet` 注册进 `ToolRegistry` | Agent 工具列表含 remember/recall/forget |
| P1-1 | 衰减接入 `cleanup.py` 周期任务 | 衰减任务被实际调用 |
| P1-2 | `WorkingMemory`（L1 结构化） | goals/observations/hypotheses 进 prompt |
| P1-3 | `IdentityMemory`（L4）接 PromptEngine Layer 0 | inviolable 准则不可被用户层覆盖 |
| P2-1 | `TurnState` + `Turn.turn_state` 列 | 可查询轮次阶段；AWAITING 可恢复 |

**全程约束**：不动 `run()` 签名、不动 SSE 流式响应、单文件不超 300 行、
`test_max_iterations` 与现有 726 项后端测试保持通过。

---

## 五、风险

| 风险 | 缓解 |
|-----|------|
| 修好检索后 prompt 突然变长，触发上下文超限 | 四层预算硬上限（2.5 节）+ 既有 `ContextCompressor` |
| `logger.debug` 改 `warning` 后日志噪音 | 仅对"服务已接线但调用失败"告警；未接线走一次性 info |
| L1 归档到 L2 增加写入量 | 仅归档 importance ≥ 0.5 的观察 |
| `IdentityMemory` 与 PromptEngine Layer 0 职责重叠 | Identity 只产出文本块，注入与优先级仍由 PromptEngine 决定 |
