# 接口定义

> 核心类型与接口。以真实源码为准（详见行号引用）。

## 执行引擎

### AgentEngine（`app/core/agent_engine.py`）

主线执行引擎，由 `app/main.py` 注册为 DI 单例。

- `create_session(...) -> AgentSession`：创建会话。
- `run(session, message)`：async generator，产出 `AgentEvent` 流：
  ```python
  async for event in engine.run(session, message):
      ...
  ```
- `run_agent(...) -> dict`：兼容方法，聚合输出并返回 `output` 与 `tokens_used`。
- `resolve_permission(...)`：批准或拒绝 ASK 权限请求，等待其完成。
- `get_permission_config()`：返回当前真实权限配置。

### PregelEngine（`app/core/engine/pregel/`）

图执行内核，已加固并发隔离与中断恢复。**当前未接入主线**。

- `run(graph_input)` / `astream(graph_input)` / `astream_events(graph_input)`：每次调用独立 `ExecutionContext`；缺少 `thread_id` 自动生成 UUID。
- `interrupt_before`：checkpoint 保留被拦截节点，resume 后先执行该节点。
- `interrupt_after`：先合并节点更新再中断，resume 后从后继节点继续。
- `TimeoutPolicy.node_timeout` / `run_timeout`：超时进入 ErrorHandler 并输出 ERROR 事件。
- `update_state`：从线程最新 checkpoint 继承 step、pending nodes 与 parent ID。

## 会话

### AgentSession（`app/core/session.py`）

- `snapshot() -> dict`：序列化 config/context、messages、status、iteration、stop、error、tool results、turn/pause/terminate/resume 状态；排除 Lock/Event/Task 等运行时对象。
- `from_snapshot(data)`：从快照恢复会话。
- `app/core/engine/session.py`：兼容 re-export facade。

## Checkpoint（`app/core/checkpoint.py`）

`SQLiteCheckpointStore` 保存并恢复：

- `channel_values`
- `channel_versions`
- `versions_seen`
- `pending_writes`
- `tool_results`

`ensure_checkpoint_schema()` 幂等为既有表补列；历史记录缺失字段使用安全默认值。`CheckpointRecord` 提供对应存储列。

## Principal（`app/core/principal.py`）

```python
@dataclass(frozen=True, slots=True)
class Principal:
    subject_id: str
    tenant_id: str | None = None
    role: str | None = None
    scopes: tuple[str, ...] = ()
    auth_method: str = "local"
```

- `identity_key -> str`：`f"{auth_method}:{tenant_id or 'default'}:{subject_id}"`，用于限流与审计。
- `CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]`：FastAPI 依赖注入入口。
- `principal_context`：request-scoped `ContextVar`，经 `set_current_principal` / `reset_current_principal` 管理。
- local 模式（`enable_auth=false`）仅在 `get_current_principal` 处生成 `subject_id="default-user"`。

## 权限

- `PermissionOverlay`（多文件）：更具体 scope 覆盖泛化 scope；同层 `DENY > ASK > ALLOW`；user deny 覆盖 default allow。
- ASK 校验返回结构化 `requires_approval`；AgentEngine 创建 pending permission、发送审批事件、等待 `resolve_permission`，超时 fail-closed；批准后仍执行 schema 与 sandbox 验证。

## API 契约

- 写请求模型位于 `app/schemas/api_v1/`：命名 Pydantic 模型，`extra=forbid`，兼容 `{data:{...}}` envelope。
- 已迁移资源：Agents、Workflows、Crews、Groups、Tasks、Skills。
- Agent 响应脱敏：移除 `api_key`、`api_key_encrypted`、`env`、`environment`。
- 尾斜杠兼容路由：`include_in_schema=False`，不进入 OpenAPI。
- 归属校验：Workflow/Crew run 的 agent_id、group member 的 agent_id、task worker/reviewer 均验证属于当前用户/父 group。
- 限流键：`Principal.identity_key`。
- 认证：未认证 HTTP 401；未认证 WebSocket 4401；JWT 携带 `Authorization: Bearer <token>`。

## 协作

### GroupCollaborationEngine（`app/core/collaboration/base.py`）

统一协作主实现，公开 API 包括 `run_task`、`run_group_tasks`、`handoff_task`、`cancel_task` 与 review state 管理。通过 `app/tools/builtins.py::get_group_collaboration_engine()` 延迟获取。

## 中间件

- `app/middleware/auth.py`：写入 `request.state.auth`。
- `app/middleware/security.py`：`RateLimitMiddleware`（受信代理才读取转发头）、`SecurityHeadersMiddleware`、`RequestValidationMiddleware`。
- `app/middleware/metrics.py`：Metrics + `/metrics` 端点。
- 静态托管：`frontend-react/dist`，SPA fallback，缺 index 快速报错。

## 前端

- `apiClient` 直接返回泛型数据（非 fetch `Response`），调用方禁止再次使用 `.ok` 或 `.json()`。
- Hash 路由入口：`frontend-react/src/App.tsx`；工作区布局 `src/components/workspace/WorkspaceLayout.tsx`。
- 移动底部导航 5 项；页面选择器与按钮文案保持稳定（如 "New Agent"、容器类 `rounded-xl`）。
