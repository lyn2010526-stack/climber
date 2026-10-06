# Session Plan: 群组协作层 multi-agent 强化（reviewer principal / 失败语义 / guardrail fail-closed）

## Goal
- 在 /workspace/climber 将群组协作层按 multi-agent 方向补强：reviewer 显式 principal、group_chat/hierarchical 失败语义、消除 base.py 重试分叉、函数 guardrail fail-closed、补行为测试，最后跑协作测试与 ruff 并总结（不 commit）。

## Constraints & Preferences
- 只允许修改 `app/core/collaboration/` 与相关测试文件；禁止修改 `app/core/agent_engine.py`、`app/api/v1/`、`app/core/engine/`、前端文件。
- 保持现有公开 API 兼容（保留 `strict` 参数等），不破坏现有测试。
- ruff 只报告，不必修完所有历史问题。
- 不得 commit；工作区存在大量历史未提交改动（非本次会话产生），总结只归属本次改动。
- 最终测试命令：`cd /workspace/climber && python3 -m pytest tests/core/test_collaboration_review45.py tests/core/test_collaboration_guardrails.py tests/core/test_critical_regressions.py tests/core/test_concurrency_limits.py tests/core/test_collaboration_multiagent.py tests/core/test_collaboration_deadlock.py -q`

## Progress
### Done（全部完成）
- 分析：读全 `agent_runner.py`、`base.py`、`sequential.py`、`group_chat.py`、`hierarchical.py`、`checkpoint.py`、`guardrails.py`、`prompts.py`、`constants.py`、`callbacks.py`、`principal.py`、`models_groups.py`、4 个测试文件及 `.monkeycode` 设计文档。
- 代码修改（全部已应用，语法通过）：
  - `agent_runner.py`：新增 `principal_for_group(group)`（owner-first，从 `group.user_id` 构造 `Principal`），导入 `LOCAL_SUBJECT_ID`、`Any`。
  - `base.py`：`_run_agent_with_retry` 重试分叉逻辑删除、改为纯转发 `run_agent_with_retry`（失败抛 RuntimeError）；`run_task` 用 `principal_for_group(group)` 捕获并经 `_dispatch_by_process_type(..., principal=)` 传入三个 process；`_run_single_task_in_dag` worker/reviewer 均传 `principal`；reviewer 调用改为模块引用 `agent_runner.run_agent_simple(...)`；`_run_sequential_process` 签名加 `principal`。
  - `sequential.py`：`run_sequential_process` 加 `principal=None` 并贯穿 `_execute_worker_turn`/`_execute_reviewer_turn`；调用改 `agent_runner.*` 模块属性调用；动态 import 清理；guardrails 导入排序修正（I001）。
  - `group_chat.py`：`run_group_chat_process`/`_execute_chat_round` 加 `principal` 贯穿；删除异常吞没（不再 `output = f"[Error: {e}]"` 继续跑），异常回抛由 run_task 兜底标 failed；message broadcast 改用真实 `tokens_used`。
  - `hierarchical.py`：`run_hierarchical_process` 加 `principal=None` 并贯穿 `_plan_subtasks`/`_delegate_subtasks`/`_validate_output`（保留 RuntimeError re-raise 语义）；调用改 `agent_runner.*`；`__import__` 动态导入清理为顶层 import。
  - `guardrails.py`：`run_llm_guardrail` 与 `run_function_guardrail` 异常统一 fail-closed（恒返回 `False, [_exception_issue(...)]`）；`strict` 改为日志字段真实使用；docstring 更新。
- 测试修改/新增：
  - `tests/core/test_collaboration_guardrails.py`：更新至 fail-closed 语义；新增空 feedback 默认 issue、function false 无 feedback 拦截、LLM 无可解析 issues 仍拦截等测试。
  - 新增 `tests/core/test_collaboration_multiagent.py`（6 个测试）：checkpoint resume 从旧轮继续、sequential/group_chat/hierarchical worker 失败标 failed、DAG worker+reviewer 收到 owner principal、`_run_agent_with_retry` 转发且 principal 透传。
- 验证（全部通过）：
  - 目标测试组 102 passed：review45 + guardrails + critical_regressions + concurrency_limits + multiagent(6) + deadlock(15)。
  - `tests/core` 全量：633 passed，1 failed（`test_reasoning_levels.py::test_permission_tiers_report_mode_and_tool_states`，套件级测试顺序污染，单独运行通过，排除新测试文件后仍失败，与本次改动无关）。
  - ruff：6 个被改协作文件 32（基线）→ 25 个错误，无新增问题，剩余均为历史 TRY/ARG/RUF 项（任务允许只报告）。
  - `git diff --stat` 确认范围：7 个协作文件 + 2 个测试文件（checkpoint.py 为历史 diff，本次未改）。
- 未 commit（按要求保留在工作区）。

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- principal 采用 owner-first：`principal_for_group(group)` 直接从 `group.user_id` 构造 `Principal(subject_id=owner)`，确定性、不依赖 auth context（后台任务不抛 RuntimeError、群任务以所有者身份执行）。
- base.py `_run_agent_with_retry` 改为纯转发，行为从"失败返回 ("",0)"变为"失败抛 RuntimeError"，对齐 agent_runner 单一实现。
- sequential/group_chat/hierarchical 的 agent 调用统一改 `agent_runner.run_agent_*` 模块属性调用（call-time 解析，兼容 monkeypatch）；但 base.py `_run_single_task_in_dag` 保留模块全局名 `run_agent_with_retry(...)` 调用（test_critical_regressions monkeypatch 依赖）。
- group_chat 失败语义选择"回抛由 run_task 兜底"（标 failed 并广播 task_failed）。
- `strict` 参数保留（API 兼容）但通过 `logger.exception(..., strict=strict)` 真实使用以满足 ARG 规则。

## Next Steps
1. (none — 任务完成，等待用户下一步指示)
2. 如需 commit：只 add `app/core/collaboration/` 下 6 个本次修改的文件 + `tests/core/test_collaboration_guardrails.py` + `tests/core/test_collaboration_multiagent.py`（checkpoint.py 的 diff 属历史改动，需用户确认归属）。

## Critical Context
- 修改前工作区已有大量历史未提交改动（`app/api/v1/*`、`app/core/agent_engine.py` 等约 60+ 文件），非本次产生。
- 关键事实：`Principal` frozen dataclass（`subject_id` 等）；`get_context_principal()` 在 auth 开启且无 context 时抛 `RuntimeError`；`AgentGroup.user_id` 默认 "default-user"；`constants.MAX_RETRIES=2`、`TASK_TIMEOUT=300`、`FALLBACK_MODELS` 含 gpt-4o→gpt-4o-mini 等。
- patch 兼容点：`agent_runner.run_agent` 被 review45/新测试 scripted patch（9 个位置参数，args[8]=principal）；`agent_runner.run_agent_simple` 与 `base_module.run_agent_with_retry` 被 test_critical_regressions monkeypatch。
- 测试环境：unittest 风格 + `patch.dict(os.environ, APP_TESTING=true, TEST_DATABASE_URL=sqlite+aiosqlite:///:memory:, DATABASE_URL=...)`；`base.group_ws_hub` 是共享单例，`patch.object(base.group_ws_hub, "broadcast", AsyncMock)` 对所有模块生效。
- 已修过的测试坑：`"不通过"` 含子串 `"通过"` 导致 LLM guardrail 关键词匹配误判 pass（改用 `"needs rework entirely"`）；直接调用 `_run_agent_with_retry` 无 principal 时落回 context principal（owner 解析在 run_task 层）。
- pytest 配置 asyncio_mode=AUTO；ruff line-length=100，ARG/TRY/SIM 等全开，per-file-ignores 仅 tests。
- git stash 注意：工作区混合历史改动，用 stash 对比基线时必须立即 pop（本次已两次安全恢复）。

## Relevant Files
- `app/core/collaboration/agent_runner.py`：本次加 `principal_for_group`。
- `app/core/collaboration/base.py`：本次删重试分叉、principal 贯穿 run_task/_dispatch/_run_single_task_in_dag。
- `app/core/collaboration/sequential.py`：本次 principal 贯穿、模块属性调用、动态 import 清理、I001 修正。
- `app/core/collaboration/group_chat.py`：本次失败回抛 + principal。
- `app/core/collaboration/hierarchical.py`：本次 principal 贯穿三阶段 + 清理。
- `app/core/collaboration/guardrails.py`：本次 fail-closed 统一。
- `app/core/collaboration/checkpoint.py`：历史 diff，本次未改。
- `tests/core/test_collaboration_guardrails.py`：本次更新至 fail-closed。
- `tests/core/test_collaboration_multiagent.py`：本次新增 6 个行为测试。
- `tests/core/test_reasoning_levels.py`：套件级污染失败来源之一，非本次范围。
- `app/core/collaboration/prompts.py`、`constants.py`、`callbacks.py`、`app/core/principal.py`、`app/storage/models_groups.py`：只读上下文。
- `.monkeycode/specs/2026-08-05-unified-agent-platform/design.md`：历史设计参考（Principal fail-closed 哲学）。

## 2026-10-03 续跑修正（8 路并行后）
- 修 `app/core/agent_engine.py` stop/freeze 时被 claim 输入 `error=null`：改为按 finish_status 生成兜底 error（stopped→"Execution stopped before the input completed"；其余→"Input ended without a recorded error"），报告不再渲染 `": blocked"`。新增回归 `test_stopped_claimed_input_always_records_error`。
- 新增 Alembic merge 迁移 `f0a1b2c3d4e5_merge_queue_and_genome_heads.py`，合并 `1b2c3d4e5f6a` 与 `d5e6f7a8b9c0` 两 head；`alembic upgrade head` 现为单一 head。验证：fresh DB `upgrade head`→`downgrade base`→`upgrade head` 全通过。
  - 关键坑：`alembic/env.py` 用 `settings.database_url`，不读 `TEST_DATABASE_URL`；隔离迁移验证必须用 `DATABASE_URL=sqlite+aiosqlite:////tmp/...` + `PYTHON_DOTENV_DISABLED=1`。
- 修 profile 测试隔离失败（17 项）：根因是 `tests/isolated/test_profile_persistence_window.py` 用测试本地 `Base.metadata.create_all` 建表，与真实模型绑定的 `app.storage.Base` 元数据不一致；该模块被其它测试先 import 后本地 Base 不含任何表。改为按模型自身 metadata 显式创建 profile 三表（`user_profile_events`/`user_profile_snapshots`/`user_profile_learning_settings`）。全量 isolated：238 passed / 0 failed（此前 221/17）。
- 修 `TaskTracePanel.tsx`：三泳道改为恒定渲染（去掉 `tasks.some(...) &&` 空泳道隐藏），符合 `frontend-anchored-ui.md` 固定三泳道规范；AnchoredComponents 11/11、TaskTracePanel 18/18。
- 修 `RightPanel.persistence.test.tsx`：单 section 组不渲染 `role="tab"` 是组件既有设计（RightPanel.tsx:226），测试用 `selectTab` 查询错误；改用 `expandGroup`。rightPanel 全套 51/51。
- 参考文档：`reference-coverage.md` openagents SHA 与矩阵版本表冲突，已对齐为矩阵 `OA` 值并加注；新增读状态权威性说明（矩阵 `S` 行附 file:line，coverage 的"存在-未读"为早期快照）。
- 桌面主题验证 5/5（live 5173），截图重生成；翻译检查 exit 0，0 缺失（6 locale，921 键）。

## 2026-10-04 续跑（子任务拉取闭环验证）
- 子任务拉取闭环（后端 API + 前端面板）已完成并通过 API e2e 与 Playwright UI 验收；预览地址 https://5173-1822695f51232c6b.monkeycode-ai.online
- 回归验证：后端 `test_task_worker_progress_controls.py` + `test_workflow_task.py` + `test_task_owner_workflow_contract.py` 共 56 passed；前端 `Task14.logs.test.tsx` 6 passed；翻译检查 exit 0。
- 发现 `collaborationLayout.test.tsx` 13 项失败为**历史遗留**（非本次改动引入）：用 git worktree 在 HEAD(720633b3) 上复现同样 14 项失败（工作区因历史修复 group-creation 断言后为 13 项），根因是测试期望 heading `name: 'Task'` 但 en.json 文案已改为 `Group task`（head 已不一致）。与本次 subtask 改动无关，可留待专门修复。

## 2026-10-04 续跑（评估指标 + 指令理解/澄清 UI）
- 任务评估指标面板：后端 `routes/misc.py` 新增 `POST /eval/assess`（复用 core `DeterministicJudge` 离线打分，weighted mean + essential/veto 语义，无需 LLM，可立即复现）、`GET /eval/reports` 与 `GET /eval/reports/{report_id}`（读内存 REPORT_STORE）；`report_store.py` 增公开 `list_all()` 替代私有 `_reports` 访问（消除 SLF001）。前端 `EvalDashboard.tsx` 增 `EvalQuickAssess`（术语 rubric 行编辑器，逐项 PASS/FAIL + score/passed/failure_reasons）与 `EvalReports`（最近报告摘要卡片）。
- 指令理解/澄清 UI：后端 `instruction_traces.py` 新增 `POST /instruction-traces/understand`（消费 `understand_instruction` 返回 trace `task_spec` 结构，剥离 `profile_evidence` 字段，仅理解不落库）。前端 `ChatInterface.tsx` Composer 在输入防抖 600ms 后调用，仅 `progress=needs_clarification` 时在输入框上方显示警告色澄清气泡（意图摘要 + clarification_questions + Dismiss），发送时清空。
- 前端 api.ts 增 `evaluateOutput`/`listEvalReports`/`understandInstruction`；7 语言 locale 增 `eval.assess.*`、`eval.reports.*`、`chat.clarify_hint`、`common.dismiss`。
- 配置回归验证：后端新增 11 API 测试全过 + 既有 37（evaluation/instruction）全过；ruff 无新增违规（report_store `list_all` 修掉我引入的 SLF001，其余为既有）；前端 typecheck/lint/build 全绿，`reportedValues` 9 失败经 worktree 在 HEAD 复现同样失败（历史遗留，mock 补充 `listEvalReports`/`evaluateOutput` 保持契约对齐）；Anchored 系列 6 失败文件在 HEAD 不存在，属工作区未提交既有内容。
- 顺带修复 2 处既有 typecheck 错误：`ModelSelector.tsx` errorMessage 签名 `options?: object`→`(key: string)=>string`；`SettingsPage.tsx` `ErrorBanner` 补 `useI18n`。
- 冒烟：真实 uvicorn 进程 curl 新三端点全 200（assess/understand/reports），understand 返回正确结构化结果且无 profile_evidence。
- 说明：前/后端 dev server 此前已超时退出，本轮验证用临时 uvicorn 冒烟后已 kill；预览端口未占用。

## 2026-10-04 续跑（澄清 UI 落地真实组件 + UI↔后端联通盘点实施）
- 澄清气泡从旧 `ChatInterface.tsx` 移植到 `#chat` 实际渲染的 `AnchoredComposer.tsx`：新增 `clarity` state + 600ms 防抖 `api.understandInstruction` effect（输入 <2 字符/斜杠命令/流式中不触发）+ 会话重置时清空 + `slashFeedback` 下方渲染警告色气泡（summary + `chat.clarify_hint` + questions + `common.dismiss`）。Playwright 实测：填 `请重构这个模块。` → RESP progress=needs_clarification → 气泡含摘要/澄清问题/Dismiss 可见。
- 系统盘点 27 个路由面：21 connected、3 partial（#chat #agents #settings）、3 移动端占位。判定：#settings 个人资料保存为后端无能力（R10-09）的有意降级，保留；ControlBar 仅在旧 WorkspaceLayout（非 #chat 主路径），保留。
- 修复 #agents 运行时参数假交互（参数从未随 Agent 保存）：后端 `AgentCreateRequest`/`AgentResponse` 增 `temperature`（0–2）与 `max_tokens`（≥1），`create_agent` 写入 ORM 既有列，`_agent_dict`/create 响应回显；前端 `buildAgentCreatePayload` 合并 `temperature`/`max_tokens`，参数卡文案由"session-only/不保存"改为"随 Agent 创建时保存"，AgentCard 回显 `T{temp} · {max_tokens}`。7 语言 locale `params_session_note`→`params_saved_note` 并更新文案。
- 验证：后端新测试 `tests/test_agents_runtime_params_api.py` 5 passed + schema_alignment/critical 20 passed；前端 typecheck/lint/build 全绿、AgentsPage.test 9 passed、i18n:check exit 0；Playwright 实测滑块 0.9 → POST 200 → 卡片回显 `T0.9 · 4096`。
- 说明：首次实测 422（extra_forbidden）因 uvicorn 无 --reload 仍持旧 schema；kill 旧后端后重启（新 term_1791123510945_308，:8000），复测全通过。
- 待办：对照 Codex 系开源 UI（monkeycode/zcode/chatbot-ui/lobe-chat/OpenHands/LibreChat）的交互盘点（T1–T8 已立项），以及清理 e2e/_tmp-*.mjs 临时脚本。
