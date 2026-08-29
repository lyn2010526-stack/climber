# 实施任务清单

Feature Name: unified-agent-run-protocol
Updated: 2026-08-28

## 第一增量：协议纯类型与内存存储

- [x] 新增 `RunStatus`、`RunRecord`、`RunEvent`、`MessageEnvelope`、`StartRun`、`ResumeRun`、`RunHandle` 和 `ReplayPage`。
- [x] 新增统一 Run 状态转换表和结构化状态冲突错误。
- [x] 新增内存 `RunStore` fake，覆盖创建、条件状态转换、事件追加、事件幂等和回放。
- [x] 为事件顺序连续、终态 fencing、execution token fencing、回放缺口和消息序列化往返补充单元测试。
- [x] 运行 Run 协议定向测试和 Ruff 检查。

## 第二增量：持久化数据结构

- [x] 为 `turns` 增加 Run 元数据、Trace、序号和 execution token 字段。
- [x] 新增 `run_events` 表及 `(run_id, event_id)`、`(run_id, sequence)` 唯一约束。
- [x] 为迁移增加可逆的 `downgrade` 并验证 SQLite/PostgreSQL 兼容性。

## 第三增量：SQLAlchemy RunStore

- [x] 实现 SQLAlchemy `RunStore`，复用内存 fake 的状态与错误语义。
- [x] 使用条件更新实现状态转换、execution token fencing 和终态写入 fencing。
- [x] 使用事务内序号分配和唯一约束实现事件幂等。
- [x] 增加数据库回放、重建运行时对象和并发写入测试。

## 第四增量：Agent Chat 兼容接入

- [x] 实现 AgentEngine adapter，将 `current_turn_id` 与 `run_id` 关联。
- [x] 将 `AgentEvent` 映射为持久化 `RunEvent`，并关联 Trace/Checkpoint。
- [x] 将 Chat SSE 切换到统一运行时，同时保持现有事件名和数据字段。
- [x] 将 Chat replay 切换到持久化事件，并保留现有响应字段、补充 `run_id`。
- [x] 增加实时 SSE 与 replay 的事件标识、序号和数据一致性测试。

## 第五增量：载荷策略与剩余观测能力

- [x] 实现 Raw Payload `standard` 策略、脱敏、摘要和截断。
- [x] 单独实现 `debug` 模式的加密载荷、过期转换和清理任务。
- [ ] 补充 Run 查询接口、Trace/Checkpoint 关联校验和前端兼容验证。

## 第六增量：对标开源的代码审查修复

- [x] 状态机放宽：允许 `pending`/`paused` 直接转 `failed`/`cancelled`（启动前/恢复前放弃），并同步 design.md。
- [x] start 阶段识别并恢复陈旧活动 Run（无活跃执行器即置为 `failed`，error code `stale_run`），避免重启后永久阻塞会话。
- [x] 取消竞态：流处理循环内检测到已取消时输出合成 `stopped` 事件后正常结束，不再向客户端输出错误 SSE。
- [x] resume 归属不匹配（session/user）改抛 `RunStateConflictError(code=forbidden)`。
- [x] cancel 允许无归属记录（匿名）的 Run。
- [x] InMemory 与 SQL `find_active_for_session` 统一取最新活动 Run 语义。
- [x] transition 字段白名单收敛为 `RUN_TRANSITION_FIELDS` 单一来源。
- [x] `replay` 协议透传 `limit`。
- [x] SQL `attach_checkpoint` 对缺失的 CheckpointRecord 输出告警日志。

## 第七增量：开源对标学习 + Run 管理 API + 消息关联

- [x] 并行学习 34 个开源项目（Agent 框架/编程 Agent/基础设施/Agent造Agent），产出候选模式清单。
- [x] 全仓库架构诊断，定位 Run 管理 API 缺失、消息无 run_id、遗留回放路径等 6 类问题。
- [x] `RunStore.list_runs` + `RunPage`（session/status/user 过滤，offset 分页，InMemory 与 SQL 双实现）。
- [x] 新增 `/api/v1/runs` 管理路由：`GET /runs/{id}`、`GET /runs`、`GET /runs/{id}/events`、`POST /runs/{id}/cancel`、`POST /runs/{id}/resume`。
- [x] `Message.run_id` 列 + 迁移 `d5e6f7a8b9c0`（已在全新库验证升级链），`_persist_message` 全链路传入 run_id，Run 详情返回关联消息。
- [x] 测试：Run 管理 API 7 项、`list_runs` InMemory/SQL 各 2 项；定向回归 72 passed、engine/raw_payload 374 passed。

## 第八增量：并行子任务（余额不足改为亲自串行完成）

- [x] Raw Payload `debug` 策略：加密全量 canonical payload（`pl:v1:` 前缀 + Fernet），`expires_at = retention_days` 过期；`_record_raw_payload` 移除 `policy != standard` 早退，支持 debug 落库；新增 `cleanup_expired_raw_payloads`（SQL store，仅删 `expires_at` 非空且过期）。
- [x] 遗留回放路径确认：chat.py replay 在无持久化 Run 时返回空页而非回退 `engine.replay_events()`（上一轮已完成，本轮验证 6 passed）。
- [x] 新增 `app/core/run_cleanup.py`：`cleanup_stale_runs`（活动 Run 超过 `max_age` 置 FAILED，error code `stale_run` + interrupted 终止元数据，逐 Run 隔离冲突）+ `cleanup_expired_raw_payloads`；`main.py` 注册 watchdog 周期任务（间隔 `RUN_CLEANUP_INTERVAL_MINUTES` 默认 30，max_age `RUN_STALE_MAX_AGE_MINUTES` 默认 120）。
- [x] 增量 7C：抽取 InMemory/SQL 公共校验到 `run_protocol.py` 共享助手 `validate_execution_token`/`validate_run_transition`/`validate_event_write`/`is_audit_event_type`/`merge_transition_metadata`，两 Store 复用，消除重复。
- [x] 测试：`test_run_cleanup.py` 3 项、`test_raw_payload_debug.py` 6 项；定向回归 75 passed（9 套件）、engine 40 passed；ruff 全绿。

## 第九增量：全面优化

- [x] API 层直访 engine 私有属性清零：为 `AgentEngine` 新增公共访问器 `get_session`/`register_session`/`get_session_lock`/`drop_session_lock`/`has_active_session`，替换 chat.py（4 处）与 sessions.py（2 处）的 `engine._sessions`/`engine._session_locks` 直访。
- [x] `helpers.py` 的 `payload`/`DEFAULT_USER` 与 `_shared.py` 重复，改为转发 facade，消除重复实现。
- [x] `create_session_legacy` 与 `create_session_with_slash` 重复 DB 逻辑，改为委托复用。
- [x] 修复 watchdog 健康检查回归：`run_cleanup` 周期任务须在 `watchdog.start()` 之前注册，否则任务不会被 spawn，`/health` 误报 `degraded`。
- [x] 测试：健康端点修复后 test_integration 10 passed、session 4 passed、API 模块 229 passed、后台回归 93 passed；ruff 全绿。
