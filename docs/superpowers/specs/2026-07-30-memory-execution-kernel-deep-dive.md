# AGI Ready: 记忆系统与执行内核深度设计

## 一、记忆系统完整架构

### 1.1 现状诊断

当前代码已有 **7 个记忆子系统**，但存在严重架构问题：

| 子系统 | 实现状态 | 接入状态 | 问题 |
|--------|---------|---------|------|
| Core Memory | ✅ 完整 | ✅ 已接入 | 无 |
| Persistent Memory | ✅ 完整 | ⚠️ 部分接入 | AgentEngine 只用了 `format_memories_for_prompt`，未用归档/反思 |
| Vector Memory | ✅ 完整 | ❌ 未接入 | AgentEngine 完全不调用 |
| Memory Reflection | ✅ 完整 | ⚠️ 部分接入 | 只在会话结束后触发，检索时从未使用 |
| Hierarchical Orchestrator | ✅ 代码存在 | ❌ **未接入** | 这是统一协调器，但 AgentEngine 完全不用 |
| Memory Provider ABC | ⚠️ 有接口无实现 | ❌ 未接入 | 无法切换后端 |
| File-backed Manager | ⚠️ 存在但断开 | ❌ 未接入 | 与数据库记忆数据分裂 |

**核心问题**：不是"没有记忆系统"，而是"记忆系统太多但没统一"。

### 1.2 四层记忆架构设计

#### L1: Working Memory（工作记忆）

**职责**：当前任务上下文，单次执行生命周期

**实现方案**：复用现有 `AgentSession.messages`，新增 `ContextLayer` 管理注入层

```python
# app/core/context_layer.py (已有设计，细化)
class ContextLayer:
    def __init__(self):
        self.injected: list[dict] = []  # 注入的上下文（记忆、系统提示）
        self.core: list[dict] = []       # 核心对话（用户/助手/工具）
        self.goals: list[Goal] = []      # 当前任务目标
        self.observations: list[Observation] = []  # 当前观察
    
    def build_prompt(self) -> list[dict]:
        """组装最终 prompt：identity + semantic + episodic + working"""
        return [
            *self.injected,      # L4 + L3 + L2 检索结果
            *self.core,          # L1 核心对话
        ]
```

**生命周期**：
- 创建 Session 时初始化
- 每次 `run()` 开始时清空 `injected`，保留 `core`
- 任务结束（COMPLETED/FAILED/CANCELLED）时归档到 Episodic Memory

#### L2: Episodic Memory（情景记忆）

**职责**：过去的事件和经验，带时间戳和重要性评分

**现状**：`PersistentMemoryService.create_episodic_memory()` 已实现，存储在 PostgreSQL

**增强**：
- 接入 `HierarchicalMemoryOrchestrator` 统一检索
- 增加衰减机制（已有 `decay_recency_scores`，需接入自动触发）
- 增加遗忘阈值（`effective_importance < 0.2` 自动归档）

```python
# 在 AgentEngine.run() 的 _finalize() 阶段
async def _finalize(self, session: AgentSession, turn: Turn):
    # 1. 将本轮对话存入情景记忆
    if result and len(result.content) > 10:
        await self.memory_service.create_episodic_memory(
            user_id=session.user_id,
            content=f"User: {message}\nAssistant: {result.content[:500]}",
            agent_id=session.agent_id,
            source_session_id=session.session_id,
            importance=0.7,
        )
    
    # 2. 触发记忆反思
    await self.memory_reflection.maybe_reflect(session.user_id)
    
    # 3. 衰减低重要性记忆
    await self.memory_service.decay_recency_scores(session.user_id)
```

#### L3: Semantic Memory（语义记忆）

**职责**：结构化知识和事实

**现状**：
- `KnowledgeGraph` 三元组已实现（`app/storage/models_memory.py`）
- `ArchivalPassage` 已实现，有 embedding 字段
- `VectorMemoryService` 已实现 ChromaDB 检索
- `create_archival_passage` / `search_archival_memories` 已实现

**缺失**：
- AgentEngine 从不调用 `search_archival_memories`
- 知识图谱查询（`query_graph`）未接入

**接入方案**：
```python
# 在 ContextPreparer 中增加 semantic injector
class SemanticMemoryInjector:
    def __init__(self, memory_service: PersistentMemoryService):
        self.memory_service = memory_service
    
    async def inject(self, session: AgentSession, query: str):
        # 1. 检索归档记忆
        archival = await self.memory_service.search_archival_memories(
            user_id=session.user_id,
            query=query,
            limit=3,
        )
        if archival:
            session.context_layer.add_injected(
                MessageRole.SYSTEM,
                f"[Archival Memory]\n{archival}"
            )
        
        # 2. 检索知识图谱
        facts = await self.memory_service.query_graph(
            user_id=session.user_id,
            query=query,
            limit=5,
        )
        if facts:
            session.context_layer.add_injected(
                MessageRole.SYSTEM,
                f"[Knowledge Graph]\n{facts}"
            )
```

#### L4: Identity Memory（身份记忆）

**职责**：Agent 的人格和价值观

**现状**：
- `CoreMemoryService` 已实现，存储 `CoreMemoryBlock`
- 已注入 system prompt（XML 格式）
- `AgentPersona` 模型待实现（Phase 3）

**增强**：
- 保持现有 `CoreMemoryService` 不变
- 新增 `AgentPersona` 模型（Phase 3 实现）
- 注入顺序：Identity → Semantic → Episodic → Working

### 1.3 统一记忆编排器

**方案**：复用现有 `HierarchicalMemoryOrchestrator`，修复接入

```python
# app/core/hierarchical_memory.py (已有，修复接入)
class HierarchicalMemoryOrchestrator:
    def __init__(self):
        self.core_memory = CoreMemoryService()
        self.persistent_memory = PersistentMemoryService()
        self.vector_memory = VectorMemoryService()
        self.reflection = MemoryReflectionService()
    
    async def retrieve_for_query(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        session_context: dict,
        token_budget: int = 4000,
    ) -> list[dict]:
        """统一检索，按优先级填充 token budget"""
        results = []
        
        # 1. Identity (L4) - 固定 500 tokens
        identity = await self._get_identity(agent_id)
        results.append(identity)
        token_budget -= 500
        
        # 2. Semantic (L3) - 最多 1000 tokens
        semantic = await self._get_semantic(user_id, query, token_budget)
        results.extend(semantic)
        token_budget -= len(semantic)
        
        # 3. Episodic (L2) - 最多 1500 tokens
        episodic = await self._get_episodic(user_id, query, token_budget)
        results.extend(episodic)
        token_budget -= len(episodic)
        
        # 4. Working (L1) - 剩余预算
        working = await self._get_working(session_context, token_budget)
        results.extend(working)
        
        return results
```

**接入点**：
```python
# AgentEngine.__init__()
self.memory_orchestrator = HierarchicalMemoryOrchestrator()

# AgentEngine.run() 的 _initialize() 阶段
async def _initialize(self, session: AgentSession, message: str):
    # 统一记忆检索
    memories = await self.memory_orchestrator.retrieve_for_query(
        user_id=session.user_id,
        agent_id=session.agent_id,
        query=message,
        session_context={"messages": session.messages},
        token_budget=4000,
    )
    
    for memory in memories:
        session.context_layer.add_injected(MessageRole.SYSTEM, memory)
```

### 1.4 记忆生命周期管理

```python
class MemoryLifecycleManager:
    """记忆生命周期管理"""
    
    async def on_turn_complete(self, turn: Turn):
        """每轮结束后触发"""
        # 1. 将重要观察写入情景记忆
        if turn.importance > 0.5:
            await self.episodic.record_event(turn.to_event(), turn.importance)
        
        # 2. 更新工作记忆状态
        self.working.update_goal_status(turn.goal_id, turn.status)
        
        # 3. 如果发现新知识，写入语义记忆
        if turn.contains_knowledge():
            await self.semantic.index_document(turn.to_document())
        
        # 4. 衰减低重要性记忆
        await self.episodic.decay_old_memories()
    
    async def on_session_end(self, session: AgentSession):
        """会话结束后触发"""
        # 1. 归档会话到情景记忆
        await self.episodic.archive_session(session)
        
        # 2. 提取用户画像
        await self.persistent_memory.auto_extract_from_session(
            session.user_id, session.session_id, session.messages
        )
        
        # 3. 清理工作记忆
        self.working.clear()
```

### 1.5 记忆工具（Agent 可调用）

**现状**：已有 `memory_tools.py`、`memory_vector_tools.py`、`core_memory_tools.py`

**增强**：统一为 `MemoryToolSet`

```python
class MemoryToolSet:
    def __init__(self, orchestrator: HierarchicalMemoryOrchestrator):
        self.orchestrator = orchestrator
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "remember",
                    "description": "记录重要信息到记忆",
                    "parameters": {
                        "content": str,
                        "importance": float,  # 0.0-1.0
                        "memory_type": str,   # "episodic" | "semantic" | "identity"
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recall",
                    "description": "主动回忆相关记忆",
                    "parameters": {
                        "query": str,
                        "limit": int,
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "forget",
                    "description": "主动遗忘记忆",
                    "parameters": {
                        "memory_id": str,
                        "reason": str,
                    }
                }
            },
        ]
    
    async def execute(self, tool_name: str, arguments: dict):
        if tool_name == "remember":
            return await self._remember(arguments)
        elif tool_name == "recall":
            return await self._recall(arguments)
        elif tool_name == "forget":
            return await self._forget(arguments)
```

### 1.6 记忆系统实施计划

#### Phase 1: 统一接入（1 周）

**目标**：将 `HierarchicalMemoryOrchestrator` 接入 AgentEngine

**任务**：
1. 修复 `HierarchicalMemoryOrchestrator.wire_services()` 依赖注入
2. 实现 `retrieve_for_query()` 统一检索接口
3. 在 `AgentEngine.__init__()` 中替换分散的记忆服务为 orchestrator
4. 在 `ContextPreparer` 中调用 orchestrator 替代直接调用

**改动**：
- 修改：`app/core/hierarchical_memory.py`
- 修改：`app/core/agent_engine.py`（__init__ 和 run 的注入点）
- 新增：`app/core/context_preparer.py`

**验证**：
- 后端测试通过（47 passed）
- 新增 3 个记忆系统测试

#### Phase 2: 生命周期管理（1 周）

**目标**：实现记忆衰减和遗忘

**任务**：
1. 实现 `MemoryLifecycleManager`
2. 接入 `decay_recency_scores()` 自动触发
3. 实现遗忘阈值（`effective_importance < 0.2`）
4. 实现归档机制（`auto_archive_old_memories`）

**改动**：
- 新增：`app/core/memory_lifecycle.py`
- 修改：`app/core/agent_engine.py`（_finalize 阶段）

#### Phase 3: Agent 记忆工具（1 周）

**目标**：Agent 可自主管理记忆

**任务**：
1. 实现 `MemoryToolSet`
2. 注册到 `ToolRegistry`
3. 前端记忆管理页面

**改动**：
- 新增：`app/tools/memory_toolset.py`
- 修改：`app/tools/__init__.py`（注册）
- 新增：`frontend-react/src/pages/MemoryPage.tsx`

---

## 二、执行内核重构方案

### 2.1 现状诊断

`AgentEngine.run()` 是 **250+ 行的 God Method**，包含 **7+ 个职责**：

| 职责 | 行数 | 问题 |
|------|------|------|
| Turn 创建 | 10 | 与业务逻辑混合 |
| 状态转换 | 8 | 散布在各处 |
| 记忆注入 | 20 | scattered try-except |
| 上下文压缩 | 5 | 无独立策略 |
| LLM 调用 | 40 | 流式/非流式混合 |
| 工具执行 | 30 | 与调试逻辑耦合 |
| 检查点保存 | 20 | 重复代码 |
| 错误处理 | 15 | 重复 try-except |
| 后处理 | 20 | fire-and-forget  scattered |

### 2.2 重构目标

**原则**：最小侵入，逐步提取

**不做的**：
- 不改 `run()` 签名
- 不动 SSE 流式响应
- 不动现有测试

**做的**：
- 提取阶段方法（`_initialize`、`_react_loop`、`_finalize`）
- 提取组件类（`ContextPreparer`、`ToolPipeline`、`CheckpointManager`）
- 统一错误处理
- 消除动态导入

### 2.3 重构 Phase 1: 提取阶段（1 周）

**目标**：将 `run()` 拆分为 3 个阶段方法

```python
async def run(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
    """协调器，保持不变"""
    turn = await self._initialize(session, message)
    
    async for event in self._react_loop(session, message):
        yield event
    
    yield await self._finalize(session, turn)
```

**改动**：
```python
# app/core/agent_engine.py

async def _initialize(self, session: AgentSession, message: str) -> Turn:
    """阶段 1: 初始化"""
    turn = await self._turn_repository.create(
        session_id=session.session_id,
        status="running",
        metadata_={"message": message},
    )
    session.current_turn_id = turn.id
    
    await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    session.messages.append({"role": MessageRole.USER, "content": message})
    
    # 记忆注入（通过 ContextPreparer）
    await self._prepare_context(session, message)
    
    return turn

async def _react_loop(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
    """阶段 2: ReAct 主循环"""
    iteration = 0
    executor = ParallelToolExecutor(...)
    compressor = ContextCompressor(session.context_config)
    result: ChatResult | None = None
    
    try:
        adapter = self.model_registry.get_or_create(...)
        tools = self._build_tools(session.tools, task_description=message)
        
        while iteration < session.max_iterations and not session._stop_requested:
            iteration += 1
            
            # 压缩检查
            await self._maybe_compress(session, compressor, adapter)
            
            yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": iteration})
            
            # LLM 调用
            result = await self._call_model(session, adapter, tools)
            
            # 处理响应
            yield await self._handle_response(session, result, executor)
            
            # 检查点
            await self._checkpoint.save(...)
    
    except Exception as e:
        yield await self._handle_error(e, session)
    
    return result

async def _finalize(self, session: AgentSession, turn: Turn) -> AgentEvent:
    """阶段 3: 收尾"""
    try:
        # 记忆存储
        if result and result.content:
            await self.memory_service.create_episodic_memory(...)
        
        # 反思
        await self.memory_reflection.maybe_reflect(session.user_id)
        
        # Turn 完成
        await self._turn_repository.complete(turn.id, ...)
        
        # 状态转换
        if session._stop_requested:
            await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
        else:
            await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")
    
    except Exception:
        pass
    
    return AgentEvent(type=AgentEventType.DONE, data={...})
```

**验证**：
- 后端测试 47 passed
- 新增 2 个阶段测试

### 2.4 重构 Phase 2: 提取组件（2 周）

**目标**：将阶段内的逻辑提取为独立组件

#### 2.4.1 ContextPreparer

```python
# app/core/context_preparer.py
class ContextPreparer:
    def __init__(
        self,
        memory_orchestrator: HierarchicalMemoryOrchestrator,
        core_memory: CoreMemoryService,
    ):
        self.memory_orchestrator = memory_orchestrator
        self.core_memory = core_memory
    
    async def prepare(self, session: AgentSession, query: str) -> None:
        """准备上下文，注入到 session.context_layer"""
        # 1. 统一记忆检索
        memories = await self.memory_orchestrator.retrieve_for_query(
            user_id=session.user_id,
            agent_id=session.agent_id,
            query=query,
            session_context={"messages": session.messages},
            token_budget=4000,
        )
        
        for memory in memories:
            session.context_layer.add_injected(MessageRole.SYSTEM, memory)
        
        # 2. Core Memory blocks
        try:
            blocks = await self.core_memory.get_blocks(
                user_id=session.user_id,
                agent_id=session.agent_id,
            )
            if blocks:
                xml = self.core_memory.format_for_prompt(blocks)
                session.context_layer.add_injected(MessageRole.SYSTEM, xml)
        except Exception:
            pass
```

#### 2.4.2 ToolExecutionPipeline

```python
# app/core/tool_pipeline.py
class ToolExecutionResult:
    def __init__(self, tool_name: str, result: str, error: str | None, success: bool):
        self.tool_name = tool_name
        self.result = result
        self.error = error
        self.success = success

class ToolExecutionPipeline:
    def __init__(
        self,
        executor: ParallelToolExecutor,
        prioritizer: ToolPrioritizer,
        debug_loop: DebugLoopEngine | None = None,
        approval_gate: ApprovalGate | None = None,
    ):
        self.executor = executor
        self.prioritizer = prioritizer
        self.debug_loop = debug_loop
        self.approval_gate = approval_gate
    
    async def execute(
        self,
        tool_calls: list[dict],
        session: AgentSession,
    ) -> list[ToolExecutionResult]:
        """执行工具管道"""
        results = []
        
        for tc in tool_calls:
            # 1. 审批检查
            if self.approval_gate:
                approval = await self.approval_gate.check(
                    tc["function"]["name"],
                    tc["function"]["arguments"],
                )
                if approval.requires_approval:
                    # 创建 Approval 记录，暂停等待
                    session.execution_state = ExecutionState.AWAITING_HUMAN
                    yield AgentEvent(type=AgentEventType.TOOL_CALL, data={
                        "id": tc.get("id"),
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                        "requires_approval": True,
                    })
                    # 等待审批（通过 asyncio.Event）
                    continue
            
            # 2. 执行工具
            tool_results = await self.executor.execute_all([tc])
            
            # 3. 记录结果
            for tr in tool_results:
                self.prioritizer.record_outcome(tr.tool_name, tr.success, tr.duration_ms)
                results.append(ToolExecutionResult(...))
                
                # 4. 调试循环
                if self.debug_loop and self._should_debug(session, tr):
                    fixed = await self._attempt_debug(session, tr)
                    if fixed:
                        results[-1] = fixed
        
        return results
```

#### 2.4.3 CheckpointManager

```python
# app/core/checkpoint_manager.py
class CheckpointManager:
    def __init__(self, store: CheckpointStore):
        self.store = store
    
    async def save_tool_checkpoint(
        self,
        session: AgentSession,
        iteration: int,
        tool_calls: list[dict],
        tool_results: list[ToolExecutionResult],
        ctx_tokens: int,
    ) -> None:
        cp = CheckpointData(
            session_id=session.session_id,
            messages=session.messages,
            iteration=iteration,
            status=session.state_machine.state.value,
            channel_values={
                "last_tool_calls": tool_calls,
                "last_tool_results": [r.result for r in tool_results],
                "context_tokens": ctx_tokens,
            },
            channel_versions={"messages": iteration, "tools": len(tool_calls)},
            versions_seen={"node": {"messages": iteration, "tools": len(tool_calls)}},
        )
        await self.store.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
    
    async def save_final_checkpoint(
        self,
        session: AgentSession,
        iteration: int,
        result: ChatResult,
        ctx_tokens: int,
    ) -> None:
        cp = CheckpointData(
            session_id=session.session_id,
            messages=session.messages,
            iteration=iteration,
            status=session.state_machine.state.value,
            channel_values={
                "final_content": result.content,
                "total_iterations": iteration,
                "context_tokens": ctx_tokens,
            },
            channel_versions={"messages": iteration},
            versions_seen={"node": {"messages": iteration}},
        )
        await self.store.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
```

### 2.5 重构 Phase 3: 事件驱动（2 周）

**目标**：将状态转换和副作用解耦

```python
# app/core/event_bus.py (已有，扩展)
class AgentEventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
    
    def on(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)
    
    async def emit(self, event_type: str, data: dict):
        for handler in self._handlers[event_type]:
            try:
                await handler(data)
            except Exception:
                pass

# 使用方式
class AgentEngine:
    def __init__(self):
        self.event_bus = AgentEventBus()
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        self.event_bus.on("state:processing", self._on_processing)
        self.event_bus.on("state:completed", self._on_completed)
        self.event_bus.on("state:failed", self._on_failed)
        self.event_bus.on("tool:call", self._on_tool_call)
        self.event_bus.on("tool:result", self._on_tool_result)
    
    async def _on_completed(self, data: dict):
        # 统一处理完成逻辑
        await self.memory_service.create_episodic_memory(...)
        await self.notification_service.task_complete(...)
```

### 2.6 重构优先级矩阵

| 重构项 | 侵入度 | 收益 | 风险 | 优先级 |
|--------|--------|------|------|--------|
| 提取 `_initialize/_react_loop/_finalize` | 低 | 中 | 低 | P0 |
| 创建 `ContextPreparer` | 低 | 高 | 低 | P0 |
| 创建 `ToolExecutionPipeline` | 中 | 高 | 中 | P1 |
| 创建 `CheckpointManager` | 低 | 中 | 低 | P1 |
| 统一错误处理 | 低 | 中 | 低 | P1 |
| 事件驱动架构 | 高 | 高 | 高 | P2 |
| DI 容器 | 中 | 中 | 中 | P2 |

---

## 三、记忆系统 + 执行内核整合方案

### 3.1 整合架构

```
┌─────────────────────────────────────────────────────────────┐
│  AgentEngine (协调器)                                         │
│  ├── run() - 保持签名不变                                     │
│  └── _initialize/_react_loop/_finalize - 阶段拆分             │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: ContextPreparer (统一记忆检索)                      │
│  ├── HierarchicalMemoryOrchestrator                          │
│  │   ├── CoreMemoryService (L4)                              │
│  │   ├── SemanticMemoryInjector (L3)                         │
│  │   ├── EpisodicMemoryInjector (L2)                         │
│  │   └── WorkingMemory (L1)                                  │
│  └── ContextLayer                                            │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: ToolExecutionPipeline (工具执行)                    │
│  ├── ParallelToolExecutor                                    │
│  ├── ToolPrioritizer                                         │
│  ├── DebugLoopEngine                                         │
│  └── ApprovalGate                                            │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: CheckpointManager (状态持久化)                      │
│  └── CheckpointStore (Protocol)                              │
│       ├── InMemoryCheckpointStore                            │
│       └── SQLiteCheckpointStore                              │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: EventBus (事件驱动)                                 │
│  ├── StateChangeHandler                                      │
│  ├── LoggingHandler                                          │
│  └── MetricsHandler                                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 实施顺序

#### Week 1: 记忆统一 + 阶段拆分

**Day 1-2**: 修复 `HierarchicalMemoryOrchestrator` 接入
- [ ] 修复 `wire_services()` 依赖注入
- [ ] 实现 `retrieve_for_query()` 统一检索
- [ ] 编写测试验证四层记忆检索

**Day 3-4**: 创建 `ContextPreparer`
- [ ] 实现 `ContextPreparer` 类
- [ ] 替换 `AgentEngine.run()` 中的记忆注入点
- [ ] 编写测试

**Day 5**: 提取 `_initialize/_react_loop/_finalize`
- [ ] 拆分 `run()` 方法
- [ ] 保持原有逻辑不变
- [ ] 运行现有测试验证

#### Week 2: 执行管道 + 检查点

**Day 1-2**: 创建 `ToolExecutionPipeline`
- [ ] 实现 `ToolExecutionPipeline` 类
- [ ] 集成 `ApprovalGate`
- [ ] 编写测试

**Day 3-4**: 创建 `CheckpointManager`
- [ ] 实现 `CheckpointManager` 类
- [ ] 替换重复的检查点代码
- [ ] 编写测试

**Day 5**: 统一错误处理
- [ ] 创建 `AgentErrorHandler` 类
- [ ] 替换 scattered try-except
- [ ] 运行全量测试

#### Week 3: 事件驱动 + 前端

**Day 1-2**: 事件驱动架构
- [ ] 扩展 `EventBus`
- [ ] 将状态转换改为事件驱动
- [ ] 将通知改为事件处理器

**Day 3-4**: 前端新页面
- [ ] Task Board
- [ ] Approval Queue
- [ ] Trace Explorer

**Day 5**: 集成测试 + 文档
- [ ] 运行全量测试
- [ ] 更新 ARCHITECTURE.md
- [ ] 提交

---

## 四、关键设计决策

### 4.1 为什么保留 AgentEngine.run() 签名？

**原因**：
- 现有 10+ 处调用 `engine.run(session, message)`
- 前端 SSE 流式响应依赖 async generator
- 外部系统（telegram_bot、workflow_engine）依赖此接口

**替代方案评估**：

| 方案 | 侵入度 | 兼容性 | 推荐 |
|------|--------|--------|------|
| 保持 async generator，内部拆阶段 | 低 | 100% | ✅ 推荐 |
| 改为 async/await + poll API | 高 | 0% | ❌ |
| 改为 EventEmitter 模式 | 中 | 50% | ❌ |

### 4.2 为什么复用 HierarchicalMemoryOrchestrator？

**原因**：
- 已有完整实现（`app/core/hierarchical_memory.py`）
- 已实现 `retrieve_for_query()` 统一检索
- 已实现 `on_session_end()` 自动提取
- 只需修复依赖注入，无需重写

**替代方案评估**：

| 方案 | 工作量 | 风险 | 推荐 |
|------|--------|------|------|
| 修复现有 orchestrator 接入 | 低 | 低 | ✅ 推荐 |
| 重写 MemoryOrchestrator | 高 | 高 | ❌ |
| 保持分散调用 | 0 | 高 | ❌ |

### 4.3 为什么先提取阶段再提取组件？

**原因**：
- 提取阶段（`_initialize/_react_loop/_finalize`）是纯重构，不改变行为
- 风险最低，可快速验证
- 提取组件需要在阶段清晰后才能正确识别边界

**风险对比**：

| 顺序 | 风险 | 收益 | 推荐 |
|------|------|------|------|
| 先提取阶段，再提取组件 | 低 | 中 | ✅ 推荐 |
| 直接提取所有组件 | 高 | 高 | ❌ |
| 只提取阶段，不提取组件 | 低 | 低 | ❌ |

---

## 五、文件变更清单

### 新增文件（12 个）

| 文件 | 职责 | 行数估计 |
|------|------|---------|
| `app/core/context_preparer.py` | 统一记忆检索和注入 | 150 |
| `app/core/tool_pipeline.py` | 工具执行管道 | 200 |
| `app/core/checkpoint_manager.py` | 检查点管理 | 100 |
| `app/core/memory_lifecycle.py` | 记忆生命周期管理 | 150 |
| `app/core/agent_error_handler.py` | 统一错误处理 | 100 |
| `app/core/event_bus.py` | 事件总线（扩展已有） | 100 |
| `app/tools/memory_toolset.py` | Agent 记忆工具 | 150 |
| `app/storage/models_tasks.py` | Task 模型 | 100 |
| `app/storage/models_approvals.py` | Approval 模型 | 100 |
| `app/api/v1/tasks.py` | Task API | 150 |
| `app/api/v1/approvals.py` | Approval API | 150 |
| `frontend-react/src/pages/TaskBoardPage.tsx` | 任务看板 | 200 |

### 修改文件（5 个）

| 文件 | 修改内容 | 行数变化 |
|------|---------|---------|
| `app/core/agent_engine.py` | 提取阶段方法，接入 ContextPreparer | +100/-80 |
| `app/core/hierarchical_memory.py` | 修复依赖注入，实现 retrieve_for_query | +50/-20 |
| `app/core/context_layer.py` | 已完成（之前实现） | 0 |
| `app/core/execution_state.py` | 已完成（之前实现） | 0 |
| `frontend-react/src/App.tsx` | 注册新路由 | +10 |

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 阶段提取破坏现有逻辑 | 中 | 高 | 每阶段后运行全量测试 |
| ContextPreparer 导致记忆检索性能下降 | 中 | 中 | token budget 限制，异步检索 |
| ToolPipeline 引入审批逻辑导致工具链断裂 | 中 | 高 | 默认白名单，低风险自动通过 |
| 事件驱动架构过度设计 | 低 | 中 | Phase 3 可选，不强制 |
| 前端新页面与现有页面冲突 | 低 | 低 | 独立路由，共享 ApiClient |

---

## 七、成功标准

### 代码质量
- [ ] `AgentEngine.run()` 行数 < 100（从 250+ 减少）
- [ ] 核心文件改动 < 5 个
- [ ] 新增文件 < 15 个
- [ ] 单文件 < 300 行
- [ ] 测试覆盖率新增 > 80%

### 功能验证
- [ ] 后端测试：47 passed + 新增测试通过
- [ ] 前端测试：84 passed + 新增测试通过
- [ ] `run()` 签名不变
- [ ] SSE 流式响应兼容
- [ ] 记忆检索延迟 < 200ms

### AGI 就绪度
- [ ] 四层记忆统一检索
- [ ] Turn 可暂停/恢复（通过 ApprovalGate）
- [ ] 工具执行可拦截
- [ ] 检查点持久化（已有 SQLiteCheckpointStore）
- [ ] 状态机事件驱动（可选）

---

## 八、待确认事项

1. **Phase 3 事件驱动架构**：是否需要在 Week 3 实现，还是延后到 AGI Phase 2？
2. **Agent 记忆工具**：是否在 Week 2 实现，还是延后？
3. **前端页面**：是否全部 4 个页面（Task Board、Approval Queue、Trace Explorer、Agent Persona）都在 Week 3 实现，还是优先 Task Board + Approval Queue？

确认后我输出实施计划。
