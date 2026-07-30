# AGI Ready 最小侵入架构升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改 AgentEngine 核心执行循环的前提下，通过新增薄抽象层实现 AGI 就绪能力

**Architecture:** 3 个 Phase，共 11 个新文件，5 个文件修改。所有新功能通过依赖注入接入，不动核心执行循环。

**Tech Stack:** Python 3.11, SQLAlchemy 2.x, FastAPI, React 19, TypeScript

## Global Constraints

- 不动 `AgentEngine.run()` 签名
- 不动现有消息循环
- 不动现有 SSE 流式响应
- 所有新功能通过依赖注入接入
- 数据库保持 SQLite 单文件
- 前端新增页面并行，不替换现有页面
- 单文件不超过 300 行
- 新增文件不超过 15 个

---

## Phase 1: 执行模型升级

### Task 1: ExecutionState 状态枚举

**Files:**
- Create: `app/core/execution_state.py`
- Test: `tests/test_execution_state.py`

**Interfaces:**
- Consumes: None
- Produces: `ExecutionState` enum

- [ ] **Step 1: Write the failing test**

```python
def test_execution_state_enum():
    from app.core.execution_state import ExecutionState
    assert ExecutionState.IDLE.value == "idle"
    assert ExecutionState.THINKING.value == "thinking"
    assert ExecutionState.EXECUTING.value == "executing"
    assert ExecutionState.AWAITING_HUMAN.value == "awaiting_human"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_execution_state.py -v`
Expected: FAIL with "cannot import name 'ExecutionState'"

- [ ] **Step 3: Write minimal implementation**

```python
from enum import Enum

class ExecutionState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    AWAITING_HUMAN = "awaiting_human"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_execution_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/execution_state.py tests/test_execution_state.py
git commit -m "feat: add ExecutionState enum for agent execution states"
```

### Task 2: ContextLayer 分层上下文

**Files:**
- Create: `app/core/context_layer.py`
- Test: `tests/test_context_layer.py`

**Interfaces:**
- Consumes: None
- Produces: `ContextLayer` class with `add_injected()`, `build_prompt()`, `compress_injected()`

- [ ] **Step 1: Write the failing test**

```python
def test_context_layer_build_prompt():
    from app.core.context_layer import ContextLayer
    from app.core import MessageRole
    
    layer = ContextLayer()
    layer.add_injected(MessageRole.SYSTEM, "injected memory")
    
    core = [
        {"role": MessageRole.USER, "content": "hello"},
        {"role": MessageRole.ASSISTANT, "content": "hi"},
    ]
    
    prompt = layer.build_prompt(core)
    assert prompt[0] == {"role": MessageRole.SYSTEM, "content": "injected memory"}
    assert prompt[1] == {"role": MessageRole.USER, "content": "hello"}
    assert prompt[2] == {"role": MessageRole.ASSISTANT, "content": "hi"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context_layer.py -v`
Expected: FAIL with "cannot import name 'ContextLayer'"

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from typing import Any
from app.core import MessageRole

class ContextLayer:
    def __init__(self):
        self.injected: list[dict[str, Any]] = []
        self.core: list[dict[str, Any]] = []
    
    def add_injected(self, role: MessageRole, content: str) -> None:
        self.injected.append({"role": role.value, "content": content})
    
    def build_prompt(self, core_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [*self.injected, *core_messages]
    
    def compress_injected(self) -> None:
        self.injected = self.injected[-4:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context_layer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/context_layer.py tests/test_context_layer.py
git commit -m "feat: add ContextLayer for separating injected context from core messages"
```

### Task 3: TurnExecutor 包装层

**Files:**
- Create: `app/core/turn_executor.py`
- Test: `tests/test_turn_executor.py`

**Interfaces:**
- Consumes: `AgentEngine`, `TurnRepository`
- Produces: `TurnExecutor` class with `start()`, `pause()`, `resume()`, `cancel()`, `events()`

- [ ] **Step 1: Write the failing test**

```python
def test_turn_executor_start_creates_turn():
    from app.core.turn_executor import TurnExecutor
    from app.core.agent_engine import AgentEngine
    from app.storage.repository import TurnRepository
    
    engine = AgentEngine(...)
    executor = TurnExecutor(engine, TurnRepository())
    
    # Mock AgentEngine.run to yield events
    async def mock_run(session, message):
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "hello"})
        yield AgentEvent(type=AgentEventType.DONE, data={"status": "completed"})
    
    engine.run = mock_run
    
    session = engine.create_session(...)
    turn = await executor.start(session, "test")
    
    assert turn.id is not None
    assert turn.status == "running"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_turn_executor.py -v`
Expected: FAIL with "cannot import name 'TurnExecutor'"

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
import asyncio
from typing import AsyncIterator
from app.core import AgentEngine, AgentSession, AgentEvent, AgentEventType
from app.storage.repository import TurnRepository

class TurnExecutor:
    def __init__(self, engine: AgentEngine, turn_repo: TurnRepository):
        self._engine = engine
        self._turn_repo = turn_repo
        self._turns: dict[str, asyncio.Event] = {}
    
    async def start(self, session: AgentSession, message: str) -> Turn:
        turn = await self._turn_repo.create(
            session_id=session.session_id,
            status="running",
            metadata_={"message": message},
        )
        session.current_turn_id = turn.id
        self._turns[turn.id] = asyncio.Event()
        return turn
    
    async def pause(self, turn_id: str) -> None:
        pass  # Future: implement pause logic
    
    async def resume(self, turn_id: str) -> None:
        if turn_id in self._turns:
            self._turns[turn_id].set()
    
    async def cancel(self, turn_id: str) -> None:
        if turn_id in self._turns:
            self._turns[turn_id].set()
    
    async def events(self, session: AgentSession, message: str) -> AsyncIterator[AgentEvent]:
        turn = await self.start(session, message)
        async for event in self._engine.run(session, message):
            yield event
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_turn_executor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/turn_executor.py tests/test_turn_executor.py
git commit -m "feat: add TurnExecutor wrapper for turn lifecycle management"
```

### Task 4: AgentSession 状态字段扩展

**Files:**
- Modify: `app/core/agent_engine.py` (AgentSession class)
- Test: `tests/test_agent_session_state.py`

**Interfaces:**
- Consumes: `ExecutionState`
- Produces: `AgentSession.execution_state`, `AgentSession.context_layer`

- [ ] **Step 1: Write the failing test**

```python
def test_agent_session_has_execution_state():
    from app.core.agent_engine import AgentSession
    from app.core.execution_state import ExecutionState
    
    session = AgentSession(
        session_id="test",
        agent_id="agent",
        user_id="user",
        provider="openai",
        model_id="gpt-4",
        api_key="key",
    )
    
    assert hasattr(session, "execution_state")
    assert session.execution_state == ExecutionState.IDLE
    assert hasattr(session, "context_layer")
    assert session.context_layer is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_session_state.py -v`
Expected: FAIL with "AttributeError: 'AgentSession' object has no attribute 'execution_state'"

- [ ] **Step 3: Write minimal implementation**

```python
# In AgentSession.__init__ (app/core/agent_engine.py)
from app.core.execution_state import ExecutionState
from app.core.context_layer import ContextLayer

class AgentSession:
    def __init__(self, ...):
        # ... existing fields ...
        self.execution_state = ExecutionState.IDLE
        self.context_layer = ContextLayer()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent_session_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/agent_engine.py tests/test_agent_session_state.py
git commit -m "feat: add execution_state and context_layer to AgentSession"
```

### Task 5: AgentEngine 注入点改为 ContextLayer

**Files:**
- Modify: `app/core/agent_engine.py`
- Test: `tests/test_context_layer_integration.py`

**Interfaces:**
- Consumes: `ContextLayer`
- Produces: Modified `AgentEngine.run()` using `context_layer.build_prompt()`

- [ ] **Step 1: Write the failing test**

```python
def test_agent_engine_uses_context_layer():
    from app.core.agent_engine import AgentEngine
    from app.core.context_layer import ContextLayer
    
    engine = AgentEngine(...)
    session = engine.create_session(...)
    session.context_layer.add_injected(MessageRole.SYSTEM, "injected")
    
    # Verify build_prompt includes injected context
    prompt = session.context_layer.build_prompt(session.messages)
    assert len(prompt) == 2  # injected + system prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context_layer_integration.py -v`
Expected: FAIL with assertion error

- [ ] **Step 3: Write minimal implementation**

```python
# In AgentEngine.run(), replace:
# session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": memory_context})
# with:
session.context_layer.add_injected(MessageRole.SYSTEM, memory_context)

# Before adapter call, replace:
# messages=session.messages
# with:
# messages=session.context_layer.build_prompt(session.messages)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context_layer_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/agent_engine.py tests/test_context_layer_integration.py
git commit -m "refactor: use ContextLayer for memory injection in AgentEngine.run()"
```

---

## Phase 2: 安全与可观测性

### Task 6: ToolCallTracker 薄层

**Files:**
- Create: `app/core/tool_call_tracker.py`
- Test: `tests/test_tool_call_tracker.py`

**Interfaces:**
- Consumes: None
- Produces: `ToolCallTracker` class with `track()`, `get_by_id()`

- [ ] **Step 1: Write the failing test**

```python
def test_tool_call_tracker_by_id():
    from app.core.tool_call_tracker import ToolCallTracker
    
    tracker = ToolCallTracker()
    tool_calls = [
        {"id": "call-1", "function": {"name": "read_file", "arguments": "{}"}},
        {"id": "call-2", "function": {"name": "write_file", "arguments": "{}"}},
    ]
    
    tracked = tracker.track(tool_calls)
    assert tracker.get_by_id(tracked, "call-1") == "read_file"
    assert tracker.get_by_id(tracked, "call-2") == "write_file"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tool_call_tracker.py -v`
Expected: FAIL with "cannot import name 'ToolCallTracker'"

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from typing import Any

class ToolCallTracker:
    def track(self, tool_calls: list[dict[str, Any]]) -> dict[str, str]:
        return {
            tc.get("id", ""): tc.get("function", {}).get("name", "")
            for tc in tool_calls
        }
    
    def get_by_id(self, tracker: dict[str, str], call_id: str) -> str:
        return tracker.get(call_id, "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tool_call_tracker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/tool_call_tracker.py tests/test_tool_call_tracker.py
git commit -m "feat: add ToolCallTracker for safe tool call result matching"
```

### Task 7: ApprovalGate 拦截器

**Files:**
- Create: `app/core/approval_gate.py`
- Create: `app/storage/models_approvals.py`
- Create: `app/api/v1/approvals.py`
- Test: `tests/test_approval_gate.py`

**Interfaces:**
- Consumes: `ToolRegistry`, `TurnRepository`
- Produces: `ApprovalGate` class with `check()`, `approve()`, `reject()`

- [ ] **Step 1: Write the failing test**

```python
def test_approval_gate_blocks_write_file():
    from app.core.approval_gate import ApprovalGate
    
    gate = ApprovalGate()
    result = await gate.check("write_file", {"path": "/tmp/test.txt"})
    assert result.requires_approval is True
    assert result.tool_name == "write_file"

def test_approval_gate_allows_read_file():
    from app.core.approval_gate import ApprovalGate
    
    gate = ApprovalGate()
    result = await gate.check("read_file", {"path": "/tmp/test.txt"})
    assert result.requires_approval is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_approval_gate.py -v`
Expected: FAIL with "cannot import name 'ApprovalGate'"

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass
class ApprovalResult:
    requires_approval: bool
    tool_name: str
    reason: str | None = None

class ApprovalGate:
    HIGH_RISK_TOOLS = {"write_file", "run_command", "delete"}
    
    async def check(self, tool_name: str, arguments: dict) -> ApprovalResult:
        if tool_name in self.HIGH_RISK_TOOLS:
            return ApprovalResult(
                requires_approval=True,
                tool_name=tool_name,
                reason=f"Tool '{tool_name}' requires human approval",
            )
        return ApprovalResult(requires_approval=False, tool_name=tool_name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_approval_gate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/approval_gate.py app/storage/models_approvals.py app/api/v1/approvals.py tests/test_approval_gate.py
git commit -m "feat: add ApprovalGate for high-risk tool interception"
```

### Task 8: TraceCollector 追踪收集

**Files:**
- Create: `app/core/trace_collector.py`
- Test: `tests/test_trace_collector.py`

**Interfaces:**
- Consumes: None
- Produces: `TraceCollector` class with `emit_span()`, `get_trace()`

- [ ] **Step 1: Write the failing test**

```python
def test_trace_collector_emit_and_get():
    from app.core.trace_collector import TraceCollector
    
    collector = TraceCollector()
    span_id = collector.emit_span(
        task_id="task-1",
        turn_id="turn-1",
        span_type="model_call",
        name="gpt-4o",
        input={"messages": []},
        output={"content": "hello"},
    )
    
    trace = collector.get_trace("task-1")
    assert len(trace) == 1
    assert trace[0]["span_type"] == "model_call"
    assert trace[0]["name"] == "gpt-4o"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trace_collector.py -v`
Expected: FAIL with "cannot import name 'TraceCollector'"

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from typing import Any
from collections import defaultdict

class TraceCollector:
    def __init__(self):
        self._traces: dict[str, list[dict[str, Any]]] = defaultdict(list)
    
    def emit_span(
        self,
        task_id: str,
        turn_id: str,
        span_type: str,
        name: str,
        input: dict,
        output: dict,
    ) -> str:
        import uuid
        span_id = str(uuid.uuid4())
        self._traces[task_id].append({
            "id": span_id,
            "turn_id": turn_id,
            "span_type": span_type,
            "name": name,
            "input": input,
            "output": output,
        })
        return span_id
    
    def get_trace(self, task_id: str) -> list[dict[str, Any]]:
        return self._traces.get(task_id, [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trace_collector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/trace_collector.py tests/test_trace_collector.py
git commit -m "feat: add TraceCollector for execution tracing"
```

---

## Phase 3: 任务抽象与前端

### Task 9: Task Board 后端

**Files:**
- Create: `app/storage/models_tasks.py`
- Create: `app/api/v1/tasks.py`
- Test: `tests/test_tasks_api.py`

**Interfaces:**
- Consumes: None
- Produces: Task CRUD API

- [ ] **Step 1: Write the failing test**

```python
def test_create_and_get_task(client):
    response = client.post("/api/v1/tasks", json={
        "title": "Test Task",
        "description": "A test task",
        "agent_id": "agent-1",
    })
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "Test Task"
    
    response = client.get(f"/api/v1/tasks/{task['id']}")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tasks_api.py -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: Write minimal implementation**

```python
# app/storage/models_tasks.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.storage.database import Base

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# app/api/v1/tasks.py
from fastapi import APIRouter, Depends
from app.storage.repository import TaskRepository

router = APIRouter()

@router.post("/tasks")
async def create_task(data: dict, user_id: str = Depends(get_current_user)):
    async with async_session() as db:
        repo = TaskRepository(db)
        task = await repo.create(
            title=data["title"],
            description=data.get("description"),
            agent_id=data["agent_id"],
            user_id=user_id,
        )
        return task

@router.get("/tasks")
async def list_tasks(user_id: str = Depends(get_current_user)):
    async with async_session() as db:
        repo = TaskRepository(db)
        tasks = await repo.list_by_user(user_id)
        return {"items": tasks, "total": len(tasks)}

@router.get("/tasks/{task_id}")
async def get_task(task_id: str, user_id: str = Depends(get_current_user)):
    async with async_session() as db:
        repo = TaskRepository(db)
        task = await repo.get_by_id(task_id)
        if task is None or task.user_id != user_id:
            raise HTTPException(status_code=404)
        return task
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tasks_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/storage/models_tasks.py app/api/v1/tasks.py tests/test_tasks_api.py
git commit -m "feat: add Task Board backend API"
```

### Task 10: Agent 身份编辑器后端

**Files:**
- Create: `app/storage/models_agent_personas.py`
- Create: `app/api/v1/agent_personas.py`
- Test: `tests/test_agent_personas_api.py`

**Interfaces:**
- Consumes: None
- Produces: AgentPersona CRUD API

- [ ] **Step 1: Write the failing test**

```python
def test_create_and_get_agent_persona(client):
    response = client.post("/api/v1/agents/agent-1/persona", json={
        "name": "CodeReviewer",
        "description": "Senior Python engineer",
        "core_memories": ["Use async", "Parameterize queries"],
        "tools_whitelist": ["read_file", "write_file"],
        "auto_approve_tools": ["read_file"],
    })
    assert response.status_code == 200
    
    response = client.get("/api/v1/agents/agent-1/persona")
    assert response.status_code == 200
    assert response.json()["name"] == "CodeReviewer"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_personas_api.py -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: Write minimal implementation**

```python
# app/storage/models_agent_personas.py
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, func
from app.storage.database import Base

class AgentPersona(Base):
    __tablename__ = "agent_personas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    core_memories = Column(JSON, default=list)
    tools_whitelist = Column(JSON, default=list)
    auto_approve_tools = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# app/api/v1/agent_personas.py
from fastapi import APIRouter, Depends, HTTPException
from app.storage.repository import AgentPersonaRepository

router = APIRouter()

@router.get("/agents/{agent_id}/persona")
async def get_persona(agent_id: str, user_id: str = Depends(get_current_user)):
    async with async_session() as db:
        repo = AgentPersonaRepository(db)
        persona = await repo.get_by_agent_id(agent_id)
        if persona is None:
            raise HTTPException(status_code=404)
        return persona

@router.post("/agents/{agent_id}/persona")
async def create_persona(agent_id: str, data: dict, user_id: str = Depends(get_current_user)):
    async with async_session() as db:
        repo = AgentPersonaRepository(db)
        persona = await repo.create(agent_id=agent_id, **data)
        return persona

@router.patch("/agents/{agent_id}/persona")
async def update_persona(agent_id: str, data: dict, user_id: str = Depends(get_current_user)):
    async with async_session() as db:
        repo = AgentPersonaRepository(db)
        persona = await repo.update(agent_id, **data)
        if persona is None:
            raise HTTPException(status_code=404)
        return persona
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent_personas_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/storage/models_agent_personas.py app/api/v1/agent_personas.py tests/test_agent_personas_api.py
git commit -m "feat: add Agent Persona editor backend API"
```

### Task 11: 前端新页面与路由

**Files:**
- Create: `frontend-react/src/pages/TaskBoardPage.tsx`
- Create: `frontend-react/src/pages/ApprovalQueuePage.tsx`
- Create: `frontend-react/src/pages/TraceExplorerPage.tsx`
- Create: `frontend-react/src/pages/AgentPersonaPage.tsx`
- Modify: `frontend-react/src/App.tsx`
- Modify: `frontend-react/src/api.ts`

**Interfaces:**
- Consumes: Task API, Approval API, Trace API, AgentPersona API
- Produces: 4 new frontend pages

- [ ] **Step 1: Write the failing test**

```typescript
// frontend-react/src/__tests__/TaskBoardPage.test.ts
describe('TaskBoardPage', () => {
  it('renders task list', async () => {
    const page = await render(<TaskBoardPage />);
    expect(page.getByText('Task Board')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-react && npm test -- --run src/__tests__/TaskBoardPage.test.ts`
Expected: FAIL with "Cannot find module"

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend-react/src/pages/TaskBoardPage.tsx
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function TaskBoardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => api.get('/tasks').then(r => r.json()),
  });
  
  if (isLoading) return <div>Loading...</div>;
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Task Board</h1>
      <div className="grid gap-4">
        {data?.items?.map((task: any) => (
          <div key={task.id} className="border rounded p-4">
            <h3 className="font-semibold">{task.title}</h3>
            <p className="text-gray-600">{task.description}</p>
            <span className="text-sm text-gray-500">Status: {task.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Register routes in App.tsx**

```typescript
// frontend-react/src/App.tsx
import { TaskBoardPage } from './pages/TaskBoardPage';
import { ApprovalQueuePage } from './pages/ApprovalQueuePage';
import { TraceExplorerPage } from './pages/TraceExplorerPage';
import { AgentPersonaPage } from './pages/AgentPersonaPage';

// Add to Page type and navItems
type Page = /* existing */ | 'task-board' | 'approval-queue' | 'trace-explorer' | 'agent-persona';

const navItems = [
  // ... existing
  { id: 'task-board', icon: Cpu, label: '任务看板', group: 'main' },
  { id: 'approval-queue', icon: Bell, label: '审批队列', group: 'main' },
  { id: 'trace-explorer', icon: Activity, label: '执行追踪', group: 'main' },
];
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend-react && npm test -- --run src/__tests__/TaskBoardPage.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/pages/TaskBoardPage.tsx frontend-react/src/pages/ApprovalQueuePage.tsx frontend-react/src/pages/TraceExplorerPage.tsx frontend-react/src/pages/AgentPersonaPage.tsx frontend-react/src/App.tsx frontend-react/src/api.ts
git commit -m "feat: add AGI frontend pages (Task Board, Approval Queue, Trace Explorer, Agent Persona)"
```

---

## 实施检查清单

### 代码质量
- [ ] 核心文件改动 < 5 个
- [ ] 新增文件 < 15 个
- [ ] 单文件 < 300 行
- [ ] 测试覆盖率新增 > 80%

### 功能验证
- [ ] 后端测试：47 passed + 新增测试通过
- [ ] 前端测试：84 passed + 新增测试通过
- [ ] `run()` 签名不变
- [ ] SSE 流式响应兼容

### AGI 就绪度
- [ ] Turn 可暂停/恢复/取消
- [ ] 审批队列可拦截高风险工具
- [ ] Trace 可展示完整执行链
- [ ] Task Board 可管理 Agent 任务
- [ ] Agent Persona 可编辑身份配置

---

## 执行方式选择

**1. Subagent-Driven (推荐)** - 我为每个 Task 分发一个 subagent，在 Task 之间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中按 Task 顺序执行，使用 executing-plans skill 分批执行并检查点

请选择执行方式。
