# UI 来源核验：081-090

调研日期：2026-09-25。项目：climber。范围：调试与观测 UI，只读调研。

## 核验口径

- 按原名逐项发起真实搜索，再打开搜索找到的维护者仓库或官方文档。搜索采用批量并行查询；来源读取也按批次执行。
- 状态指原名的身份归属：确认＝可定位项目；歧义＝泛称、组件组合或多个候选；未确认＝只有近名项目，身份关联证据不足；重复＝同一项目身份已有确证。候选有功能证据也继续注明候选。
- 产品层级：框架 / 组件与示例 / 独立工具 / 产品内功能 / 研究方法。读取层级：R＝维护者 README，D＝官方说明或 API 文档，P＝发布者包说明，L＝许可证正文，C＝源码。搜索摘要只用于发现。
- 本批外部功能证据止于 R/D/P，许可证另核 L；没有启动候选、运行样例、验证截图交互或审阅外部实现源码。文档所称能力均为来源声明。
- URL 为实际成功读取的地址；失败地址另列。动态分支及文档以本次访问为准，未固定到 commit，不据此保证某个已发布版本具备全部功能。
- 许可证按具体仓库、具体读取层级记录；README 声明与 LICENSE 正文分别标注。未读到的许可不补猜，也不把一个候选的许可转移给同名项目。
- 以下 Climber 建议是研究者推导，属于后续设计方向；本次只新增本文。

## 本地对照基线

- 已完整读取 `frontend-react/src/pages/TracesPage.tsx:1-20`：页面承载 `TraceViewer`，文案涉及 LLM 调用、工具执行和智能体循环。
- 已完整读取 `frontend-react/src/components/tracing/TraceViewer.tsx:1-177`：`TraceSpan` 包含 `parent_id`、`status`、`duration_ms`、`tokens_used`、`model`、`error`、`metadata`；现有 UI 为记录列表、六项汇总、递归跨度树。
- 该组件通过 `api.listTraces()` / `api.getTrace(tid)` 加载数据，包含手动刷新；本次读取中未见持续订阅、详情抽屉或节点折叠控制。建议中的输入输出快照、记忆评分和事件流字段仍需后续核对服务端契约。
- 已只读检查既有调研标题和匹配行；`references-021-060.md` 与并行新增的 `references-021-030.md` 的 022 条目均提到 LibreChat 的 Trace Viewer。这里只据此提示名称重叠，跨批唯一项目去重仍需完整清单。

## 081 · Agent Tracer

- **状态：歧义。** 至少存在轨迹风险研究仓库和 AgentTracer SDK/仪表盘候选；原名无法唯一落到某个开源 UI。
- **真实查询：** `"Agent Tracer" github`。
- **候选与层级：** `sinatayebati/agent-tracer` 是 TRACER 研究项目（R/L）；`agenttracer-ai` 是发布者描述的追踪 SDK 与仪表盘（P），其关联源码可访问性未确认。
- **实际读取 URL（R）：** https://github.com/sinatayebati/agent-tracer
- **实际读取 URL（P）：** https://pypi.org/project/agenttracer-ai/
- **实际读取 URL（L）：** https://raw.githubusercontent.com/sinatayebati/agent-tracer/main/LICENSE
- **具体证据：** TRACER README 的 Overview 列出循环/连贯性信号及轨迹片段尾部风险聚合；Viewing Results 列出模拟、任务与性能结果浏览。PyPI 的 Fork / Merge 段列出 `log_fork`、`log_subagent`、`log_merge`，并声明带 fork/merge 数据时出现展示交互 DAG 的 Graph 页签。两组证据分别归属各自候选。
- **失败与替代：** https://github.com/CrazeXD/agenttracer 读取失败；改读 https://raw.githubusercontent.com/CrazeXD/agenttracer/main/README.md 仍失败。工具均返回 Internal Error，HTTP 状态未获确认。保留发布者说明作为较弱证据，同时成功读取上述 TRACER 官方仓库；读取失败不能证明仓库不存在。
- **许可证：** TRACER 仓库 LICENSE 实读为 MIT；`agenttracer-ai` 关联仓库许可证正文未读到，留待核验。
- **Climber 建议：** 在现有 `parent_id` 树旁规划并行分支/汇合视图；循环警告、重复工具调用和高风险片段应定位到具体跨度。DAG 需要显式分支/汇合数据；风险分值需要可追溯算法与输入，避免由耗时直接推断。
- **重复判断：** 与 087、088 属观测功能重叠；本批证据不足以合并其项目身份。

## 082 · Thinker UI

- **状态：未确认。** 检索到近名 Thinker 训练工作台；原名与该项目之间的唯一对应关系缺乏证据。
- **真实查询：** `"Thinker UI" github`；补充 `"Thinker" "UI" github`。
- **候选与层级：** `lalomorales22/thinker`，完整训练工作台（R）；README 将其定位为使用 Tinker training API 的微调 studio。此候选身份与 Thinking Machines Lab 的官方归属分开处理。
- **实际读取 URL（R）：** https://github.com/lalomorales22/thinker
- **实际读取 URL（R/raw）：** https://raw.githubusercontent.com/lalomorales22/thinker/main/README.md
- **具体证据：** README 描述导入的 inspect → map → preview → commit 阶段；Demo mode 单独标识；训练 loss/reward 经 WebSocket 更新；失败请求退避重试，重连后重新拉取。以上为文档声明，未运行验证。
- **许可证：** README 的 License 段实际写有 MIT；未读取独立 LICENSE 正文，许可证据层级仅为 R。
- **Climber 建议：** 长任务卡显示实际阶段名称与最后更新时间；连接状态和任务状态分别显示；演示记录带持续可见的标签；导入 trace 时先预览字段映射和脱敏结果，再明确确认。
- **边界与重复：** 只保留候选交互参考，原名的 Agent 调试 UI 身份仍未确认；未证实与本批其他项目重复。

## 083 · Chainlit

- **状态：确认。** 可定位到 `Chainlit/chainlit` 及对应官方文档。
- **真实查询：** `"Chainlit" github`。
- **产品与读取层级：** Python 对话应用框架；R/D/L。
- **实际读取 URL（R）：** https://github.com/Chainlit/chainlit
- **实际读取 URL（D）：** https://docs.chainlit.io/concepts/step
- **实际读取 URL（L）：** https://raw.githubusercontent.com/Chainlit/chainlit/main/LICENSE
- **具体证据：** Step 文档明确列出类型、输入输出、开始结束；`config.ui.cot` 控制全部显示、隐藏或仅工具调用；示例把工具 Step 与最终 Message 分开。README 说明原团队自 2025-05-01 起退出主动开发，项目转由社区维护。
- **许可证：** 独立 LICENSE 正文实读 Apache-2.0。
- **Climber 建议：** 对话保留最终答复，执行过程使用带类型/耗时的独立步骤卡；工具输入输出按需展开；观测面板只展示后端实际产生、允许公开的事件和摘要。可将现有跨度树与聊天轮次联动。
- **边界与重复：** 本批确认的是框架身份；Step UI 与 084、085 的执行状态呈现重叠，各自仍为独立上游。

## 084 · Streamlit Agent Components

- **状态：歧义。** 已确认 Streamlit 状态组件及 LangChain 官方示例仓库；此完整原名作为独立项目的身份未确认。
- **真实查询：** `"Streamlit Agent Components" github`；补充 `Streamlit agent components official langchain`。
- **候选与层级：** `langchain-ai/streamlit-agent` 为参考应用集合（R/L）；`st.status` 为框架组件（D）。
- **实际读取 URL（R）：** https://github.com/langchain-ai/streamlit-agent
- **实际读取 URL（D）：** https://docs.streamlit.io/develop/api-reference/status/st.status
- **实际读取 URL（L）：** https://raw.githubusercontent.com/langchain-ai/streamlit-agent/main/LICENSE
- **具体证据：** 示例 README 列出流式响应、会话历史、带搜索的聊天，以及反馈与 LangSmith trace 链接。仓库页面明确显示于 2026-02-24 归档。`st.status` 文档列出 running/complete/error、展开状态及 `.update()`，还说明 step 风格可连接为时间线。
- **许可证：** 示例仓库 LICENSE 正文实读 Apache-2.0；此记录仅覆盖该仓库，Streamlit 本体与第三方组件需分别核验。
- **Climber 建议：** 把工具执行变为稳定的状态行：运行中展开，结束后保留摘要，错误保持可见；统一阶段状态与时长展示，提供由反馈跳回对应 trace 的入口。借鉴已归档示例时应将 API 兼容性列为待验证项。
- **重复判断：** 组件集合与上游框架分别计层级；与 090 的 Streamlit 控制台是技术依赖关联。

## 085 · Gradio Agent Blocks

- **状态：歧义。** 证据支持 Gradio 的 Blocks + Chatbot + ChatMessage 组合；完整原名作为独立开源仓库未确认。
- **真实查询：** `"Gradio Agent Blocks" github`；补充 `Gradio agents Blocks ChatMessage metadata title documentation`。
- **候选与层级：** Gradio 官方 Agent 界面教程及 Chatbot 组件 API，框架内组件组合（D/L）。
- **实际读取 URL（D，固定旧版）：** https://gradio.app/4.44.1/guides/agents-and-tool-usage
- **实际读取 URL（D，当前入口）：** https://gradio.app/docs/gradio/chatbot
- **实际读取 URL（D，入口重定向正文）：** https://gradio.app/api/markdown/chatbot
- **读取回退：** 直接请求 markdown 地址曾返回 Internal Error；改走上列官方 docs 入口后成功重定向并读取正文。
- **实际读取 URL（L）：** https://raw.githubusercontent.com/gradio-app/gradio/main/LICENSE
- **具体证据：** 4.44.1 教程以 `gr.Blocks()` 构建 Agent 聊天 UI，`metadata.title` 形成可折叠工具消息。当前 Chatbot 文档进一步列出 `id`、`parent_id`、`duration`、`status`；pending 显示旋转提示并展开，done 默认收起。两份资料版本分开记录。
- **许可证：** Gradio 仓库 LICENSE 正文实读 Apache-2.0。
- **Climber 建议：** 用现有 span ID/parent ID 建立折叠步骤卡，标题含工具名、状态和时长；保留错误展开，完成摘要收起。文档 duration 为秒，Climber 为 `duration_ms`，映射时明确单位；补全取消/失败状态需依据自身事件契约。
- **重复判断：** 属 Gradio 官方能力组合；与 083 的步骤概念重叠，未证实为同一项目。

## 086 · Solara AI UI

- **状态：歧义。** Solara 框架及 Lab Chat Components 可确认，完整原名的独立产品身份未确认。
- **真实查询：** `"Solara AI UI" github`；补充 `Solara AI chat UI github widgetti`、`Solara chat documentation ChatBox ChatMessage`。
- **候选与层级：** `widgetti/solara` Python UI 框架及 Lab 聊天组件（R/D/L）。
- **实际读取 URL（R）：** https://github.com/widgetti/solara
- **实际读取 URL（D）：** https://solara.dev/documentation/components/lab/chat
- **实际读取 URL（L）：** https://raw.githubusercontent.com/widgetti/solara/master/LICENSE
- **具体证据：** Chat Components 列出 ChatBox、ChatInput、ChatMessage；ChatInput 将 `disabled_input` 与 `disabled_send` 分开；ChatMessage 接受自定义 children，页面给出 CustomMessage 示例。README 定位为基于 Reacton/ipywidgets 的 Python 框架。
- **许可证：** 本次根 LICENSE 正文实读 MIT；仅记该读取范围，额外商业或依赖模块另核。
- **Climber 建议：** 工具运行期间保留草稿编辑能力，发送权限单独控制；把检索结果、图片、表格和耗时作为消息内独立内容块。借鉴组件职责划分，继续沿用项目现有 React 前端。
- **重复判断：** 与 083-085 同属交互层参考；框架身份独立，通用 AI UI 标签需要具体组件证据补充。

## 087 · Agent Debugger UI

- **状态：歧义。** 属功能泛称；本批保留 `Rxflex/agenttrace` 作为有证据的候选，原名与该仓库的唯一对应关系未确认。
- **真实查询：** `"Agent Debugger UI" github`；同批 `"Trace Viewer" agent github` 也返回该候选。
- **候选与层级：** AgentTrace，本地追踪 SDK、存储后端及 Web 调试工具（R/L）。
- **实际读取 URL（R）：** https://github.com/Rxflex/agenttrace
- **实际读取 URL（L）：** https://raw.githubusercontent.com/Rxflex/agenttrace/main/LICENSE
- **具体证据：** README 的 Web UI 段明确列出 run list、可展开/收起的 trace tree、展示类型/时间/提示词/响应/属性的 details panel；架构图标注 React + TypeScript 前端、FastAPI/SQLite 后端。README 的 quickstart 仍有 `yourusername` 克隆占位符，采用前需另验可运行性。
- **许可证：** 候选独立 LICENSE 正文实读 MIT。
- **Climber 建议：** 扩展现有记录列表与跨度树，增加固定选中节点和右侧详情面板；详情分基础字段、输入输出、错误/属性。读取快照与实际重执行使用独立入口，执行动作必须先具备后端支持。
- **边界与重复：** 文档证据支持轨迹检查；断点、暂停进程和确定性重放未获证实。与 081/088 为用途关联，项目去重保持独立。

## 088 · Trace Viewer

- **状态：歧义；存在名称重复。** 多个项目和产品内功能使用该词；本批未确认唯一原项目，也未证实跨批项目身份重复。
- **真实查询：** `"Trace Viewer" agent github`。
- **候选与层级：** `abelperry/TraceViewer` 的 README 当前标题为 Trace Review，属于独立 Agent 日志查看工具（R/L）；Google Trace-viewer 属通用性能追踪前端（D）。
- **实际读取 URL（R）：** https://github.com/abelperry/TraceViewer
- **实际读取 URL（D）：** https://google.github.io/trace-viewer/
- **实际读取 URL（L）：** https://raw.githubusercontent.com/abelperry/TraceViewer/main/LICENSE
- **具体证据：** Agent 候选 README 描述按项目目录归组的 Claude Code/Codex JSONL、增量读取和 SSE patch、Trace/Stats/Reviews 导航；评审注释定位至 evidence event indexes，并在 trace 增长后提示锚点可能变化。Google 官方页自述对应 chrome tracing 与 Android systrace。
- **许可证：** `abelperry/TraceViewer` LICENSE 正文实读 MIT；Google 项目许可证本次未读，留待核验。
- **Climber 建议：** 增加运行事件持续更新与连接新鲜度提示；错误/评审注释锚定不可变事件 ID，并保留快照版本。先核对现有服务端流式契约；评审意见作为派生层，支持跳回原始事件。
- **重复判断：** 既有 022 条目也出现 Trace Viewer 功能名，登记为名称/功能重叠。081、087 的 SDK/调试器与本项的日志查看器应按实际数据入口区别归档。

## 089 · Prompt Studio UI

- **状态：歧义。** 同名覆盖提示词版本管理、媒体生成和 Agent 工具工作台；保留候选，完整原名无法唯一定位。
- **真实查询：** `"Prompt Studio UI" github`；补充 `"prompt studio" github UI`、`"Prompt Studio" "github.com" "MIT"`。后者仅为检索词，不作为许可结论。
- **候选与层级：** `JoeyLearnsToCode/prompt-studio` 为提示词版本管理工具（R/L）；`apatassini/prompt-studio` 为媒体生成工作台（R）；`docs.prompt.studio` 为工具工作台官方说明（D）。
- **实际读取 URL（R）：** https://github.com/JoeyLearnsToCode/prompt-studio
- **实际读取 URL（R/raw）：** https://raw.githubusercontent.com/JoeyLearnsToCode/prompt-studio/master/README.md
- **实际读取 URL（L）：** https://github.com/JoeyLearnsToCode/prompt-studio/blob/master/LICENSE
- **实际读取 URL（L/raw）：** https://raw.githubusercontent.com/JoeyLearnsToCode/prompt-studio/master/LICENSE
- **实际读取 URL（其他候选）：** https://github.com/apatassini/prompt-studio ; https://docs.prompt.studio/ （后者重定向至 https://prompt.studio/ 并读到正文）。
- **具体证据：** 版本管理候选 README 列出分支树、节点定位、CodeMirror 编辑、并排 Diff、本地浏览器存储和 JSON/ZIP 导出。媒体候选自述基于 ComfyUI + llama.cpp；另一官方文档首页标为 Alpha，并将产品称为 Agent 所建工具的工作台。三者保持独立归属。
- **失败与替代：** main 分支地址 https://raw.githubusercontent.com/JoeyLearnsToCode/prompt-studio/main/README.md 与 https://raw.githubusercontent.com/JoeyLearnsToCode/prompt-studio/main/LICENSE 均读取失败，工具返回 Internal Error，HTTP 状态未获确认；核对仓库的 master 分支后成功读取上列正文。
- **许可证：** 版本管理候选 README 与独立 LICENSE 均实际标为 AGPL-3.0；先前过程消息中的“许可冲突”判断撤回。另两个候选许可证正文未核，留待核验。仅记录标识，不推导商业使用结论。
- **Climber 建议：** 为实验增加 prompt 版本树和并排差异；每次 run 关联提示词快照、模型配置、工具集合与评测结果。历史 run 保留原快照，编辑后显式形成新版本，便于比较失败前后的输入变化。
- **重复判断：** 多个同名候选用途不同；跨项目身份不合并。

## 090 · Memory Inspector

- **状态：歧义。** 至少两个 Agent 项目把它用作内置面板名称；本批以功能模块记录，独立同名仓库身份未确认。
- **真实查询：** `"Memory Inspector" agent github`；补充 `"memory inspector" "github" "agent" UI`、`"memory inspector" github agent memory UI -site:reddit.com`。
- **候选与层级：** `rishipratap10/memory-guardian` 的 Admin UI（R/L）；`improving/agentic-memory` 的右侧 Memory Inspector 演示面板（R）。
- **实际读取 URL（R）：** https://github.com/rishipratap10/memory-guardian
- **实际读取 URL（R）：** https://github.com/improving/agentic-memory
- **实际读取 URL（L）：** https://raw.githubusercontent.com/rishipratap10/memory-guardian/main/LICENSE
- **具体证据：** Memory Guardian 的 Memory Inspector (Admin UI) 段描述检索调试、评分轨迹、冲突审查、生命周期监测；数据表说明列有 retrieval_logs。另一个候选的 Agent Loop 分 Read/Retrieve/Assemble/Act/Write-back，README 明确说右侧面板逐步显示过程，并列出用户画像、检索记忆、情节上下文与压缩面板。
- **许可证：** Memory Guardian 根 LICENSE 正文实读 Apache-2.0；`improving/agentic-memory` 许可证本次未核，留待核验。
- **Climber 建议：** 规划与 span/轮次关联的记忆抽屉，分别呈现候选召回、排序分量、入选原因、压缩前后 token、写回变化；保持当前记忆状态与本次 run 的历史快照可区分。先验证服务端数据字段，评分缺失时明确显示未采集。
- **边界与重复：** Memory Guardian README 自述 early-stage，并说明示例场景为设计意图；本批仅核到控制台/演示面板的说明，成熟度、评分准确性和实际交互未运行验证。与 084 为 Streamlit 生态关联，两个 Memory Inspector 候选各自独立。

## 覆盖与优先建议

- 10/10 原名已逐项查询；10/10 均成功读取至少一个相关官方仓库或官方文档，候选身份与原名确认率分开统计。
- 唯一项目身份确认 1 项：083。歧义 8 项：081、084、085、086、087、088、089、090。原名未确认 1 项：082。
- 跨项目身份“重复”确证 0 项；088 有名称/功能重复提示。由于并行批次仍在变化，本批去重范围仅限实际读取的既有标题与匹配行。
- 最有用 1：执行步骤与答复分层。结合 083-085 的步骤/状态组件，给现有 span 树增加稳定 ID、显式状态、可折叠详情，完成与失败分别处理。
- 最有用 2：可定位的调试证据。结合 087-088 的树、详情与事件注释，规划“记录列表 → 执行树 → 输入输出/错误详情”，并标明数据更新时间与快照版本。
- 最有用 3：实验输入可追溯。结合 089-090，把 prompt 版本、记忆召回/压缩/写回证据与同一次 run 关联，支持有依据的差异比较。
- 以上均为设计建议。本次无代码修改、依赖安装、服务启动、第三方 Agent 安装/运行、commit 或 push；仅使用 apply_patch 新增本文件，保留并行工作区已有变更。
