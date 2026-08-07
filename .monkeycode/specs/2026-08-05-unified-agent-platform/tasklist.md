# 统一 Agent 平台实施计划

Feature Name: unified-agent-platform
Updated: 2026-08-05

## 已完成基座（本轮六路实施）

- [x] 1. Pregel 执行内核加固
  - [x] 1.1 ExecutionContext 每次 run/astream 独立，并发 thread 隔离
  - [x] 1.2 缺 thread_id 自动生成 UUID
  - [x] 1.3 interrupt_before/after 顺序正确恢复
  - [x] 1.4 node/run timeout 进入 ErrorHandler 并输出事件
  - [x] 1.5 checkpoint ID 时间排序与分页
  - [x] 1.6 StreamManager 多 subscriber 广播
  - [x] 验收：`python3 -m pytest tests/core/engine/pregel/test_runtime_hardening.py -q -p no:cacheprovider`

- [x] 2. 持久化与会话恢复
  - [x] 2.1 SQLiteCheckpointStore 完整保存 channel_values/channel_versions/versions_seen/pending_writes/tool_results
  - [x] 2.2 旧 schema 兼容，缺失字段安全默认
  - [x] 2.3 engine/session.py 转为 session.py 兼容 facade
  - [x] 2.4 AgentSession snapshot/from_snapshot 排除运行时对象
  - [x] 2.5 chat.py 内存缺失时从 checkpoint 恢复
  - [x] 验收：`python3 -m pytest tests/test_checkpoint_session_persistence.py tests/test_checkpoint.py tests/test_smoke_cases.py -q -p no:cacheprovider`

- [x] 3. 多 Agent 与权限 P0
  - [x] 3.1 builtins 延迟工厂消除 None 缓存
  - [x] 3.2 handoff 先保存 source_worker_id；selectinload 消除 async lazy-load
  - [x] 3.3 MultiAgentOrchestrator 同步 create_session、AgentEventType.TEXT、实际使用 roles
  - [x] 3.4 CrewExecutorAdapter 适配真实 CrewOutput
  - [x] 3.5 PermissionOverlay 层级与 DENY > ASK > ALLOW
  - [x] 3.6 ASK 返回 requires_approval，AgentEngine pending permission + resolve 等待 + 超时 fail-closed
  - [x] 3.7 AgentEngine.run_agent 兼容方法
  - [x] 验收：`python3 -m pytest tests/test_multi_agent_unification.py tests/test_multi_agent.py tests/test_permission_controller.py tests/test_permission_tiers.py -q -p no:cacheprovider`

- [x] 4. 基础设施与关键故障
  - [x] 4.1 RateLimitMiddleware 注册，受信代理转发头
  - [x] 4.2 静态服务 frontend-react/dist + SPA fallback + 缺 index 报错
  - [x] 4.3 prompt templates 单一前缀
  - [x] 4.4 APP_SECRET_KEY 移除随机回退，生产/认证缺失快速失败
  - [x] 4.5 reasoning feedback trace_id 关联，普通 message feedback 校验真实 message
  - [x] 4.6 eval run 校验 dataset/agent 归属返回 422/404
  - [x] 4.7 IntegrityError rollback 映射 409/422
  - [x] 验收：`python3 -m pytest tests/test_runtime_infrastructure_fixes.py tests/test_smoke_cases.py -q -p no:cacheprovider`

- [x] 5. Principal 与 API 契约首批
  - [x] 5.1 Principal/CurrentPrincipal/ContextVar，local 模式仅此处 default-user
  - [x] 5.2 六类资源写端点命名 Pydantic schema，extra=forbid，data envelope 兼容
  - [x] 5.3 Agent 响应脱敏 api_key/env
  - [x] 5.4 Workflow/Crew run 仅选择当前 Principal 拥有 Agent
  - [x] 5.5 group member/task worker/reviewer 归属验证
  - [x] 5.6 rate-limit key 使用 principal identity
  - [x] 5.7 ToolGateway/记忆工具链传播真实 Principal，认证模式缺失 fail closed
  - [x] 验收：`python3 -m pytest tests/test_principal_api_contracts.py -q -p no:cacheprovider`

- [x] 6. 前端真实入口工作区
  - [x] 6.1 桌面稳定侧栏 + 上下文栏 + 主内容
  - [x] 6.2 移动底部导航 5 项覆盖全部真实路由
  - [x] 6.3 Chat/Agents/Workflows/Dashboard/Settings 重构
  - [x] 6.4 三视口验收测试
  - [x] 验收：typecheck/build/3305 项 Vitest/Playwright 1440·768·375

- [x] 7. 联合集成回归
  - [x] 7.1 后端联合 103 passed，compileall/ruff/OpenAPI 154 paths/194 unique operations
  - [x] 7.2 前端 typecheck/build/3305 passed/E2E 3 passed

## 后续迁移

- [ ] 8. Pregel 主线接入
  - [ ] 8.1 编写 PregelAdapter/Facade，保持 create_session/run/AgentEvent 协议
  - [ ] 8.2 将低风险真实入口（如 Workflow run）切换至 Pregel
  - [ ] 8.3 收敛旧实现：`app/core/pregel_loop.py`、`app/core/state_graph.py`、`app/core/channels.py`
  - [ ] 8.4 验收：切换入口协议测试 + 既有 AgentEngine 测试保持通过

- [ ] 9. 剩余多用户与 schema
  - [ ] 9.1 清理业务路径剩余 `DEFAULT_USER`（`app/` 内 71 处）至 Principal 单点
  - [ ] 9.2 剩余 generic 写端点迁移命名 schema 与 response_model
  - [ ] 9.3 OpenAPI 断言扩展：全量写操作命名 requestBody
  - [ ] 9.4 验收：双用户隔离全量 + OpenAPI 契约测试

- [ ] 10. 迁移链修复
  - [ ] 10.1 修复 `alembic/versions/52310c24d4c8...` 重复建表与 down_revision
  - [ ] 10.2 增加持久化 session/checkpoint schema 迁移
  - [ ] 10.3 验收：`alembic upgrade head` 在干净库执行成功

- [ ] 11. 协作与安全收敛
  - [ ] 11.1 Crew/MultiAgentOrchestrator 收敛为 GroupCollaborationEngine 适配层
  - [ ] 11.2 统一权限决策接口与策略数据源；沙箱专注执行隔离
  - [ ] 11.3 验收：多 Agent 单主实现测试 + 权限回归

- [ ] 12. 全量与质量治理
  - [ ] 12.1 停止并发 `scripts/watch_tests.py` 后执行可信后端全量 pytest
  - [ ] 12.2 治理前端 `act(...)` 警告
  - [ ] 12.3 复验 Docker 构建、MCP SDK import、OpenAPI 契约
