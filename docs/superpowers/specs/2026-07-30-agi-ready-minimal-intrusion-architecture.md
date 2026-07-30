# AGI Ready: 最小侵入架构升级 Spec

## 1. 背景与目标

### 现状
- `AgentEngine.run()` 是 async generator，无法暂停/恢复
- 记忆注入直接 `session.messages.insert(-1, ...)`，污染核心消息
- 工具调用无拦截机制，无法实现人类审批
- 无任务级抽象，只有 Session/对话
- 无执行追踪，Agent 行为黑盒
- 前端是"聊天页面集合"，非"Agent 管理面板"

### 目标
在不修改 `AgentEngine` 核心执行循环的前提下，通过新增薄抽象层，实现：

1. **可暂停的执行模型** - Turn 级生命周期管理
2. **分层上下文** - 注入记忆与核心消息分离
3. **安全拦截** - 高风险工具前置审批
4. **可观测性** - Trace 级执行追踪
5. **任务抽象** - Task Board + Approval Queue + Trace Explorer

## 2. 约束

### 硬约束
- **不动 `AgentEngine.run()` 签名**
- **不动现有消息循环**
- **不动现有 SSE 流式响应**
- 所有新功能通过依赖注入接入
- 数据库保持 SQLite 单文件
- 前端新增页面并行，不替换现有页面

### 软约束
- 优先复用已有模型（Turn、Checkpoint、Session）
- 新增文件数量控制在 15 个以内
- 单文件职责单一，不超过 300 行

## 3. 5 个 AGI 卡点的薄层解决方案

### 卡点 1：run() 无法暂停

**方案**：新增 `TurnExecutor` 包装层

```
新增: app/core/turn_executor.py
接口:
  - async start(session, message) -> Turn
  - async pause(turn_id)
  - async resume(turn_id)
  - async cancel(turn_id)
  - async events(turn_id) -> AsyncIterator[AgentEvent]
```

**实现**：
- `TurnExecutor` 内部调用 `AgentEngine.run()`
- 在 `AgentEngine` 的 checkpoint yield 点注入 `asyncio.Event`
- 外部控制 `event.set()` 决定继续/暂停
- `TurnExecutor` 持有 `Turn` 生命周期，`AgentEngine` 无感知

**改动**：
- 新增 1 个文件
- 修改 0 个核心文件

### 卡点 2：tool_call_map 覆盖风险

**现状**：当前代码用 `accumulated_tool_calls[idx]` 按索引聚合，不存在覆盖问题

**防护**：新增 `ToolCallTracker` 薄层

```
新增: app/core/tool_call_tracker.py
接口:
  - track(tool_calls) -> CallTracker
  - get_by_id(tracker, call_id) -> ToolCall
```

**实现**：
- 在 `ParallelToolExecutor.execute_all()` 前插入 tracker
- 用 `call_id` 做 key，不是 `name`
- 工具结果回传时通过 tracker 反查 name
- 不改动现有工具执行逻辑

**改动**：
- 新增 1 个文件
- 修改 0 个核心文件

### 卡点 3：锁粒度太粗

**方案**：新增 `ExecutionState` 状态枚举

```
新增: app/core/execution_state.py
  - class ExecutionState(Enum):
        IDLE = "idle"
        THINKING = "thinking"
        EXECUTING = "executing"
        AWAITING_HUMAN = "awaiting_human"

修改: AgentSession.__init__
  - 新增: self.execution_state = ExecutionState.IDLE
```

**实现**：
- `TurnExecutor.start()` 设为 THINKING
- 工具执行时设为 EXECUTING
- 暂停时设为 AWAITING_HUMAN
- 只加字段，不加锁
- 前端通过 `execution_state` 判断是否可中断

**改动**：
- 新增 1 个文件
- 修改 1 个文件（`AgentSession.__init__`，只加一行）

### 卡点 4：记忆注入污染 messages

**方案**：新增 `ContextLayer` 分层

```
新增: app/core/context_layer.py
接口:
  - class ContextLayer:
        def __init__(self)
        def add_injected(self, role, content)
        def build_prompt(self, core_messages) -> list[dict]
        def compress_injected(self)

修改: AgentSession
  - 新增: self.context_layer = ContextLayer()
  - session.messages 只存核心对话
  - 注入的记忆存入 context_layer.injected
```

**实现**：
- 在 `_build_tools()` 或 adapter 调用前，用 `context_layer.build_prompt()` 替换 `session.messages`
- 压缩只作用于 core 层
- 持久化时分别存储

**改动**：
- 新增 1 个文件
- 修改 2 个文件（`AgentSession.__init__`、`AgentEngine.run()` 的注入点）

### 卡点 5：前端 fetch 散点

**现状**：已集中到 `ApiClient`，但类型不完整

**方案**：类型补全 + 新 Hook

```
修改: frontend-react/src/api.ts
  - 补充完整泛型类型
  - 不改架构，只加类型

新增: frontend-react/src/hooks/
  - useTaskBoard.ts
  - useApprovalQueue.ts
  - useTraceExplorer.ts
```

**实现**：
- 现有 `ApiClient` 保留，补充泛型类型
- 新 hook 封装新 API
- 不动现有页面逻辑

**改动**：
- 新增 3 个文件
- 修改 1 个文件（`api.ts`，只加类型定义）

---

## 4. 从零构建的 5 项能力

### 4.1 Task Board

**新增文件**：
- `app/api/v1/tasks.py` - Task CRUD
- `app/storage/models_tasks.py` - Task, SubGoal, Artifact 模型
- `frontend-react/src/pages/TaskBoardPage.tsx`

**最小实现**：
- Task 只存 `id/title/description/status/agent_id/user_id`
- 一个 Session 对应一个 Task（先不做分支）
- 前端用现有 `ApiClient` 调用

**API**：
```
POST   /tasks
GET    /tasks
GET    /tasks/{id}
PATCH  /tasks/{id}
DELETE /tasks/{id}
GET    /tasks/{id}/turns
```

### 4.2 Approval Queue

**新增文件**：
- `app/core/approval_gate.py` - 拦截器
- `app/api/v1/approvals.py` - 审批 API
- `app/storage/models_approvals.py` - Approval 模型

**最小实现**：
- 在 `ParallelToolExecutor.execute_all()` 前加拦截
- 高风险工具列表：`write_file`, `run_command`, `delete`
- 审批通过前工具不执行
- 低风险工具自动通过

**API**：
```
GET    /approvals
GET    /approvals/{id}
POST   /approvals/{id}/approve
POST   /approvals/{id}/reject
POST   /approvals/{id}/auto-approve  # 批量规则
```

### 4.3 Trace Explorer

**新增文件**：
- `app/core/trace_collector.py` - Span 收集
- `app/api/v1/traces.py` - Trace API
- 复用已有 `app/storage/models_traces.py`

**最小实现**：
- 在 `AgentEngine` 关键节点 emit span（通过事件监听）
- 不改变事件流，只是额外记录
- 前端树形展示

**API**：
```
GET /tasks/{id}/trace
GET /tasks/{id}/trace?turn_id={turn_id}
GET /tasks/{id}/trace?span_id={span_id}
```

### 4.4 Agent 身份编辑器

**新增文件**：
- `app/api/v1/agent_personas.py`
- `app/storage/models_agent_personas.py`

**最小实现**：
- 新增表 `agent_personas`
- 前端 `/agents/{id}/persona` 页面
- 与现有 Agent 模型解耦

**API**：
```
GET    /agents/{id}/persona
PATCH  /agents/{id}/persona
```

### 4.5 回归评测集

**新增文件**：
- `app/evals/runner.py`
- `app/evals/suites/` - 评测用例目录
- `app/evals/models.py` - EvalSuite, EvalCase 模型

**最小实现**：
- CLI 命令：`python -m app.evals run --suite safety`
- 通过 `FakeModelAdapter` 运行
- 结果写入 `eval_runs` 表

**CLI**：
```bash
python -m app.evals run --suite safety
python -m app.evals run --suite safety --case case-1
python -m app.evals list
```

---

## 5. 实施计划

### Phase 1：执行模型升级（1 周）

**目标**：Turn 级生命周期管理 + 分层上下文

**任务**：
1. 新增 `app/core/execution_state.py`
2. 新增 `app/core/context_layer.py`
3. 新增 `app/core/turn_executor.py`
4. 修改 `AgentSession.__init__` 加 `execution_state` + `context_layer`
5. 修改 `AgentEngine.run()` 注入点改为 `context_layer`
6. 新增 `tests/test_turn_executor.py`
7. 新增 `tests/test_context_layer.py`

**验证**：
- 后端核心测试通过（47 passed）
- 前端测试通过（84 passed）
- 新增 4 个测试文件，覆盖 TurnExecutor、ContextLayer

### Phase 2：安全与可观测性（1 周）

**目标**：审批拦截 + 执行追踪

**任务**：
1. 新增 `app/core/tool_call_tracker.py`
2. 新增 `app/core/approval_gate.py`
3. 新增 `app/core/trace_collector.py`
4. 修改 `ParallelToolExecutor.execute_all()` 加入口
5. 新增 `app/api/v1/approvals.py`
6. 新增 `app/api/v1/traces.py`
7. 新增 `app/storage/models_approvals.py`
8. 新增 `tests/test_approval_gate.py`
9. 新增 `tests/test_trace_collector.py`

**验证**：
- 后端核心测试通过
- 新增 5 个测试文件

### Phase 3：任务抽象与前端（1 周）

**目标**：Task Board + Agent Persona + Eval

**任务**：
1. 新增 `app/api/v1/tasks.py`
2. 新增 `app/storage/models_tasks.py`
3. 新增 `app/api/v1/agent_personas.py`
4. 新增 `app/storage/models_agent_personas.py`
5. 新增 `app/evals/runner.py`
6. 新增 `app/evals/models.py`
7. 新增 `app/evals/suites/safety.py`
8. 新增 `frontend-react/src/pages/TaskBoardPage.tsx`
9. 新增 `frontend-react/src/pages/AgentPersonaPage.tsx`
10. 新增 `frontend-react/src/hooks/useTaskBoard.ts`
11. 新增 `frontend-react/src/hooks/useApprovalQueue.ts`
12. 新增 `frontend-react/src/hooks/useTraceExplorer.ts`
13. 修改 `frontend-react/src/App.tsx` 注册新页面
14. 修改 `frontend-react/src/api.ts` 补充类型

**验证**：
- 后端核心测试通过
- 前端测试通过
- 新增 6 个测试文件

---

## 6. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| TurnExecutor 包装层引入性能开销 | 中 | 低 | 通过 asyncio.Event 实现，无额外线程 |
| ContextLayer 导致 prompt 组装错误 | 低 | 高 | 单元测试覆盖 build_prompt() 所有组合 |
| ApprovalGate 拦截导致工具链断裂 | 中 | 高 | 默认白名单机制，低风险工具自动通过 |
| TraceCollector 影响主循环性能 | 低 | 中 | 异步写入，失败不阻断主流程 |
| 前端新页面与现有页面状态冲突 | 中 | 低 | 新增页面独立路由，共享 ApiClient |

---

## 7. 成功标准

### 代码质量
- 核心文件改动 < 5 个
- 新增文件 < 15 个
- 单文件 < 300 行
- 测试覆盖率新增 > 80%

### 功能验证
- 后端测试：47 passed + 新增测试通过
- 前端测试：84 passed + 新增测试通过
- `run()` 签名不变
- SSE 流式响应兼容

### AGI 就绪度
- Turn 可暂停/恢复/取消
- 审批队列可拦截高风险工具
- Trace 可展示完整执行链
- Task Board 可管理 Agent 任务
- Agent Persona 可编辑身份配置

---

## 8. 待确认事项

1. **ApprovalGate 的默认策略**：建议默认只拦截 `write_file`、`run_command`、`delete`，其他自动通过。是否接受？
2. **Trace 存储策略**：建议异步写入 SQLite，失败不阻断主流程。是否接受？
3. **前端路由**：建议新页面用 `/tasks`、`/approvals`、`/trace`，是否接受？

确认后进入实施计划。
