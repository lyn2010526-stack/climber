# Climber 深度做重设计规格

> 创建日期：2026-07-30
> 状态：执行中
> 原则：每个领域对标顶级开源项目，做深做透，不留"能跑但脆弱"的代码

## 1. 核心引擎管线化（参考 OpenSquilla Pipeline）

### 设计
- 引入 `TurnContext` 作为单次 Agent 回合的不可变上下文载体
- 管线步骤（TurnStep）有序执行，每步可失败开放（fail-open）并记录决策日志
- 步骤间通过 `metadata` 字典传递状态，支持快照回滚
- 管线阶段：意图分类 → 路由决策 → 技能过滤 → 上下文压缩 → 执行 → 后处理

### 文件
- `app/core/engine/pipeline.py` — TurnContext、run_pipeline
- `app/core/engine/steps/` — 各管线步骤实现
- `app/core/agent_engine.py` — 重构为管线调度器

### 关键类
```python
@dataclass
class TurnContext:
    message: str
    session_id: str
    model: str
    tool_defs: list[ToolDef]
    system_prompt: str
    metadata: dict  # 步骤间状态传递
    raw_message: str | None = None
    route_plan: RoutePlan | None = None

TurnStep = Callable[[TurnContext], Awaitable[TurnContext]]

async def run_pipeline(ctx: TurnContext, steps: list[TurnStep]) -> TurnContext:
    """有序执行步骤，失败开放并记录"""
```

## 2. 路由决策结构化（参考 OpenSquilla RouterDecision）

### 设计
- 每次路由决策产生结构化事件 `RouterDecisionEvent`
- 包含：目标层级、模型、置信度、概率分布、节省百分比、回退原因
- 路由来源分类：classifier / fallback / user_override / ensemble
- 决策日志持久化，支持事后审计和模型训练数据回流

### 文件
- `app/core/engine/router_decision.py`

## 3. 子 Agent 生命周期管理（参考 OpenSquilla SubagentManager）

### 设计
- `SubagentManager`：深度限制（默认 3）、并发限制（默认 5）
- `SubagentRegistry`：活跃运行追踪、孤儿清理、归档
- `SubagentSpec`：任务定义、模型覆盖、超时、工作上下文
- `SubagentUsage`：每个子 Agent 独立的 Token/成本快照
- 父任务取消时级联取消子任务

### 文件
- `app/core/engine/subagent.py`

## 4. 工具规则求解器（参考 Letta ToolRulesSolver）

### 设计
- 工具间依赖关系：TerminalTool / InitTool / ContinueTool
- 上一次工具失败时自动禁止重试同一工具
- 心跳请求控制多步执行节奏
- 工具调用历史追踪

### 文件
- `app/core/engine/tool_rules.py`

## 5. 内存压力管理（参考 Letta Memory Pressure）

### 设计
- 每轮检测 token 使用率，超过阈值触发压缩
- 压缩策略：摘要最近 N 轮 / 丢弃工具结果 / 保留系统消息
- 压力告警去重（同一会话只告警一次直到压缩完成）
- 自动压缩 + 手动压缩双模式

### 文件
- `app/core/engine/memory_pressure.py`

## 6. 运行时状态胶囊（参考 OpenSquilla RuntimeStateCapsule）

### 设计
- 代码类任务的工作空间状态快照
- Git dirty files 分类：source / test / scratch
- 工具执行 receipt 追踪（哪个工具改了哪个文件）
- 阻塞事实检测（有 scratch 无 source = 需要检查）

### 文件
- `app/core/engine/runtime_capsule.py`

## 7. 共识聚合增强（参考 OpenSquilla Ensemble + AutoGen Message Passing）

### 设计
- 多模型并行执行：同一任务同时发给 N 个模型
- 投票机制：结果一致性 > N/2 视为共识
- 分歧标记：低于阈值时标记为 needs_review
- 跨 Agent 消息传递协议（类似 AutoGen publish/subscribe）

### 文件
- `app/multi_agent/ensemble.py`
- `app/multi_agent/message_bus.py`

## 8. 记忆系统深化（参考 Letta Block Memory）

### 设计
- Block-based 记忆：每块有 label/value/read_only/limit
- 编译时注入 system prompt（而非运行时拼接）
- 记忆变更检测 + 自动重建
- 归档记忆分页（Passage Memory）
- 跨会话实体提取

### 文件
- `app/core/memory/blocks.py`
- `app/core/memory/consolidation.py`

## 执行顺序

1. Pipeline + RouterDecision（基础骨架）
2. SubagentManager（协作基础）
3. ToolRulesSolver + MemoryPressure（稳定性）
4. RuntimeStateCapsule（代码任务能力）
5. Ensemble + MessageBus（协作增强）
6. Memory Blocks（长期记忆）
7. 测试 + 回归验证
