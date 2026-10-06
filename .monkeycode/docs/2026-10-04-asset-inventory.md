# 2026-10-04 资产整合盘点

范围：用户要求"全面严格对齐设计稿/竞品（含 deepseek-harness）"、"A 卷循环功能"、"前端审美提升"前，先整合当前内存（MEMORY）与仓库已有什么保障、什么待办、什么已知问题，并审核问题清单、拉取子任务。

## 1. 内存与执行约束（.monkeycode/MEMORY.md，248 行）

### 保障（已固化的正确做法）
- 中文对话（含推理与工具标题）。
- 多子任务并发执行（"并发 8 个子任务"：能拆尽拆、一次拉满并行），失败不停止、逐项汇报。
- 前端修改前必须先读 `docs/plans/frontend-anchored-ui.md`（锚定式三栏布局、组件顺序、显隐触发、设计令牌约束），禁止自由发挥布局。
- 前端视觉方法论：先定风格/主色/设计约束再写页面；单一成熟组件库不混用；复用规则（同一形式出现 2 次封装复用组件）；配色/字号/间距/圆角/阴影统一为 token；设计规范成文并被引用；学习参考截图布局不照搬表面样式；Tag/Chip/Badge 语义区分。
- 前端多 Agent 协同只借鉴 `cc-haha` 交互范式（浅克隆在 /tmp/opencode/cc-haha），不复制源码/图标/品牌资产；仅访问源码/README/架构资料，不访问第三方在线演示。
- 画像本地存储不对外暴露；提示词版本管理不做（内置 agent）。
- 前端必须与后端联通（用户强调"前端 ui 跟后端要接上来"，参考开源地址都要看）。
- 保持公开 API 兼容、不破坏既有测试。

### 已知环境/仓库事实（排错保障）
- 环境无 `python`/`uv`，只有 `python3`；后台终端用 sh。
- climber 后端基线：`python3 -m pytest tests/`；ruff 只查改动文件（全仓约 864 个既有错误）。
- 前端基线：`npm run typecheck`/`lint`/`build`；`i18n:check` exit 0 但存在既有 legacy drift 告警。
- `tests/conftest.py` 静默忽略机制已彻底移除，不要加忽略列表。
- `app/modules/*` 的自动生成测试套件（test_huge/massive/ultra）期待 `list` 返回 dict，已统一补齐；test_comprehensive 无参弱断言与 test_large 的 test_method_N 是测试自身 bug，用 deselect 排除。
- 测试自身 bug 只记录不改测试逻辑。
- docparse 对 33 页 DOCX 大文档曾失败，需用户贴文本或本地解析。
- 算法层深挖文档在 docs/references/deep-dives/（9 篇），NeMo/Zep/OpenSandbox/HyperAgents 四篇标注"未读源码"，移植项待评估不直接实现。

## 2. 仓库资产与已交付

### 前端
- 锚定式三栏布局已落地：`AnchoredWorkspaceLayout`（左 `AnchoredLeftNav` / 中 `AnchoredChatColumn` / 右 `AnchoredInfoPanel`）、`AnchoredComposer`（#chat 真实渲染的 Composer，含斜杠菜单/模型选择/思考等级/权限/技能/附件/澄清气泡）、`AnchoredPopupStack`（审批栈）、`TaskTracePanel`/`ArtifactPreview`/`ControlBar`（旧布局）。
- 27 个 Hash 路由面：21 connected / 3 partial（#chat #agents #settings）/ 3 移动端占位。
- 本会话已交付：`#chat` 澄清气泡（AnchoredComposer 600ms 防抖 → `POST /instruction-traces/understand`，needs_clarification 时气泡）；`#eval` 评估面板（EvalQuickAssess + EvalReports）；`#agents` 运行时参数闭环（temperature/max_tokens 随 Agent 创建持久化并回显 T0.9 · 4096）；api.ts 111+ 方法。

### 后端
- `AutoLoopEngine`（app/core/auto_loop.py，459 行）已装配：lifespan 自动启动、`recover_interrupted_sessions`、watchdog 看门狗、AutoLoopTask 表持久化、TaskStateMachine 状态机、双 loop（monitor + execute）。**但无 API 暴露、无前端控制 UI**。
- `TaskCreateRequest.max_rounds`（默认 5）存在。
- 评估：`app/core/evaluation/*`（DeterministicJudge 离线打分、report_store）+ `/eval/assess`、`/eval/reports`。
- 指令理解：`understand_instruction` → `POST /instruction-traces/understand`。
- 任务/子任务：`/tasks` 提交/取消/快照/事件 SSE + subtask claim 闭环（TaskWorkerProgressControls）。

### 设计/对齐资产
- `docs/plans/frontend-anchored-ui.md`（161 行，锚定三栏强制规范）。
- `docs/plans/ui-backend-alignment.md`（79 行，行级证据表 + 本轮可用契约：/ui/rules GET/PUT、/tasks/{id}/snapshot、/tasks/{id}/events、/groups/{group_id}/snapshot、/permissions/resolve）。
- `.monkeycode/specs/2026-09-26-parity-codex-deepseek-opencode/tasklist.md`：T1–T8 全 [x]（色板/图标/控件/叠加层/图表/工具调用审批 diff tracing/终端）。
- 设计稿解析：/tmp/opencode/bf63a5e1.md（33 页，含内层任务循环 + 外层元进化循环概念，70+ 开源地址）。
- 本地参考克隆：`/tmp/opencode/codex`（OpenAI Codex，含 codex_ui_spec.md 详细 TUI 结构）、`/tmp/opencode/harness`（deepseek-harness `@deepseek-ai/dsh-root` v0.2.1-alpha，一切皆插件/Cordis/agent-loop，apps: cli/desktop/desktop-host/web）、`/tmp/opencode/openhands`、`/tmp/opencode/CodeWhale`、`/tmp/opencode/cc-haha`。

## 3. 已知问题清单（a_all-issues.json / a_handover.json）

- 195 条去重核验记录：193 条当前状态 = 119 仍存在 / 58 条件成立 / 12 已修复 / 4 证据不足；严重度 9 high / 140 medium / 44 low。
- 9 条 high 集中在：PostgreSQL checkpoint upsert 编译失败（R9-15）、迁移与 ORM 漂移（R11-H18）、sessions.working_memory 无迁移（R13-17）、sessions.agent_id NOT NULL 冲突（R13-18）、documents.content_hash/indexed_at 迁移缺失（R13-19）、agents.agent_role/goal/backstory 迁移缺失（R13-20）、工作流错误事件吞掉/死分支（R11-H11）、协作空输出挂起/假恢复（R11-H12）、_running_tasks 从不写入（R13-32）。
- 明细已导出：/tmp/opencode/issues_193.md（386 行）。
- 历史审计分组：LLM 适配器正确性（含 R9-07 Anthropic 工具调用、R9-08/R10-08 Ollama 流式 tool_calls 丢弃、R9-09 OpenAI 超时尾块重复、R10-07 累计 token）、记忆与上下文子系统（R11-N12 压缩删除已注入记忆）、OpenAPI 与前端契约断裂（17 处高严重度）、cost 计量与 usage 链路、认证与中间件链、多用户隔离、数据库迁移链（alembic upgrade head 必崩）、调度器三份实现、前端 stores 与 API client 层、工具沙箱与命令安全、流式协议（SSE/WS/断流）等。

## 4. 待澄清（阻塞项）

1. **"A 卷"** 具体指什么？工作区与设计稿中均无"A 卷"字样；设计稿含"内层任务循环 + 外层元进化循环"。可能指：a) 某份评估/任务卷要接持续循环；b) 让 Agent 一直自主跑（参考 deepseek-harness agent-loop / auto_loop）；c) 其他用户特定含义。
2. **deepseek-harness 对齐范围**：后端插件架构（一切皆插件/Cordis/agent-loop）要落地多少？前端 Web UI 视觉是否作为审美基准之一？
3. **循环功能落地形态**：接现有 AutoLoopEngine（已装配后端但无 API/UI）？还是实现任务级"持续循环直到完成/用户停止"？
4. **审美提升**：允许参考 deepseek-harness Web UI / codex TUI / openhands / cc-haha 哪些？以现有 token 体系（T1 色板）为基线重做哪些区域？

## 5. 建议执行路径

1. 澄清 A 卷与对齐范围（本盘点对应的 4 项）。
2. 循环功能：若指 Agent 持续自主运行 → 暴露 AutoLoopEngine API + 前端循环控制（继续/停止/轮次上限）。
3. 问题清单：从 9 high 开始拆子任务并发修复（迁移漂移、工作流事件、协作挂起、_running_tasks）。
4. 全面对齐：以 ui-backend-alignment.md 的"剩余"列 + frontend-anchored-ui.md 为准逐项验收；deepseek-harness 后端插件能力按优先级对齐。
5. 审美：基于 T1 色板 + 参考克隆建立对照，重塑高优先级页面。
