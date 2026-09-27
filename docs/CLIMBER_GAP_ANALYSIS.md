# Climber 竞准备战差距分析

> 审计对象：`https://github.com/lyn2010526-stack/climber`（commit `e0ab69f`，56 commits，2026-09-26 快照）
> 目标赛事：GOSIM Shenzhen 2026「智能体软件工厂」黑客松（提交 10/17）、2026 上海开源软件应用创新大赛（报名 10/11）
> 审计范围：后端 53,880 行 Python / 前端 41,919 行 TS / 测试 16,841 行 / 58 张表 / 约 118k LOC
> 所有结论均实地查证，附 `文件:行号`

---

## 摘要

Climber 是一个功能完整的 **AI 工作台**，harness 与评测是最薄的一环。两场赛事要的正好是这一环。

- GOSIM 赛题原文：*Build and evaluate production-grade agent harnesses*
- OSCHINA 开源 AI 工具赛道明确收"数据处理、微调与**模型评测**工具"

约 21,000 行死代码（17.9%）横在中间，其中包括 README 重点宣传的两套记忆分层实现。

### 总账

| 维度 | 数字 |
|---|---|
| 死代码 | **约 21,164 行 / 17.9%**（后端 9,507 + 前端 11,657） |
| 后端 | 53,880 行 Python，295 文件，58 张表 |
| 前端 | 41,919 行 TS/TSX + 4,291 CSS，293 文件 |
| 后端测试 | 9,220 行 / 512 个 test 函数（**真实有效**） |
| 前端测试 | 7,621 行（**57% 测死代码**） |
| 端到端跑通的编排 | **3.5 条**（单 Agent / Workflow DAG / Crew / collaboration 半条） |
| 社区信号 | 4 star / 0 fork / 无 release / 无 CHANGELOG |

### 已有资产（低估了的部分）

1. **`adapters/arcbench/`（2,165 行）是全仓最有价值的资产，README 零提及。**
   `acceptance.py:1-10` 自陈：*Only this module provides the evidence required for honest `mark_test_passed` / `mark_test_failed` events; whenever the test infra or a usable report is missing it reports inconclusive instead of guessing.* —— 评测器在缺证据时主动报 inconclusive 并拒绝猜测，正是本赛题想奖励的诚实性设计。`vendor/arcbench_agent_runtime/` 含 `traceability.py` / `gitops.py` / `events.py`，`main.py` 完整实现平台契约（`.arc` 事件流、端口探测、Playwright 验收、postflight 结构校验）。

2. **后端测试是真测试。** 512 个 test 函数 / 9,220 行。文件名暴露生成方式：`test_reported_security_regressions.py`、`test_review6_task_recovery.py`、`test_critical_regressions.py`、`test_api_key_scope_isolation.py` —— 每轮审计发现都配了回归测试。

3. **`app/simulation/` 是唯一 README 描述与代码完全相符的子系统。** 数值后端有真 CFL 稳定判据（`experiments.py:80`），收敛探针实测能拒发散/异常/空输出，自动调参实测走出 reject→perturb→accept 链，JSONL 账本落盘，工具→工作流节点→API→前端全链路打通。

4. **活的 ReAct 循环工程质量在线。** `agent_engine._iteration_loop:363-467` 有 `merge_stream_chunk` 正确合并 delta、真实 token 计量（`response_usage(result)["total_tokens"]`）、stop 时记录部分响应、空响应注入纠偏消息、metrics 全量埋点。

---

## P0 — 决定参赛资格与评审第一栏（5 项）

### P0-1 `/eval/*` 全是纯 CRUD，零评测引擎

**位置** `app/api/v1/routes/misc.py:580-621`

`run_evaluation` 的 docstring 就是 *"Create an evaluation run record"* —— 插一行数据库记录就返回。全仓 `find app -iname '*eval*'` 只有两个结果：

- `app/storage/models_eval.py`（ORM 表）
- `app/reflection/self_evaluation.py`（硬编码 `return EvaluationResult(score=0.8, passed=True)`）

**影响** 主题是 "build AND evaluate" 的项目，评测是空壳。技术可行性栏直接归零。

---

### P0-2 前端 `#eval` → EvalDashboard 是零测试空壳

**位置** `frontend-react/src/pages/` → `eval/EvalDashboard`

19 个无测试页面里排第一。评委点进去发现不跑任何东西。

---

### P0-3 唯一真评测能力被埋在 adapters/ 里当配角

**位置** `adapters/arcbench/`（2,165 行，README 零提及）

详见「已有资产」第 1 条。

**方向** 提为主叙事：「Climber 是唯一在提交时诚实报告 inconclusive 的 agent harness」。把 `arcbench_agent_runtime` 从 vendor 提为正式模块，接上 `/eval`，让它跑在真实数据集上。

---

### P0-4 headless harness 无官方评测契约

**位置** `app/headless/__init__.py:1`

自陈 *"Standalone local coding harness. No official benchmark contract is claimed."*

`grep -iE 'swe-?bench|terminal-?bench|harbor'` 全仓零实现，唯一提及在 `docs/OPEN_SOURCE_COMPARISON.md:263` 的待办清单里。

**方向** 定 harness 契约：输入输出 JSON schema、事件流格式、超时语义。

---

### P0-5 Alembic 迁移链已损坏，README 第一条命令跑不通

**位置** `alembic/versions/`

**44 张表被两个迁移各建一次**：

| 迁移 | 内容 |
|---|---|
| `dd8212a8f22a_initial.py` | 建 44 表 |
| `52310c24d4c8_...py` | 建 48 表（57KB，218 个 `op.`） |

`comm -12` 求交集 = **44 张完全重复**（`agents`、`sessions`、`messages`、`api_keys`、`users`、`cost_records`、`traces` …）。第二次 `op.create_table` 必然 `DuplicateTable`。

而 `52310c24d4c8` 的文件名是 *"add_enhanced_prompt_enabled_to_user_settings"* —— 内容与名字完全不符，是把整个 initial schema 复制了一遍。

**实际部署绕过路径** `app/storage/__init__.py:143-166` 的 `init_db()` 用 `Base.metadata.create_all`，且包在 `contextlib.suppress(Exception)` 里（`:165-166`）**失败静默**。`main.py:127-143` 捕获异常只打 warning。`cd.yml:189,276` 和 `Dockerfile:55` 都调 `alembic upgrade head`，与 `create_all` 并存形成**两条 schema 权威来源**。

**另有裸 DDL 旁路** `app/storage/database.py:224-259` `ensure_checkpoint_schema()` 直接 `ALTER TABLE ... ADD COLUMN`，且 `text(f'...')` 拼串。

**影响** 评委 clone 照 README 走，第三步 `alembic upgrade head` 就炸。

---

## P1 — 安全与可靠性硬伤（27 项）

### 认证 / 授权

| # | 位置 | 问题 |
|---|---|---|
| P1-1 | `app/api/v1/sessions.py:236,249,274,298,307` | **5 处 fail-open IDOR**。统一模式 `if not row or (row.user_id and row.user_id != user_id)`，`row.user_id` 为 NULL 时短路为 `True` 而 `not row` 不成立 → 放行。`clear_session` 在此条件下**跨用户 DELETE 全部消息**。`Session.user_id` 声明 `nullable=False`（`storage/database.py:78`），但 `create_all` 旁路和历史数据都可能留 NULL。同文件 `:204-208` 和 `chat.py:86-90` 是正确写法（放进 WHERE）——**两种标准并存** |
| P1-2 | `app/middleware/auth.py:78-82` | JWT 分支 `return {"method":"jwt","sub":payload.get("sub"),"scopes":...}` —— **不查库、不校验 active、不带 role/tenant**。对比 `auth_manager.py:200-240` 的 API key 分支确实查库并检查 `is_active`。同一中间件两套强度 |
| P1-3 | `app/core/auth_manager.py:40-43` | 手工 base64 + HMAC-SHA256，签名截断到 **16 hex（64 bit）**。无 `jti`/`kid`/算法协商。`config.py:47` 的 `jwt_algorithm: HS256` 是死配置，无人读取 |
| P1-4 | `app/core/principal.py:22` | `tenant_id` 定义了，但**全库 `tenant_id` 只出现在 `principal.py` 自己**。`app/storage/*.py` 和 `app/models/*.py` 零个 tenant 列、零个 tenant 过滤。多租户 = 单列 `user_id` 相等，而 `user_id` 来自可伪造的 JWT |
| P1-5 | `app/core/auth_manager.py:118-122` | `scopes_for_role` 把 admin/manager/developer/viewer/api 五种角色全压成 `["read","write"]`（admin 多一个 `admin`）。角色模型形同虚设 |
| P1-6 | `app/core/auth_manager.py:179-192` | `enable_auth=False` + `id=="default-user"` → `require_admin` 直接授予 `["admin"]`。`config.py:143-146` 靠 `APP_ENV=local` 字符串判断生产是否强制开认证 |
| P1-7 | `app/api/v1/auth_management.py:140-158` | logout 删 `UserSession` 行，但 **`UserSession(...)` 从未被实例化** → 纯 no-op。无 refresh token 撤销/黑名单（`grep revok\|denylist\|jti` 零命中） |
| P1-8 | `app/models/users.py:46` | `failed_login_attempts` 列零读写 → **无暴力破解锁定** |

### 写了没接的安全组件（6 项）

> 评审者读代码会误判覆盖度。「以未接线形式存在的安全能力」比缺失更危险。

| # | 位置 | 问题 |
|---|---|---|
| P1-9 | `app/core/security/docker_sandbox.py`（239 行） | **配置完全正确**：`cap_drop=["ALL"]`、`read_only_root`、`security_opt=["no-new-privileges"]`、`pids_limit=64`、`network_mode="none"`，默认 ephemeral + `finally` 销毁（`:217-219`）。**零调用**。隐患：`:98` `network_mode: "bridge" if network else ...` 让 `network=True` 绕过 none；`:110` `storage_opt` 要求 overlay2 驱动 |
| P1-10 | `app/core/security/fs_isolation.py` | `validate_path:50-66`（resolve + blocked/allowed 双向校验）和 `sanitize_path:68-81`（先 resolve 再查 `..`，顺序正确）**质量好，但整个模块零调用** |
| P1-11 | `app/core/security/{network_allowlist,resource_quotas}.py` | 419 行。`quota_manager` / `network_allowlist` 零执行点；其 API router 未挂载 |
| P1-12 | `app/middleware/security.py:80-137` | `CsrfProtectionMiddleware` 完整实现（双提交 cookie + `compare_digest`），`main.py:260-271` **未注册** |
| P1-13 | `app/core/observability/audit.py`（227 行） | `AuditChain` 自带独立 `sqlite3` 连接（`:60`，默认 `:memory:`）和自建表（`:65-84`），**绕开 ORM 和 Alembic，从不写入**。`grep log_decision` 的唯一"调用方"是 `router_decision.py:263` 的同名私有方法（不同实现）。`core/security/api.py` 的 router 从未 include |
| P1-14 | `app/core/mcp_controller.py`（34 行） | `McpController` 无 importer；`start()`/`stop()` 直接 `return True`（`:26-31`）是桩 |

### 沙箱实现矛盾

| # | 位置 | 问题 |
|---|---|---|
| P1-15 | `app/core/security_sandbox.py`（662 行） | **黑名单制，且自相矛盾**：`:290` 白名单允许 `chmod` 而 `:168` 只拦 `chmod 777`；`:290` 允许 `rm` 而 `:156` 拦 `rm -rf`。`_ALLOWED_COMMANDS` 含 `docker`/`chmod`/`chown`/`curl`/`wget`/`xargs`/`awk`/`sed` |
| P1-16 | `app/core/security/code_sandbox.py:355-357` | AST 禁用表可绕：`getattr` 被禁但 `obj.__getattribute__` 可用。`FORBIDDEN_MODULES` 缺 `builtins`/`importlib`/`runpy`/`code`/`mmap`/`multiprocessing` |
| P1-17 | `app/core/security_sandbox.py:72-77,91` | `PermissionOverlay.evaluate` 无匹配时返回 `DENY`（默认安全），但 `_merge_rules:91` **只要任一层有匹配就 return**，先匹配层胜出 —— 与文档宣称的"三层叠加"相反，agent/user override 可覆盖 defaults |
| P1-18 | `app/core/security_sandbox.py:234-235` | `fnmatch` 分支留下 `/proc`、`/sys`、`/dev` 前缀匹配，`/devfoo` 类构造可绕。`:255-260` 的 `os.path.realpath` + `commonpath` 是正确写法 |
| P1-19 | 全局 | 同一代码库**两套矛盾沙箱**：`security_sandbox.py`（黑名单，662 行）vs `core/sandbox.py`（白名单，194 行，`main.py:77` 注册为 `SandboxExecutor`）。后者质量明显更高：`shlex.split` 无 shell、`create_subprocess_exec` 无注入面、显式拦 `..`、`realpath` 逃逸校验、rlimit（`RLIMIT_AS`/`CPU`/`NOFILE`/`NPROC`）。诚实缺陷：`:115-116` 静默吞掉 macOS 上 `RLIMIT_AS` 失败 |

### 限流 / 配额 / 流式 / 长任务

| # | 位置 | 问题 |
|---|---|---|
| P1-20 | `app/storage/usage.py:68-70` | `RateLimitMiddleware`（`middleware/security.py:185-250`）计数器是**进程内 `list` + `defaultdict`**。gunicorn 多 worker（`gunicorn.conf.py`）下每进程独立计数 → **限额可被 N 倍放大**。Redis（`storage/cache.py`）在 `main.py:145-149` 只做缓存，**不参与限流** |
| P1-21 | `app/storage/usage.py:72-102` | `record()` 是唯一填 `tokens_used` 的方法，`grep "usage_tracker\."` 只命中 `check_rate_limit` 和 `record_request` → **`record()` 零调用点**。于是 `check_rate_limit:130-137` 的 `daily_tokens` 恒为 0，`tokens_per_day` 永不触发。`tool_calls_per_hour:147` 同理 |
| P1-22 | `app/api/v1/cost.py:50,85` | 硬编码 `DEFAULT_USER` 而非当前用户。`BudgetConfig`/`UsageQuota` 是与 usage.py 无关的另一套表 |
| P1-23 | `app/api/v1/chat.py:155-170` | SSE **无 `id:`**（不支持 `Last-Event-ID` 续传）、**无 `retry:`**、**无心跳注释行**（反向代理空闲掐断）、无背压。取消处理正确（`:167-168` `finally`），并发保护到位（`:126-127` `_chat_inflight` + per-session lock 返 409） |
| P1-24 | `app/api/v1/routes/websocket.py` | WS 是三者中质量最高的（`_authenticate_websocket:78-107` 对 session/group/agent 做 owner 校验、30s 心跳、状态上限 1000/200、优雅关闭），但：**零背压**（所有 `send_json` 无队列上限/超时）；`disconnect_count:180` 记录重连并回传 `reconnect` 标记但**无重放逻辑**；`/ws/{session_id}:163` 和 `/ws/agents/{id}:327-331` 实质是 **echo server**（不驱动 agent、不落库）；`generic.py:40-41` + `main.py:276-282` **重复注册同一路径** |
| P1-25 | `app/core/task_worker.py:397-407` | **零重试**。捕获异常后直接置 `FAILED`，错误信息写死 "manual review required before resubmission"。无退避、无次数上限、无 `max_attempts` 列 |
| P1-26 | `app/core/task_worker.py:207` + `app/core/auto_loop.py:356` | **崩溃后 RUNNING 行永久悬挂**。`recover_pending_tasks:207` 只 `where(status == PENDING)`；`auto_loop._check_stalled_tasks:355-375` 有心跳超时检测但遍历的是内存 dict `self._tasks`（`:356`）→ 重启后为空。`run_standalone_worker:709-714` **从未被调用**（`main.py:155` 只调 `recover_interrupted_sessions()`）。无幂等键，重复 POST 产生重复 LLM 计费 |
| P1-27 | 12 个 API 文件 | **零 `response_model`**，含 59 端点的 `routes/misc.py`、`routes/workflows.py`、`skills_router.py`、`scheduler.py`、`settings.py`、`routes/groups.py`、`routes/crews.py`。`main.py:252-258` 无自定义 `openapi_url`/`docs_url`/`openapi_tags`。无 API 版本化（只有 `prefix="/api/v1"`），无弃用机制 |

**正面记录**：`core/sandbox.py` 白名单制实现扎实 · `utils/ssrf.py` 质量好且接入点密集（`builtins.py:64,76,92`、`native_tools.py:256-274` 含重定向复查、`research.py:219`）· 安全响应头完整（CSP/HSTS/Permissions-Policy/COOP/CORP/COEP）· 凭据 Fernet 加密 + `resolve_owner_agent_payload:25-74` 拒绝 payload 明文 key · `task_worker._run_task:340-353` 条件 UPDATE 抢占是正确的乐观锁。

---

## P2 — Harness 能力差距（30 项）

### 工具面

| # | 位置 | 问题 |
|---|---|---|
| P2-1 | `app/tools/builtins.py`（28 个工具） | **工具面是助手味的**：`get_weather` / `wikipedia_summary` / `translate` / `generate_image` / `summarize` / `base64_encode` / `json_get` 混在编码工具里 |
| P2-2 | `app/tools/builtins.py` | **零跨文件内容检索原语** —— `grep -rniE 'def (grep\|search_code\|code_search\|glob)' app/tools/ app/core/` 零命中。模型找代码只能退回 `run_command("grep ...")` 或整文件 `read_file`。这是编码 agent 的地基 |
| P2-3 | `app/core/agent_engine.py` + `app/core/parallel.py` + `app/tools/__init__.py` | `grep -iE 'truncat\|max_output\|MAX_TOOL\|\[:2000\]'` **零命中**。tool result 原始进 context（`agent_engine.py:788-796` yield 全量 `tr.result`），一次 `run_command` 输出几千 token 直接吃掉窗口 |
| P2-4 | `app/core/agent_engine.py:746-751` | 参数 JSON 解析失败**静默变 `{}`**。模型参数写错 → 工具收到空参数 → 报语焉不详的错误。**缺 repair 重试** |
| P2-5 | `app/core/permission_rules.py` | 权限系统与 `permissionMode: 'sandbox'\|'native'` 存在，但**无一个测试证明 denied 的 tool call 真的被拦住** |

> 文件工具其实有：`read_file:141` / `write_file:151` / `edit_file:274`（old_string 替换）/ `apply_patch:424` / `file_diff:312` / `list_files:161` / `run_command:175` / `stream_command:475`。缺的是检索。

### 死掉的 harness 核心（1,599 行）

| # | 位置 | 问题 |
|---|---|---|
| P2-6 | `app/core/engine/react_loop.py`（216 行） | **零调用零测试的死代码，且是劣化的重复实现**。`agent_engine` 没有 import 它，自己手写了 105 行 `_iteration_loop`（`:363-467`）。死版问题：`:144` tool result 无截断 · `:128-133` content+tool_calls 同时存在时 assistant 消息**双写** · `:106` `finish_reason="stop"` 写死 + `tokens_used=0` · `:109-118` 工具参数错误即整轮 FAILED。**留着一个看起来更"架构化"实际没接的模块，评审会以为主循环在用它** |
| P2-7 | `app/core/engine/pipeline.py`（208 行） | 零引用 |
| P2-8 | `app/core/engine/router_decision.py`（296 行） | 零引用 |
| P2-9 | `app/core/engine/ensemble.py`（360 行） | `EnsembleEngine` **完整实现**（`execute_parallel:84-120` gather + `_evaluate_consensus` 相似度投票 + `ConsensusResult` 带 `agreement_ratio`/`needs_review` + pub/sub 消息总线）。**零实例化、零测试、零 API、前端零命中** |
| P2-10 | `app/core/engine/subagent.py`（339 行） | `SubagentManager` **完整实现**（`depth_limit=3`、`Semaphore(5)`、`orphan_timeout=300s`、级联取消 `_run_with_cancel:229-250`、`SubagentUsage` 成本追踪）。**零实例化、零测试、零 API、前端零命中** |

### 编排：四套 DAG 引擎并存（~6,000 行）

| # | 位置 | 问题 |
|---|---|---|
| P2-11 | 四处 | **四套独立调度实现零共享抽象**：`workflow/__init__.py:73` Kahn 分层 · `collaboration/deadlock.py:98` Kahn 分层 · `skill_composition.py:81-116` 手写依赖 while 循环 · Pregel superstep |
| P2-12 | `app/core/engine/pregel/`（2,061 行） | BSP/超步实现完整（`_execute_super_step:374-471` gather 并行 + reducer 合并 + 去重剔除终止哨兵 + 每步 checkpoint + interrupt before/after + `RetryPolicy`/`TimeoutPolicy`/`HITLManager`/`StreamManager`）。**18 个测试是全仓最好的**（并发隔离、thread_id 隔离、两种 interrupt 恢复、超时→error handler、checkpoint 分页、astream 不崩）。**零业务调用**，只在 `engine/__init__.py:16,19` 再导出 |
| P2-13 | `app/core/integration/langgraph_bridge.py:14,46-55` | 用的是**真 `langgraph.graph.StateGraph`**，与本地 Pregel 引擎**并行运行、互不调用** |
| P2-14 | `app/api/v1/routes/groups.py`（8 端点） | **无任何创建/运行 group task 的端点**。`GroupCollaborationEngine.run_task:193` / `run_group_tasks:242` 唯一调用者是三个内置工具。**代码质量最高的编排层（2,125 行 + 好测试）没有入口** |
| P2-15 | `app/tools/builtins.py:534-592` | `auto_decompose_task` 硬编码 `provider="openai"` / `model_id="gpt-4o"` / `api_key=""`（`:563-564,592`），**不读用户配置的模型凭据** → 必然鉴权失败。且它是 `AgentGroupTask` 的**唯一创建者** |
| P2-16 | `app/tools/builtins.py:383,403` | `handoff_task` 需要模型提供无从获知的 `task_id`+`target_agent_id`（且目标 `AgentGroupMember` 必须已存在 `base.py:419-428`）；`run_group_tasks` 需要 `group_id`。**无 UI 能设置这些参数** |
| P2-17 | `app/core/prompt_engine/engine.py:144` | `MULTI_AGENT_COLLABORATION_PROMPT` 从未注入任何 agent。`multi_agent_mode` 在 `models.py:142` 恒 False 且全仓无处置 True。`PromptEngine` 本身零消费者（仅 `prompt_engine/__init__.py:8` 再导出）。**该 prompt 点名的 `read_task_context`/`write_task_context`/`update_task_dependencies`/`group_ws_hub` 在 `builtins.py` 里一个都不存在**（该文件共 28 个工具函数） |
| P2-18 | `app/core/collaboration/checkpoint.py:73-95` | `resume_from_checkpoint` 只写回 `final_output`/`current_round` + 广播 `checkpoint_restored` + 广播 `task_partial`，**不重新进入 `run_sequential_process` 的 while 循环，不重放任何 LLM 调用**。`base.py:220-224` 加载到 running/paused 后直接 `return` → 任务永远不续跑。而 `save_checkpoint:40` 硬编码 `status="running"` → **只要存过点，重启必走死路** |
| P2-19 | `app/core/collaboration/hierarchical.py:132`、`group_chat.py:93` | 名为 delegate / 群聊，实为**串行 for 循环**。`group_chat:141-148` 共识判定是关键词计数（"同意"/"agree"/"looks good" 命中即算），语义极弱。无 guardrail、无 checkpoint。`sequential.py` 才是完整实现（多轮 worker→guardrail→HITL→reviewer + 降级） |
| P2-20 | `app/core/collaboration/{aggregation,handoff,a2a_protocol,roles}.py` | 817 行。含 `A2AProtocol`（HMAC-SHA256 签名）、`HandoffManager`、`RoleRegistry` 能力边界、`ResultAggregator`（majority_vote/weighted_average/best_confidence）。**零调用点、零测试** |
| P2-21 | `app/multi_agent/flow.py:336` | `FlowExecutor`（装饰器事件驱动，约 330 行：`@start`/`@listen`/`@listen_or`/`@router`/`@listen_route`）**零调用**。真正被用的是同文件 `:336` 的 `Flow` 类，而它只是 `WorkflowEngine.execute` 的命名包装器。`workflow_executor.py` 与 `Flow` 功能重复 |

**质量最高的编排块** `app/core/collaboration/deadlock.py`（130 行）：三色 DFS 找环（`:48-87`）+ Kahn 分层（`:98-130`）+ `_canonical:40-45` 旋转去重，环节点及其传递依赖者一起丢弃。`tests/core/test_collaboration_deadlock.py` 11 个测试含 3 个真连 SQLite 的集成测试。**这是全仓编排代码里质量最高的一块。**

### Workflow 具体缺陷

| # | 位置 | 问题 |
|---|---|---|
| P2-22 | `frontend-react/.../WorkflowEditor.tsx:118` + `app/core/workflow_executor.py:106-117` | **条件分支从可视化编辑器断链**。后端靠 `edge.get("sourceHandle")` 判 `"true"/"false"`；编辑器保存时写 `condition: (e as any).condition`，且 `sourceHandle` 在整个前端只出现在死代码 `workflowService.ts:14` 的类型定义里 → `condition=""` → `engine.py:375-378` 两个分支条件都不匹配 → **`skip_targets` 恒为空，两条分支永远都执行**。只有 API 模板能正常分支 |
| P2-23 | `app/workflow/engine.py` | **零重试、零退避、零补偿**（无 saga/rollback）。`engine.execute` 本身**无单测**。`iterator:436-481` 是串行 for 循环 + `safe_eval`，非图级回边循环 |
| P2-24 | `app/core/workflow_executor.py:39-46` | `type_mapping` 只映射 `input/llm/tool/condition/simulation/output` → **`iterator` 和 `code` 节点无法从可视化编辑器创建** |
| P2-25 | `app/workflow/templates.py:151-189` | `map_reduce` 模板 docstring 写 "process items in parallel"，实际 ITERATOR config 是 `transform: "str(item)"` —— **map 阶段根本没调 LLM**。假 map-reduce |
| P2-26 | `frontend-react/src/services/workflowService.ts:55-101` | 8 个方法中 6 个后端端点不存在（`/execute` `/validate` `/clone` `/executions` `/stop`；真实端点是 `/run` 和 `/runs`）。**全文件零消费者** |

**正面记录** `engine.py:73-92` Kahn 分层 + `:127-131` 同层 `asyncio.gather` 真并行 + `:335-387` 条件分支 + `:199-244` `_skip_downstream` 用 BFS 判可达性（**正确处理了菱形依赖**）+ `:668-728` 变量解析 + `:483` 代码沙箱有 AST 校验有测试。

### Skill 系统：对 agent 行为影响为零

| # | 位置 | 问题 |
|---|---|---|
| P2-27 | `app/skills/definitions.py:26-356` | 约 20 个内置 skill 带 `system_prompt` + `tools` + `tags`。`grep skill_ids` 只有 5 处，**全是存储/CRUD**（`storage/database.py:61`、`routes/agents.py:57,126`、两个 schema）—— **`agent_engine` 零引用**（`:236-237` 只用 `session.system_prompt` 一个裸字符串） |
| P2-28 | `app/api/v1/skills_router.py:157-251` | 8 个端点**全是 CRUD**（list/create/enable/disable/delete/update），**无一个 invoke**。`skills/builtins.py`（1,014 行）19 个 handler 通过 `BUILTIN_HANDLER_MAP`（`definitions.py:357`）绑定，`SkillRegistry.invoke:96` 和 `SkillComposer.execute_composition:66` 能调，但无人调。质量参差：`skill_recursive_research:16-63` 真跑代码；`skill_task_decomposition:66-96` 和 `skill_self_evolving:99-` 是**纯 f-string 返回 markdown 模板** |
| P2-29 | `skills/*.skill.json`（5 文件 45 行） | **零 loader**（`grep skill.json` 在 py/ts/tsx/toml/yaml/sh 零命中）。且引用的 `move_file`/`copy_file`/`web_scrape`/`extract_links` 在 `builtins.py` 里**全都不存在**。`app/skills/package_manager.py`（23 行）空壳字典。**第三套独立格式**（既非 `SkillInfo` pydantic，也非 `AgentGroupMember`） |
| P2-30 | Anthropic adapter | **未接 prompt caching 与 extended thinking**，usage 统计可能不真实。多轮 ReAct 每轮重发完整 system prompt + 历史，未用 `cache_control` 断点复用 → 成本与延迟成倍浪费 |

---

## P3 — 记忆 / 元认知 / 叙事代码（15 项）

### 记忆系统

| # | 位置 | 问题 |
|---|---|---|
| P3-1 | `app/core/engine/memory_blocks.py`（372 行） | `BlockType` 五层（`CORE/USER/ARCHIVE/ENTITY/CONTEXT/PERSONA`，`:25-31`）**恰好对上 README 第 19 行宣传的"核心/会话上下文/归档/实体/人格"**，但**零 importer**。纯 `dict[label, MemoryBlock]` + `list[PassageRecord]`，进程内不持久化。**主链路用的是完全不同的 DB 表实现** |
| P3-2 | `app/core/engine/memory_pressure.py`（307 行） | 零 importer。上下文压力阈值 + 4 种压缩策略枚举 |
| P3-3 | `app/core/memfs/store.py`（543 行） | Git 版本化记忆文件系统，只被自身 `memfs/__init__.py:10` 引用 |
| P3-4 | `persistent_memory.py:199,213,245,677` + `lifecycle.py:219,295,277` | **4 个衰减函数 + 3 个归档/遗忘函数全部零调用方**。衰减数学是真的：`lifecycle.py:219-274` 指数衰减 `old * (DECAY_BASE ** days_since_access)`、`persistent_memory.py:677-695` 倒数 `1/(1+days)`、`:199-211` 乘法 `*= 0.95` —— 但没人调。README 的"情节记忆衰减与自动归档"：**衰减部分靠 `memory_reflection.py:78` 的 `recency_score *= 0.8`（乘常数，非时间函数）部分成立，自动归档完全不运行** |
| P3-5 | `app/core/scheduler.py:117-121` | "Memory Cleanup" 模板任务存在，但 `register_handler` **从未被调用**，`SCHEDULED_TASK_TEMPLATES` 定义后无人使用，`run_pending:76-77` 对无 handler 的 task 直接跳过。**所有 cron 任务空转** |
| P3-10 | `app/skills/memory_manager.py:31` | 类名 `PersistentMemory`，实现是 `self._cache: list[MemoryEntry]`，**进程内列表，重启即丢**。命名与行为相悖 |

**正面记录** ChromaDB **真用真调**（`vector_memory.py:57` `PersistentClient` + `:115` `coll.query(query_texts=[...])`），双层检索设计合理（`:97-105` 向量优先 → `:138-181` SQL 关键词兜底），`MemoryRetrievalLog` 真实写入（`:128-135`），访问计数与 `last_accessed_at` 真实更新（`:124-125`）。上下文压缩 `compressor.py` 真跑且有 LLM 失败回退（`:97-99` except → `_truncate`）。

### 元认知 / 反思：叙事代码

| # | 位置 | 问题 |
|---|---|---|
| P3-6 | `app/core/metacognition/`（11 模块 2,040 行） | 9/11 有**真实算法**：`monitor.py:97-188` 5 类缺陷检测（重复调用/上下文溢出/目标漂移/工具误用/能力缺口）+ 加权健康分 · `causal.py:81-160` 6 类根因归因 · `self_refactor.py:31-158` 效率评分 + JSON 真实持久化 · `goal_adjuster.py:38-202` 可行性评估 · `capability_discovery.py:54-136` 5 类模式模板匹配 · `resource.py:51-136` 复杂度评估与三档资源分配 · `hypothesis.py:69-193` 4 条路径打分 · `memory_pruner.py:85-168` Jaccard 合并剪枝 · `orchestrator.py:65-175` 编排逻辑完整。**但全仓零 importer、零 API、零测试** |
| P3-7 | `app/core/metacognition/sub_agent.py:110-130` | docstring 自认 *"Execute a single sub-agent (simulated)"*，注释写 "In a real implementation, this would: 1. Create an isolated context 2. Run the agent loop 3. Collect results"。实际 `agent.result = f"Completed: {agent.goal[:50]}"`、`tokens_used = len(agent.goal) * 10  # simulated`、`iterations = 3  # simulated` |
| P3-8 | `app/core/metacognition/orchestrator.py:1-6` | docstring 声称 *"unified execution loop"* —— **从未运行过** |
| P3-9 | `app/reflection/`（3 文件 1,728 字节） | **最劣质的一档**。`improvement.py:18-22` `analyze` 永远 `return []`，`add_suggestion` 是 `pass` · `reflection_engine.py:22-23` `return ReflectionResult(score=0.8, feedback="Good progress")` **无视输入** · `self_evaluation.py:25-30` 返回硬编码 `score=0.8, passed=True` **完全无视被评估的 output**。类名/docstring/方法签名齐全，行为是 return 常量。零调用方（仅自身 `__init__.py`）、零测试 |

> **P3-7 / P3-9 / P3-8 三处的杀伤力大于缺少任何单个功能。** 评审翻到 `reflection_engine.py:22` 看到无视输入的 `score=0.8`，对整个项目可信度的折损远超少一个功能。

### 仿真（唯一完全达标的子系统）

| # | 位置 | 问题 |
|---|---|---|
| P3-13 | `app/simulation/llm_reviewer.py`（110 行） | 完整实现，降级安全设计好（`__call__:89-105` 失败返 RETRY 而非 ACCEPTED、`:107-110`）。**但生产路径 `workflow/engine.py:637` 和 `orchestrator.py:198` 都用 `HarnessReviewer()`** → LLM 评审层未接入，只在 `simulation/__init__.py:9` 重导出 |
| P3-14 | `app/core/vector_memory.py:193` | **模块导入期实例化 ChromaDB 单例**。`main.py:42` 的 `find_spec` 预检晚于 `app.core.agent_engine` 导入链 → chromadb 缺失时 import 直接抛错（导入顺序耦合缺陷） |
| P3-15 | `app/simulation/experiments.py:90` | 热传导 `temp_limit` 过宽，实测 `dt=5.0`（cfl=5.56，远超 0.5 稳定极限）返回 `converged:true, iterations:1` —— **发散漏判**。`_diverged` 未捕获，影响自动调参有效性 |

### 引擎活着但无人派活

| # | 位置 | 问题 |
|---|---|---|
| P3-11 | `app/core/auto_loop.py`（459 行） | 引擎活着（`main.py:162` 注册进 watchdog 跑 `run_forever`、`:223-249` 注册唯一 runner `register_runner("autonomous", ...)`、`:155` 启动恢复），但 **`grep start_task app/api/` 零命中** —— 没有任何 API 能创建 AutoLoopTask。且 `TaskManager.submit:172` 用同一张表走独立路径，**不经过 AutoLoopEngine** |
| P3-12 | `app/services/settings_service.py:137` | `autonomous_agent_mode` 返回 `"auto"/"manual"`，**全仓无任何执行逻辑读它切换引擎**。纯展示用 |

---

## P4 — 前端（24 项）

| # | 位置 | 问题 |
|---|---|---|
| P4-1 | 多个目录 | **11,657 行死代码 = 27.8%**：`src/utils/` 5,233（28 模块 0 importer）· `src/forms/` 3,570（30 文件 0 importer）· `src/legacy/` 877 · `src/components/full/` 584 · 16 个未用 ui 原语 ~1,280（Box/Chart/Details/Divider/Error/ErrorBoundary/Form/Header/Helper/Label/List/MarkdownRenderer/Modal/Nav/Tabs/Toast，且 `ui/index.ts` barrel 也 0 消费者）· `pages/TasksPage.tsx` 113 |
| P4-2 | `src/utils/__tests__/` | **57% 的测试量（25 文件 4,353 行）花在 0 引用的代码上**。而 agent/chat/code/collaboration/workflow/tracing/eval/terminal/group/mobile/messages/charts/full/ios/a11y **15 个组件目录零测试**。关键路径无测试：`WorkflowsPage` `MCPPage` `SkillsPage` `PluginsPage` `TracesPage` `EvalPage` `TerminalPage` `ReasoningPage` `DoctorPage` `DashboardPage` |
| P4-3 | `src/store/__tests__/page.test.ts:7,8,14,20` | 断言 `isValidRoute` / `page: null` —— **这两个字段在 `store/page.ts:30-33` 不存在**。`tsconfig.app.json:34-39` 排除测试，所以编得过 |
| P4-4 | `src/api.ts`(830) + `src/lib/api-client.ts`(117) + `src/services/*.ts`(597) | **3 套并行 API client**。20 个页面用返回 `any`、抛裸 `Error`、重试时改共享 headers 对象的 `api.ts`；3 个用类型化 `ApiError` 的 `api-client.ts`（最干净，且有契约测试）；1 个用 services。**另有 5 处裸 `fetch` 绕过全部**（`api.ts`、`api-client.ts`、`chatService.ts`、`DashboardPage.tsx`、`legacy/LoginPage.tsx`） |
| P4-5 | `navConfig.ts:10-14` / `store/types.ts:83-89` / `store/page.ts:3-28` | **3 套 Page union 互不一致**（28/24/26 个 id）。`plugin-manage` 在 `store/page.ts` **重复两次**；`approvals`/`memory` 是**幽灵**（有声明无路由无组件无导航）；`crews`/`authapikeys` 可路由但不在 `ALL_NAV_NAV_ITEMS_BASE` → 导航/搜索/⌘K 到不了 |
| P4-6 | 3 份 ErrorBoundary | `components/ErrorBoundary.tsx`(52，只有 1 个接在 `main.tsx:16`) + `ui/ErrorBoundary.tsx`(115，0 importer) + `full/ErrorBoundary.tsx`(146，0 importer)。**零路由级边界** —— 任一 lazy page 抛错白屏 |
| P4-7 | i18n | **6.8% 采用**：107 个 `t()` 在 9 个文件，对 **1,255 条硬编码中文**（60+ 文件，含**全部页面标题**：`TracesPage.tsx:10-11` "链路追踪"、`ReasoningPage.tsx:10-11` "推理引擎"）。156/167 个 tsx 从不 import i18n。切英文后 ~93% UI 仍是中文 |
| P4-8 | i18n 细节 | 7 个 key 在 `en.json` 缺失（`home.create_agent`/`home.quick_actions`/`home.start_task`/`home.subtitle` + 3 个 `_desc`）静默降级 · `index.html:2` 硬编码 `lang="zh-CN"` 从不同步 · 7 个语言全 `rtl: false` 但 `styles/rtl.css`(151 行) 无 importer · `npm run i18n:check` **未接 CI** |
| P4-9 | `package.json` | **8 个零引用依赖**：`vaul`/`react-hotkeys-hook`/`@monaco-editor/react`（~2MB）/`@tanstack/react-virtual`/`react-dropzone`/`zod`/`react-hook-form`/`@hookform/resolvers`。加 `@tanstack/react-query`（5.101.4，最大未用依赖，正是缺失的缓存层）+ `react-router-dom` 只被 2 个死文件引用 |
| P4-10 | `.eslintrc.json` vs `package.json:9` | **108 键的 ESLint 配置未生效**，`npm run lint` 跑 oxlint（**2 条规则**）。`no-explicit-any: warn` 不执行 → **314 个 `any` 存活**（130 文件），`as any` 38 处 |
| P4-11 | `vite.config.ts:77-82` vs `ci.yml:91` | coverage 阈值定义（lines 60 / functions 59 / statements 60 / branches 49），CI 跑 `npm test` 而非 `npm run test:coverage` → **阈值从未被评估** |
| P4-12 | `App.tsx` | **无 auth gate**。`PROTECTED_PAGES`（`store/page.ts:37`）只被自己的测试和死代码 `legacy/route-guard` 引用；`LoginForm.tsx` 0 引用；`legacy/{pages/LoginPage,store/auth,services/authService}` 孤儿；`api.ts:97-153` 的 refresh token 机制服务着一个没人驱动的流程。**E2E 钉 `ENABLE_AUTH=false`（`playwright.config.ts:43`）并断言无登录字段** |
| P4-13 | 全局 | **零乐观更新**（`grep optimistic` 0），112 个手写 `setState(prev => ...)`，无缓存失效层。`useChat.ts:55-57` 失败静默 `.catch(() => setMessages([]))` |
| P4-14 | 全局 | **16 处 `console.*` 残留**（PluginsPage 5、useTheme 3、LazyImage 3…），无客户端错误上报，**API 失败无 toast** |
| P4-15 | `App.tsx:53-56,101-143` | 手写 hash switch 路由。**无 `<BrowserRouter>`、无路由表、无嵌套路由、无 URL 参数**，25 个 `lazy()` + 4 个 `manualChunks` 代码分割是好的 |
| P4-16 | 组件 | **14 个重复 basename**：`SessionSidebar`（`workspace/` 309 + `messages/` 335）· `MarkdownRenderer`（`chat/` 277 + `ui/` 219）· `ErrorBoundary` ×3 · `EmptyState` ×3 · `MobileChatPage` ×2 · `Badge`/`Button`/`Card`/`Dropdown`/`Progress`/`Skeleton`/`Toast`/`ToolCallCard`/`MobileLayout` 各 ×2-3（`ui/` vs `full/` vs `ios/` vs `agent/` vs `collaboration` vs `legacy/`） |
| P4-17 | 超大文件 | `api.ts` 830 · `SettingsPage` 780 · `FactoryModePage` 704 · `ClusterPage` 671 · `RightPanel` 507 · `CollaborationConsole` 506 · `PluginsPage` 476 · `AgentsPage` 447 · `index.css` 1,558。**全是无 class 的手写巨组件，无路由内代码边界** |
| P4-18 | `MOBILE_ADAPTED_PAGE_IDS`（8 项） | 另外 20 个页面静默 fallback 到 `MobileChatPage`（`App.tsx:103`） |
| P4-19 | 魔法字符串 | storage key 字面量散落无 constants 模块（`auth_token` 15×、`i18next_lng` 10×、`refresh_token` 3×、`user_info` 2×、`climber.sidebar` 2×）· `'/api/v1'` ×5 绕过 `API_BASE_URL` · SSE 事件名裸字符串（`'text'`/`'thinking'`/`'tool_call'`/`'tool_result'`/`'done'`/`'error'`，`useChat.ts:91-162`）无 union |
| P4-20 | `@/` alias | `vite.config.ts:12-14` + tsconfig paths 都配了，**使用 0 次**，全部相对路径 |
| P4-21 | `src/store/` + `src/stores/` | **双 store 并存**，`useSessions.ts` 的头注释记录了它被写出来修的同步 bug |
| P4-22 | `collaboration/CollaborationConsole.tsx`(506) + `group/GroupRoom.tsx`(265) | 两个 WebSocket 消费端，**零测试** |
| P4-23 | E2E | 6 spec / 26 测试 / 357 行，`workers:1`、`fullyParallel:false`，只覆盖 6 条路由的导航 + a11y 标记 + 一次 agent CRUD |
| P4-24 | 依赖细节 | `@fontsource-variable/inter` + **两个** `@fontsource/jetbrains-mono` 走 JS 而非 CSS 自托管 · devDeps 里 `canvas` 3.2.3 原生构建 · Capacitor 3 包与响应式 Web + PWA **两套移动方案并存** |

**正面记录** React 19.2.7 + Vite 8.1.1 + TS strict（含 `noUncheckedIndexedAccess`）· Zustand 5 · Radix 原语 + Tailwind 4.3 + CVA · 代码分割完整 · 暗色模式**真正完整**（160 个 CSS 变量 + 系统偏好检测 + localStorage）· 25 个 lazy + 4 vendor chunks · xterm + @xyflow + monaco + 8 个 i18n locale（各 356 行/326 key）· 无障碍标记（`aria-current`/`aria-expanded`/`aria-label`/焦点环）· CI 有真门禁（lint/typecheck/build/unit/e2e 五个 job）· **零 `@ts-ignore`** + 仅 8 个非空断言。

---

## P5 — 治理与信号（12 项）

| # | 位置 | 问题 |
|---|---|---|
| P5-1 | `pyproject.toml` | **包名 `agent-engine`**，description 才写 Climber。唯一 entry point 是 `climber-headless` |
| P5-2 | `pyproject.toml [tool.coverage.run] omit` | `fail_under = 80` 但 omit 排除 `app/api/*` · `app/models/*` · `app/services/*` · `app/schemas/*` · `app/main.py` + **10 个 `app/utils/{massive_final,ultimate,extreme,ultra_mega,mega,super,max,ultra,huge,massive}`** —— **这 10 个目录在仓库里根本不存在**。评委翻配置文件即判定覆盖率注水 |
| P5-3 | `app/api/v1/test_factory_configuration_review2.py` | **235 行测试文件混在生产代码目录** |
| P5-4 | 根目录 8 份 `*_REPORT.md` | `PERFORMANCE_REPORT` / `SECURITY_AUDIT_REPORT` / `REGRESSION_TEST_REPORT` / `DARK_MODE_OPTIMIZATION_REPORT` / `OPTIMIZATION_REPORT` / `DEPLOYMENT_VERIFICATION_REPORT` / `mobile-ux-optimization-report` / `CODE_QUALITY_REPORT` —— 互相覆盖，抢占"规范"叙事却稀释信号 |
| P5-5 | 文档冲突 | `docs/ARCHITECTURE.md` + README Mermaid 图（**GitHub 渲染显示 "Loading"**）+ `docs/integration/INTEGRATION_SUMMARY.md:163` 三份架构说法不一致 |
| P5-6 | README 快速开始 | 直接 `pip install -r requirements.txt`（无锁文件、无 `pip install -e .`、无版本矩阵）+ `alembic upgrade head`（**必炸**） |
| P5-7 | README 能力表 | 宣称"分层记忆（核心/会话上下文/归档/实体/人格）"→ 宣传的那套是死代码（P3-1）· 宣称"多 Agent 协作 顺序/层级/群聊"→ 后两者半成品（P2-19）· 宣称"安全加固 路径穿越防护"→ 正确实现零调用（P1-10） |
| P5-8 | 仓库 | **4 star / 0 fork / 无 release tag / 56 commits** |
| P5-9 | 缺失文件 | 无 `CHANGELOG.md` · 无 `CODE_OF_CONDUCT.md` · 无 `GOVERNANCE.md` · 无 `SECURITY.md`（只有 `SECURITY_AUDIT_REPORT.md`）· 无 `maintainers` 区块 |
| P5-10 | 协议 | **A2A / ACP 零实现**。`docs/MARKET_RESEARCH.md:451` 仍是待办（"必须支持 MCP（已是事实标准），考虑实现 A2A 兼容"） |
| P5-11 | `skills/` 目录 | 5 个 `.skill.json` 是**隐藏文件**，`skills/*/*` glob 匹配不到 —— 任何自动化盘点都会误判为"5 个空文件" |
| P5-12 | 仓库根 | `.test_daemon.pid` / `.test_daemon_alert_config.json` 运行时产物误提交 |

---

## 死代码明细（21,164 行 / 17.9%）

| 分组 | 行数 | 成员 |
|---|---|---|
| **前端** | **11,657** | `utils/` 5,233（4,353 行测试陪着）· `forms/` 3,570 · `legacy/` 877 · `components/full/` 584 · 16 个未用 ui 原语 ~1,280 · `TasksPage` 113 |
| 后端·编排 | 5,637 | Pregel 2,061 · FlowExecutor 330 · ensemble 360 · subagent 339 · react_loop+pipeline+router_decision 720 · collaboration 孤儿 817 · `SkillComposer` 334 · mcp_controller 34 |
| 后端·记忆/元认知 | 3,262 | metacognition 2,040 · memory_blocks 372 · memory_pressure 307 · memfs 543 |
| 后端·安全/死实现 | 1,581 | `security_sandbox.py` 662 · docker_sandbox 239 · fs_isolation+network+quotas 419 · audit 227 · reflection 60 |
| 小计 | 22,137 | 四行相加 |
| **计入「死代码」的净额** | **21,164** | 扣除 973 行在**已接线模块**内部的死函数（`mcp_controller` 34 · `SkillComposer` 334 · `FlowExecutor` 330 · 协作编排内未调用的 handler 275），这些随宿主模块一起接线，不单独计入 |

> 口径说明：标题的 21,164 是**应删净行数**；22,137 是**死代码所在文件总行数**，两者相差 973 行的部分是已接线模块内部的残留死函数。整改时以 21,164 作为删除量目标。

> 这 21,164 行是**评审的注意力成本**。技术评委翻到 `metacognition/sub_agent.py:110-130` 会看到 docstring 自认 simulated + `tokens_used = len(goal) * 10 # simulated`；翻到 `reflection/reflection_engine.py:22` 会看到无视输入的 `score=0.8`。
---

## 排期建议

> 距 GOSIM 提交 10/17、OSCHINA 报名 10/11 约 2.5 周

### 第 1 周：把叙事从工作台翻成 harness

| 优先级 | 动作 | 对应缺口 |
|---|---|---|
| 1 | `/eval` 接上 `adapters/arcbench/` 运行时，落一张真实分数表进 README | P0-1 P0-2 P0-3 P0-4 |
| 2 | 重建 Alembic 基线，删掉 `create_all` + `suppress`，全新库跑通 `alembic upgrade head` | P0-5 |
| 3 | 修 `sessions.py` 五处 fail-open + JWT 改查库 | P1-1 P1-2 |
| 4 | 接上 Docker 沙箱（配置已对，只差接线） | P1-9 P1-10 |

### 第 2 周：补 harness 能力 + 清死代码

| 优先级 | 动作 | 对应缺口 |
|---|---|---|
| 5 | 加 `grep` / `glob` / `search` 三个检索原语 | P2-1 P2-2 |
| 6 | tool result 截断（头尾各 2k）+ 参数解析失败改显式 repair 重试 | P2-3 P2-4 |
| 7 | Anthropic adapter 接 prompt caching + extended thinking | P2-30 |
| 8 | **删约 12,000 行**：`app/reflection/` 整包、metacognition 11 模块（或接一个进主循环）、`react_loop.py`、`engine/pipeline.py`、`router_decision.py`、4 个 collaboration 孤儿模块、`mcp_controller.py`、前端 `utils/`+`forms/`+`legacy/`+`full/` | P2-6~10 P2-20 P3-1~3 P3-6 P4-1 |
| 9 | groups 加 `POST /groups/{id}/tasks` + `/run`，解锁已有 2,125 行已测代码 | P2-14 P2-15 P2-16 |
| 10 | 修编辑器 `sourceHandle`；collaboration checkpoint 真正续跑 | P2-22 P2-18 |

### 第 3 周：治理收口

| 优先级 | 动作 | 对应缺口 |
|---|---|---|
| 11 | 包名改 climber，清掉失效的 coverage omit | P5-1 P5-2 |
| 12 | CHANGELOG / CODE_OF_CONDUCT / GOVERNANCE / SECURITY.md；8 份报告合并进 `docs/`；删 `.test_daemon.*` | P5-4 P5-8 P5-9 P5-12 |
| 13 | 录 3 分钟视频：一条 bug → agent 自改 → 测试绿 → 提交 → 评测数字上屏 | — |

### 杠杆点

**第 1 项和第 8 项是两端的杠杆：**

- **第 1 项**给你评审要的证据（"技术可行性"栏的可复现分数）
- **第 8 项**让你已有的能力被看见（把评审注意力从死代码抢回主链路）

单次改动收益最高的两处：**P0-3 + P0-1**（2,165 行现成评测资产接进空壳接口，两周内拿到证据）、**P2-14**（2 个端点解锁 2,125 行已测代码）。

---

## 附录：只读未修的正面项

- 活的主循环 `agent_engine._iteration_loop:363-467` 质量在线（delta 合并、真实 token 计量、stop 记录部分响应、空响应纠偏、metrics 埋点）
- `core/sandbox.py` 白名单制沙箱扎实（`shlex.split` 无 shell + `realpath` 逃逸校验 + rlimit + 环境变量白名单）
- `utils/ssrf.py` 质量好且接入点密集（含重定向复查）
- `collaboration/deadlock.py` 三色 DFS + Kahn 分层，11 个测试含 3 个真连 SQLite 集成测试 —— **全仓编排代码质量最高的一块**
- `app/simulation/` 全链路打通，README 描述与代码相符（含"不自研求解器"的诚实边界声明 `harness.py:7-8`）
- `task_worker._run_task:340-353` 条件 UPDATE 抢占是正确乐观锁；`resolve_owner_agent_payload:25-74` 拒绝 payload 明文 key
- 后端 512 个 test 函数真实有效，多轮审计发现均配回归测试
- 前端 TS strict + `noUncheckedIndexedAccess`，零 `@ts-ignore`，暗色模式完整，代码分割完整，CI 五门禁
- 依赖精简（59 个，无 MUI/AntD/moment/lodash/axios/storybook/MSW）
