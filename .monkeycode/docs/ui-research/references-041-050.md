# UI 参考调研 041–050

调研日期：2026-09-25。范围：Climber 多 Agent 协作、任务观察与工作流画布。

## 方法与边界

- 10/10 项分别提交了搜索词，并实际打开第一方仓库 README、源码或官方文档；独立搜索和网页读取采用批量请求。泛称项目读取候选自己的仓库，候选身份与用户原意分别判断。
- 主状态：确认 7 项，歧义 3 项（043、047、048），整项未确认 0 项；歧义项仍保留“用户具体所指未确认”。041 的旧仓库与 monorepo 示例属于同一项目，合并计数。跨批次完整去重未开展。
- 读取层级：R = README 正文；D = 官方文档正文；C = 实际源码文本；L = LICENSE 正文；W = 官方产品页正文；S = 搜索结果定位。R/D/C/L 用于功能与许可证据，W 仅辅助确认归属。搜索摘要、图片链接和源码导入名称分别保留其证据边界。
- 所有外部项目均只读。没有安装、启动或接入第三方 Agent，没有运行 Demo、构建或测试，也没有截图视觉实测。README 中的安装、隧道和凭据示例均未执行。
- URL 指向本次实际读取的动态分支/网页，未锁定 commit；日期是本次调研日期。页面可能后续更新，不能据此宣称历史版本行为或运行效果。失败 URL 单独记录，404 只证明该路径本次读取失败。
- 许可证只填写实际看见的文件或 README 声明，并标明证据等级；上游框架许可证不自动覆盖托管 Studio、依赖、图片或品牌资产。
- 本文属于调研记录；下文“Climber 建议”均为研究者提出的候选方向，功能可用性仍需独立验证。仅新增本文件，保留工作树既有及并行改动；不改代码、不提交、不推送。

## Climber 本地只读锚点

- B1：`frontend-react/src/components/workflow/WorkflowEditor.tsx:1–200`。实际读取到 ReactFlow、节点/连线 state、Input/LLM/Tool/Simulation/Condition/Output 调色板、选中节点及属性更新；`handleSave` 序列化 nodes/edges，`handleRun` 通过 `api.runWorkflow(workflowId, {})` 运行。建议在这个既有画布入口上评估增量交互。
- B2：`frontend-react/src/components/workspace/RightPanel.tsx:1–200`。实际读取到配置、Diff、工具、DAG、链路、推理、文件标签；`DAGPanel` 调用 `api.getClusterStatus()` 并映射 `plan` 的 id/description/task/status。这给节点详情、会话关联和执行观察提供现成界面落点；本次未检查其完整后端事件契约。

## 覆盖表

| 编号 | 用户原名 | 主状态 | 实际对应与边界 | 最高读取层级 |
| --- | --- | --- | --- | --- |
| 041 | Open Multi-Agent Canvas(CopilotKit) | 确认 | CopilotKit 原仓库及 monorepo 同名示例；合并计数 | R |
| 042 | agent-chat-ui(LangChain) | 确认 | langchain-ai/agent-chat-ui；与 049 为独立产品入口 | C、L |
| 043 | AgentGUI | 歧义 | ETH Medical AI Lab 与 AnEntrypoint 均有同名仓库 | R、L |
| 044 | AUTOGEN STUDIO | 确认 | microsoft/autogen 的 autogen-studio 子包 | D、L |
| 045 | Edict(三省六部系统) | 确认 | cft0808/edict | D、L |
| 046 | Council of High Intelligence | 确认 | 0xNyk/council-of-high-intelligence；协议/插件型项目 | R、L |
| 047 | Multi-Agent Playground | 歧义 | Azure-Samples 同名示例与 Pommerman 等语境并存 | 候选 C、L |
| 048 | CrewAI Studio(声称官方需核验) | 歧义 | 官方 Crew Studio 已确认；strnad/CrewAI-Studio 为另一候选 | D、R |
| 049 | LangGraph Studio | 确认 | 官方历史发布文章；当前官方文档标题 LangSmith Studio | D |
| 050 | LangFlow | 确认 | 按协作/画布语境对应 langflow-ai/langflow | C、L |

## 041 · Open Multi-Agent Canvas(CopilotKit)

- **身份与重复**：确认。旧仓库 README 尾部明确迁入 CopilotKit monorepo；两个地址合并为同一参考项。
- **逐项搜索**：`"Open Multi-Agent Canvas" CopilotKit`，定位 CopilotKit 所有者下的原仓库。
- **实际读取 URL / 层级**：
  - 41-R1：<https://raw.githubusercontent.com/CopilotKit/open-multi-agent-canvas/main/README.md>，R，成功；重点读取介绍、MCP Agent Setup、License、迁移说明。
  - 41-R2：<https://raw.githubusercontent.com/CopilotKit/CopilotKit/main/examples/showcases/multi-agent-canvas/README.md>，R，成功；交叉核对当前示例名称与配置方式。
- **具体证据**：41-R1/R2 将其定义为在同一动态对话中管理多个 Agent 的界面；列出旅行、研究和 MCP Agent。MCP 配置入口支持 Standard IO/SSE，README 同时声明该示例依赖 Copilot Cloud。这些材料支持多 Agent 会话与工具配置参考；自由节点编排能力尚未核实。
- **Climber 建议**：围绕 B2 的当前会话增加“参与 Agent / 当前处理者 / 工具来源”标识；在 B1 节点详情中关联该节点对应的会话和产物。MCP 配置可独立成抽屉，展示连接状态与可用工具，凭据沿用项目自身配置边界。
- **许可证**：实际看见 41-R1/R2 的 MIT 声明；LICENSE 正文未取得，属于 README 声明级。
- **失败与未确认**：<https://api.github.com/repos/CopilotKit/CopilotKit/contents/examples/showcases/multi-agent-canvas/frontend> 返回 403；<https://raw.githubusercontent.com/CopilotKit/CopilotKit/main/examples/showcases/multi-agent-canvas/frontend/src/app/page.tsx> 返回 404，未计作源码读取；<https://raw.githubusercontent.com/CopilotKit/open-multi-agent-canvas/main/LICENSE> 返回 404。未确认实时多人共同编辑或云端服务授权条款。

## 042 · agent-chat-ui(LangChain)

- **身份与重复**：确认 `langchain-ai/agent-chat-ui`。与 049 同属 LangChain 生态，聊天前端和开发调试 Studio 分别计数。
- **逐项搜索**：`"agent-chat-ui" LangChain github`。
- **实际读取 URL / 层级**：
  - 42-R：<https://raw.githubusercontent.com/langchain-ai/agent-chat-ui/main/README.md>，R，成功。
  - 42-C：<https://raw.githubusercontent.com/langchain-ai/agent-chat-ui/main/src/providers/Stream.tsx>，C，成功；读取 `StateType`、`StreamSession`、`useTypedStream` 配置及事件更新。
  - 42-L：<https://raw.githubusercontent.com/langchain-ai/agent-chat-ui/main/LICENSE>，L，成功。
- **具体证据**：42-R 要求服务端 state 含 `messages`，并描述通过 `thread.meta.artifact` 在聊天右侧渲染产物。42-C 的 `StreamSession` 使用 URL 中的 `threadId`，开启 `fetchStateHistory`；`onCustomEvent` 识别 UI 更新/删除事件，以 `uiMessageReducer` 更新 `ui`。这是实际源码中的会话及 UI 事件同步逻辑。
- **Climber 建议**：把 B2 的文件/Diff/工具详情和聊天消息关联到同一 session/run/node 标识；让产物卡片打开右侧详情。B1 中点击执行节点可定位相关消息，消息可反向定位画布节点；事件删除、重连、历史读取应分别定义行为。
- **许可证**：42-L 正文为 MIT，版权行 `2025 Brace Sproul`。
- **失败与未确认**：本项上述读取成功。未运行界面；本次只读取 provider 源码，未核验全部消息组件、HITL 界面或多人协同功能。

## 043 · AgentGUI

- **身份与重复**：歧义。原名缺少所有者或 URL，至少两个第一方仓库直接使用 AgentGUI 名称，用户具体所指未确认。候选分别记录，不合并功能。
- **逐项搜索**：`"AgentGUI" github`，命中下列两个仓库。
- **实际读取 URL / 层级**：
  - 43A-R：<https://raw.githubusercontent.com/eth-medical-ai-lab/agent-gui/main/README.md>，R，成功，重点读取介绍与使用前提。
  - 43A-L：<https://raw.githubusercontent.com/eth-medical-ai-lab/agent-gui/main/LICENSE>，L，成功。
  - 43B-R：<https://raw.githubusercontent.com/AnEntrypoint/agentgui/main/README.md>，R，成功，重点读取 How it works、Why AgentGUI、Features。
- **具体证据 A**：43A-R 描述可滚动办公室中的 Agent 工位，点击工位查看实时活动、文件树、终端和 debug message，并可中途调整方向或重新分派；前提依赖 Hermes，介绍同时标注实验性 Claude Agent 支持。此处只确认 README 描述。
- **具体证据 B**：43B-R 描述 Node 服务、ACP、本地 Agent daemon、WebSocket 流和 SQLite 会话持久化，列出并排比较、历史续接、文件变更及工具调用观察。它对应编码 Agent 客户端语境。
- **Climber 建议**：从 A 提取“Agent 概览卡片 → 单 Agent 活动详情 → 干预入口”；映射到 B2 的 DAG/工具/文件标签。由 B 提取同任务多 Agent 结果对比与断线恢复状态；B1 保留任务依赖语义，工位隐喻作为可选概览形式。
- **许可证**：43A-L 为 MIT，版权行 `2026 ETH Zurich, Medical AI Lab`；43B-R 实际看到 MIT badge，属于 README 声明级。
- **失败与未确认**：<https://raw.githubusercontent.com/AnEntrypoint/agentgui/main/LICENSE> 返回 404。两个候选均未安装或运行；未读取前端实现，未验证工位拖拽、多人同时控制、冲突解决。

## 044 · AUTOGEN STUDIO

- **身份与重复**：确认 Microsoft 的 `autogen/python/packages/autogen-studio`。本批无同一产品重复项。
- **逐项搜索**：`"AUTOGEN STUDIO" github microsoft`。
- **实际读取 URL / 层级**：
  - 44-R：<https://raw.githubusercontent.com/microsoft/autogen/main/python/packages/autogen-studio/README.md>，R，成功。
  - 44-D：<https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html>，D，成功；读取 Team Builder、JSON Editor、Gallery、Playground。
  - 44-L：<https://raw.githubusercontent.com/microsoft/autogen/main/LICENSE-CODE>，L，成功。
- **具体证据**：44-D 规定 Team 节点接 Agent 与终止条件，Agent 节点接模型与工具，并设置相应 drop zone；可切换 JSON 编辑；Gallery 可复用组件，Playground 观察产物、turn/token 指标及工具动作。44-R 明确研究原型定位，生产使用需要另外完善安全能力。
- **Climber 建议**：B1 的节点调色板可增加明确的容器/成员/资源关系和合法放置提示；在 B2 属性面板显式显示负责人、模型、工具和终止条件。模板复用采用可校验的配置版本，试跑结果与模板定义分开保存。
- **许可证**：44-L 实际正文为 MIT，版权方 Microsoft；此项记录代码许可。
- **失败与未确认**：本项读取成功。未读取 Team Builder 实现、未运行示例。官方使用文档中的 JSON 编辑能力尚未在本环境实测。

## 045 · Edict(三省六部系统)

- **身份与重复**：确认 `cft0808/edict`；“三省六部”和 Edict 在同一仓库标题中对应。本批合并为一项。
- **逐项搜索**：`"Edict" "三省六部" github`。
- **实际读取 URL / 层级**：
  - 45-R：<https://raw.githubusercontent.com/cft0808/edict/main/README.md>，R，成功；读取功能全景、看板与角色流程。
  - 45-D：<https://raw.githubusercontent.com/cft0808/edict/main/docs/task-dispatch-architecture.md>，D，成功；重点读取开头的架构概览，未作全文实现审计。
  - 45-L：<https://raw.githubusercontent.com/cft0808/edict/main/LICENSE>，L，成功。
- **具体证据**：45-R 描述规划、审核/退回、派发、执行的分工；看板含按状态列展示、任务流转链、心跳徽章及叫停/取消/恢复。45-D 开头具体列出状态机、`flow_log + progress_log + session JSONL` 合并活动流，以及重试、升级、回滚调度。这里确实读取了作者的架构文档，仅对该读取范围作证。
- **Climber 建议**：B1 在执行前展示审核关卡和退回路径，卡片含负责人/更新时间/阻塞原因；B2 统一任务、工具及状态事件时间线。干预操作依据后端实际支持的命令启用，并记录操作者及前后状态。
- **许可证**：45-L 为 MIT，版权行 `2026 openclaw-sansheng-liubu contributors`。
- **失败与未确认**：读取成功；没有安装 OpenClaw、执行脚本或启动 Docker。README 对其他框架的优劣比较属于作者宣传，本研究未采纳为事实；文档中的重试/回滚能力仍待源码及运行验证。

## 046 · Council of High Intelligence

- **身份与重复**：确认 `0xNyk/council-of-high-intelligence`。已读材料支持结构化讨论协议/插件形态，可借鉴协作过程；独立 Web 画布未确认。
- **逐项搜索**：`"Council of High Intelligence" github`。
- **实际读取 URL / 层级**：
  - 46-R：<https://raw.githubusercontent.com/0xNyk/council-of-high-intelligence/main/README.md>，R，成功；读取 Choose a mode、What the protocol protects、Track the outcome。
  - 46-L：<https://raw.githubusercontent.com/0xNyk/council-of-high-intelligence/main/LICENSE>，L，成功。
- **具体证据**：46-R 区分 Full/Quick/Duo；Full 包括独立分析、交叉质询、最终立场和综合。结论保留未解决问题、异议、终止条件及下一行动，证据标签分 FACT/INFERENCE/ASSUMPTION/UNKNOWN；结果追踪记录责任人、复查日期和改变判断的证据。
- **Climber 建议**：把这些阶段表达为 B1 的可配置协作模板，在 B2 以“主张/依据/异议/待验证/结论”呈现产物；明确讨论轮次预算与人工裁决入口。只展示参与者公开提交的证据和简要理由，保护内部推理边界。
- **许可证**：46-L 为 MIT，版权行 `2026 nyk`。
- **失败与未确认**：读取成功。未加载其 SKILL、安装插件或运行任何 council/provider；未读取协议实现文件。README 配图仅见引用，不能作为已体验的交互界面证据。

## 047 · Multi-Agent Playground

- **身份与重复**：歧义。候选 A 为 Azure-Samples/agent-playground，同名 README 明确署名 Simon Lacasse；搜索同时出现 Pommerman: A Multi-Agent Playground，候选 B 仓库为 MultiAgentLearning/playground。原名缺少作者，用户具体所指未确认。
- **逐项搜索**：`"Multi-Agent Playground" github`；补充 `"Multi-Agent Playground" github Azure Samples`。
- **实际读取 URL / 层级**：
  - 47A-R：<https://raw.githubusercontent.com/Azure-Samples/agent-playground/main/README.md>，R，成功。
  - 47A-C：<https://raw.githubusercontent.com/Azure-Samples/agent-playground/main/main.py>，C，成功。
  - 47A-L：<https://raw.githubusercontent.com/Azure-Samples/agent-playground/main/LICENSE.md>，L，成功。
  - 47B-R：<https://raw.githubusercontent.com/MultiAgentLearning/playground/master/README.md>，R，成功；用于辨别强化学习游戏语境。
- **具体证据 A**：47A-R 明示教学用途、function calling/RAG simulation 和合成数据。47A-C 采用 Streamlit；初始化 `st.session_state.plan`/`plan_history`，在 `Industry`、`Use Case`、query 输入后调用 `get_initial_plan`，把初始计划写入 `plan`，并通过 `update_sidebar` 更新侧栏。历史数组初始化本身不足以证明完整版本追踪。README 写“右侧”，源码入口仅使用 `st.sidebar`，具体屏幕方位以运行验证为准。
- **具体证据 B**：47B-R 描述 Bomberman 风格 AI 研究环境，包含 FFA、Team、Team Radio 及比赛回放。其材料对应多 Agent 强化学习场景，不能据此确认用户要找的 LLM 协作 UI。
- **Climber 建议**：仅从 A 提取“任务描述 → 初始计划 → Agent 通信 → 计划状态更新”的观察顺序，与 B1/B2 对齐；模拟工具与真实执行均需醒目标记。保留计划版本对比入口，避免只显示最终计划而丢失调整经过。候选 B 暂不列为直接 UI 借鉴来源。
- **许可证**：47A-L 为 MIT/Microsoft；候选 B 许可证正文未读取，留空。
- **失败与未确认**：上述读取成功；未运行 Streamlit、调用模型或评估仿真。自由拖拽画布和真实检索能力未确认。两候选保持独立，不替用户强选。

## 048 · CrewAI Studio(声称官方需核验)

- **身份与重复**：歧义，官方性已分层核验。CrewAI 第一方文档确认官方产品 **Crew Studio**；`strnad/CrewAI-Studio` 是另一同名仓库候选，已读材料未建立其 CrewAI 官方归属。用户具体所指仍待原始 URL。
- **逐项搜索**：`"CrewAI Studio" github official`、`CrewAI Studio visual builder official site:docs.crewai.com`、`"CrewAI Studio" site:crewai.com`。
- **实际读取 URL / 层级**：
  - 48-D：<https://docs.crewai.com/en/enterprise/features/crew-studio>，D，成功；网页读取跳转到 <https://docs-platform.crewai.com/platform/en/features/crew-studio>，正文标题 Crew Studio。
  - 48-W：<https://www.crewai.com/amp>，官方产品页，成功；跳转到 <https://crewai.com/agent-management-platform>，仅辅助核对官方平台归属。
  - 48-R：<https://raw.githubusercontent.com/strnad/CrewAI-Studio/main/README.md>，R，成功；社区候选自己的第一方说明。
- **官方具体证据**：48-D 明确 chat 与拖拽画布共享状态；界面分 AI Thoughts、Canvas、Resources，Execution 包括事件时间线与 Details/Messages/Raw Data。Download ZIP 是单向导出，后续代码修改无法回写 Studio，定制部署成为独立代码来源自动化。以上为官方文档能力描述，未访问付费工作区。
- **社区具体证据**：48-R 明确 Streamlit、结果历史、知识源、单页应用导出及可停止的后台 crew run；文件开头声明 low-maintenance。该材料只支持此仓库自身定位。
- **Climber 建议**：让对话辅助修改和 B1 拖拽操作共享同一工作流草稿，修改前展示差异并允许确认；B2 增加运行详情与原始事件的层级切换。导出界面明确可回导范围、版本来源及后续编辑归属，防止用户误认自动双向同步。
- **许可证**：官方 Studio UI/托管服务许可证未读取，留空；社区仓库 LICENSE 正文未取得，留空。CrewAI 框架许可不用于推定这两项。
- **失败与未确认**：<https://raw.githubusercontent.com/strnad/CrewAI-Studio/main/LICENSE> 与 <https://raw.githubusercontent.com/strnad/CrewAI-Studio/main/LICENSE.txt> 均返回 404。官方 Studio 前端源码未取得；未确认社区仓库存在节点画布或获得官方背书。

## 049 · LangGraph Studio

- **身份与重复**：确认 LangChain 官方历史产品。2024-08-01 官方文章标题为 LangGraph Studio；本次当前官方文档标题为 LangSmith Studio。分别记录历史和当前材料，具体更名日期未核实；与 042 分开计数。
- **逐项搜索**：`LangGraph Studio official github langchain-ai`。
- **实际读取 URL / 层级**：
  - 49-D1：<https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide>，官方发布文章，成功；明确作者 LangChain Team、日期 2024-08-01。
  - 49-D2：<https://docs.langchain.com/langsmith/studio>，D，成功；读取 Features、Graph mode、Chat mode。
- **具体证据**：49-D1 描述图可视化、逐步调试、修改中间 state 后继续、修改节点逻辑后重跑。49-D2 列出 graph architecture、threads、assistants、time travel；Graph mode 展示走过的节点及中间状态，Chat mode 面向对话测试，要求 state 包含或扩展 `MessagesState`。历史文章的 Apple Silicon 桌面限制仅代表当时说明。
- **Climber 建议**：在 B1 区分“编辑定义”和“观察运行”，运行态叠加节点轨迹；B2 展示所选节点输入、输出和时间。进一步评估 checkpoint/state diff/分支重跑时，先确认后端快照与副作用处理能力，并为重放生成新的运行标识。
- **许可证**：Studio 自身许可证未读取，留空；LangGraph 框架开源属性不自动覆盖 Studio UI。
- **失败与未确认**：<https://raw.githubusercontent.com/langchain-ai/langgraph-studio/main/README.md> 返回 404，已用官方历史文章和当前文档补足身份与交互证据；未声称读取旧 Studio 源码，未运行调试或验证 checkpoint 恢复。

## 050 · LangFlow

- **身份与重复**：确认本任务 UI/协作语境下的 `langflow-ai/langflow`，官方材料使用 Langflow 拼写。本批无同一项目重复项；未把其他同名研究项目强配进来。
- **逐项搜索**：`LangFlow official github langflow-ai`。
- **实际读取 URL / 层级**：
  - 50-R：<https://raw.githubusercontent.com/langflow-ai/langflow/main/README.md>，R，成功。
  - 50-C：<https://raw.githubusercontent.com/langflow-ai/langflow/main/src/frontend/src/pages/FlowPage/index.tsx>，C，成功；读取 `FlowPageMainContent`、离开页面保护和 Playground 布局。
  - 50-L：<https://raw.githubusercontent.com/langflow-ai/langflow/main/LICENSE>，L，成功。
- **具体证据**：50-R 列出可视构建、逐步试验 Playground、API/JSON 导出和 MCP 服务。50-C 通过 `changesNotSaved`/`useBlocker`/`beforeunload` 保护未保存或正在构建的流程；右侧 Playground 可调整尺寸并全屏，主体同时挂载 AssistantPanel。Traces/Memories/Agent 切换分支受 `ENABLE_NEW_SIDEBAR` 控制，是否在发布配置启用需另查。
- **Climber 建议**：B1 增加未保存/运行中离开提示，保存状态明确可见；B2 的对话测试、产物和执行观察复用当前 flow/run 上下文。抽屉、分屏和全屏切换保留当前选中节点与画布视口，避免长任务观察时丢失定位。
- **许可证**：50-L 正文为 MIT，版权行 `2024 Langflow`。
- **失败与未确认**：本项读取成功。未读取所有导入组件或执行构建；仅出现 `useRestoreCanvasHitl` 调用不足以确认其全部恢复语义。未确认多人实时协同编辑。

## 最可用的三点

1. **同一任务的跨视图关联**：结合 041 的多 Agent 会话、042 的 thread/UI 事件与产物侧栏、050 的画布/Playground，优先设计 session/run/node/artifact 的互相定位，落点为 B1/B2。证据范围见 41-R1/R2、42-R/C、50-C。
2. **协作责任与审核显式化**：结合 044 的团队组件关系、045 的审核退回路径、046 的异议及待验证结论，将角色、终止条件和人工裁决表达为可见状态。证据范围见 44-D、45-R/D、46-R。
3. **编辑态与运行态分离**：结合 048 的 Execution 视图和单向导出边界、049 的节点调试/中间状态、050 的未保存保护，评估可追踪的运行面板与版本来源；快照重放须以真实后端能力为前提。证据范围见 48-D、49-D1/D2、50-C。

## 完成核对

- 041–050 共 10 条，均包含搜索词、实际读取 URL、读取层级、证据、Climber 建议及许可证依据/留空原因。
- 043/047/048 的歧义保留；041 的迁移地址合并，042/049 产品角色区分。许可证正文成功核对 7 个仓库候选；041 和 043B 仅引用实际看到的 README 声明。
- HTTP 403/404 均在相应条目明确列出；未把失败路径、未打开的设计文档或未运行的界面记为已验证。
- 本次外部读取成功不等于端到端验证。以上建议仍是研究结论，本次交付仅限本文件。
