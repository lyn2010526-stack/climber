# 开源项目深度研究：Agent 前端 UI #21-32

> 核验日期：2026-10-01。
> 研究范围：`docs/references/open-source-projects.md` 第三组 #21-32 共 12 个项目，全部聚焦 Agent 前端 UI、对话界面、工具与思考可视化。
> 证据原则：只提炼结构、契约和可复用交互模式，不复制源码、截图或品牌资产。每项记录均标 `verified / unavailable / inferred`；`verified` 表示本次通过公开仓库页面或 README 核验，`inferred` 表示来自同名候选仓库、历史文档或项目内既有代码注释，不能视为原仓库的直接源码证据。
> 关联实现：`frontend-react/src` 下对话、工作台、模型切换、工具卡片、思考流、trace 与 workflow 模块。

## 1. 结论速览

1. 原索引中 10 个仓库可访问并标 `verified`：EditHere、LobeChat、Open-WebUI、LibreChat、Dify、Flowise、Chatbot UI、Vercel AI Chatbot、Jan、UI-TARS Desktop。
2. 原索引中 MonkeyCode 与 Zcode 两个仓库 404，原始 URL 均标 `unavailable`。
3. MonkeyCode 找到同名候选仓库 `lizepenggithub/monkeycode-ai-agent-worktrace`，README 只有“工作留痕智能体项目”一句话，不足以核验“思考流可视化、补丁操作界面”，相关结论标 `inferred`。
4. Zcode 找到 `zai-org/ZCode`，README 可访问并定位为“AI 编程工作台，提供桌面应用、浏览器界面和终端 Agent”，但不能证明它就是原 `zcode-ai/zcode` 改名后的仓库，原始项目身份标 `unavailable`，候选 README 内容标 `inferred`。
5. LobeChat 当前 README 已以 LobeHub 身份出现，定位从单聊产品转向“Agent 编排工作空间”；本次只核验当前公开 README，不对历史 LobeChat 细节作已核验声明。
6. Flowise README 顶部明确标注仓库已归档，只能作为历史交互范式参考。
7. EditHere 实际公开 README 定位是本地截图批注工具，不是代码 Agent 前端；它对 Climber 的价值是“把修改意图转成可交给 Agent 的结构化反馈”，应作为交互范式参考而非前端本体。

## 2. 每项目结论

### 21 · EditHere

- 一句话定位：本地截图、批注、调整布局后导出 JSON/图片给 AI 的界面修改工具，适合作为“改哪里、怎么改”的可视化反馈范式。
- 交互/架构精华：
  - 全局截图后支持点批注、框批注、全局意见和“大爆炸”区域拆分。
  - 批注按编号与画面位置一一对应，侧栏意见直接定位到具体区域。
  - 拖拽/缩放区域会记录调整前后坐标和尺寸，导出 JSON 同时包含原图、批注和布局变化。
  - 提供配套 CLI 与 skill，AI 等待用户完成标注后再接收反馈；取消或超时不会把未提交编辑当作修改要求。
  - 明确本地识别、不上传截图，不内置模型调用，反馈与模型服务解耦。
- Climber 映射：
  - `frontend-react/src/components/code/DiffPanel.tsx` 已做统一 diff 解析、行号、CSS 变量主题。
  - `frontend-react/src/components/workspace/rightPanel/sections/ChangesSection.tsx` 可作为“改动反馈”挂载点。
  - `frontend-react/src/components/agent/FloatingPermissionDialog.tsx` 已具备“用户确认再继续”的权限交互。
- 可借鉴：把“位置/范围/文字意见/调整前后值”做成结构化反馈，而不是只让用户写自然语言。
- 不采用：不引入桌面截图、图像识别、拖拽布局能力；Climber 是无登录 Web 工作台，复用其 JSON 契约和“AI 等待明确反馈”的交互即可。
- 证据等级：`verified`。

### 22 · MonkeyCode

- 一句话定位：原索引指向“思考流可视化、补丁操作界面”，但原始仓库 404；候选同名仓库无法证明是原项目。
- 交互/架构精华（受证据限制）：
  - 候选仓库仅一句话，无可用 UI 证据。
  - Climber 项目内 `DiffPanel.tsx` 注释引用 `MonkeyCode desktop/ui/src/diffView.tsx`，`ThinkingDetails.tsx` 注释引用 MonkeyCode 的 thinking strip，可作为既有实现意图线索，但不是本次核验到的源码证据。
- Climber 映射：
  - 思考流：`frontend-react/src/components/chat/ThinkingDetails.tsx`、`components/agent/ThinkingStream.tsx`。
  - 补丁/改动：`frontend-react/src/components/code/DiffPanel.tsx`、`components/workspace/rightPanel/sections/ChangesSection.tsx`。
- 可借鉴：仅当未来拿到原仓库或可信源码后，再对照“thinking strip 自动折叠、diff 操作面板”的细节。
- 不采用：本次不能依据候选仓库或内部注释做源码级对标。
- 证据等级：原始 URL `unavailable`；候选 README 与内部注释 `inferred`。

### 23 · Zcode

- 一句话定位：候选仓库 `zai-org/ZCode` 是 AI 编程工作台，包含桌面应用、浏览器界面、终端 Agent，符合原索引“Agent 工作台”方向；原始 `zcode-ai/zcode` 仍 404。
- 交互/架构精华（候选 README 核验）：
  - Web 模式通过 `zcode --web` 启动，浏览器访问，API/WebSocket 用访问令牌认证。
  - CLI、TUI、Web 共用同一套 agent 运行时，`zcode` 无参数进 TUI，`--web` 进 Web。
  - 支持远程项目（SSH/WSL）和本地/远程资源准备，区分开发态与发行态。
  - 未在 README 层面核验“模型端点/API 密钥/任务进度面板”的具体 UI 结构。
- Climber 映射：
  - 模型端点/密钥：`frontend-react/src/pages/ApiKeysPage.tsx`、`components/chat/ModelConfig.tsx`、`components/chat/ModelSelector.tsx`。
  - 任务进度/工作台：`frontend-react/src/components/workspace/RightPanel.tsx`、`ReasoningPanel.tsx`、`TaskHistoryPage.tsx`、`TaskMonitorPage.tsx`。
- 可借鉴：同一 Agent 运行时同时承载桌面、Web、CLI 的架构思路，前端只需消费统一事件/API。
- 不采用：不引入 Electron 桌面壳；Climber 当前以 Web 工作台为目标。
- 证据等级：原始 URL `unavailable`；候选 README `inferred`。

### 24 · LobeChat / LobeHub

- 一句话定位：当前 `lobehub/lobe-chat` README 已以 LobeHub 身份出现，定位为把 Agent 当作持续工作单元的编排工作空间。
- 交互/架构精华：
  - Agent Builder：描述一次需求即生成可用 Agent，模型和模态统一接入。
  - Agent Groups：多 Agent 协作、共享上下文、并行迭代。
  - Workspace 共享空间：明确所有权和可见性。
  - 10,000+ Skills 与 MCP 兼容插件，插件可扩展工具和消息渲染。
  - `OPENAI_MODEL_LIST` 环境变量支持 `+` 增加、`-` 隐藏、`model_name=display_name` 控制模型列表。
- Climber 映射：
  - 模型列表控制：`frontend-react/src/components/chat/ModelSelector.tsx`、`ModelPickerButton.tsx`。
  - 多 Agent/会话组织：`frontend-react/src/components/workspace/SessionSidebar.tsx`、`components/agents/AgentStatusBadge.tsx`。
  - 插件/MCP 页面：`frontend-react/src/pages/PluginsPage.tsx`、`MCPPage.tsx`。
- 可借鉴：模型列表可由配置追加/隐藏/重命名；Agent 作为持续工作单元而非一次性任务。
- 不采用：不照搬“IM Gateway、定时调度 Agent、订阅制社区”等平台级能力。
- 证据等级：`verified`（当前 README，身份注意已标注）。

### 25 · Open-WebUI

- 一句话定位：可完全离线自托管的 AI 平台，支持 OpenAI-compatible API 与 Ollama，强调扩展性、RBAC 和本地化隐私。
- 交互/架构精华：
  - 细粒度 RBAC 与用户组，管理员按组给访问权限。
  - 插件体系区分 Filters、Actions、Pipes、Tools、Skills，并可接 MCP/MCPO/OpenAPI 工具服务。
  - Live Workflow & Message Flow：实时展示 AI 构建与执行清单，消息可排队。
  - Open Terminal：Agent 获得终端和文件系统，可在聊天中执行多步任务。
  - 本地/离线优先、PWA、持久记忆、RAG、多模型并发、用量分析。
- Climber 映射：
  - 权限/审批：`frontend-react/src/components/workspace/permissionMode.ts`、`PermissionModeToggle.tsx`、`agent/FloatingPermissionDialog.tsx`。
  - 消息/队列/状态：`frontend-react/src/components/agent/ChatInterface.tsx`、`hooks/useChatVisuals.ts`。
  - 任务/工具流：`frontend-react/src/components/workspace/rightPanel/sections/ExecutionSection.tsx`、`ActivitySection.tsx`。
- 可借鉴：工具执行状态放到聊天流中实时展示，并把权限模式和工具能力分开建模。
- 不采用：不引入多用户登录、SSO、企业租户和终端隔离后端；Climber 当前是无登录本地 Web 形态。
- 证据等级：`verified`。

### 26 · LibreChat

- 一句话定位：多模型、多会话、可自定义端点的开源聊天前端，直接覆盖 Climber 的模型注册/切换和推理可视化需求。
- 交互/架构精华：
  - Custom Endpoints：直接接任何 OpenAI-compatible API，无需代理。
  - Reasoning UI：为 DeepSeek-R1 等 CoT 模型提供动态推理展示。
  - Trace Viewer：按顺序查看模型对话、工具轮次和成本，支持 OpenTelemetry/Langfuse 导出。
  - Context Usage：查看对话、工具流量、Agent 指令、缓存、成本和上下文压力。
  - 会话 fork、续写、压缩、导入导出；Agent 支持 MCP、Skills、Subagents、代码工作区。
- Climber 映射：
  - 模型/凭据：`frontend-react/src/components/chat/ModelSelector.tsx`、`ModelConfig.tsx`、`ModelPickerButton.tsx`、`pages/ApiKeysPage.tsx`。
  - 推理/思考：`frontend-react/src/components/chat/ThinkingDetails.tsx`、`components/agent/ThinkingStream.tsx`。
  - trace：`frontend-react/src/components/tracing/TraceViewer.tsx`、`pages/TracesPage.tsx`。
  - 会话/分支：`frontend-react/src/components/workspace/SessionSidebar.tsx`。
- 可借鉴：将“模型切换、上下文用量、trace、reasoning”放在同一套可观察信息模型里。
- 不采用：不引入其多租户认证、OIDC、订阅计费和企业部署层。
- 证据等级：`verified`。

### 27 · Dify-WebUI

- 一句话定位：开源 LLM 应用开发平台，核心是可视化 workflow、Agent、RAG、模型管理和 LLMOps 可观测。
- 交互/架构精华：
  - 可视化工作流画布，支持构建和调试 AI workflow。
  - Agent 自带沙箱，可运行命令、安装软件、处理文件。
  - LLMOps：监控应用日志和性能，支持 Opik、Langfuse、Arize Phoenix 集成。
  - 模型供应商统一接入，支持大量 OpenAI-compatible 模型。
  - 本项目历史 UI 调研已记录 Dify 运行详情以 Result/Detail/Tracing 稳定标签组织、加载层独立、内容区独立滚动。
- Climber 映射：
  - workflow：`frontend-react/src/components/workflow/WorkflowEditor.tsx`、`WorkflowNodes.tsx`、`PropertiesPanel.tsx`。
  - 右侧运行详情：`frontend-react/src/components/workspace/rightPanel/lazySections.tsx` 的 Trace/Diff/Files 等分区。
  - trace：`frontend-react/src/components/tracing/TraceViewer.tsx`。
- 可借鉴：运行详情按“结果、细节、追踪”分组，加载中/运行中/结果状态占用稳定面板空间。
- 不采用：不引入 Dify 品牌、外观、多租户或企业计费；只借鉴信息架构。
- 证据等级：`verified`。

### 28 · Flowise

- 一句话定位：可视化构建 AI Agent 的低代码平台，React UI + Node server + 第三方节点组件；README 已标注归档。
- 交互/架构精华：
  - Agent Flow 可视化画布，用户通过拖拽节点构建 Agent。
  - monorepo 分 server、ui、components、api-documentation，UI 与执行端分离。
  - 曾作为答辩调试面板原型参考，对应任务状态机可视化。
- Climber 映射：
  - 状态机/任务：`app/core/task_state_machine.py`（后端），前端见 `frontend-react/src/pages/TaskMonitorPage.tsx`、`TaskHistoryPage.tsx`。
  - 可视化画布：`frontend-react/src/components/workflow/WorkflowEditor.tsx`。
- 可借鉴：只借鉴“节点类型面板 + 属性面板 + 画布运行态”的布局契约。
- 不采用：仓库已归档，不引入代码、依赖或生态节点；不把 Flowise 当活跃维护基线。
- 证据等级：`verified`（归档状态已核验）。

### 29 · Chatbot-UI-Next

- 一句话定位：面向所有人的开源 AI 聊天应用，2.0 已迁移到 Supabase 持久化。
- 交互/架构精华：
  - 基础聊天消息流、会话列表、移动端布局。
  - 1.0 保留在 legacy 分支，可作为历史模板参考。
  - 从浏览器存储迁移到 Supabase，说明持久化选择会影响多模态和跨设备场景。
- Climber 映射：
  - 对话基础：`frontend-react/src/pages/ChatPage.tsx`、`components/agent/ChatInterface.tsx`、`components/chat/MessageBubble.tsx`。
  - 移动端：`frontend-react/src/pages/MobileChatPage.tsx`、`components/layout/AdaptiveMobileLayout.tsx`。
- 可借鉴：消息折叠/基础对话组件模板和会话持久化边界。
- 不采用：不照搬 Supabase 依赖；Climber 已有本地后端会话模型。
- 证据等级：`verified`。

### 30 · Vercel-AI-Chatbot

- 一句话定位：基于 Next.js + AI SDK + shadcn/ui 的流式对话模板，是“如何消费模型流式输出”的最小工程范本。
- 交互/架构精华：
  - AI SDK 统一文本、结构化对象和工具调用 API。
  - AI Gateway 统一路由多个模型，模型配置集中在一个 models 文件。
  - shadcn/ui + Radix UI 提供可访问的组件原语。
  - 数据持久化使用 Neon Postgres，文件使用 Vercel Blob。
  - 对 Climber 的核心价值是 SSE 流式输出和工具调用前端消费范式。
- Climber 映射：
  - SSE：`frontend-react/src/api.ts`、`useChat.ts`。
  - 对话界面：`frontend-react/src/components/agent/ChatInterface.tsx`、`components/chat/MessageBubble.tsx`、`StreamingCursor.tsx`。
  - 模型路由：`frontend-react/src/components/chat/ModelSelector.tsx`、`ModelPickerButton.tsx`。
- 可借鉴：模型 provider 路由集中配置，流式 UI 与工具调用使用统一 hook。
- 不采用：不引入 Vercel 托管依赖、Auth.js 和 Neon/Blob 服务；Climber 是自托管后端。
- 证据等级：`verified`。

### 31 · Jan

- 一句话定位：本地优先的开源 ChatGPT 替代品，桌面应用形态，强调完全控制与隐私。
- 交互/架构精华：
  - 本地模型下载与运行，也可连接 OpenAI、Anthropic、Mistral、Groq、MiniMax 等云模型。
  - 自定义 Assistant 和 MCP 集成。
  - 本地 OpenAI-compatible API 端口 `localhost:1337`，供其他应用复用。
  - 桌面安装覆盖 Windows、macOS、Linux，构建依赖 Tauri/Rust。
- Climber 映射：
  - 隐私/锁屏：`frontend-react/src/components/privacy/LockScreen.tsx`、`PinSetup.tsx`、`hooks/useAppLock.ts`。
  - 多会话：`frontend-react/src/components/workspace/SessionSidebar.tsx`。
  - 本地模型端点：`frontend-react/src/pages/ApiKeysPage.tsx`（provider 含 `ollama`）。
- 可借鉴：本地优先产品把“模型选择、自定义助手、本地 API”统一成清晰的控制面板。
- 不采用：不引入 Tauri 桌面壳和本地模型下载引擎。
- 证据等级：`verified`。

### 32 · UI-TARS-Desktop

- 一句话定位：字节 UI-TARS 生态的桌面 GUI Agent 和通用 Agent TARS 栈，核心是 GUI 操作、工具流事件和实时状态展示。
- 交互/架构精华：
  - UI-TARS Desktop 提供本地/远程电脑与浏览器操作员。
  - Agent TARS 提供 CLI、Web UI 和 headless server，同一事件流驱动多种前端。
  - Event Stream：协议驱动的事件流，用于 Context Engineering 和 Agent UI。
  - 工具流支持 shell 命令、多文件结构化展示、工具调用与 deep thinking 计时统计。
  - MCP 作为核心工具协议，可挂载真实世界工具。
- Climber 映射：
  - 工具卡片：`frontend-react/src/components/agent/ToolCallCard.tsx`、`ToolCallVisualization.tsx`、`ToolDisclosure.tsx`。
  - 事件/trace：`frontend-react/src/components/tracing/TraceViewer.tsx`。
  - 终端/执行：`frontend-react/src/pages/TerminalPage.tsx`、`components/workspace/rightPanel/sections/ExecutionSection.tsx`。
- 可借鉴：把工具调用、思考计时、事件流统一为前端可渲染的流式事件，避免不同面板各自猜测状态。
- 不采用：不引入 GUI Agent 模型、远程操作服务和桌面端。
- 证据等级：`verified`。

## 3. 5 条 UI 落地优先项

1. 在 `frontend-react/src/components/workspace/RightPanel.tsx` 和 `rightPanel/groupModel.ts` 上落地“结果/细节/追踪”稳定分组，参照 Dify 的运行详情三标签，避免刷新或切换任务时面板内容跳动。
2. 在 `frontend-react/src/components/agent/ToolCallVisualization.tsx` 和 `TraceViewer.tsx` 上统一工具事件模型，参照 UI-TARS Event Stream 与 LibreChat Trace Viewer，让聊天工具卡片、右侧执行面板、trace 树共用同一状态语义。
3. 在 `frontend-react/src/pages/ApiKeysPage.tsx`、`components/chat/ModelConfig.tsx`、`ModelSelector.tsx` 上补齐“自定义模型端点 + API 密钥 + 模型发现错误”的完整闭环，参照 LibreChat Custom Endpoints 与候选 ZCode 的工作台方向；现有 `ModelSelector` 已覆盖 HTTPS 端点校验和超时错误，下一步是让配置页和会话内切换共享同一凭据状态。
4. 在 `frontend-react/src/components/code/DiffPanel.tsx` 和 `rightPanel/sections/ChangesSection.tsx` 上增加“改动反馈”结构化契约，参照 EditHere 的 JSON 契约：文件路径、原值、新值、修改原因、审批状态，供工具执行与用户修改意图对齐。
5. 在 `frontend-react/src/components/chat/ThinkingDetails.tsx` 和 `components/agent/ThinkingStream.tsx` 上保持“运行中可见、完成后自动折叠、保留真实字符数/耗时”的交互，参照 LibreChat Reasoning UI 与 MonkeyCode 历史意图；不要在无流式数据时渲染伪造的思考进度。

## 4. 证据清单与计数

| # | 项目 | 等级 | 证据数 | 可访问证据 |
| --- | --- | --- | --- | --- |
| 21 | EditHere | verified | 2 | 仓库状态 200、README |
| 22 | MonkeyCode | unavailable + inferred | 1 | 候选 README 一句话 |
| 23 | Zcode | unavailable + inferred | 1 | 候选 README `zai-org/ZCode` |
| 24 | LobeChat | verified | 2 | 仓库状态 200、当前 README（LobeHub） |
| 25 | Open-WebUI | verified | 2 | 仓库状态 200、README |
| 26 | LibreChat | verified | 2 | 仓库状态 200、README |
| 27 | Dify | verified | 2 | 仓库状态 200、README |
| 28 | Flowise | verified | 2 | 仓库状态 200、README（归档标注） |
| 29 | Chatbot UI | verified | 2 | 仓库状态 200、README |
| 30 | Vercel AI Chatbot | verified | 2 | 仓库状态 200、README |
| 31 | Jan | verified | 2 | 仓库状态 200、README |
| 32 | UI-TARS Desktop | verified | 2 | 仓库状态 200、README |

说明：证据数按“可访问的公开核验落点”计算，不把 HTTP 404 算作可访问证据；MonkeyCode 和 Zcode 的原始 404 已作为 `unavailable` 记录，不计入证据数。
