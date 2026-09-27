# UI 资料核验：061–070

核验日期：2026-09-25。目标：Climber。范围：本文件的十个原名条目。

## 核验口径与覆盖

- 独立联网检索 **10/10**，各项至少实际打开一份官方、作者仓库或明确标注的候选/方法论正文；完整有效正文共 **17 个独立 URL**。第 65 项另有一份截断页面，未计入这 17 个。检索摘要用于定位，行为结论以实际读取正文为依据。
- 身份结果：**重复 2 项（061、062，相关实现存在已确认）；确认方法论 1 项（069）；歧义 6 项（063、064、066、067、068、070）；原名未确认 1 项（065）**。原名尚未唯一对应具体项目的编号为 **063、064、065、066、067、068、070**；069 只确认方法论身份，同名独立软件库未确认。
- “官方”指相应项目自己的仓库/文档。候选项目的官方 README 不构成原清单名称的身份证明；原名、候选名、证据分别记录。
- 读取层级：061 到达实现源码；其余为官方/作者 README 或文档。README 内示例按文档层计数。没有运行外部项目、浏览器演示、安装命令或第三方 Agent。
- 许可证只填写本次可见正文明确写出的名称；未知项标为“未核验”。徽章只有泛化的 License 链接时不据此猜测。未作法律适用判断。
- 当前分支和网页可变化，本次未统一固定 commit，也未验证搜索索引的相对发布日期；“稳定”“实验性”等均标明各自来源，不作为独立生产质量认证。
- 去重已读取 `references-001-020.md` 第 004、005、008 项：061 对应 004 的实现层；062 对应 005 的客户端实现；065 的机制候选对应 008。三者均不增加独立项目数量。
- 本批仅用 apply_patch 新增本文件；现有代码、其他研究文件和记忆文件保持原样。未执行 commit/push、构建、部署或第三方 Agent。

## Climber 本地只读依据

- `frontend-react/src/useChat.ts:4–20`：已有 Message、ToolCall 类型与工具运行/成功/错误状态。
- `frontend-react/src/useChat.ts:87–162`：已有 text、thinking、tool_call、tool_result、done、error 的事件消费分支。
- `frontend-react/src/useChat.ts:166–172`：已有停止流回调；本次只读范围未复核对应服务端取消语义。
- 通过定向检索定位 `frontend-react/src/components/agent/ChatInterface.tsx:178–205` 的工具结果呈现，以及 `frontend-react/src/components/workspace/RightPanel.tsx:418–484` 的工具调用面板。后两处仅作入口定位，未声称完整阅读文件。
- 下文均为后续采用建议；不表示本次已实施、已完成兼容性测试或已验证完整后端能力。

## 061 · AG-UI Reference Implementation

- **原名**：AG-UI Reference Implementation。
- **身份状态**：**重复，实现存在确认**；归入 `ag-ui-protocol/ag-ui`。原名可对应该协议随附的参考 HTTP 实现和默认连接器，同名独立产品未确认。
- **实际查询词**：`"AG-UI" "reference" implementation site:github.com/ag-ui-protocol`。
- **实际读取 URL / 层级**：
  - https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/README.md （官方 README；What is AG-UI、Dojo、License）。
  - https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/sdks/typescript/packages/client/src/agent/http.ts （实现源码；HttpAgent）。
- **证据**：README 明确说明随协议提供 reference HTTP implementation、default connector，并将 Dojo 指向同仓库示例。源码 `requestInit()` 使用 POST、JSON body、`Accept: text/event-stream` 与 AbortController signal；`runAgent()` 为运行选择控制器；`abortRun()` 调用 abort；`run()` 把请求结果交给事件流转换函数。
- **证据边界**：本次只读 HttpAgent 文件及 README，未追读其父类、HTTP 请求工具和事件转换器；取消服务端任务、断线恢复、事件去重均需独立核验。
- **Climber 采用建议**：优先抽出当前 useChat 的事件适配边界，为运行、消息、工具调用保留关联 ID；分别表达请求中止和服务端任务终止。先把已有事件映射到清晰契约，再评估引入 SDK。
- **许可证**：MIT；本次 README 的 License 段明示。
- **与 4/5 的关系**：**与 004 AG-UI Protocol 属同一项目，明确重复参考**，本项增加实现层证据；与 005 的 UI 描述格式职责不同。

## 062 · A2UI Renderers（Angular / Flutter / React）

- **原名**：A2UI Renderers（Angular、Flutter、React 分别核验）。
- **身份状态**：**重复，三端实现均确认存在**。Angular、React 位于 A2UI 主仓库；Flutter 位于 `flutter/genui`。
- **实际查询词**：`A2UI Renderers Angular Flutter React official`。
- **实际读取 URL / 层级**：
  - https://a2ui.org/guides/client-setup/ （官方客户端文档；三端表格、Shared Web Library、Error Handling）。
  - https://raw.githubusercontent.com/a2ui-project/a2ui/main/renderers/angular/README.md （官方包 README）。
  - https://raw.githubusercontent.com/a2ui-project/a2ui/main/renderers/react/README.md （官方包 README）。
  - https://raw.githubusercontent.com/flutter/genui/main/README.md （Flutter 官方仓库 README）。

| 平台 | 是否存在 | 本次正文直接证据 | 限制与状态口径 |
| --- | --- | --- | --- |
| Angular | 确认 | `@a2ui/angular/v0_9`、A2uiRendererService、SurfaceComponent、BasicCatalog；描述 Signals、独立 surface 和 actionHandler | 已确认包与文档；未运行组件或版本兼容测试 |
| Flutter | 确认 | `genui`、`genui_a2a`、A2uiAgentConnector；A2UI Support 明示支持 v0.9 | A2UI 文档表格标 Stable，Flutter 自身 README 标 highly experimental；保留冲突，按实验性风险评估 |
| React | 确认 | `@a2ui/react/v0_9`、MessageProcessor、A2uiSurface、basicCatalog；createSurface/updateComponents/updateDataModel 示例 | README 另保留 v0.8 导出；采用前固定协议和包版本，勿混用示例导入 |

- **证据**：React README 将 Processor、Surface、Catalog 分开，并通过 surface 创建/删除订阅更新 UI；自定义组件按 schema 定义、binder 解析属性与动作。Angular README 将相同协议处理映射到服务与组件。Flutter README 明确用 A2UI 表达 UI，独立仓库承载原生渲染。
- **Climber 采用建议**：优先评估 React 子包，为工具结果建立小型自有 Catalog，按 task/message/surface 标识管理增量更新；未知组件、未创建 surface、缺失字段提供可解释降级。Angular、Flutter 用于跨端契约参照。
- **许可证**：未核验；本次上述包 README 和客户端页面未看到明确许可条款。未把前批 005 的许可结论自动外推到 Flutter 仓库。
- **与 4/5 的关系**：**与 005 A2UI 明确重复参考**，本项是三端实现细化；与 004/061 的传输和事件层可组合，组合兼容性本次未验证。

## 063 · React GenUI

- **原名**：React GenUI。
- **身份状态**：**歧义，原名未唯一确认**。候选 A 为 Tambo AI / `@tambo-ai/react`；检索也引出 OpenTiny GenUI SDK 的 React 相关宣传线索。两者均以各自原名记录。
- **实际查询词**：`"React GenUI" github`。
- **实际读取 URL / 层级**：
  - https://raw.githubusercontent.com/tambo-ai/tambo/main/README.md （候选 A 官方 README；What is Tambo、How It Works、License）。
  - https://raw.githubusercontent.com/opentiny/genui-sdk/main/README.md （候选 B 官方 README；Instruction、Packages）。
- **证据**：Tambo 自述为 React 生成式 UI toolkit，组件注册包含名称、描述、Zod props schema；区分一次性生成组件和持续可交互组件；同时提供 React SDK 与处理对话/执行的后端。
- **候选 B 限制**：实际读到的 OpenTiny README 只在 Packages 列出 server、Vue、Angular；搜索结果提及的 React 测试版未在本次该正文中得到实现证据。保留“React 支持本次未确认”。
- **Climber 采用建议**：借鉴 Tambo 的组件注册契约与“一次性结果/持久可交互对象”分离；将现有任务卡作为受约束结果。保留当前任务执行主链，另行评估引入其对话后端的成本。
- **许可证**：Tambo README 写 MIT unless otherwise noted，并指出部分 workspace（示例 `apps/api`）为 Apache-2.0；OpenTiny README 写 MIT。许可仅属于相应候选，不代表原名独立项目。
- **去重边界**：未将 062 的 A2UI React 渲染器改名为 React GenUI；未确认本项与 004/005 是同一项目。

## 064 · Vue Generative UI

- **原名**：Vue Generative UI。
- **身份状态**：**歧义，原名未唯一确认**；已读候选为 OpenUI 的 `@openuidev/vue-lang`。
- **实际查询词**：`"Vue Generative UI" github`。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/thesysdev/openui/main/packages/vue-lang/README.md （候选官方包 README；Overview、RendererProps、Errors、License）。
- **证据**：该包明确为 Vue 3 的 OpenUI Lang bindings；用组件定义及 Zod props schema 建立库、生成提示词，通过 Renderer 消费流式输出。`isStreaming` 文档说明生成期间禁用表单交互；`onError` 和 `meta.errors` 暴露 unknown-component、missing-required 等结构化错误。
- **证据边界**：README 说明解析器宽容地渲染可用内容；错误回调本身不足以证明所有非法内容都会被阻断。它采用 OpenUI Lang，本次未验证与 A2UI 消息格式互通。
- **Climber 采用建议**：吸收“生成未完成时禁用提交”“把解析错误与网络错误分开”的交互规则；在现有 React 组件层实现同样状态契约，Vue 包作为跨框架参照。
- **许可证**：MIT；该 README 的 License 段明示。
- **去重边界**：候选身份为 OpenUI Vue 包；与 005 同属生成式界面领域，项目同一性未确认。063 的 OpenTiny Vue 能力也构成另一个技术路线线索，泛称不足以选定唯一目标。

## 065 · Dynamic UI Renderer

- **原名**：Dynamic UI Renderer。
- **身份状态**：**未确认**；属于广泛使用的能力描述，本次精确检索未建立作者/包名/仓库的一一对应关系。
- **实际查询词**：`"Dynamic UI Renderer" github`。
- **实际读取 URL / 层级**：
  - https://raw.githubusercontent.com/vercel-labs/json-render/main/packages/react/README.md （相关机制候选 `@json-render/react` 的官方包 README，完整正文）。
  - https://a2ui.org/ecosystem/renderers/ （官方生态背景页，工具输出截断；不计完整正文，不据未显示段落下结论）。
- **证据（仅机制候选）**：`@json-render/react` 将 catalog、registry、spec 分离；spec 使用 root 与 elements 映射，Renderer 按注册表映射 React 组件；StateProvider、ActionProvider 分别承载状态和动作。上述能力支持比较动态渲染机制。
- **身份限制**：检索还返回不相关 Unity 与区块链结果，均未采用为身份依据。官方生态页用于定位机制候选，当前证据不足以确认存在原名对应的独立工具。
- **Climber 采用建议**：先为工具结果建立类型到自有组件的有限映射，并让动作回调受宿主控制；保留未知类型的结构化文本回退。采购或新增依赖清单中暂缓登记原名。
- **许可证**：未核验；本次所读 React 包 README 未给出明确许可。前批 008 的许可结论未在本条重新核验。
- **去重边界**：候选 **json-render 与 008 为同一项目**，本次只补充渲染包资料；不可将候选改名后计作第 065 个独立产品。与 004/005 的直接重复未确认。

## 066 · LiveKit AI UI

- **原名**：LiveKit AI UI。
- **身份状态**：**歧义，品牌相关候选确认存在**；实际官方名称为 LiveKit Components，以及其中的 Agents UI。原名尚未对应同名独立包。
- **实际查询词**：`LiveKit AI UI Agents UI official components`。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/livekit/components-js/main/README.md （官方 README；Agents UI Quick Start、Prerequisites、示例、FAQ）。
- **证据**：Agents UI 为面向语音 Agent 的 shadcn 组件集合；示例包含 AgentSessionProvider、AgentControlBar、AgentChatTranscript、AgentAudioVisualizerBar、StartAudioButton。连接态决定显示会话界面或连接按钮，connecting 时禁用按钮；音频播放受浏览器限制时提供显式启动入口。
- **边界**：README 说明 Agents UI 面向 React 19 和 Tailwind CSS 4，需 LiveKit Cloud 或自托管服务及相应会话连接；本次未核对 Climber 依赖版本或运行媒体服务。
- **Climber 采用建议**：将媒体连接态、设备状态、转录消息与任务执行态分开；语音入口采用独立开关和显式权限提示。当前纯文本工作区优先借鉴状态反馈，媒体栈列为后续可选能力。
- **许可证**：未核验；所读根 README 未给出明确许可条款。
- **去重边界**：未确认与 004/005 重复；本项候选属于实时媒体交互 UI，不能据其“agentic”表述推断实现 AG-UI 或 A2UI。

## 067 · Daily AI UI

- **原名**：Daily AI UI。
- **身份状态**：**歧义，原名未唯一确认**；相关候选为 Pipecat 官方 Web 客户端中的 React 绑定和 DailyTransport。
- **实际查询词**：`Daily AI UI pipecat client react ui github`。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/pipecat-ai/pipecat-client-web/main/README.md （候选官方 README；Overview、Transport packages、Quickstart）。
- **证据**：README 将 client-js 与 client-react 分为两包，后者提供 React 组件和 hooks；媒体传输另外注入，示例采用 DailyTransport。客户端暴露 transport state、connected、disconnected、bot ready 等回调，服务端端点负责启动与认证材料。
- **失败记录**：尝试 https://raw.githubusercontent.com/pipecat-ai/pipecat-client-react-ui/main/README.md 返回 404；该次已为 raw 路径，随即停止重试。不能据此断言所有 Pipecat UI 组件库不存在，也未取得该猜测仓库的能力证据。
- **Climber 采用建议**：借鉴“传输已连接/Agent 已就绪”分离，语音会话状态独立于任务卡状态；媒体凭据经项目服务端发放。以已确认客户端接口作评估基线，UI 库选型待准确链接。
- **许可证**：未核验；成功读取的 README 未见明确许可条款。
- **去重边界**：Daily 在已读材料中是传输提供方；Pipecat 为客户端项目。两者关系有正文依据，“Daily AI UI”为其正式独立产品名仍待确认；与 004/005 的直接重复未确认。

## 068 · Inkeep AI UI

- **原名**：Inkeep AI UI。
- **身份状态**：**歧义，官方候选确认存在**；实际对应线索为 Inkeep Agents 中的 `agents-ui`，原名独立产品未唯一确认。
- **实际查询词**：`Inkeep AI UI components github official`。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/inkeep/agents/main/README.md （官方根 README；Platform Overview、Architecture、License and Community）。
- **证据**：架构把 agents-api、agents-manage-ui、agents-sdk 与 agents-ui 分开；agents-ui 定义为嵌入 Web 应用的动态对话组件库。管理 UI 为可视化构建器，对话组件库为面向使用者的嵌入层；根文档另说明与 Vercel useChat 的兼容关系。
- **证据边界**：本次未打开 agents-ui 的实现源码或组件 API 文档；不推断其具体卡片注册协议、客户端权限机制、工具审批组件或与 Climber useChat 的直接可替换性。
- **Climber 采用建议**：沿用管理工作区与用户聊天视图的职责划分，将工具结果呈现抽成可复用嵌入组件；采用其源码前先按目标子包复核许可范围和集成接口。
- **许可证**：仓库 README 明示 **Elastic License 2.0，并受 Inkeep Supplemental Terms 约束**；本次未读补充条款全文，也未查目标子包特例。不能从该根声明推出宽松许可或可无条件复制组件。
- **去重边界**：未确认与 004/005 重复。品牌相关搜索还出现 cxkit-react 线索，本次未读取该包正文，未将其与 agents-ui 合并为同一实体。

## 069 · Component-Driven UI

- **原名**：Component-Driven UI。
- **身份状态**：**确认到方法论**，名称对应 Component Driven User Interfaces；同名独立软件库未确认。
- **实际查询词**：`"Component-Driven UI" Storybook`。
- **实际读取 URL / 层级**：
  - https://storybook.js.org/docs/ （官方文档；简介、Stories、页脚 Component driven UI 链接）。
  - https://componentdriven.org/ （概念原站；定义、How to be Component Driven、Tools，页脚注明 Chromatic 与社区维护）。
- **证据**：原站定义从独立组件、组合组件到页面的自底向上构建方法；组件有明确 API 和可模拟状态，页面再接入业务数据。Storybook 文档以 story 表达组件呈现状态，支持隔离开发与测试。
- **Climber 采用建议**：为现有工具卡、输入器、右侧结果面板建立 idle/running/success/error/cancelled 的状态样例，再覆盖长文本、无结果、生成中和会话切换边界；桌面布局优先，移动端按兼容目标检查。
- **许可证**：未核验；已读页面未见相关许可条款。方法论原站内容与 Storybook 软件的许可应分别核查。
- **去重边界**：与 004/005 属不同层次；此项计方法论参考，独立 AI UI 软件数量增加 0。Storybook 是相关实践工具。

## 070 · Generative UI Kit

- **原名**：Generative UI Kit。
- **身份状态**：**歧义，同名风格包候选确认存在**；检索命中 npm `generative-ui-kit`，作者仓库为 `anahtiris/generative-ui-playground`。原清单缺少作者/链接，保留候选身份。
- **实际查询词**：`"Generative UI Kit" github`。
- **实际读取 URL / 层级**：
  - https://raw.githubusercontent.com/anahtiris/generative-ui-playground/main/README.md （作者根 README；Key design rule、v1 scope、Not included）。
  - https://raw.githubusercontent.com/anahtiris/generative-ui-playground/main/packages/generative-ui-kit/README.md （作者包 README；组件清单、onSubmit、License）。
- **证据**：包提供 GenerativeChat、GenerativeUIRouter 与表单/提问/表格/仪表盘四个默认 renderer；宿主提供 onSend 并负责模型接入。工具 handler 分离供界面使用的 render 与回给模型的 forModel；表单说明 forModel 仅返回 session_id/status，提交回调由宿主注入。
- **重要限制**：根 README 明写真实表单加密仍待实现、示例相关字段当前按明文插入；流式事件契约存在，但根 README 说明 GenerativeChat 尚未累积 text_chunk。以上均为文档自述，未运行或审计源码，不能把 SecureFormRenderer 的名称当作数据保护保证。
- **来源差异**：搜索索引显示已发布 npm 包，包 README 给出安装命令；根 README 仍把发布列作未包含项。发布状态与具体版本本次未通过 npm 正文或发布工件核验，未选择任一描述冒充最新发布结论。
- **Climber 采用建议**：优先吸收 render/forModel 的数据分流原则，用户表单交给自有后端校验并实施数据保护；先保留现有流式聊天链路，候选组件只作独立设计参考。
- **许可证**：候选包 README 的 License 段明示 MIT；结论限于该候选包。
- **去重边界**：未确认与 004/005 同一项目，也未验证该包实现 AG-UI/A2UI。泛称、同名 npm 包与原清单意图分别保留。

## 优先采用的三条

1. **061：事件与取消边界。** 最贴近现有 useChat；先明确运行/消息/工具关联和前后端终止语义，再评估 SDK 接入。证据已达到 HttpAgent 源码层。
2. **062：受约束结果渲染。** React renderer 的 Processor/Surface/Catalog 分层可用于任务结果与确认表单；首批使用少量自有组件，固定协议版本并处理未知输入。
3. **069：组件状态样例。** 将工具卡和工作区边界状态固化为可复现样例，再接入流式数据；适合并行 UI 改进与回归检查。

## 读取与执行审计

- 10 个编号均保留原名、状态、真实查询词、实际读取 URL、层级、证据、采用建议及许可证核验边界。
- 17 个完整正文 URL 全部逐项列明；另列 1 个截断生态页与 1 个 raw 404。正文截断与失败都未补写成已读完整证据。
- 第 67 项失败已发生在 raw 地址，停止重试；其他作为结论依据的正文均实际取得。没有根据第三方搜索摘要填充官方实现细节。
- 只读研究过程中其他并行会话新增了相邻编号文档，本批未修改这些文件。目标文件新增前再次确认不存在。
- 本次验证对象为文档完整性与修改范围；未运行产品测试、安装第三方依赖、启动 Agent 或提交代码。
