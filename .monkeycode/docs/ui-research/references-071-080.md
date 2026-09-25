# UI 资料核验：071-080

核验日期：2026-09-25。目标：climber。工作范围：只调研；本次仅通过 apply_patch 新增本文件。

## 口径与结果

- 071-080 共 10 项，每项均提交了独立查询词；相互独立的联网查询和候选打开采用批量并行。没有启动第三方 Agent，没有安装依赖、运行外部项目、改应用代码、commit 或 push。
- 名称身份：确认 1 项（071）；歧义 4 项（072、074、075、080）；未确认 5 项（073、076、077、078、079）；本批确认重复 0 项。这里的“未确认”只表示本次检索证据不足，不表示项目不存在。
- 阅读覆盖：10/10 均读到原项目、候选或相关一手正文；原名确认仍仅为 1/10。成功读取并纳入证据账本的独立外部正文 URL 为 23 个，包含 2 个源码文件、1 个完整许可证文件。相同 URL 的多次打开不重复计数，同仓库 HTML 与 raw 是两个 URL、同一来源。
- 读取层级：S=源码片段；D=维护者 README/官方文档；I=项目仓库 issue 中的设计讨论；P=站点产品页面。只读目录、搜索摘要和 GitHub 导航均不升级为正文或源码证据。D 表示作者材料来源，MCP 官方归属另行核验。
- 每项“climber 建议”是设计推导；没有验证远端交互效果或 Climber 后端契约。仅参考交互范式，不复制源码、图标或品牌。许可证仅在本次实际可见文本明确命名时记录；许可名称来自 README/标签的，另注明未读条款。
- 访问日期与代码发布时间分别处理：默认分支和抓取缓存会变化，未锁定所有 commit，也未证明所有可见内容在该日期之前的历史版本。搜索摘要与正文不一致时，以实际可见正文为边界。
- 本批只检查 071-080 内的重复关系。前批文件只读取了局部作为格式参照，未完成跨全部历史编号的去重审计。

## Climber 已读源码锚点

- C1：`frontend-react/src/components/chat/ToolCallCard.tsx:5-25`，`result` 为可选字符串；状态由 `error`、`isRunning`、`result` 的真值推导。空字符串结果落入 running 分支。这是静态源码观察，未运行组件验证。
- C2：同文件 `:53-74`、`:107-117`，展开条件依赖输出/错误/参数；重试按钮嵌套在展开按钮中。建议实施时分离按钮与键盘焦点，并补充空结果完成态。
- C3：同文件 `:134-185`，参数用 JSON.stringify，输出和错误以 pre 展示；输出有高度限制。当前已读接口没有结构化 MIME/产物渲染字段。
- C4：`frontend-react/src/pages/MCPPage.tsx:12-23,39-75,93-120,163-195`，已读页面是 MCP 市场，记录安装状态、分类、搜索和作者；安装/卸载异常在空 catch 中结束。连接健康与工具 schema 需要独立的数据契约。只读该文件第 1-200 行。
- 阅读过 `.monkeycode/MEMORY.md` 全文；项目根目录未见 `.gitmodules`。已有文档、记忆及应用代码均保持原样。

## 071 · MCP Inspector

- **身份状态**：确认，对应 `modelcontextprotocol/inspector`。官方 docs 仓库明确链接此仓库；搜索里的 Docker、Pipedream fork 及 MCPJam 同类工具未计为本项。
- **实际查询词**：`"MCP Inspector" github`。
- **实际读取 URL**：S01-S05，见末尾完整账本。
- **读取层级**：S + D。读了根 README、Web README 的组件分层与 schema portability 段、官方 Inspector 文档 Feature overview；源码读了 `main.tsx` 入口和 `schemaLint.ts` 的类型/路径/建议数据结构片段。没有审阅整库。
- **证据**：官方文档分开列 Tools、Resources、Prompts、Notifications；Web README 说明 schema 问题用计数徽章和折叠详情表达。`SchemaFinding` 明确包含 `severity`、`schema`、`path`、`issue`、`suggestion`；入口以统一主题提供者装配界面。S02-S05 支撑这些结论。
- **climber 工具调用 UI 建议**：在 C4 之外设计只读工具详情抽屉；参数表单上方显示简短校验摘要，展开后给字段路径和修正建议。将参数校验失败、连接失败与工具执行失败分开呈现。
- **许可证**：S01 README 的 License 段明示处于 MIT 向 Apache-2.0 迁移期：新代码、文档和未获重新许可同意的历史贡献分别处理，提及 Apache-2.0、CC-BY-4.0、MIT。本次未读完整 LICENSE，不能概括成单一许可。
- **边界/重复**：官方身份已核实；所读根 README 为 v2 路线，旧 Inspector 文档和当前 Web README 的细节按各自来源记录；没有运行调试器。

## 072 · MCP Playground

- **身份状态**：歧义；至少两个真实同名候选，缺少 owner/链接无法唯一匹配。
- **实际查询词**：`"MCP Playground" github`。
- **实际读取 URL**：S06 `shroomlife/mcp-playground`；S07 `bighadj22/mcps-playground`。
- **读取层级**：D，两个仓库 README 的简介与功能表。
- **证据**：S06 描述浏览器客户端、JSON Schema 参数表单、带 rpc-id/大小/时间的 JSON-RPC 会话记录；S07 描述 Claude/Gemini 聊天、服务器连接与 Tools/Prompts/Resources 能力发现。两者具有不同 owner、仓库和产品定位。
- **climber 工具调用 UI 建议**：为 C3 增加参数表单/原始 JSON 双视图；执行详情保留 call ID 与时间信息；对连接能力和单次调用记录分层展示。
- **许可证**：S06 README/仓库许可标签明示 MIT，未审阅完整条款；S07 未核验。
- **边界/重复**：两候选分别记证据，不合并功能，不替用户选定原项目。搜索出现的其他 Playground 没有全部展开，也不列为已读候选。

## 073 · HiMCP Server UI

- **身份状态**：未确认；确认找到 HiMCP 目录网站，未确认同名独立 Server UI 仓库/产品。
- **实际查询词**：`"HiMCP Server UI"`；`HiMCP server UI github`。
- **实际读取 URL**：S08 `https://www.himcp.cn/`。
- **读取层级**：P，仅站点正文；未取得该名称对应的源码、README 或开发文档。
- **证据**：正文是 MCP 服务器发现页，包含搜索、类别、语言及精选/官方等列表标签。页面内容足以支持目录界面观察；工具测试、执行结果查看器和管理后台实现仍待确认。
- **climber 工具调用 UI 建议**：C4 的市场列表可增加来源与核验日期；“精选”“发布者声明官方”“已核验官方”采用不同字段。执行健康状态另行展示。
- **许可证**：未核验。目录中收录项目的许可证不能推到 HiMCP 站点。
- **边界/重复**：目录条目的官方标签属于条目元数据；HiMCP Server UI 的独立身份继续保留未确认。

## 074 · MCP Studio

- **身份状态**：歧义；已读 `sandraschi/mcp-studio` 和 `RPieterse/mcp-studio-releases`，属于不同作者的同名项目线索。
- **实际查询词**：`"MCP Studio" github`；`"MCP Studio" github -sandraschi`。第二次查询定位到 RPieterse 的发布文档链接。
- **实际读取 URL**：S09、S10；失败 URL 与 raw 回退见 F01。
- **读取层级**：D；S09 README 的 Beta Status、Working Sets、MCP Server Management；S10 发布仓库 README 全文。
- **证据**：S09 明示 beta、管理仪表盘与 MCP server 双用途，描述配置切换预览和备份。S10 明示公开库承载签名发布包、静态页面和 gallery，应用源码位于私有仓库。
- **climber 工具调用 UI 建议**：C4 若增加工具集切换，先列本次启用/停用差异和影响范围；保存配置后展示明确结果。应用安装、连接就绪、工具调用权限分别建模。
- **许可证**：S09 仓库可见 MIT 标签，未审阅条款；S10 未核验。
- **边界/重复**：S09 的功能表是作者自述；S10 的公开发布文件不能作为读过私有源码的证据。两个候选保持独立，原名尚未唯一匹配。

## 075 · Model Context Protocol UI（官方声称核验）

- **身份状态**：歧义；近名 MCP-UI SDK 与官方 MCP Apps 应分开。确认官方协议/SDK 仓库为 `modelcontextprotocol/ext-apps`；原名所称独立“官方 UI 产品”未确认。
- **实际查询词**：`"Model Context Protocol UI" official`；`site:blog.modelcontextprotocol.io MCP Apps official January 26 2026`。后者定位到官方博客，并实际打开全文。
- **实际读取 URL**：S11 `MCP-UI-Org/mcp-ui`；S12 `modelcontextprotocol/ext-apps`；S23 官方博客。
- **读取层级**：D，两个仓库 README 的身份、架构、工具 UI 关联与渲染说明。
- **证据**：S11 名称为 Model Context Protocol UI SDK，Core Team 写明作者，介绍 `@mcp-ui/*`。S12 位于 MCP 官方组织，仓库说明标明官方 spec/SDK，How It Works 说明工具声明 UI 资源、宿主读取、沙箱 iframe 与双向通信。S23 署名 MCP Core Maintainers、日期 2026-01-26，明确宣布 MCP Apps 成为官方扩展，并说明 MCP-UI 与 OpenAI Apps SDK 的先期贡献；其代码例子明确 `_meta.ui.resourceUri`。
- **climber 工具调用 UI 建议**：C3 先保留原始文本/JSON，再以有类型的结果注册表增加自有视图；远端 HTML 扩展采用能力协商、隔离容器和由宿主处理的动作回调。官方协议归属、SDK 作者及具体 renderer 各自展示。
- **许可证**：S11 README 明示 Apache License 2.0；S12 未读取完整许可证，也不沿用 S11 的许可结论。
- **边界/重复**：MCP Apps 的官方归属有证据；MCP-UI 为其生态实现，两者关联不构成同一仓库或同一品牌。保留两条身份记录。

## 076 · Agent Tools UI Kit

- **身份状态**：未确认；精确名称未唯一定位。已读近名 `agents-ui/agents-kit`，其正文名称为 Agents Kit。
- **实际查询词**：`"Agent Tools UI Kit"`；`"Agent Tools" "UI Kit" github`；`"agent" "UI kit" tool github`。
- **实际读取 URL**：S13 仓库 README；S14 `LICENSE.md` 全文。
- **读取层级**：D + 完整许可证。只读组件目录说明，未读各组件实现。
- **证据**：当前 README 将消息、工具、审批、音频和生成结果归入组件库，并描述 ready/loading/error 示例。LICENSE.md 明确 Non-Commercial License，商用须事先获得书面许可；README 同时保留不同上游来源的许可说明。
- **climber 工具调用 UI 建议**：将工具名称、状态、审批控件与结果面板形成统一自有组件契约；围绕 C1/C3 组织 loading、空结果、成功与错误样例。
- **许可证**：近名候选项目许可证为 Non-Commercial License，已读完整文件；上游组件各自许可仍需逐文件核验。不能用上游 MIT/Apache 名称覆盖整个 kit 的项目许可。
- **边界/重复**：本项只借鉴范式。Agents Kit 与用户原名的同一性未证实；未将其计作原项目确认，也未导入候选代码。

## 077 · Function Calling UI

- **身份状态**：未确认；属于通用功能名称，已读相关设计讨论和其宿主项目。
- **实际查询词**：`"Function Calling UI" github`。
- **实际读取 URL**：S15 `posit-dev/shinychat/issues/31`；S16 `posit-dev/shinychat`。
- **读取层级**：I + D；issue 的 Tool calls in shinychat 段和主仓库简介。
- **证据**：issue 讨论块级/内联两种表达，分别在调用开始、完成时更新同一 UI，并允许完成后呈现自定义结果。主仓库自称 Shiny 的聊天组件，提供 Python/R 文档入口。该 issue 的设计描述与已实现行为分开记录。
- **climber 工具调用 UI 建议**：C1 使用显式调用状态与稳定 call ID；多次并行调用采用紧凑摘要行，选中后展开详情；空字符串结果也允许进入完成态。
- **许可证**：S16 仓库可见 MIT 标签，未读条款；未确认的独立 Function Calling UI 无许可结论。
- **边界/重复**：Function Calling 是能力泛称；本次没有确认同名产品，也没有将 shinychat issue 升格为已发布的独立 UI 库。

## 078 · Toolbar UI for Agents

- **身份状态**：未确认；精确泛称缺少唯一项目映射。已读相关 `stagewise-io/stagewise` 和明确标注 fork 的 `21st-dev/21st-extension`。
- **实际查询词**：`"Toolbar UI for Agents"`；`"toolbar" "agents" stagewise github`。
- **实际读取 URL**：S17、S18；GitHub 页面打开失败后的 raw 回退见 F03。
- **读取层级**：D，当前 Stagewise 简介；21st 扩展 README 的 About、Features、连接故障提示及 License。
- **证据**：S17 当前自称 agentic IDE；S18 明示 fork 自 Stagewise，描述选中网页元素、附加评论、发送 DOM 元数据，并提示多编辑器窗口可能导致发送目标错位。
- **climber 工具调用 UI 建议**：工具条必须显示当前任务/会话目标；上下文附件用可移除标签呈现。把重试操作与展开按钮分开，审批或危险动作显示作用域。
- **许可证**：S18 README 明示 AGPLv3，未审阅完整条款；S17 仅见 AGPL-3.0 标签，未审阅条款。
- **边界/重复**：21st 与 Stagewise 的 fork 关系有正文证据，属于来源重叠，原名归属仍未确认；本批重复项计数维持 0，不把 fork 当成原名已定位的证明。

## 079 · Tool Result Viewer

- **身份状态**：未确认；检索命中工具结果组件描述，未确认同名独立产品。
- **实际查询词**：`"Tool Result Viewer" github`。
- **实际读取 URL**：S19 `PTFOPlayer/TinyHarness`；S20 该库 master 分支 raw README。错误分支尝试与回退见 F02。
- **读取层级**：D；实际读到 Features、Project Structure 和 CLI/工具输出相关段落，未读其结果渲染源码。
- **证据**：搜索摘要出现 `tool_output.rs Tool result viewer`；实际打开的仓库正文未找到该字符串。raw README 描述终端输出格式、diff、确认提示，并列出 `src/agent/tool_result.rs` 的格式化/批处理职责。缓存/版本差异只记录现象，旧文件路径未证实。
- **climber 工具调用 UI 建议**：在 C3 上按内容类型设计纯文本、JSON、表格、差异和文件产物视图；保留原始结果入口、截断说明、复制/下载权限与错误详情。该类型化方案是研究建议。
- **许可证**：S19 可见 MIT 标签，未审阅 LICENSE 条款；泛称原项目继续未核验。
- **边界/重复**：TinyHarness 为 Rust/终端 Agent 框架，仅作相关一手材料。没有安装、启动或接入它，也没有用搜索摘要证明结果查看器当前实现。

## 080 · MCP Browser UI

- **身份状态**：歧义；原名可能指浏览器客户端或浏览器自动化任务 UI。本次已读两个不同候选，均不能单凭泛称确定为原项目。
- **实际查询词**：`"MCP Browser UI"`；`"MCP Browser" github UI`。
- **实际读取 URL**：S21 `brainfuel/mcp-browser`；S22 `Saik0s/mcp-browser-use`。
- **读取层级**：D；S21 简介/Features；S22 Web UI 与 Web Dashboard 段。
- **证据**：S21 是 SwiftUI/WKWebView 原生 macOS 浏览器，README 描述工具操作日志包含参数、摘要和时间；S22 是 browser-use 的 MCP 包装，README 描述任务列表、进度、日志、历史筛选和错误详情。
- **climber 工具调用 UI 建议**：长任务卡持续显示调用标识、当前阶段、耗时和最新事件；详情抽屉连接同一调用的日志与结果。取消、重试和恢复按钮须先核验后端能力。
- **许可证**：S21、S22 的已读仓库页面均显示 MIT 标签；未审阅完整许可条款。
- **边界/重复**：两个候选各有独立仓库与定位；MCP 服务浏览器、真实网页浏览器、浏览器自动化服务分别记录。未将任何候选确定为用户原项目。

## 三条优先建议

1. **先统一调用状态和标识**：围绕 C1/C2 定义 call ID、queued/running/succeeded/failed/cancelled/awaiting-approval 等可用状态；按后端契约裁剪。覆盖空字符串结果、并行完成乱序与重试新调用，分离展开和重试按钮。参考 077、080。
2. **结果采用渐进式详情**：摘要行常驻，参数/结果/错误在详情内切换；纯文本与 JSON 先行，自有类型化视图逐步加入；schema 警告折叠但保留计数，原始结果始终可查。参考 071、072、075、079。
3. **分开来源、连接和权限**：C4 保留市场发现职责，另设连接健康与工具检查层；官方归属、发布者、版本和许可来源各自表达。富 UI 要有隔离和动作授权，工具集切换先展示差异。参考 073-076。

## 成功读取证据账本（23 个独立正文 URL）

以下均实际打开；记录的是已读范围，未声明完整审阅整个仓库。

| ID | URL | 层级与已读范围 |
| --- | --- | --- |
| S01 | https://github.com/modelcontextprotocol/inspector | D，根 README 简介、布局、分支说明 |
| S02 | https://github.com/modelcontextprotocol/inspector/blob/main/clients/web/README.md | D，组件分层、schema portability |
| S03 | https://raw.githubusercontent.com/modelcontextprotocol/docs/main/docs/tools/inspector.mdx | D，官方文档与仓库链接、Feature overview |
| S04 | https://raw.githubusercontent.com/modelcontextprotocol/inspector/main/clients/web/src/main.tsx | S，22 行入口源码 |
| S05 | https://raw.githubusercontent.com/modelcontextprotocol/inspector/main/core/json/schemaLint.ts | S，SchemaFinding、severity、路径及建议字段片段 |
| S06 | https://github.com/shroomlife/mcp-playground | D，简介、schema 表单、JSON-RPC trace、许可标签 |
| S07 | https://github.com/bighadj22/mcps-playground | D，简介、模型/服务器能力功能表 |
| S08 | https://www.himcp.cn/ | P，目录搜索、分类及条目标签 |
| S09 | https://github.com/sandraschi/mcp-studio | D，beta、工作集预览/备份、管理能力、许可标签 |
| S10 | https://raw.githubusercontent.com/RPieterse/mcp-studio-releases/main/README.md | D，发布库 README 全文，私有源码边界 |
| S11 | https://github.com/MCP-UI-Org/mcp-ui | D，SDK 身份、工具资源关联、Core Team、License |
| S12 | https://github.com/modelcontextprotocol/ext-apps | D，官方仓库身份、How It Works |
| S13 | https://github.com/agents-ui/agents-kit | D，当前组件族、示例状态、Provenance and licensing |
| S14 | https://raw.githubusercontent.com/agents-ui/agents-kit/main/LICENSE.md | 完整许可证，Non-Commercial License |
| S15 | https://github.com/posit-dev/shinychat/issues/31 | I，Tool calls in shinychat 设计讨论 |
| S16 | https://github.com/posit-dev/shinychat | D，Shiny 聊天组件简介、许可标签 |
| S17 | https://github.com/stagewise-io/stagewise | D，当前 agentic IDE 简介、许可标签 |
| S18 | https://raw.githubusercontent.com/21st-dev/21st-extension/main/README.md | D，fork 身份、toolbar、连接提示、License |
| S19 | https://github.com/PTFOPlayer/TinyHarness | D，框架简介、当前分支、工具说明、许可标签 |
| S20 | https://raw.githubusercontent.com/PTFOPlayer/TinyHarness/master/README.md | D，当前项目结构、终端输出与结果格式化职责 |
| S21 | https://github.com/brainfuel/mcp-browser | D，原生浏览器、工具动作日志、许可标签 |
| S22 | https://github.com/Saik0s/mcp-browser-use | D，Web UI、Web Dashboard、许可标签 |
| S23 | https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/ | D，官方扩展发布日期、作者、MCP-UI 关系、UI metadata 与隔离模型 |

## 失败、回退与未确认记录

| ID | 实际尝试 URL / 情况 | 回退与结论 |
| --- | --- | --- |
| F01 | https://rpieterse.github.io/mcp-studio-releases/docs.html 返回 Internal Error | 换 S10 raw README 一次成功；仅确认发布库与私有源码关系，未读取 docs.html 正文 |
| F02 | https://raw.githubusercontent.com/PTFOPlayer/TinyHarness/main/README.md 返回 Internal Error | 从 S19 确认默认分支为 master，再读取 S20 成功；失败 main 地址不作项目证据 |
| F03 | https://github.com/21st-dev/21st-extension 返回 Internal Error | 换 S18 raw README 一次成功；统计采用 S18 正文，失败请求不计成功 |
| F04 | 079 搜索摘要中的 tool_output.rs，在 S19 实际正文检索未命中 | S20 交叉读取显示另一套项目结构；原文件路径与独立 Viewer 身份保持未确认 |

未把搜索未命中等同于不存在；未把相关候选替代原名；未把阅读文档升级为运行验证。所有待确认身份都需要原清单提供 owner、仓库链接或截图来源后才能消歧。
