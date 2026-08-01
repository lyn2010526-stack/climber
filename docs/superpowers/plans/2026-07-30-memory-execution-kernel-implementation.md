# AGI Ready: 记忆系统与执行内核实施计划

## phase 1: 记忆统一 + 阶段拆分 (week 1)

### 任务 1.1: 修复 HierarchicalMemoryOrchestrator 接入
**文件**: `app/core/hierarchical_memory.py`

**改动**:
- 修复 `wire_services()` 依赖注入，接受 `memory_service`/`core_memory`/`vector_memory` 参数
- 实现 `retrieve_for_query()` 统一检索接口（L4→L3→L2→L1 优先级）
- 增加 token budget 控制和截断逻辑

**测试**:
- `tests/test_memory_orchestrator.py` - 新增 3 个用例：
  - `test_retrieve_for_query_returns_layered_memories`
  - `test_retrieve_respects_token_budget`
  - `test_retrieve_with_no_memories_returns_empty`

**验证**: `pytest tests/test_memory_orchestrator.py -v`

---

### 任务 1.2: 创建 ContextPreparer
**文件**: `app/core/context_preparer.py` (新增)

**实现**:
```python
class ContextPreparer:
    def __init__(
        self,
        memory_orchestrator: HierarchicalMemoryOrchestrator,
        core_memory: CoreMemoryService,
    ):
        self.memory_orchestrator = memory_orchestrator
        self.core_memory = core_memory
    
    async def prepare(self, session: AgentSession, query: str) -> None:
        # 1. 统一记忆检索
        memories = await self.memory_orchestrator.retrieve_for_query(...)
        for memory in memories:
            session.context_layer.add_injected(MessageRole.SYSTEM, memory)
        
        # 2. Core Memory blocks
        blocks = await self.core_memory.get_blocks(...)
        if blocks:
            xml = self.core_memory.format_for_prompt(blocks)
            session.context_layer.add_injected(MessageRole.SYSTEM, xml)
```

**接入**:
- 修改 `app/core/agent_engine.py`:
  - `__init__()` 新增 `self.context_preparer = ContextPreparer(...)`
  - `run()` 的 `_initialize()` 阶段调用 `await self.context_preparer.prepare(session, message)`

**测试**:
- `tests/test_context_preparer.py` - 新增 2 个用例：
  - `test_prepare_injects_memories_into_context_layer`
  - `test_prepare_handles_memory_service_failure_gracefully`

**验证**: `pytest tests/test_context_preparer.py tests/test_memory_orchestrator.py -v`

---

### 任务 1.3: 提取 run() 阶段方法
**文件**: `app/core/agent_engine.py`

**改动**:
- 提取 `_initialize(session, message) -> Turn`
- 提取 `_react_loop(session, message) -> AsyncIterator[AgentEvent]`
- 提取 `_finalize(session, turn) -> AgentEvent`
- `run()` 保持为协调器，逻辑不变

**约束**:
- 不改变 `run()` 签名
- 不改变 SSE 流式响应
- 不改变任何外部行为

**测试**:
- 运行现有 `tests/test_p0_runtime_contracts.py` 验证无回归
- 运行 `tests/test_agent_engine.py` 验证核心逻辑

**验证**: `pytest tests/test_p0_runtime_contracts.py tests/test_agent_engine.py -v`

---

## phase 2: 执行管道 + 检查点 (week 2)

### 任务 2.1: 创建 ToolExecutionPipeline
**文件**: `app/core/tool_pipeline.py` (新增)

**实现**:
```python
class ToolExecutionPipeline:
    def __init__(
        self,
        executor: ParallelToolExecutor,
        prioritizer: ToolPrioritizer,
        debug_loop: DebugLoopEngine | None = None,
        approval_gate: ApprovalGate | None = None,
    ):
        ...
    
    async def execute(
        self,
        tool_calls: list[dict],
        session: AgentSession,
    ) -> list[ToolExecutionResult]:
        ...
```

**接入**:
- 修改 `app/core/agent_engine.py`:
  - `__init__()` 新增 `self.tool_pipeline = ToolExecutionPipeline(...)`
  - `_react_loop()` 中替换 `await self.executor.execute_all(tool_calls)` 为 `await self.tool_pipeline.execute(tool_calls, session)`

**测试**:
- `tests/test_tool_pipeline.py` - 新增 3 个用例：
  - `test_execute_runs_tools_in_parallel`
  - `test_execute_respects_approval_gate`
  - `test_execute_retries_on_debug_loop_success`

**验证**: `pytest tests/test_tool_pipeline.py -v`

---

### 任务 2.2: 创建 CheckpointManager
**文件**: `app/core/checkpoint_manager.py` (新增)

**实现**:
```python
class CheckpointManager:
    def __init__(self, store: CheckpointStore):
        self.store = store
    
    async def save_tool_checkpoint(self, session, iteration, tool_calls, tool_results, ctx_tokens):
        ...
    
    async def save_final_checkpoint(self, session, iteration, result, ctx_tokens):
        ...
```

**接入**:
- 修改 `app/core/agent_engine.py`:
  - `__init__()` 新增 `self.checkpoint_manager = CheckpointManager(self.checkpoint_store)`
  - 替换 `_react_loop()` 中重复的检查点代码

**测试**:
- `tests/test_checkpoint_manager.py` - 新增 2 个用例：
  - `test_save_tool_checkpoint_persists_to_store`
  - `test_save_final_checkpoint_includes_result`

**验证**: `pytest tests/test_checkpoint_manager.py -v`

---

### 任务 2.3: 统一错误处理
**文件**: `app/core/agent_error_handler.py` (新增)

**实现**:
```python
class AgentErrorHandler:
    def __init__(self, event_bus: AgentEventBus | None = None):
        self.event_bus = event_bus
    
    async def handle(self, error: Exception, session: AgentSession) -> AgentEvent:
        ...
```

**接入**:
- 修改 `app/core/agent_engine.py`:
  - `__init__()` 新增 `self.error_handler = AgentErrorHandler()`
  - 替换 `_react_loop()` 和 `_finalize()` 中的 scattered try-except

**测试**:
- `tests/test_agent_error_handler.py` - 新增 2 个用例：
  - `test_handle_model_error_returns_failure_event`
  - `test_handle_tool_error_records_failure`

**验证**: `pytest tests/test_agent_error_handler.py -v`

---

### 任务 2.4: 实现 MemoryLifecycleManager
**文件**: `app/core/memory_lifecycle.py` (新增)

**实现**:
```python
class MemoryLifecycleManager:
    async def on_turn_complete(self, turn: Turn):
        ...
    
    async def on_session_end(self, session: AgentSession):
        ...
```

**接入**:
- 修改 `app/core/agent_engine.py`:
  - `__init__()` 新增 `self.memory_lifecycle = MemoryLifecycleManager(...)`
  - `_finalize()` 中调用 `await self.memory_lifecycle.on_turn_complete(turn)`
  - 会话结束时调用 `await self.memory_lifecycle.on_session_end(session)`

**测试**:
- `tests/test_memory_lifecycle.py` - 新增 3 个用例：
  - `test_on_turn_complete_records_episodic_memory`
  - `test_on_turn_complete_triggers_reflection`
  - `test_on_session_end_archives_session`

**验证**: `pytest tests/test_memory_lifecycle.py -v`

---

## phase 3: 事件驱动 + 前端 (week 3)

### 任务 3.1: 扩展 EventBus
**文件**: `app/core/event_bus.py` (修改已有)

**改动**:
- 增加 `emit_async()` 支持异步 handler
- 增加 `once()` 一次性监听
- 增加 `remove_listener()`

**接入**:
- 修改 `app/core/agent_engine.py`:
  - 状态转换改为 `await self.event_bus.emit("state:processing", {...})`
  - 工具调用改为 `await self.event_bus.emit("tool:call", {...})`

**测试**:
- `tests/test_event_bus.py` - 新增 2 个用例：
  - `test_emit_calls_all_handlers`
  - `test_once_handler_removed_after_first_call`

**验证**: `pytest tests/test_event_bus.py -v`

---

### 任务 3.2: 创建 MemoryToolSet
**文件**: `app/tools/memory_toolset.py` (新增)

**实现**:
```python
class MemoryToolSet:
    def __init__(self, orchestrator: HierarchicalMemoryOrchestrator):
        ...
    
    def get_tools(self) -> list[dict]:
        ...
    
    async def execute(self, tool_name: str, arguments: dict):
        ...
```

**接入**:
- 修改 `app/tools/__init__.py`:
  - 注册 `memory_toolset` 到 `tool_registry`

**测试**:
- `tests/test_memory_toolset.py` - 新增 3 个用例：
  - `test_remember_creates_episodic_memory`
  - `test_recall_returns_relevant_memories`
  - `test_forget_removes_memory`

**验证**: `pytest tests/test_memory_toolset.py -v`

---

### 任务 3.3: 前端新页面
**文件**: 
- `frontend-react/src/pages/TaskBoardPage.tsx` (新增)
- `frontend-react/src/pages/ApprovalQueuePage.tsx` (新增)
- `frontend-react/src/pages/TraceExplorerPage.tsx` (新增)
- `frontend-react/src/pages/MemoryPage.tsx` (新增)
- `frontend-react/src/App.tsx` (修改，注册路由)

**路由**:
- `/tasks` - Task Board
- `/approvals` - Approval Queue
- `/trace` - Trace Explorer
- `/memory` - Memory Management

**验证**:
- `cd frontend-react && npm run test -- --run`
- `cd frontend-react && npm run build`

---

## 全量验证清单

### Week 1 末
```bash
# 后端
pytest tests/test_memory_orchestrator.py tests/test_context_preparer.py tests/test_p0_runtime_contracts.py tests/test_agent_engine.py -v

# 前端
cd frontend-react && npm run test -- --run
```

### Week 2 末
```bash
# 后端
pytest tests/test_tool_pipeline.py tests/test_checkpoint_manager.py tests/test_agent_error_handler.py tests/test_memory_lifecycle.py tests/test_p0_runtime_contracts.py -v

# 前端
cd frontend-react && npm run test -- --run
```

### Week 3 末
```bash
# 后端全量
pytest tests/ -v --tb=short

# 前端全量
cd frontend-react && npm run test -- --run && npm run build
```

---

## 回滚策略

### 阶段回滚
每个 Phase 完成后打 tag，回滚到上一 Phase tag：
```bash
git tag phase-1-memory-unified
git tag phase-2-tool-pipeline
git tag phase-3-event-driven
```

### 文件级回滚
所有改动通过 Edit 工具 incremental 修改，不删除历史文件。如需回滚：
```bash
git checkout HEAD~1 -- app/core/agent_engine.py
```

### 数据库回滚
Checkpoint 和 Session 状态写入已有表，无需迁移。Memory 表已有，无需改动。

---

## 依赖关系图

```
Phase 1
├── 任务 1.1 (HierarchicalMemoryOrchestrator)
│   └── 无依赖
├── 任务 1.2 (ContextPreparer)
│   └── 依赖 1.1
└── 任务 1.3 (run() 阶段拆分)
    └── 依赖 1.2

Phase 2
├── 任务 2.1 (ToolExecutionPipeline)
│   └── 无依赖
├── 任务 2.2 (CheckpointManager)
│   └── 无依赖
├── 任务 2.3 (AgentErrorHandler)
│   └── 无依赖
└── 任务 2.4 (MemoryLifecycleManager)
    └── 依赖 Phase 1 完成

Phase 3
├── 任务 3.1 (EventBus 扩展)
│   └── 依赖 Phase 2 完成
├── 任务 3.2 (MemoryToolSet)
│   └── 依赖 Phase 1 完成
└── 任务 3.3 (前端页面)
    └── 依赖 Phase 1 完成
```

---

## 下一步行动

1. **确认实施计划**：用户确认后开始 Phase 1
2. **Phase 1 启动**：任务 1.1 - 修复 HierarchicalMemoryOrchestrator
3. **持续验证**：每个任务完成后运行对应测试
4. **阶段交付**：每个 Phase 完成后运行全量验证

---

## 附件：关键代码片段

### A. HierarchicalMemoryOrchestrator.retrieve_for_query()
```python
async def retrieve_for_query(
    self,
    user_id: str,
    agent_id: str,
    query: str,
    session_context: dict,
    token_budget: int = 4000,
) -> list[dict]:
    results = []
    
    # L4: Identity - 固定 500 tokens
    identity = await self._get_identity(agent_id)
    if identity:
        results.append(identity)
        token_budget -= 500
    
    # L3: Semantic - 最多 1000 tokens
    semantic = await self._get_semantic(user_id, query, min(token_budget, 1000))
    results.extend(semantic)
    token_budget -= sum(len(s) for s in semantic)
    
    # L2: Episodic - 最多 1500 tokens
    episodic = await self._get_episodic(user_id, query, min(token_budget, 1500))
    results.extend(episodic)
    token_budget -= sum(len(e) for e in episodic)
    
    # L1: Working - 剩余预算
    working = await self._get_working(session_context, token_budget)
    results.extend(working)
    
    return results
```

### B. ContextPreparer.prepare()
```python
async def prepare(self, session: AgentSession, query: str) -> None:
    try:
        memories = await self.memory_orchestrator.retrieve_for_query(
            user_id=session.user_id,
            agent_id=session.agent_id,
            query=query,
            session_context={"messages": session.messages},
            token_budget=4000,
        )
        
        for memory in memories:
            session.context_layer.add_injected(MessageRole.SYSTEM, memory)
        
        # Core Memory
        blocks = await self.core_memory.get_blocks(
            user_id=session.user_id,
            agent_id=session.agent_id,
        )
        if blocks:
            xml = self.core_memory.format_for_prompt(blocks)
            session.context_layer.add_injected(MessageRole.SYSTEM, xml)
    except Exception:
        pass  # 记忆失败不影响主流程
```

### C. AgentEngine.run() 拆分后
```python
async def run(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
    """协调器，保持不变"""
    turn = await self._initialize(session, message)
    
    async for event in self._react_loop(session, message):
        yield event
    
    yield await self._finalize(session, turn)
```

---

**文档版本**: v1.0  
**创建日期**: 2026-07-30  
**状态**: 待用户确认后实施
