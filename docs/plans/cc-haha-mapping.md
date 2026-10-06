# cc-haha 架构映射文档（供 Climber 前后端多 Agent 协作参考）

- 研究对象：https://github.com/NanmiCoder/cc-haha（浅克隆于 /tmp/opencode/cc-haha，MIT License）
- 产出日期：2026-10-02
- 结论性质：仅借鉴交互范式与架构思想，不复制源码、图标、品牌资产、吉祥物与配色品牌值。
- 上游规范：本文件是 `frontend-anchored-ui.md`（前端锚定式 UI 规范）的参考源研究，落地时以锚定式规范为准。

---

## 一、cc-haha 整体架构

### 1.1 进程模型（四类进程协作）

桌面端把 CLI、Server、UI 拆成独立进程，边界清晰（docs/internals/desktop.md）：

```
Electron main
├── Chromium renderer（React 18 + Vite + Zustand 5 + Tailwind 4）
├── claude-sidecar server（Bun.serve：HTTP API + WebSocket 会话网关 + 按会话启动 CLI 子进程）
└── claude-sidecar adapters（Telegram / Feishu / WeChat / DingTalk / WhatsApp，按平台独立进程）
```

- Renderer 只做界面，通过 preload 暴露的类型化 Host API 使用原生能力，禁止直接 import Electron 或自拼 IPC channel。
- Server 是桌面端与 H5 共用的本地服务：`/api/*` REST、`/ws/:sessionId`（桌面/H5/宠物客户端）、`/sdk/:sessionId`（CLI 内部连接）、OAuth 回调、受限预览、静态 H5，全部走同一个 fetch 边界，鉴权按客户端来源区分。
- 每个平台一个独立 Adapter Sidecar，避免单个平台凭据或启动失败拖垮其他平台；共享层 `adapters/common/` 管配置、配对、会话映射、消息缓冲、去重与 WS 桥接。

### 1.2 入口与运行时

| 入口 | 运行时 | 职责 |
|---|---|---|
| `src/entrypoints/cli.tsx` | Bun | CLI/TUI 与 Agent 工具 |
| `src/server/index.ts` | Bun / Bun.serve | 本地 HTTP、WebSocket、H5 |
| `desktop/electron/main.ts` | Electron main | 窗口、IPC、Sidecar 生命周期 |
| `desktop/sidecars/claude-sidecar.ts` | Bun 编译二进制 | server / cli / adapters 统一打包入口 |

### 1.3 多 Agent 调度（核心，docs/internals/agent-internals.md）

**AgentTool.call() 单入口按参数路由到四条生成路径：**

1. **Teammate 路径**（`team_name` + `name` 同时存在）：加入团队，支持 in-process / tmux / iTerm2 三种执行后端。in-process 队友用独立 AbortController + AsyncLocalStorage 上下文隔离，权限管道经邮箱共享。
2. **异步 Subagent 路径**（`run_in_background: true`）：创建 LocalAgentTask（running）→ 异步分离执行查询循环 → 完成时 finalize + `enqueuePendingNotification()`（XML `<task-notification>`，原子 notified 标志防重复）。
3. **Fork 路径**（省略 subagent_type 且实验开启）：字节级一致保留父代理 API 请求前缀（system prompt + user context + 全部 tool_use 块 + 占位 tool_result），仅 per-child directive 是唯一差异，实现 prompt cache 命中；`isInForkChild()` 防递归。
4. **同步 Subagent 路径**（默认）：解析 Agent 定义 → 构建系统提示词 → createSubagentContext 隔离上下文 → query() async generator 查询循环。

**六种内置 Agent**（general-purpose / Explore / Plan / verification / claude-code-guide / statusline-setup），每种绑定不同工具池、模型档位与权限模式。

**工具池三层过滤**：
- 第一层全局禁止（TaskOutput、ExitPlanMode、AskUserQuestion 等仅主 Agent 可用）；
- 第二层按 Agent 类型过滤（异步 Agent 有 15 个工具白名单，MCP 工具始终允许）；
- 第三层按 Agent 定义解析（tools 白名单交集 / disallowedTools 差集）。

**Agent Teams 协作**：
- 团队事实源：`~/.claude/teams/{team}/config.json`（TeamFile：leadAgentId、members[] 含 agentId/color/backendType/mode/subscriptions）；共享任务目录 `~/.claude/tasks/{team}/`。
- 通信：`SendMessage({ to, message })` 路由——`"*"` 广播、in-process 注册表、进程级队友写 mailbox（`inboxes/{agent}.json`，proper-lockfile 文件锁 + 指数退避）、`bridge:`/`uds:` 前缀走远程。
- 消息类型协议化：纯文本、shutdown_request/response、plan_approval_response、permission_request、idle_notification。
- 关停协调：Lead 发 shutdown_request → 队友回 shutdown_response → 全部关停后 TeamDelete()。
- 权限同步：TeamAllowedPath（目录 + 工具粒度的团队级权限）；Fork 用 `bubble` 模式把权限提示冒泡到父 Agent 终端。
- 收件箱轮询：useInboxPoller 每 1s 读未读消息，按消息类型分流（关停/审批/权限/纯文本对话）。

**任务系统**：LocalAgentTask 状态机（running / completed / failed / killed），ProgressTracker 维护 tokens、toolUseCount、最近 5 个活动（循环缓冲区）、最后活动时间（检测卡死）；前台 Agent 超 120s 自动后台化；输出文件上限 5GB、O_NOFOLLOW 防符号链接攻击。

### 1.4 状态管理（Renderer）

Zustand 按领域拆 store（desktop/src/stores/）：sessionStore、chatStore、teamStore（成员 1.5s 轮询 + transcript 游标匹配）、taskStore、agentStore、activityPanelStore、workflowStore、workspaceReviewStore、settingsStore、providerStore、skillStore、mcpStore、tabStore、uiStore 等。特点：

- 后端（Server/CLI）是会话与模型配置的唯一真相来源，Renderer 只是镜像。
- workflowStore 用 epoch/generation 防并发写乱序，用 WeakSet 区分磁盘快照与实时 WS 数据，`authoritativeProgressRuns` 防止瞬态读取失败降级权威快照。
- 断线期间消息进内存队列，重连成功先补发队列再发 `sync_state` 拉取 Server 权威状态。

### 1.5 WebSocket 语义与消息流

- 每会话一条连接 `ws://<server>/ws/:sessionId`；30s ping / 10s pong 超时主动断开；重连 1s 起指数增长封顶 30s；显式关闭才停止重试。
- **客户端断开不等于停止任务**：最后客户端断开后任务继续跑，工作结束进入空闲宽限期，宽限期内重连取消清理——手机锁屏、刷新都不打断任务。
- chatStream 事件协议（docs/ui-clone/03-server-architecture.md）：`content_start` / `content_delta`（text 或 toolInput）/ `tool_use_complete` / `tool_result` / `permission_request` / `message_complete`（含 usage）/ `error` / `status`（thinking / tool_executing / idle）。

### 1.6 UI 主流程

- 布局：Title Bar(40px) + Sidebar(280px，min 240/max 400) + Main Content(flex 1) + Status Bar(36px)；全套设计令牌（ui-clone/02-ui-design-spec.md：色彩、间距 space-1~10、字号层级、圆角规范）。
- 消息流组件（desktop/src/components/chat/）：MessageList（虚拟化 + itemBoundary 测试）、UserMessage、ThinkingBlock、ToolCallBlock / ToolCallGroup、ToolResultBlock、DiffViewer、PermissionDialog、SlashCommandMenu、ContextUsageIndicator、StreamingIndicator、TurnCompletionStamp（回合结束时间戳）。
- Agent Teams 工作台（components/agentTeams/）：Workbench + Canvas（依赖泳道）+ CommunicationFeed（通信流）+ MemberInspector（成员详情）+ PlanCard；agentTeamsModel.ts 做数据建模。
- 会话活动面板（components/activity/）：SessionActivityPanel 集中查看任务进度、后台任务、SubAgent 与来源。
- 工作区 Diff 审阅（components/workspace/）：逐文件 Diff + web worker 做高亮计算。
- 输入框（ChatInput + Composer*）：斜杠命令菜单、@引用、附件拖放、能力菜单（权限/模型选择内嵌在输入框内）。

### 1.7 配置管理与持久化边界

- Agent 定义以 Markdown 文件为唯一事实源（用户级 `~/.claude/agents/*.md`、项目级 `.claude/agents/*.md`），桌面端编辑即写回文件并热重载会话；同名来源优先级：policy > flag > project > user > plugin > built-in。
- 内置 Agent 仅允许经 settings.json 的 `builtInAgentOverrides` 覆盖 model/effort 两个字段。
- 模型解析优先级链：环境变量 > 工具调用参数 > frontmatter > settings 覆盖 > 主会话模型；effort 同理。
- 持久化分域：Renderer UI 偏好（浏览器存储）、会话消息（Server/CLI）、Provider 等设置（Server 配置文件）、Electron 原生状态、IM 配置（Adapter）各不混用；任何配置形状变化必须带前向迁移 + 旧数据回归测试。
- 用户态安全：测试永不触碰真实 `~/.claude`，全部重定向到临时目录。

---

## 二、值得 Climber 借鉴的机制

| # | 机制 | cc-haha 做法 | 对 Climber 的价值 |
|---|------|-------------|------------------|
| 1 | 后端唯一真相 + 前端镜像 | Server/CLI 持有会话、模型、权限状态，Renderer 重连后 `sync_state` 拉权威状态 | Climber 已有此约定（SessionOut 为准），可强化断线恢复语义 |
| 2 | 断线消息队列 + 指数重连 | 断线消息入队、重连先补发再 sync；客户端断开任务不中断（宽限期清理） | group_ws_hub 广播目前直发，缺队列与重连协议 |
| 3 | 结构化 WS 事件协议 | content_start/delta、tool_use_complete、tool_result、permission_request、message_complete、status 六类事件 | 与 Climber 六种 Message 类型（user/thinking/tool-call/tool-result/reflection/system）天然对应，可对齐事件粒度 |
| 4 | 任务通知协议 | XML `<task-notification>`（task-id/status/summary/output-file），原子防重复入队 | 子任务完成回传主 Agent / 前端的标准化载体 |
| 5 | 进度追踪器 | ProgressTracker：tokens、toolUseCount、最近 5 个活动循环缓冲、最后活动时间检测卡死 | 直接支撑右侧"子 Agent 任务树"卡片与卡死检测 |
| 6 | 团队消息协议化 | shutdown_request/response、plan_approval、permission_request、idle 通知等类型化消息 | Climber 的 a2a_protocol.py（REQUEST/RESPONSE/EVENT）可吸收这套语义类型 |
| 7 | 邮箱 + 文件锁通信 | 成员 inbox JSON + proper-lockfile 指数退避；收件箱轮询分流处理 | Climber 后端为内存/DB 模型，可借鉴"按成员收件箱 + 消息状态机（pending/processing/processed）" |
| 8 | Fork 缓存共享思想 | 字节级一致请求前缀，仅 directive 为差异部分，prompt cache 命中 | Climber 多 Agent 同上下文派生 worker 时可显著降费（映射到 agent_runner 请求构造） |
| 9 | 工具池三层过滤 | 全局禁止 → 类型过滤 → 定义白名单/黑名单 | 映射到 roles.py 能力边界 + guardrails 的执行前过滤 |
| 10 | 自动后台化 | 前台超 120s 自动转后台，释放主流程 | Climber 长任务（checkpoint/resume 已有）可加同款阈值策略 |
| 11 | 设计令牌 + AI 可读规范 | ui-clone/02 完整 token 表，AI 生成 UI 有唯一依据 | 印证 Climber"设计令牌系统 + AI 可读规范"路线，可补齐间距/字号/圆角 token |
| 12 | 状态内嵌指示器 | ContextUsageIndicator、StreamingIndicator、TurnCompletionStamp、底部 Status Bar | 对应锚定式规范"底部状态栏（状态/缓存命中率/Token 消耗）" |
| 13 | 输入框内嵌能力菜单 | 权限模式、模型选择内嵌 ChatInput，斜杠命令直接触发 | 对应锚定式规范"底部输入栈 + 弹窗栈"与斜杠命令 |
| 14 | Diff 审阅与工作区 | 逐文件 Diff + web worker 高亮 + 整轮可撤销 | 对应 Climber ChangesSection / 文件预览卡片 |
| 15 | Workflow 运行重建 | workflowStore 从 task_started/progress/notification 事件 + 磁盘快照重建运行视图，epoch 防乱序 | Climber WorkflowEditor/TraceViewer 可借鉴"事件流重建 + 权威快照不降级" |
| 16 | 面板自动显隐 | 任务结束 5s 后自动折叠活动面板、evictAfter 延迟清除 | 对应锚定式规范"任务驱动面板自动显隐" |
| 17 | 聚合策略 | majority_vote / weighted_average / best_confidence（cc-haha 有对比思想） | Climber aggregation.py 已实现同名策略，可借鉴其 UI 呈现（一致度可视化） |
| 18 | 持久化前向迁移纪律 | 配置形状变化必须带迁移 + 旧 fixture 回归测试 | Climber alembic/前端持久化状态可引入同款门禁 |

---

## 三、不照搬的机制

| 类别 | 内容 | 原因 |
|------|------|------|
| 品牌与视觉资产 | Claude 品牌橙 `rgb(215,119,87)`、Clawd/搭搭等吉祥物、截图、图标、六套配色主题的品牌命名 | 品牌资产不复制；Climber 用自己的设计令牌体系 |
| 许可证敏感面 | THIRD_PARTY_LICENSES.md 中 vendored 的 ripgrep 二进制、受控 vendor 目录 | vendored 原生二进制有独立许可证链，Climber 直接依赖发行版包即可 |
| Electron 桌面体系 | Electron main / preload / IPC / node-pty / xterm.js / Sidecar 打包 | Climber 是 Web（FastAPI + React/Vite + 反向代理），进程模型完全不同；借鉴其"边界分层"思想即可 |
| Bun 运行时与 Ink TUI | Bun.serve、bun:bundle feature flags、Ink 终端 UI | 与 Climber 技术栈不匹配 |
| IM Adapter Sidecar | Telegram/Feishu/WeChat 等平台接入进程 | Climber 当前无 IM 接入需求；未来做时参考其"每平台独立进程 + 共享桥接层"思想 |
| Computer Use / 桌面宠物 / H5 | macOS/Windows 原生控制、宠物窗口、扫码远程 | 与 Climber Web 形态无关 |
| tmux/iTerm2 执行后端 | 队友跑在独立终端 pane | CLI 场景专属；Climber 用进程内 + WS 推送 |
| 文件系统团队存储 | `~/.claude/teams/` JSON 文件 + 文件锁 | Climber 有 SQLAlchemy + alembic 持久层，团队/收件箱应入库；只借鉴消息语义与锁重试策略 |
| Anthropic SDK 依赖面 | 围绕 Anthropic Messages 协议的 proxy 转换 | Climber 多 Provider 走自己的 model_registry / resolver |

---

## 四、具体落地建议（按优先级）

### P0（直接支撑锚定式 UI 规范核心项）

**P0-1 统一 WS 事件协议，对齐六种消息类型**
- 后端：`app/core/collaboration/agent_runner.py` + `app/core/group_ws_hub.py`——把广播事件规范化为 `content_start / content_delta / tool_call / tool_result / permission_request / message_complete / status`，payload 内带 `correlation_id`（a2a_protocol.py 已有该字段，复用）。
- 前端：`frontend-react/src/store/workspace.ts` 的 Message.metadata 已有 status/toolName/toolArgs 字段，事件协议直接落到 metadata；`useChat.ts` 消费。
- 支撑锚定式规范：中间消息流五种消息类型 + 底部状态栏四种状态。

**P0-2 子 Agent 任务树数据模型 + 进度追踪**
- 后端：`app/core/collaboration/` 新增 `progress.py`（参考 ProgressTracker 形状：latest_input_tokens、cumulative_output_tokens、tool_use_count、recent_activities[max 5]、last_activity），随 hierarchical.py / sequential.py 的 step_callback 一起经 group_ws_hub 广播。
- 前端：`frontend-react/src/components/collaboration/TaskProgress.tsx` 扩展为任务树（层级缩进节点：状态图标 + 任务名 + 耗时，失败节点红显），映射右侧"子 Agent 任务树卡片"。
- 数据落 `AgentGroupTaskCheckpoint`（checkpoint.py 已有表）或新表。

**P0-3 权限/审批弹窗走弹窗栈**
- 前端：`frontend-react/src/components/agent/FloatingPermissionDialog.tsx` 从"居中浮动"改为"输入区上方堆叠弹出"（宽度与输入区一致，按触发顺序堆叠，完成即销毁）。
- 事件来源：后端 `permission_request` 事件（P0-1），参考 cc-haha "权限提示冒泡到父 Agent"的 bubble 思想——子 Agent 权限请求统一冒泡到会话级 UI。

**P0-4 任务通知协议（防重复）**
- 后端：`app/core/collaboration/base.py` + `callbacks.py` 增加标准化 task-notification 载荷（task_id/status/summary/output 引用），原子 notified 标志防重复广播；映射锚定式规范"Agent 拆分子任务 → 自动展开任务树"。

### P1（多 Agent 协作深化）

**P1-1 类型化团队消息协议**
- 后端：扩展 `a2a_protocol.py` 的 A2AMessageType，吸收 cc-haha 语义类型：shutdown_request/shutdown_response/plan_approval/idle_notification；`handoff.py` 的 HandoffMessage 对齐 shutdown 协商（来源→目标→批准回执）。
- 死锁检测（deadlock.py）可利用 idle_notification 作为等待图输入。

**P1-2 收件箱状态机**
- 后端：`app/core/collaboration/` 新增 `inbox.py`：按成员收件箱（DB 表），消息状态 pending → processing → processed；轮询/推送双通道。
- 前端：`frontend-react/src/components/group/GroupRoom.tsx` 呈现成员通信流（对应锚定式规范可复用 CollaborationWorkspace）。

**P1-3 工具池三层过滤落到执行前**
- 后端：`roles.py`（能力边界）+ `guardrails.py` 合作为三层：全局禁止清单 → 角色类型过滤 → 成员定义白名单/黑名单；在 `agent_runner.py` 构造 tools 列表时统一执行。

**P1-4 Workflow 运行重建视图**
- 前端：`frontend-react/src/components/workflow/WorkflowEditor.tsx` + `tracing/TraceViewer.tsx` 借鉴 workflowStore 思想：从任务事件流重建运行时间线（阶段视图、中断点、断点续跑进度），用请求 epoch 防并发乱序，磁盘快照（checkpoint）不因瞬态读取失败降级。

### P2（体验与治理增强）

**P2-1 自动后台化 + 自动显隐**
- 后端：`base.py` 引擎增加"前台回合超阈值（参考 120s）自动转后台"策略；配合 checkpoint/resume 已有能力。
- 前端：任务结束 5s 后自动折叠右侧任务看板/任务树/文件预览（锚定式规范第三节已有规则，补实现）。

**P2-2 Token/缓存计量面板**
- 前端：右侧"Token 计量仪表盘卡片"——数据来自 message_complete 事件的 usage；`frontend-react/src/pages/CostPage.tsx` 已有费用页，卡片是它的会话内缩略版；趋势区展示最近 10 轮。

**P2-3 设计令牌补齐**
- 前端：`frontend-react/src/styles/` 补齐间距（space-1~10）、字号层级（H1~Tiny）、圆角（按钮 8 / 输入 12 / 对话 16 / 模态 16）token 表；所有组件强制引用变量。注意：只借鉴"token 分层结构"，色值全部使用 Climber 自己的品牌体系。

**P2-4 配置档分级联动**
- 前端：`workspace/PermissionModeToggle.tsx` + `usePermissionConfig.ts` 参考五档权限模式菜单（每档：图标 + 标题 + 描述 + 选中标记），切换配置档同步调整 UI 复杂度、工具权限、面板数量（锚定式规范"切换配置档"规则）。

**P2-5 持久化迁移门禁**
- 引入"前端持久化状态形状变化必须带迁移 + 旧 fixture 回归测试"纪律；后端 alembic 已覆盖，前端 `store/__tests__/workspace.snapshot.test.ts` 模式可扩展。

### 映射总表

| cc-haha 参考 | Climber 前端落点 | Climber 后端落点 |
|---|---|---|
| chatStream WS 事件协议 | useChat.ts、store/workspace.ts Message.metadata | collaboration/agent_runner.py、core/group_ws_hub.py |
| ProgressTracker | components/collaboration/TaskProgress.tsx | collaboration/ 新增 progress.py + checkpoint.py |
| PermissionDialog / bubble 冒泡 | components/agent/FloatingPermissionDialog.tsx | collaboration/callbacks.py（human review） |
| task-notification | components/collaboration/CollaborationWorkspace.tsx | collaboration/base.py、callbacks.py |
| SendMessage 语义类型 | components/group/GroupRoom.tsx | collaboration/a2a_protocol.py、handoff.py |
| 成员邮箱 + 轮询 | components/collaboration/CollaborationSidebar.tsx | collaboration/ 新增 inbox.py、deadlock.py |
| 工具池三层过滤 | components/agent/ToolCallCard.tsx（禁用态展示） | collaboration/roles.py + guardrails.py + agent_runner.py |
| Workflow 运行重建 | components/workflow/WorkflowEditor.tsx、tracing/TraceViewer.tsx | collaboration/checkpoint.py |
| Agent Teams 工作台（泳道/通信流/成员详情） | components/collaboration/ + pages/ClusterPage.tsx | storage/models_groups.py（AgentGroup/Member/Task） |
| ContextUsageIndicator / 状态栏 | workspace/ControlBar.tsx、SessionStatusBadge.tsx | core/agent_engine.py（usage 汇总） |
| 斜杠命令 / Composer 能力菜单 | pages/ChatPage.tsx、agent/ChatInterface.tsx | commands 相关（如已有） |
| 设计令牌 | styles/、components/ui/ | 无 |
| 活动面板自动折叠 | workspace/RightPanel.tsx + rightPanel/sections/ | 无（纯前端） |

---

## 五、合规声明

1. 本文档仅提炼 cc-haha 的**交互范式与架构思想**（进程边界、事件协议、状态机、优先级链、迁移纪律），供 Climber 自行实现。
2. 不复制任何源码文件、图标、吉祥物、品牌配色值、logo、截图或文档原文；Climber 落地代码全部原创。
3. cc-haha 为 MIT License；若未来确需引用其文字表述，须按 MIT 要求保留版权与许可声明，默认做法是完全不引用。
4. cc-haha 中与 Claude/Anthropic 相关的品牌元素、API 协议耦合面不在借鉴范围内。

---

## 附：研究覆盖的 cc-haha 关键文件

- README.zh-CN.md、AGENTS.md、LICENSE、THIRD_PARTY_LICENSES.md
- docs/internals/desktop.md、agent.md、agent-internals.md、structure.md
- docs/ui-clone/01-requirements.md、02-ui-design-spec.md、03-server-architecture.md
- src/AGENTS.md、src/QueryEngine.ts（会话消息消费/usage 累积）、src 目录结构
- desktop/src/stores/（teamStore、taskStore、workflowStore 等 40+ store）、desktop/src/components/（chat、agentTeams、activity、workspace）
