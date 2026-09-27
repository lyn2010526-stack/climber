# UI 资料核验：001–020

核验日期：2026-09-25。目标：Climber。本文件覆盖百项清单的 001–020；021–100 未在本批核验。

## 核验口径

- 已读取项目 `.monkeycode/MEMORY.md` 全文，并查看现有 `UI_RESEARCH_REPORT.md` 的可见内容；旧报告的工具输出存在截断，本批仅将实际可见部分用于背景与去重检查。旧报告的热度数字、已实现声明和测试结果均未作为本批证据；本批没有复核应用实现。
- 20 项均进行过实际联网获取或精确检索，并读到项目正文或明确标注的候选正文。正文覆盖 **20/20**，其中原名身份确认 **16 项**，身份歧义 **4 项（011、014、016、017）**；无法定位 0 项；确认重复 0 项。候选正文已读与原名身份确认分别计数。
- 最高读取层级：源码 1 项（003）；官方文档 19 项。这里“官方文档”仅表示从项目仓库 README、项目自身文档站或发布包取得的作者文档，不表示组织背书、治理地位或生产质量认证。四个歧义项的层级只适用于明确列出的候选。
- 013 的网站请求仅返回标题，单独标记正文访问失败；同项通过包 README 获得有效正文。019 的发布包 README 输出被截断，随后定位相关段落并读取独立组件文档；没有声称读完整个大型 README。
- 已读 URL 均为本次工具实际获取地址。检索摘要仅用于定位，具体行为结论取自实际打开的原文。未执行 README 中的安装、启动、隧道或 Agent 命令，也未复制源码、图标或品牌资产。
- 行为描述表示“文档说明”或“源码可见”；本批没有运行外部项目或实际交互演示。Climber 可采用点全部为建议，相关接口和状态仍需后续实施时核验。
- 许可证仅在实际打开内容明示时记录，注明证据所在；“未核验”表示本次正文未见明确许可，不代表无许可证。本文件不作法律适用结论。
- 分支 URL 会变化，本次未锁定所有仓库 commit。019 的 CDN README 固定为 12.1.2，仅作为所读版本，未断言最新版本；其补充组件文档来自 main，两个资料层级分开列示。

## 001 · CopilotKit

- **原名**：CopilotKit。
- **身份状态**：确认；读取 `CopilotKit/CopilotKit` 自述。
- **定位方式**：直接获取精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/CopilotKit/CopilotKit/main/README.md
- **读取层级**：官方文档（README，重点为 Features、useAgent Hook、Generative UI）。
- **具体可借鉴行为**：文档把消息流、工具返回组件、用户与 Agent 共享状态、人类确认暂停分为独立能力；示例由界面读取 Agent 状态并通过按钮修改状态。
- **Climber 可采用点（建议）**：将任务阶段、待用户确认和工具结果作为独立视图状态；用户确认后由后端决定能否继续。先设计状态契约与现有运行事件的映射。
- **许可证**：MIT；README 的 License 正文明确写出。
- **边界/去重**：与 004 存在生态联系；本项为应用 SDK，004 为交互协议，各自有独立原文。文档中的商业托管能力应单独评估。

## 002 · assistant-ui

- **原名**：assistant-ui。
- **身份状态**：确认；`assistant-ui/assistant-ui`。
- **定位方式**：直接获取精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/assistant-ui/assistant-ui/main/README.md
- **读取层级**：官方文档（Usage、What you get、Backends、Customization）。
- **具体可借鉴行为**：会话、消息、输入器、会话列表和消息操作栏可组合；运行时提供者负责连接后端；文档列出流式消息、自动滚动、重试、附件和内联人类确认。
- **Climber 可采用点（建议）**：把会话状态适配与界面组件拆开；分别为消息列表、输入器和工具卡定义输入数据与回调，便于在桌面工作区复用。
- **许可证**：MIT；README License 正文明确写出。
- **边界/去重**：README 所称可访问性和生产体验属于项目自述，本批未运行其测试。没有以本项目替代 014。

## 003 · prompt-kit（React AI UI）

- **原名**：prompt-kit(React AI UI)。
- **身份状态**：确认；`ibelick/prompt-kit` 与 React AI UI 描述相符。
- **定位方式**：获取 README，随后读取输入器组件实现。
- **实际读取 URL**：https://raw.githubusercontent.com/ibelick/prompt-kit/main/README.md
- **实际读取 URL（源码）**：https://raw.githubusercontent.com/ibelick/prompt-kit/main/components/prompt-kit/prompt-input.tsx
- **读取层级**：源码。
- **具体可借鉴行为**：源码按内容高度调整文本框并限制最大高度；容器点击可聚焦文本框；Enter 调用提交，Shift+Enter 保留换行；工具按钮阻止点击冒泡以避免触发容器聚焦。
- **Climber 可采用点（建议）**：组合输入区、附件区和操作区；自适应高度达到上限后内部滚动；保留 Shift+Enter 换行。实施时另加中文输入法组合态、空内容和提交中防重复验证。
- **许可证**：未核验；已读 README 和该源码未见许可正文。
- **边界/去重**：所读键盘处理仅检查 Enter 与 Shift，未见组合输入态检查；`isLoading` 出现在上下文，但该键盘处理没有据此阻止提交。以上明确区别于建议补充的行为。

## 004 · AG-UI Protocol

- **原名**：AG-UI Protocol。
- **身份状态**：确认；`ag-ui-protocol/ag-ui`。
- **定位方式**：直接获取精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/README.md
- **读取层级**：官方文档（What is AG-UI、协议分工、Features）。
- **具体可借鉴行为**：以后端执行事件连接用户界面，涵盖流式消息、双向状态同步、结构化消息与人类介入；README 说明传输可适配 SSE、WebSocket 等，并提供参考 HTTP 实现。
- **Climber 可采用点（建议）**：先定义统一的运行、消息、工具、状态和用户决定事件，再把不同后端数据映射到该契约；界面按事件更新对应区域。恢复、排序和幂等需另外设计并测试。
- **许可证**：MIT；README License 正文明示。
- **边界/去重**：本项为协议；001 为消费该类协议的 SDK。README 的事件类型数量未作为固定规范计数引用。

## 005 · A2UI（Google）

- **原名**：A2UI(Google)。
- **身份状态**：确认；从用户描述对应的 `google/A2UI` 地址获取正文，正文同时出现 `a2ui-project/a2ui` 后续入口。
- **定位方式**：直接获取原组织路径 README，并保留原始请求地址。
- **实际读取 URL**：https://raw.githubusercontent.com/google/A2UI/main/README.md
- **读取层级**：官方文档（Summary、High-level philosophy、Architecture）。
- **具体可借鉴行为**：Agent 发送声明式 JSON；客户端从预先批准的组件目录解析渲染；以组件 ID 引用支持逐步生成和增量修改；用户端拥有具体控件实现。
- **Climber 可采用点（建议）**：为任务确认表单、选项卡和结果摘要定义有限组件目录；先校验属性与动作，再映射到 Climber 自有组件。将权限检查保留在后端执行路径。
- **许可证**：Apache 2.0；README Contribute 正文明示。
- **边界/去重**：README 自述仍在演进。005 描述 UI 数据格式，004 描述交互传输，两者职责分别记录。目录限制也仍需搭配具体权限与渲染策略。

## 006 · Loquix（Web Components）

- **原名**：Loquix(Web Components)。
- **身份状态**：确认；站点介绍 `@loquix/core`，并链接 `loquix-dev/loquix`。
- **定位方式**：实际打开名称对应的项目文档站主页。
- **实际读取 URL**：https://loquix.dev/
- **读取层级**：官方文档（Quick Start、Streaming、Architecture、File Upload Pipeline）。
- **具体可借鉴行为**：以 header/messages/composer/footer 具名插槽组成聊天面板；生成控制发出暂停、恢复、停止事件；文档还列出上传校验与进度，以及通过 CSS 变量和部件暴露样式。
- **Climber 可采用点（建议）**：统一面板插槽与类型化交互回调；只有后端真正支持暂停/恢复时才提供对应按钮，其他状态仅呈现可执行动作。
- **许可证**：MIT；页面顶部与 Legal 明示。
- **边界/去重**：网页里的组件数量、测试数量和无障碍质量属于项目自述，本批不作保证；未运行网页内嵌 demo。

## 007 · Hashbrown（React Angular）

- **原名**：Hashbrown(React Angular)。
- **身份状态**：确认；`liveloveapp/hashbrown`。
- **定位方式**：直接获取仓库 README，核对 React 与 Angular 两组示例。
- **实际读取 URL**：https://raw.githubusercontent.com/liveloveapp/hashbrown/main/README.md
- **读取层级**：官方文档（What Is Hashbrown、How It Works、Features）。
- **具体可借鉴行为**：开发者注册自己的组件并声明属性 schema；模型选择这些组件；浏览器工具可调用应用状态与服务，结构化结果到达过程中即可逐步渲染。
- **Climber 可采用点（建议）**：把自有任务卡、检索结果卡和统计卡纳入受约束注册表；区分前端交互动作与后端业务执行权限；为流式未完整属性提供明确占位态。
- **许可证**：MIT；README License 正文明示。
- **边界/去重**：README 明确其为 headless 框架，具体聊天视觉需要宿主提供；发票示例注明数据为模拟，本批未运行。

## 008 · json-render（Vercel Labs）

- **原名**：json-render(Vercel Labs)。
- **身份状态**：确认；`vercel-labs/json-render`。
- **定位方式**：直接获取精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/vercel-labs/json-render/main/README.md
- **读取层级**：官方文档（Quick Start、React renderer、Streaming、Actions）。
- **具体可借鉴行为**：组件目录声明属性和允许动作，注册表负责映射到实际控件；UI spec 使用根节点与元素映射；流式编译器输出逐步补丁；状态变化可影响可见性和属性。
- **Climber 可采用点（建议）**：用自有 Card/Metric/TaskResult 类别定义最小结果目录，先验证 spec 再展示；未知组件和缺失属性提供可解释的降级信息。
- **许可证**：Apache-2.0；README License 正文明示。
- **边界/去重**：与 005 都可借鉴受约束渲染，但原文、接口和项目分别核验。README 的可靠性宣传未当作验证结果。

## 009 · ggui（MCP）

- **原名**：ggui(MCP)。
- **身份状态**：确认；精确检索命中 `@ggui-ai/mcp-server`，其仓库为 `ggui-ai/ggui`。
- **实际查询词**：`"ggui" "MCP" github`。
- **实际读取 URL**：https://raw.githubusercontent.com/ggui-ai/ggui/main/README.md
- **读取层级**：官方文档（How it works、MCP tools、Embedding UIs、Honest scope today）。
- **具体可借鉴行为**：把首次生成、已有界面属性更新、会话握手和用户动作消费拆成不同工具；用户点击或表单提交回到 Agent；嵌入路径描述了隔离 iframe。
- **Climber 可采用点（建议）**：工具结果保留稳定结果标识，后续更新只修改已有卡片数据；每次用户交互绑定所属任务和结果。跨域富内容须先设计隔离与明确授权。
- **许可证**：Apache 2.0；README License 正文明示。
- **边界/去重**：README 标注 pre-1.0，且有开发认证与生产适配警告。本批只读材料，未安装或运行其 CLI、生成运行时、Agent 或隧道。

## 010 · AgentLabs

- **原名**：AgentLabs。
- **身份状态**：确认；`agentlabs-inc/agentlabs`。
- **定位方式**：直接获取精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/agentlabs-inc/agentlabs/main/README.md
- **读取层级**：官方文档（标题、状态徽章文本、功能表与 Roadmap）。
- **具体可借鉴行为**：通用聊天前端由后端双向流式 SDK 驱动；功能表列出多 Agent 基础支持与实时请求/响应；Roadmap 列出嵌入、匿名模式和富交互组件。
- **Climber 可采用点（建议）**：借鉴后端推送消息和界面交互回传的双向契约；如需多 Agent 对话，在消息层保留发言来源和当前任务上下文。维持项目记忆要求的无登录前端。
- **许可证**：Apache 2.0；README 正文明示。
- **边界/去重**：README 顶部出现 `Discontinued`，正文仍有早期 Alpha 开发措辞；以“已标注停更的历史资料”处理，未推断托管服务当前可用。

## 011 · Lobe Chat UI Kit

- **原名**：Lobe Chat UI Kit。
- **身份状态**：歧义，原名未唯一确认；实际找到的候选为 **Lobe UI / `@lobehub/ui`**。
- **实际查询词**：`"Lobe Chat UI Kit" "lobehub" UI components`。
- **实际读取 URL（候选）**：https://raw.githubusercontent.com/lobehub/lobe-ui/master/README.md
- **读取层级**：官方文档（候选 README 的 Usage、I18n、ConfigProvider、Links）。
- **具体可借鉴行为（仅候选）**：主题提供者统一视觉上下文；国际化资源包与单组件文本覆盖并存，组件文本优先；动画依赖由上层配置提供者注入。
- **Climber 可采用点（建议）**：将中文状态文案、错误文案和无障碍标签统一管理，同时允许业务组件局部覆盖；界面主题和动效策略由同一配置入口传入。
- **许可证**：候选 Lobe UI 为 MIT，README 末尾明示；该结论仅属于候选。
- **边界/去重**：README 分别列出 Lobe Chat 与 Lobe UI，未见原名“Lobe Chat UI Kit”的独立身份说明。旧报告讨论的是 LobeChat/LobeHub 应用，本项候选为组件库；保持关联标记，不据此宣布重复。

## 012 · ChatUI（Alibaba）

- **原名**：ChatUI(Alibaba)。
- **身份状态**：确认；`alibaba/ChatUI`，README 对应 `@chatui/core`。
- **定位方式**：直接获取精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/alibaba/ChatUI/master/README.md
- **读取层级**：官方文档（Features、Usage）。
- **具体可借鉴行为**：示例通过消息管理 hook 追加用户消息、切换正在输入状态，并由独立的消息内容渲染回调决定气泡内容；发送示例会先检查去除首尾空白后的文本。
- **Climber 可采用点（建议）**：输入提交时区分空白内容、有效输入和待响应态；让消息外壳与各类结果内容渲染独立，便于加入工具或附件结果。
- **许可证**：MIT；README License 正文明示。
- **边界/去重**：示例以定时器产生模拟回复；本次原文不足以证明完整 LLM 执行、重连或 Agent 审批能力。保留其对话 UI 组件定位。

## 013 · TDesign AI

- **原名**：TDesign AI。
- **身份状态**：确认到 TDesign AIGC 组件族的 React Chat 分支 `@tdesign-react/chat`；“TDesign AI”在此作为系列描述，未认定存在同名独立 npm 包。
- **实际查询词**：`"TDesign" "AI" "chat" github Tencent tdesign-web`。
- **实际请求 URL（正文访问失败）**：https://tdesign.tencent.com/react-chat/genui
- **失败表现**：工具只返回页面标题 `TDesign Chat for React`；搜索摘要中的详细生成式 UI 说明未升级为已读正文证据。
- **实际读取 URL**：https://raw.githubusercontent.com/Tencent/tdesign-react/develop/packages/tdesign-react-aigc/README.md
- **读取层级**：官方文档（包 README）；另有一次网站正文访问失败。
- **具体可借鉴行为**：同时提供一体化聊天组件与 hook 组合式界面；示例将 `streaming` 状态绑定到输入器，并由停止回调调用聊天中止；配置可选自定义数据协议或 AG-UI。
- **Climber 可采用点（建议）**：以组合式消息列表和输入器接入现有接口；停止按钮关联当前运行标识，并待后端确认后更新终止状态；保留清晰的协议适配层。
- **许可证**：MIT；包 README License 正文明示。
- **边界/去重**：本项仅以已读 React Chat 包为范围；Vue、其他端和生成式 UI 页面具体实现未核验。

## 014 · shadcn-ui AI Chat

- **原名**：shadcn-ui AI Chat。
- **身份状态**：歧义，未唯一确认独立项目；检索同时出现 shadcn/ui 聊天基础组件、AI Elements 及其他 Chatbot Kit。
- **实际查询词**：`"shadcn-ui" "AI Chat" github components`。
- **实际读取 URL（候选）**：https://ui.shadcn.com/docs/changelog/2026-06-chat-components
- **读取层级**：官方文档（候选项目发布说明）。
- **具体可借鉴行为（仅候选）**：消息滚动原语负责轮次锚定、流式更新、恢复会话、前插历史和跳转消息；消息外壳、附件、状态标记分别组合；文档将 AI Elements 作为另一套可继续使用的组件说明。
- **Climber 可采用点（建议）**：优先验证阅读旧消息时的滚动稳定性、前插历史保持锚点和回到最新按钮；将滚动状态与后端会话状态分开。
- **许可证**：未核验；已读发布说明未给出许可条款。
- **边界/去重**：本项只记录 shadcn/ui 聊天原语候选。AI Elements 和其他 Kit 仅为检索线索，未冒充本项身份，也未计为本批新增独立项目。

## 015 · React Chatbot Kit

- **原名**：React Chatbot Kit。
- **身份状态**：确认；`FredrikOseberg/react-chatbot-kit`。
- **定位方式**：读取 README，并打开其指向文档站中的 Configuration 页面。
- **实际读取 URL**：https://raw.githubusercontent.com/FredrikOseberg/react-chatbot-kit/master/README.md
- **实际读取 URL（详细文档）**：https://fredrikoseberg.github.io/react-chatbot-kit-docs/docs/advanced/configuration/
- **读取层级**：官方文档。
- **具体可借鉴行为**：配置定义初始消息、内部状态、消息容器替换和命名 widgets；widget 通过声明选取需要的状态字段，可以随机器人响应进入聊天窗口。
- **Climber 可采用点（建议）**：空会话欢迎内容采用配置化结构；任务响应中通过类型标识选择自有结果控件，并只向控件提供需要的数据字段。
- **许可证**：未核验；本次已读 README 与配置文档未见明确许可。
- **边界/去重**：原文支持聊天配置与 widgets 的结论；现代流式 LLM 协议、权限执行与持久化可靠性需另行核验。

## 016 · Vue AI Chat

- **原名**：Vue AI Chat。
- **身份状态**：歧义，原名未唯一确认；实际阅读候选 **Vue AI Chatbot Template / `nuxt-ui-templates/chat-vue`**。
- **实际查询词**：`"Vue AI Chat" component github`。
- **定位结果**：检索出现多种 Vue 聊天组件和模板；在命中的模板介绍中找到 chat-vue 地址，随后读取该项目 README。
- **实际读取 URL（候选）**：https://raw.githubusercontent.com/nuxt-ui-templates/chat-vue/main/README.md
- **读取层级**：官方文档（候选 README 的概述与 Features）。
- **具体可借鉴行为（仅候选）**：可折叠会话侧栏、命令面板和快捷键；提示词菜单控制网页搜索与扩展思考；工具结果可呈现图表或天气卡片。
- **Climber 可采用点（建议）**：在桌面输入区集中展示本次会话实际可用的工具开关；可折叠会话侧栏保留主任务空间；将快捷键入口和命令面板纳入可发现导航。
- **许可证**：未核验；所读 README 未见明确许可。
- **边界/去重**：候选是 Vue 完整应用模板，其名称与原名存在差异；保持未确认映射。其认证能力只记录为项目内容，Climber 建议继续遵循无登录约束。

## 017 · Svelte Chat UI

- **原名**：Svelte Chat UI。
- **身份状态**：歧义；命中 TanStack AI 同名文档页面及其他 Svelte 聊天实现，用户原名缺少仓库或作用域。
- **实际查询词**：`"Svelte Chat UI" github components`。
- **实际读取 URL（候选）**：https://tanstack.com/ai/latest/docs/ui/svelte
- **读取层级**：官方文档（候选 TanStack AI 页面）。
- **具体可借鉴行为（仅候选）**：按工具名称与中断类型注册对应控件；布局接收消息、中断、待发送队列和输入区；待发送项目可取消；工具审批可内嵌工具区域或移入中断列表，未知中断可使用 fallback。
- **Climber 可采用点（建议）**：给工具结果、用户补充问题、权限确认分别定义视图；排队输入展示可取消状态；后端出现尚未支持的中断时保留说明和可恢复入口。
- **许可证**：未核验；该页未给出许可条款。
- **边界/去重**：所读页面属于 `@tanstack/ai-svelte`；仅以候选身份记录，未将其指定为用户原名的唯一项目。

## 018 · @burtson-labs/agent-ui

- **原名**：@burtson-labs/agent-ui。
- **身份状态**：确认；精确包名检索指向 `Burtson-Labs/bandit-agent-framework` 中的 agent-ui 包，包 README 同名。
- **实际查询词**：`"@burtson-labs/agent-ui"`。
- **实际读取 URL**：https://raw.githubusercontent.com/Burtson-Labs/bandit-agent-framework/main/packages/agent-ui/README.md
- **读取层级**：官方文档（What's in the box、Authoring a new component）。
- **具体可借鉴行为**：计划树关联步骤活动；差异审阅支持应用前接受/拒绝；权限卡区分 pending/submitting/resolved/error/expired；用量未报告时显示未知，缺少上限时不画占比条。
- **Climber 可采用点（建议）**：采用“计划步骤 → 工具活动 → 变更审阅”的关联视图；审批等待后端回执并处理过期；用量显示明确区分未知与零，展示前验证分母有效。
- **许可证**：Apache License 2.0；包 README License 正文明示。
- **边界/去重**：组件纯 props 与宿主无关为文档约定；本批未读完整实现或执行其稳定性测试。只研究 UI 文档，未安装或运行 Bandit Agent。

## 019 · @aceshooting/lyra-ui

- **原名**：@aceshooting/lyra-ui。
- **身份状态**：确认；完整包名对应 Lyra UI，发布 README 指向 `aceshooting/lyra-ui`。
- **实际查询词**：`"@aceshooting/lyra-ui"`。
- **实际读取 URL（固定版本发布文档，部分读取）**：https://cdn.jsdelivr.net/npm/@aceshooting/lyra-ui@12.1.2/README.md
- **实际读取 URL（仓库组件文档）**：https://raw.githubusercontent.com/aceshooting/lyra-ui/main/packages/lyra-ui/llms/components/lr-tool-approval-dialog.md
- **读取层级**：官方文档；发布包 README 与仓库生成的组件 API 文档，均未当作组件实现源码。
- **具体可借鉴行为**：审批面板显示工具与参数，参数编辑必须通过 JSON 解析才可批准；提案标识变化重置草稿；异步决定可保持 pending；初始焦点位于拒绝操作，关闭后恢复焦点。
- **Climber 可采用点（建议）**：审批卡绑定不可复用的提案标识与参数版本；提交中阻止重复决定，失败后恢复可操作状态；键盘焦点从低风险动作开始。权限与最终参数校验仍由后端负责。
- **许可证**：MIT；实际读取的 12.1.2 README 开头明确写出。
- **边界/去重**：JSON 语法通过与业务参数合法性分别验证。文档中“阻止 Agent 执行”的交互目标，需要宿主正确接入真实执行关口才能成立。两个已读 URL 的版本边界见核验口径。

## 020 · @nextclaw/agent-chat-ui

- **原名**：@nextclaw/agent-chat-ui。
- **身份状态**：确认；完整包名对应 `Peiiii/nextclaw` 的 `packages/nextclaw-agent-chat-ui`。
- **实际查询词**：`"@nextclaw/agent-chat-ui"`。
- **实际读取 URL**：https://raw.githubusercontent.com/Peiiii/nextclaw/master/packages/nextclaw-agent-chat-ui/README.md
- **读取层级**：官方文档（Public API、Scope）。
- **具体可借鉴行为**：将聊天输入、消息列表、视图模型、局部交互 hook 与皮肤基础件打包为表现层；公开接口列出粘底滚动和复制反馈 hook；宿主负责运行时、存储适配及页面容器。
- **Climber 可采用点（建议）**：先统一消息视图模型，再让桌面/兼容布局消费同一表现层；复制操作展示独立反馈；把滚动策略测试与后端状态测试分开。
- **许可证**：未核验；检索摘要显示 MIT，但已打开的包 README 没有许可正文，因此本批不填写确定许可。
- **边界/去重**：README 只证明相关接口被公开，粘底阈值、历史前插、失败反馈和具体重试行为未读实现，不作断言。只研究包文档，未安装或运行 NextClaw Agent。

## 归属与去重结论

| 编号 | 原名映射结果 | 后续确认所需信息 |
| --- | --- | --- |
| 011 | Lobe UI 是候选；原名 Lobe Chat UI Kit 未唯一确认 | 原清单的仓库、包名或文档入口 |
| 014 | 已读 shadcn/ui 聊天原语说明；多个 Chat/AI Kit 具有相近描述 | 明确目标是基础组件、AI Elements 还是具体 Kit |
| 016 | 已读 Vue AI Chatbot Template 候选；Vue AI Chat 泛称未唯一确认 | 原始仓库地址或 npm 作用域 |
| 017 | 已读 TanStack AI 同名 Svelte 页面；独立项目身份仍有歧义 | 原始仓库地址或 npm 作用域 |

001/004/005 分别记录 SDK、交互协议、UI 描述格式；005/007/008 的组件目录思想相近，仍属于不同项目。011 与旧报告 LobeChat 同生态，组件库与应用分别处理。本批没有将单个替代项目分配给多个编号，也没有凭同类描述判为重复。

## 三个最可用范式

以下为研究建议优先级；本批没有修改应用代码。

1. **会话表现层与运行状态解耦**：以 002、013、020 的独立原文为依据，将消息、输入、工具结果视图与后端适配分离；参考 014 候选文档建立滚动锚点验收。建议验收：流式更新、阅读历史、前插历史、停止请求与重复提交均有明确状态。
2. **可审阅且有回执的工具审批**：以 001、018、019 为依据，展示工具、参数和影响范围；批准、拒绝、提交中、失败、过期各有明确反馈；未知用量保留未知。建议验收：提案更新后旧确认失效，后端回执到达前保持等待，键盘默认焦点落在低风险操作。
3. **受约束的结构化结果卡片**：以 005、007、008 为依据，模型输出映射到 Climber 自有组件目录；属性校验、动作权限与增量更新分别处理。建议验收：未知组件、无效属性、尚未完整的流式数据、执行失败都呈现清楚的降级状态。

## 本批执行范围

仅新增本文件，使用 apply_patch。未更新 MEMORY、旧报告或其他文档，未修改应用代码，未安装依赖或第三方 Agent，未启动任何外部运行时，未 commit/push。资料中的示例、徽章、图标与品牌资产均未复制到 Climber。
