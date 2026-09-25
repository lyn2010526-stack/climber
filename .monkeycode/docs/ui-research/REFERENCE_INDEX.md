# UI 研究参考索引：001–100

日期：2026-09-25。范围：project-wiki 局部 sync，仅汇总本地九份分批报告；本轮未联网重做研究、未运行外部项目。路径均相对 `/workspace/climber`；表内报告路径相对本文件所在目录。

## 口径与覆盖

- 唯一编号覆盖 **100/100**：001–100 连续，各出现一次。这里的唯一性指编号，独立项目数量须按身份与产品层级另计。
- 主状态互斥：**确认 47、歧义 40、重复 4、未确认 9**，合计 100。确认中的 069 是方法论；053 的主框架已确认、原名独立 UI 未确认，统一列歧义；051 列未确认。
- 原名或其明确历史/子实现映射有确认依据 **51 条**，含 47 条确认和 4 条重复；扣除四组重复后为 47 个已确认参考身份，其中含 1 个方法论及协议、框架、产品内功能。此数不代表 47 个独立开源 UI 产品。
- 各报告记载逐项检索 **100/100**；原项目、候选或相关一手正文读取 **99/100**，051 仅搜索索引与失败读取。99 条分为确认 47、重复 4、歧义 40、未确认但相关正文已读 8。候选正文可读与原名身份确认分别计数。
- 最高功能证据层级达到源码 **8 条**：003、042、047、050、057、061、071、093；047 为候选源码。其余成功阅读 91 条为文档/产品页/讨论层，051 为检索层。096 的 E2 是开发文档，未计源码。LICENSE 正文单列于原报告，未用来提升功能证据层级。
- 本轮索引依据九份本地报告的可见内容及定向核对；部分读取输出曾截断，完整逐字阅读尚未确认。表中外部读取层级转述报告记录，外部原文未由本轮重新获取。分支浮动、部分阅读、失败回退、许可范围均以对应条目为准。外部安装、交互实测及运行验证 **0 项**；Climber 运行验收另见 `../REVIEW_22_STATUS.md`。
- `references-021-060.md` 为范围重叠的既有报告，本次未纳入计数，也未用其覆盖九份分批报告的结论。

## 100 行索引

“确认”严格限定为身份栏写明的对象；“歧义/未确认”行中的候选保持原作者归属。源码均为所述局部实现，文档均为实际阅读段落，均无外部运行验证。

| 编号 | 原名 | 主状态 | 身份范围或候选 | 实际读取层级（原报告记录） | 对应本地报告与定位 |
| --- | --- | --- | --- | --- | --- |
| 001 | CopilotKit | 确认 | CopilotKit/CopilotKit，SDK | README 文档 | references-001-020.md §001 |
| 002 | assistant-ui | 确认 | assistant-ui/assistant-ui | README 文档 | references-001-020.md §002 |
| 003 | prompt-kit（React AI UI） | 确认 | ibelick/prompt-kit | 源码：prompt-input.tsx；README | references-001-020.md §003 |
| 004 | AG-UI Protocol | 确认 | ag-ui-protocol/ag-ui，协议 | README 文档 | references-001-020.md §004 |
| 005 | A2UI（Google） | 确认 | google/A2UI → a2ui-project/a2ui | README 文档 | references-001-020.md §005 |
| 006 | Loquix（Web Components） | 确认 | @loquix/core、loquix-dev/loquix | 官方站文档 | references-001-020.md §006 |
| 007 | Hashbrown（React Angular） | 确认 | liveloveapp/hashbrown | README 文档 | references-001-020.md §007 |
| 008 | json-render（Vercel Labs） | 确认 | vercel-labs/json-render | README 文档 | references-001-020.md §008 |
| 009 | ggui（MCP） | 确认 | ggui-ai/ggui | README 文档 | references-001-020.md §009 |
| 010 | AgentLabs | 确认 | agentlabs-inc/agentlabs；文档标停更 | README 文档 | references-001-020.md §010 |
| 011 | Lobe Chat UI Kit | 歧义 | 候选 Lobe UI / @lobehub/ui | 候选 README | references-001-020.md §011 |
| 012 | ChatUI（Alibaba） | 确认 | alibaba/ChatUI | README 文档 | references-001-020.md §012 |
| 013 | TDesign AI | 确认 | AIGC 组件族 React Chat 分支 | 包 README；站点正文失败 | references-001-020.md §013 |
| 014 | shadcn-ui AI Chat | 歧义 | 候选 shadcn/ui 聊天原语 | 候选发布说明 | references-001-020.md §014 |
| 015 | React Chatbot Kit | 确认 | FredrikOseberg/react-chatbot-kit | README、配置文档 | references-001-020.md §015 |
| 016 | Vue AI Chat | 歧义 | 候选 nuxt-ui-templates/chat-vue | 候选 README | references-001-020.md §016 |
| 017 | Svelte Chat UI | 歧义 | 候选 @tanstack/ai-svelte 页面 | 候选官方文档 | references-001-020.md §017 |
| 018 | @burtson-labs/agent-ui | 确认 | bandit-agent-framework 内包 | 包 README | references-001-020.md §018 |
| 019 | @aceshooting/lyra-ui | 确认 | aceshooting/lyra-ui | 12.1.2 README 部分、main 组件 API 文档 | references-001-020.md §019 |
| 020 | @nextclaw/agent-chat-ui | 确认 | Peiiii/nextclaw 内包 | 包 README | references-001-020.md §020 |
| 021 | Open WebUI | 确认 | open-webui/open-webui | README 文档 | references-021-030.md §021 |
| 022 | LibreChat | 确认 | danny-avila → LibreChat-AI/LibreChat | README 文档 | references-021-030.md §022 |
| 023 | LobeChat | 确认 | lobe-chat 入口演进至 LobeHub | README 文档 | references-021-030.md §023 |
| 024 | NextChat | 确认 | ChatGPTNextWeb/NextChat | README 文档 | references-021-030.md §024 |
| 025 | Chatbot UI | 确认 | mckaywrigley/chatbot-ui | README 文档 | references-021-030.md §025 |
| 026 | BetterChatGPT | 确认 | ztjhz/BetterChatGPT | README 文档 | references-021-030.md §026 |
| 027 | chatgpt-web（描述 Go 后端须核验） | 歧义 | Go 候选 869413421；Node 对照 Chanzhaoyu | 两份 README；未读 Go 源码 | references-021-030.md §027 |
| 028 | Gemini-Next-Web | 歧义 | 近名 gemini-next-chat，当前 Neo Chat | 候选 README；原名仅搜索 | references-021-030.md §028 |
| 029 | Claude Web UI | 歧义 | ArjunDivecha 候选，上游归属待确认 | 候选 README；另一地址 404 | references-021-030.md §029 |
| 030 | Oobabooga | 确认 | text-generation-webui → TextGen | README 文档 | references-021-030.md §030 |
| 031 | SillyTavern | 确认 | SillyTavern/SillyTavern | README、官方文档 | references-031-040.md §031 |
| 032 | Jan | 确认 | janhq/jan，桌面应用 | README 文档 | references-031-040.md §032 |
| 033 | LM Studio Web UI | 歧义 | 专有桌面本体；nicholasegurley 第三方 UI | 本体文档/条款、候选 README | references-031-040.md §033 |
| 034 | Ollama Web UI | 重复 | 与 021 同谱系历史旧名 | v0.1.102 README | references-031-040.md §034 |
| 035 | Text Generation WebUI | 重复 | 与 030 同仓库谱系 | README、重定向元数据 | references-031-040.md §035 |
| 036 | FastChat Web UI | 确认 | lm-sys/FastChat 内 Web GUI | README 文档 | references-031-040.md §036 |
| 037 | Quivr UI | 歧义 | Quivr 主框架确认，具体 UI 待确认 | 主框架 README、核心文档 | references-031-040.md §037 |
| 038 | AnythingLLM | 确认 | Mintplex-Labs/anything-llm | README 文档 | references-031-040.md §038 |
| 039 | Dify | 确认 | langgenius/dify | README 文档 | references-031-040.md §039 |
| 040 | Flowise AI UI | 确认 | FlowiseAI/Flowise 的 React UI | README；归档为当次来源自述 | references-031-040.md §040 |
| 041 | Open Multi-Agent Canvas（CopilotKit） | 确认 | 原仓库迁入 monorepo 同名示例 | 两份 README；源码获取失败 | references-041-050.md §041 |
| 042 | agent-chat-ui（LangChain） | 确认 | langchain-ai/agent-chat-ui | 源码：Stream.tsx；README | references-041-050.md §042 |
| 043 | AgentGUI | 歧义 | ETH Medical AI Lab、AnEntrypoint 两候选 | 候选 README | references-041-050.md §043 |
| 044 | AUTOGEN STUDIO | 确认 | microsoft/autogen 内 Studio 子包 | README、使用文档 | references-041-050.md §044 |
| 045 | Edict（三省六部系统） | 确认 | cft0808/edict | README、架构文档局部 | references-041-050.md §045 |
| 046 | Council of High Intelligence | 确认 | 0xNyk 同名协议/插件；独立 Web 画布未确认 | README 文档 | references-041-050.md §046 |
| 047 | Multi-Agent Playground | 歧义 | Azure-Samples、Pommerman 两候选 | 候选源码 main.py；两份 README | references-041-050.md §047 |
| 048 | CrewAI Studio（声称官方需核验） | 歧义 | 官方 Crew Studio 与社区 strnad 候选分列 | 官方文档/产品页、候选 README | references-041-050.md §048 |
| 049 | LangGraph Studio | 确认 | 历史官方产品；当前文档 LangSmith Studio | 历史文章、当前文档；源码失败 | references-041-050.md §049 |
| 050 | LangFlow | 确认 | langflow-ai/langflow | 源码：FlowPage/index.tsx；README | references-041-050.md §050 |
| 051 | AgentBuilder（百度前端） | 未确认 | 平台部分定位；开源前端待确认 | 仅检索索引；直读标题/空正文/失败 | references-051-060.md §051 |
| 052 | Coze开源版 | 确认 | coze-dev/coze-studio | README 文档 | references-051-060.md §052 |
| 053 | MetaGPT Web UI | 歧义 | 主框架确认；独立官方开源 UI 待确认 | 主框架 README；Space 源码失败 | references-051-060.md §053 |
| 054 | ChatDev UI | 确认 | OpenBMB/ChatDev 2.0 Web Console | README、Web UI 指南 | references-051-060.md §054 |
| 055 | OpenDevin UI | 确认 | OpenDevin → OpenHands；当前仓库 Agent Canvas | 历史官方文章、当前 README | references-051-060.md §055 |
| 056 | SWE-agent UI | 确认 | 0.7 操作 UI 与当前轨迹 Inspector 分列 | 历史/当前官方文档、README | references-051-060.md §056 |
| 057 | Browser Use UI | 确认 | browser-use/web-ui | 源码：webui.py、interface.py；README | references-051-060.md §057 |
| 058 | Agent Reach UI | 歧义 | Panniantong、jgalea 候选为 CLI/能力层 | 两份候选 README | references-051-060.md §058 |
| 059 | Multi-Agent Workbench | 歧义 | neron82 Web 与 UBC-FRESH CLI 候选 | 两份候选 README | references-051-060.md §059 |
| 060 | AgentVerse UI | 歧义 | OpenBMB 仿真 GUI；同名 Dashboard 分开 | 主 README、ui README；Dashboard 直读失败 | references-051-060.md §060 |
| 061 | AG-UI Reference Implementation | 重复 | 与 004 同项目，实现层补证 | 源码：HttpAgent；README | references-061-070.md §061 |
| 062 | A2UI Renderers（Angular / Flutter / React） | 重复 | 与 005 同参考族；Flutter 在独立仓库 | 客户端文档、三端 README | references-061-070.md §062 |
| 063 | React GenUI | 歧义 | Tambo、OpenTiny 候选；后者 React 待确认 | 候选 README | references-061-070.md §063 |
| 064 | Vue Generative UI | 歧义 | 候选 @openuidev/vue-lang | 候选包 README | references-061-070.md §064 |
| 065 | Dynamic UI Renderer | 未确认 | 机制候选 json-render 与 008 重叠 | 候选 React 包 README；生态页部分 | references-061-070.md §065 |
| 066 | LiveKit AI UI | 歧义 | LiveKit Components / Agents UI 候选 | 候选 README | references-061-070.md §066 |
| 067 | Daily AI UI | 歧义 | Pipecat Web 客户端及 DailyTransport | 候选 README；猜测 UI 库 404 | references-061-070.md §067 |
| 068 | Inkeep AI UI | 歧义 | Inkeep Agents 内 agents-ui 候选 | 根 README；未读子包实现 | references-061-070.md §068 |
| 069 | Component-Driven UI | 确认 | 方法论；独立同名软件库未确认 | 方法论原站、Storybook 文档 | references-061-070.md §069 |
| 070 | Generative UI Kit | 歧义 | anahtiris/generative-ui-playground 内候选包 | 根及包 README | references-061-070.md §070 |
| 071 | MCP Inspector | 确认 | modelcontextprotocol/inspector | 入口及 schemaLint 源码片段、文档 | references-071-080.md §071 |
| 072 | MCP Playground | 歧义 | shroomlife、bighadj22 两候选 | 两份 README | references-071-080.md §072 |
| 073 | HiMCP Server UI | 未确认 | 已读 HiMCP 目录站；Server UI 待确认 | 产品站正文 | references-071-080.md §073 |
| 074 | MCP Studio | 歧义 | sandraschi、RPieterse 两候选 | README；后者仅发布库说明 | references-071-080.md §074 |
| 075 | Model Context Protocol UI（官方声称核验） | 歧义 | MCP-UI SDK 与官方 MCP Apps 分开 | 两份 README、官方博客 | references-071-080.md §075 |
| 076 | Agent Tools UI Kit | 未确认 | 近名 Agents Kit | 候选 README；许可另读 | references-071-080.md §076 |
| 077 | Function Calling UI | 未确认 | shinychat 及 issue 设计讨论 | README、issue 讨论 | references-071-080.md §077 |
| 078 | Toolbar UI for Agents | 未确认 | Stagewise、21st 扩展 fork 候选 | 候选 README | references-071-080.md §078 |
| 079 | Tool Result Viewer | 未确认 | TinyHarness 相关框架；摘要路径未证实 | 仓库及 raw README | references-071-080.md §079 |
| 080 | MCP Browser UI | 歧义 | brainfuel 原生浏览器、Saik0s 自动化候选 | 两份 README | references-071-080.md §080 |
| 081 | Agent Tracer | 歧义 | TRACER 研究、agenttracer-ai SDK 候选 | README、PyPI 发布说明 | references-081-090.md §081 |
| 082 | Thinker UI | 未确认 | 近名 lalomorales22/thinker 训练工作台 | 候选 README | references-081-090.md §082 |
| 083 | Chainlit | 确认 | Chainlit/chainlit，框架 | README、Step 官方文档 | references-081-090.md §083 |
| 084 | Streamlit Agent Components | 歧义 | 官方示例与 st.status 组件组合 | 示例 README、组件 API | references-081-090.md §084 |
| 085 | Gradio Agent Blocks | 歧义 | Blocks/Chatbot/ChatMessage 组合 | 4.44.1 教程、当前组件 API | references-081-090.md §085 |
| 086 | Solara AI UI | 歧义 | Solara 框架及 Lab Chat 候选 | README、聊天组件文档 | references-081-090.md §086 |
| 087 | Agent Debugger UI | 歧义 | 候选 Rxflex/agenttrace | 候选 README | references-081-090.md §087 |
| 088 | Trace Viewer | 歧义 | Trace Review、Google Trace-viewer；仅名称重叠 | 候选 README、官方说明 | references-081-090.md §088 |
| 089 | Prompt Studio UI | 歧义 | 版本管理、媒体及工具工作台三候选 | 候选 README、产品文档 | references-081-090.md §089 |
| 090 | Memory Inspector | 歧义 | memory-guardian、agentic-memory 内面板 | 两份候选 README | references-081-090.md §090 |
| 091 | MixLabPro Earth | 确认 | MixLabPro/Earth 浏览器扩展 | README 文档 | references-091-100.md §91 |
| 092 | Agent Browser（Vercel） | 确认 | vercel-labs/agent-browser CLI + Dashboard | README 文档 | references-091-100.md §92 |
| 093 | Page Agent UI（Alibaba） | 确认 | alibaba/page-agent 内 UI/Core | PageAgentCore.ts 源码片段、架构文档 | references-091-100.md §93 |
| 094 | Browser Use Extension | 歧义 | Nanobrowser 候选；官方库/CLI 作对照 | 候选与对照 README | references-091-100.md §94 |
| 095 | Claude Code GUI（JetBrains插件） | 歧义 | CC GUI、Swttch 两作者候选 | 候选 README | references-091-100.md §95 |
| 096 | Cursor UI开源实现 | 歧义 | Void 独立替代候选 | README、开发文档；未读实现源码 | references-091-100.md §96 |
| 097 | Windsurf开源复刻版UI | 未确认 | 官方商业产品对照；Void 与 096 候选重叠 | 官方 Terminal 文档、复用候选文档 | references-091-100.md §97 |
| 098 | Desktop AI Agent UI | 歧义 | UI-TARS Desktop 候选 | README、Quick Start | references-091-100.md §98 |
| 099 | System Tray Agent UI | 歧义 | sprklai/agenttray；mjtpena 专有对照 | 候选 README；许可分开 | references-091-100.md §99 |
| 100 | Mobile Agent UI | 歧义 | Happy 移动/Web 伴随客户端候选 | 候选 README | references-091-100.md §100 |

## 去重证据

| 编号关系 | 判断与计数 | 可追溯依据 |
| --- | --- | --- |
| 021 / 034 | 同一产品历史名称，034 标重复 | references-021-030.md §021；references-031-040.md §034，v0.1.102 标题 Formerly Ollama WebUI 及迁移说明 |
| 030 / 035 | 同一仓库谱系，035 标重复 | references-021-030.md §030；references-031-040.md §035，旧入口重定向 textgen |
| 004 / 061 | 同一协议及参考实现，061 标重复 | references-001-020.md §004；references-061-070.md §061，README 与 HttpAgent 路径 |
| 005 / 062 | 同一 A2UI 参考族细分，062 标重复 | references-001-020.md §005；references-061-070.md §062；Flutter 为另仓实现，许可证分别核验 |
| 008 / 065 | 机制候选重复，065 原名仍未确认 | references-061-070.md §065；不额外增加原名级重复计数 |
| 096 / 097 | Void 替代候选重复，097 原名仍未确认 | references-091-100.md §96–97；不把 Windsurf 复刻登记为已定位 |
| 011 / 023；001 / 041；042 / 049 | 同生态不同范围，保留各条身份 | 各对应条目：组件库/应用、SDK/示例、聊天前端/Studio 分列 |
| 022 / 088；081 / 087 / 088 | 名称或用途重叠，当前材料不足以合并项目身份 | references-081-090.md §081、087、088 |

## 范式采用与待补证

Climber 的 A 配色、B 图标、C 去特效及工厂状态、模型发现、凭据分离等源码/diff 映射集中记录于 `../REVIEW_22_STATUS.md` 的“范式采用”节。该映射表达既有实现与研究建议的对应关系；本轮仅新增文档，源码复制、品牌资产复用、新框架引入与运行通过均须各自提供独立证据。

待主会话补齐：40 条歧义及 9 条未确认的原始 owner/URL；051 有效正文；候选来源锁定版本；Climber 测试命令、日志路径、时间和代码快照。外部项目运行验证在本索引保持 0。
