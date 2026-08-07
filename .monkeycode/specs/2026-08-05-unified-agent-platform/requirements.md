# 统一 Agent 平台架构需求文档

Feature Name: unified-agent-platform
Updated: 2026-08-05

## Introduction

将 `agent-engine` 收敛为生产级 AI Agent 平台。本规格固化六路审计定位的执行内核、持久化恢复、多 Agent、安全权限、多租户/API 契约、基础设施与前端工作区七个域的接口边界与验收基线。本规格区分"本轮已实现基座"与"后续迁移"，避免将计划态描述为已落地。

## Glossary

- **AgentEngine**：主线兼容执行引擎，当前唯一真实入口，async generator 协议。
- **PregelEngine**：图执行内核，本轮已加固并发隔离、interrupt、timeout、stream 与 checkpoint 排序，尚未接入主线。
- **AgentSession**：统一会话类型，位于 `app/core/session.py`，`app/core/engine/session.py` 为其兼容 facade。
- **CheckpointData**：运行时状态快照，含 channel_values/channel_versions/versions_seen/pending_writes/tool_results。
- **Principal**：请求身份载体，含 subject_id/tenant_id/role/scopes/auth_method。
- **GroupCollaborationEngine**：多 Agent 协作统一主实现目标。
- **Local 模式**：`ENABLE_AUTH=false`，由 Principal dependency 生成 default-user。

## Requirements

### REQ-1 执行内核

- **用户故事**：AS 平台，I want 执行引擎具备并发隔离与可恢复控制，so that 生产环境不串线且可中断恢复。

#### 验收标准

1. WHEN 同一 compiled graph 并发携带不同 thread_id 运行，系统 SHALL 保持各次执行的 active nodes、step、checkpoint 相互隔离。
2. WHEN 图运行缺少 thread_id，系统 SHALL 为本次执行生成独立 UUID，避免共享默认线程。
3. WHEN interrupt_before 触发，系统 SHALL 在 checkpoint 保留被拦截节点，并在 resume 后先执行该节点。
4. WHEN interrupt_after 触发，系统 SHALL 先合并节点更新再中断，并在 resume 后从后继节点继续。
5. WHEN 节点或整图执行超过 TimeoutPolicy 时限，系统 SHALL 进入 ErrorHandler 并在事件流输出 ERROR。
6. WHILE 主线协议为 `async for event in engine.run(session, message)`，任何内核迁移 SHALL 保持该协议与 AgentEvent 类型。
7. WHILE PregelEngine 成为主执行内核为后续迁移目标，当前主线 SHALL 保持由 AgentEngine 提供入口，直至 adapter/facade 分入口切换完成。

### REQ-2 持久化与会话恢复

- **用户故事**：AS 用户，I want 会话与 checkpoint 在重启后完整恢复，so that 中断任务可继续。

#### 验收标准

1. WHEN SQLiteCheckpointStore 保存 CheckpointData，系统 SHALL 持久化 channel_values、channel_versions、versions_seen、pending_writes 与 tool_results。
2. WHEN 读取历史 checkpoint 缺失新增字段，系统 SHALL 使用安全默认值并兼容旧记录。
3. WHEN AgentSession 序列化，系统 SHALL 保留 config/messages/status/iteration/stop/error 等安全字段，并排除锁、事件与任务等运行时对象。
4. WHEN 会话在内存缺失时恢复，系统 SHALL 从 checkpoint 恢复 messages/iteration/status 与工具结果，且不同会话隔离。
5. WHEN checkpoint 代表正常新 turn 而非中断，系统 SHALL 将其作为历史上下文，仅中断 checkpoint 进入 resume 状态。

### REQ-3 多 Agent 协作

- **用户故事**：AS 平台，I want 多 Agent 协作收敛到单一主实现，so that Crew 与 Orchestrator 复用统一协议。

#### 验收标准

1. WHEN builtins 访问 group collaboration engine，系统 SHALL 通过延迟工厂获取，禁止缓存 None 单例。
2. WHEN 执行 handoff，系统 SHALL 先保存 source_worker_id 再更新目标，并限定目标成员属于当前 group。
3. WHEN MultiAgentOrchestrator 消费引擎事件，系统 SHALL 按同步协议调用 create_session 并以 AgentEventType.TEXT 比较事件。
4. WHEN CrewExecutorAdapter 消费 CrewOutput，系统 SHALL 转换真实结果字段，禁止访问不存在的 success/data/error 属性。
5. WHEN 任务上下文装载 group 成员，系统 SHALL 使用 selectinload 消除异步 lazy-load。

### REQ-4 安全与权限

- **用户故事**：AS 平台，I want 权限决策可预测且工具执行 fail-closed，so that 越权与未授权工具调用被阻断。

#### 验收标准

1. WHEN PermissionOverlay 决策，系统 SHALL 令更具体 scope 覆盖泛化 scope，同层按 DENY > ASK > ALLOW 生效。
2. WHEN 用户显式 deny，系统 SHALL 使默认 allow 无法覆盖该 deny。
3. WHEN 工具调用命中 ASK，系统 SHALL 返回结构化 requires_approval，创建 pending permission 并发送审批事件。
4. WHEN ASK 等待 resolve_permission 超时，系统 SHALL 按 fail-closed 阻断工具执行。
5. WHEN 权限批准后继续工具执行，系统 SHALL 仍执行 schema 与 sandbox 验证。

### REQ-5 多租户与 API 契约

- **用户故事**：AS 管理员，I want 请求身份统一且写接口具备契约，so that 用户隔离不遗漏且 API 可校验。

#### 验收标准

1. WHEN 生成请求身份，系统 SHALL 从 Principal dependency 生成，local 模式仅在该处产出 default-user。
2. WHEN Agents/Workflows/Crews/Groups/Tasks/Skills 写端点接收请求体，系统 SHALL 使用命名 Pydantic 模型并以 extra=forbid 拒绝未知字段。
3. WHEN 客户端以 `{data:{...}}` envelope 提交，系统 SHALL 保持兼容。
4. WHEN 返回 Agent 资源，系统 SHALL 隐藏 api_key/env 等敏感字段。
5. WHEN Workflow/Crew run 选择 Agent，系统 SHALL 仅选择当前 Principal 拥有的 Agent；group member 与 task worker/reviewer SHALL 验证归属。
6. WHEN 限流键生成，系统 SHALL 使用 principal/auth 身份，禁止统一 default-user。
7. WHEN ToolGateway 与记忆工具链执行，系统 SHALL 传播真实 Principal；认证模式缺失身份 SHALL fail closed。

### REQ-6 基础设施与可靠性

- **用户故事**：AS 平台，I want 基础设施故障收敛，so that 请求限流、静态托管与密钥稳定。

#### 验收标准

1. WHEN 请求进入，系统 SHALL 经 RateLimitMiddleware 限流，且仅从受信代理读取转发头。
2. WHEN 返回 401/403/429/500，系统 SHALL 仍附带 CORS、security headers 与 metrics。
3. WHEN 静态托管，系统 SHALL 服务 frontend-react/dist，并为 SPA 提供安全 fallback；缺 index 时启动即明确报错。
4. WHEN 认证启用或环境为生产/预发而缺少 APP_SECRET_KEY，系统 SHALL 快速失败，禁止随机回退。
5. WHEN prompt templates 路由，系统 SHALL 仅暴露单一 `/api/v1/prompt-templates` 前缀，固定子路由位于参数路由之前。
6. WHEN reasoning feedback 写入，系统 SHALL 通过 trace_id 关联 ReasoningFeedback，禁止将 trace 标识塞入 message FK。
7. WHEN 数据库写操作触发 IntegrityError，系统 SHALL 回滚并映射为受控 409/422。

### REQ-7 前端工作区

- **用户故事**：AS 用户，I want 真实入口具备专业工作区密度与移动适配，so that 桌面、平板与手机均可操作。

#### 验收标准

1. WHEN 在桌面视口使用应用，系统 SHALL 提供稳定侧栏、上下文面板与主内容的层级布局。
2. WHEN 在移动视口使用应用，系统 SHALL 提供不超过 5 项的底部导航并覆盖全部真实路由。
3. WHEN 页面渲染，系统 SHALL 不出现横向溢出，1440/768/375 三视口均满足 scrollWidth <= innerWidth。
4. WHEN 可见按钮渲染，系统 SHALL 满足最小 44px 触控高度并具备键盘可达焦点。
5. WHEN 数据加载或缺失，系统 SHALL 呈现 loading/empty/error/disabled 明确状态。
6. WHILE 页面改造 SHALL 保留真实数据流与现有测试选择器，禁止引入假数据或删除真实操作。

### REQ-8 验收门禁

- **用户故事**：AS 团队，I want 变更具备可复现验收，so that 集成不回归。

#### 验收标准

1. WHEN 提交后端改动，系统 SHALL 通过 compileall、ruff 与 OpenAPI operation ID 唯一性检查。
2. WHEN 运行后端联合回归，系统 SHALL 通过本规格对应测试集合与 test_smoke_cases。
3. WHEN 提交前端改动，系统 SHALL 通过 typecheck、生产 build 与 3305 项单元测试。
4. WHEN 执行响应式验收，系统 SHALL 通过 1440/768/375 三视口 Playwright。
5. WHEN 全量后端运行，系统 SHALL 以真实执行方式运行，禁止 skip、排除或修改断言伪造通过。
