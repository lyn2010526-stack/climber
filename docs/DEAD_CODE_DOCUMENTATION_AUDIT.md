# 死代码与文档事实对账

- 审计日期：2026-09-26
- 当前复核增量：2026-09-26
- 审计范围：`app/core/metacognition/`、`app/core/mcp_controller.py`、`app/core/security/`、`app/core/engine/safety.py`，以及 README/架构/安全文档中对这些模块和 Flow、observability、replay、checkpoint 的描述。
- 修改范围：仅文档和本审计清单。生产文件未删除，核心运行代码未修改。

## 状态结论

| 目标 | 状态 | 证据 | 删除建议 |
|---|---|---|---|
| `app/core/metacognition/` | 实验性、未接线 | 目录内 `orchestrator.py` 只导入同目录模块；对 `app/` 其余生产代码搜索没有导入方。 | 暂缓删除。先确认是否有外部插件、脚本或计划中的入口；确认后可整体移除，并同步删除包内测试/文档引用。 |
| `app/core/mcp_controller.py` | 未接线 stub | `McpController` 仅维护状态和配置字典；对 `app/` 生产代码搜索没有 `mcp_controller` 或 `McpController` 导入。实际 MCP 入口是 `app/tools/mcp_client.py`、`app/tools/mcp_router.py`、`app/tools/__init__.py` 和 `app/api/v1/routes/misc.py`。 | 可列为候选删除。删除前需核对外部导入方和发布包 API，确认后移除文件及其专属测试/文档引用。 |
| `app/core/security/` | 独立组件，API 未挂载 | 包导出 Docker sandbox、文件隔离、网络 allowlist、资源配额；`app/core/security/api.py` 定义 `/api/v1/security`，但 `app/main.py` 仍只挂载通用 API router 和 observability router。 | 暂缓删除。组件可能被外部调用；先决定是否挂载 router，或将组件迁移到主线安全实现后再清理。 |
| `app/core/engine/safety.py` | 兼容层，主线未调用 | 文件自身说明生产链在 `app/core/engine/validation.py`；仓库生产调用点位于 `app/core/agent_engine.py` 和 `validation.py`。 | 可列为候选删除。删除前确认外部导入方；若保留，应继续作为薄兼容层，避免重新实现分类逻辑。 |
| `FlowExecutor` | 实验性、未接线 | 类定义在 `app/multi_agent/flow.py`，仓库没有 `FlowExecutor(` 或导入它的生产调用方。 | 暂缓删除。`Flow` 同文件中的命名工作流仍由 `app/core/task_worker.py` 的 `workflow` 任务调用，不能连同文件删除。 |
| `Flow` | 仍在使用 | `app/core/task_worker.py:554-568` 导入、实例化并注册 `workflow` handler；`Flow.execute()` 委托 `WorkflowEngine`。 | 保留。文档应区分 `Flow` 与 `FlowExecutor`。 |
| observability | 仍在使用 | `app/main.py` 挂载 `app.core.observability.api.router`；`app/core/agent_engine.py` 获取共享 collector/audit 并写入；API 提供 traces、audit、alignment、emergency-stop。 | 保留。可观测存储故障按代码设计不会阻断任务，文档应描述为已接入且容错。 |
| checkpoint | 仍在使用 | AgentEngine 默认构造 `SQLiteCheckpointStore`；执行循环保存 checkpoint；`app/api/v1/chat.py` 使用 `RecoveryManager` 恢复；sessions API 提供 checkpoint/history/rollback/resume。 | 保留。文档应注明 SQLite 持久化和当前保留窗口/接口语义。 |
| replay | 仍在使用 | `app/core/recovery.py` 构造 `ToolReplayPolicy` 并过滤 `tool_results`；`app/core/replay.py` 对写入、命令、网络和未分类工具 fail closed。 | 保留。文档应避免表述为“重放所有工具调用”。 |

## README 已修正事实

## 当前复核增量

- `app/main.py:260-261` 已注册 `CsrfProtectionMiddleware`；`tests/core/test_csrf_middleware.py` 覆盖其请求处理和中间件顺序。因此“CSRF 尚未接线”的旧结论仅保留在历史审计材料中，当前状态为“已接线，配置与例外语义仍需部署复核”。
- 本次仓库级非集成回归未通过：`1024 passed, 18 failed, 2 warnings, 18 subtests passed`。失败集中在认证 HTTP、会话持久化/回滚、任务 WebSocket、工作流 HTTP 和 checkpoint schema contract；不能据此宣称全量后端回归通过。

- MCP 路径改为实际使用的 `app/tools/mcp_client.py`、`app/tools/mcp_router.py`。
- 安全路径改为 `app/core/engine/validation.py`、`app/core/security_sandbox.py` 和 `app/core/safety_pipeline.py`。
- 会话能力补充 SQLite checkpoint、recovery、rollback 和 replay policy 的边界。
- Flow 描述明确 `Flow` 是任务 worker 的使用入口，`FlowExecutor` 仍未接线。
- observability 描述明确 AgentEngine 的 trace/audit 写入与 API 挂载状态。

## 未决事项

1. 确认 `app/core/mcp_controller.py`、`app/core/engine/safety.py` 是否属于公开 Python 导入 API。确认范围后再删除。
2. 决定 `app/core/security/api.py` 是否应由 `app/main.py` 挂载；当前文档不应宣称 `/api/v1/security` 已对外提供。
3. 决定 `app/core/metacognition/` 和 `FlowExecutor` 的产品路线。两者当前均缺少主线生产引用，适合单独归档或移除评审。
4. `docs/OPEN_SOURCE_COMPARISON.md` 仍有“7 级权限控制”的竞品比较文案；该文案属于独立市场比较材料，需在后续产品事实复核中改为当前六种 `PermissionMode` 和 allow/ask/deny 决策模型。
