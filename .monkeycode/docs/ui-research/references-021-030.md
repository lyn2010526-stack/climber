# UI 资料核验：021–030

核验日期：2026-09-25。目标：Climber。本文件独立覆盖 021–030，结构参考 `references-001-020.md` 的已读部分。

## 核验口径

- 每项均完成实际联网搜索与至少一次项目仓库或明确标注候选的 README 正文读取；共覆盖 10/10 项。身份确认 7 项；身份歧义 3 项（027、028、029）；确认重复 0 项；完全无法定位 0 项。候选正文可读与原名身份确认分别统计。
- 搜索采用近一年时间范围，每项一次，029 另做一次精确 owner/repo 搜索。该范围及返回条数均有限，未命中只表示本次检索不足以确认身份，不证明项目不存在。部分搜索返回第三方索引；功能证据仍取自实际打开的仓库正文。
- 最高读取层级均为文档（README），源码 0 项。搜索用于定位与辨别同名项目，搜索摘要、第三方介绍和 fork 内容均未升级为功能实现证据。每项列出实际查询词与实际获取正文的 URL。
- 本批共读到 11 份 README 正文：十项各一份，027 额外读取另一同名仓库。029 首次请求返回 404，随后读取一份可访问候选；失败地址单独保留。未遇到 403。
- “官方文档”指项目作者仓库自述；Claude 候选为社区作者项目，该称谓不代表 Anthropic 官方产品。界面行为仅依据正文说明，未检查截图、组件源码或运行体验。
- 分支地址会变化，本次未固定 commit。日期表示本次访问日期；不据此断言某个版本为最新，也不将旧 README 的价格、模型能力或安全宣传当作当前事实。
- 许可证只记实际可见的声明；仅见 LICENSE 链接或动态徽章地址时记“未核验”。README 声明与完整许可条款审阅分开，本批未作法律适用判断。
- Climber 可采用点全部为建议，未核验或修改 Climber 的实现。保持桌面优先、兼容移动端及现有无登录前端方向；仅借鉴交互范式。
- 本批仅新增本文件；其他文档和代码保持原状，未安装或运行任何第三方 Agent、项目或 README 命令，未 commit/push。现有 `references-021-060.md` 未作为本批证据来源；本批与其他编号的全量去重仍有限。

## 021 · Open WebUI

- **原名**：Open WebUI。
- **身份状态**：确认；`open-webui/open-webui`。
- **实际查询词**：`Open WebUI github official`。
- **实际读取 URL**：https://raw.githubusercontent.com/open-webui/open-webui/main/README.md
- **读取层级**：文档（官方 README 的 Key Features、License）。
- **具体证据**：Live Workflow & Message Flow 描述实时清单以及回复进行中排队、完成后发送的消息；Notes 描述独立富文本笔记工作区和把笔记附到会话；Local RAG Integration 描述通过 `#` 从文档库选取资料。
- **Climber 可采用点（建议）**：把任务步骤与待发送消息分开呈现；排队消息提供可识别状态，并由后端决定实际发送时机。资料选择器展示本轮附加的笔记和文件，让上下文来源可检查。
- **许可证**：README 明示混合许可，包含 Open WebUI License 及保留 Open WebUI 品牌的额外要求，历史贡献遵循各自原许可；完整适用范围仍需另审 LICENSE/ LICENSE_HISTORY，本次仅读到其说明。
- **边界/去重**：本项以 Open WebUI 核心为证据；README 链接的终端、桌面程序等生态项目未分别核验或计数。实时清单与队列为文档自述。

## 022 · LibreChat

- **原名**：LibreChat。
- **身份状态**：确认；读取 `danny-avila/LibreChat` 原路径，正文中的 releases、贡献者等链接已指向 `LibreChat-AI/LibreChat`。
- **实际查询词**：`LibreChat github official`。
- **实际读取 URL**：https://raw.githubusercontent.com/danny-avila/LibreChat/main/README.md
- **读取层级**：文档（官方 README 的 What's New、Presets & Context Management、Code Artifacts、Resumable Streams）。
- **具体证据**：Trace Viewer 列出有序步骤、角色、Agent 身份、工具轮次、预览与费用；Agent activity 描述系统事件独立成轮次、实时活动保持一个稳定行；正文还列出编辑并重发消息、会话分支、断线重连续流，以及产物全屏预览和 Mermaid 导出。
- **Climber 可采用点（建议）**：使用稳定运行标识更新同一活动行，完成后收敛到执行记录；把角色、工具轮次和结果摘要放进可展开的任务轨迹。分支重试应保留原消息及其运行结果关联。
- **许可证**：未核验；实际打开的 README 未见许可正文。搜索返回的官方文档站条款摘要提及 MIT，但本次未打开该条款页，保留为搜索线索。
- **边界/去重**：断线续流与稳定活动行是文档声明，事件重放、幂等和重连细节未查看源码；保持建议与已验证实现的边界。

## 023 · LobeChat

- **原名**：LobeChat。
- **身份状态**：确认到原 `lobehub/lobe-chat` 仓库入口；本次实际返回 README 标题为 LobeHub，正文仓库链接指向 `lobehub/lobehub`。作为同一入口的名称演进记录，不增加一个项目计数。
- **实际查询词**：`LobeChat github official`。
- **实际读取 URL**：https://raw.githubusercontent.com/lobehub/lobe-chat/main/README.md
- **读取层级**：文档（官方 README 的 Features、Ecosystem、License）。
- **具体证据**：Collaborate 段将 Agent Groups、共享上下文的 Pages、Schedule、Project 和 Workspace 分开说明；Evolve 段写出结构化、可编辑的 White-Box Memory；Ecosystem 将 `@lobehub/ui` 单列为组件库。
- **Climber 可采用点（建议）**：以项目关联任务、产物与参与者，提供共享内容页及清晰归属信息；把用于当前任务的持久记忆做成可查看、可编辑的独立面板，并显示其作用范围。
- **许可证**：README 正文明示 LobeHub Community License；同文件徽章链接定义仍含 `license-apache 2.0` 字样。记录该内部不一致，以正文声明为本次所见，完整条款未读取。
- **边界/去重**：与 011 的候选 Lobe UI 属同一生态；本项为应用入口，011 为组件库，各自有独立 README。未把该生态联系直接认定为重复。

## 024 · NextChat

- **原名**：NextChat。
- **身份状态**：确认；`ChatGPTNextWeb/NextChat`。README 也保留 ChatGPT-Next-Web 的旧链接。
- **实际查询词**：`NextChat github official`。
- **实际读取 URL**：https://raw.githubusercontent.com/ChatGPTNextWeb/NextChat/main/README.md
- **读取层级**：文档（官方 README 的 Features、Roadmap、Environment Variables、LICENSE）。
- **具体证据**：Features 描述 prompt templates（mask）、流式响应和长会话历史压缩；Roadmap 的已勾选项描述在独立窗口预览、复制、分享产物；`CUSTOM_MODELS` 定义模型列表增减及展示名称映射。
- **Climber 可采用点（建议）**：新任务从可编辑模板启动，并展示模板带入的指令；正文与产物预览分区，保留返回来源消息的入口。模型显示名称与后端模型标识分别管理。
- **许可证**：MIT；实际读取的 README LICENSE 段明示。
- **边界/去重**：独立预览与上下文压缩来自文档；本地知识库在该 README Roadmap 中仍未勾选。Enterprise Edition 单独列示的权限与审计不外推为社区版已实现能力。

## 025 · Chatbot UI

- **原名**：Chatbot UI。
- **身份状态**：确认；`mckaywrigley/chatbot-ui`，README 标题及作者署名匹配。
- **实际查询词**：`Chatbot UI mckaywrigley github`。
- **实际读取 URL**：https://raw.githubusercontent.com/mckaywrigley/chatbot-ui/main/README.md
- **读取层级**：文档（官方 README 的 Legacy Code、Why Supabase、Fill in Secrets）。
- **具体证据**：README 区分当前 2.0 与 `legacy` 分支 1.0；说明持久化从浏览器存储转向 Supabase/Postgres；两处明确写出服务端设置 API Key 环境变量后，用户设置中的对应输入会被禁用。
- **Climber 可采用点（建议）**：对部署端管理的模型配置显示“由部署配置管理”来源说明，并禁用对应编辑入口；会话持久化采用明确的保存、失败和重试状态。后者是基于持久化需求提出的设计建议。
- **许可证**：未核验；实际打开的 README 未见许可名称或正文。
- **边界/去重**：更新段将移动布局改善与后端兼容列为待推进事项，未据此写成完成能力。未从 fork 的旧版 README 移植功能列表；不建议直接照搬该项目登录流程。

## 026 · BetterChatGPT

- **原名**：BetterChatGPT。
- **身份状态**：确认；`ztjhz/BetterChatGPT`，README 标题为 Better ChatGPT。
- **实际查询词**：`BetterChatGPT github ztjhz`。
- **实际读取 URL**：https://raw.githubusercontent.com/ztjhz/BetterChatGPT/main/README.md
- **读取层级**：文档（官方 README 的 Features）。
- **具体证据**：功能清单列出彩色会话文件夹、会话和文件夹筛选、token 数量与费用；支持编辑、重排和插入消息，选择 user/assistant/system 角色；列出 Markdown、图片、JSON 下载及本地自动保存。
- **Climber 可采用点（建议）**：桌面侧栏增加任务集合筛选与少量语义色；参数调试视图保留角色和消息顺序，清楚区分编辑草稿与实际已执行记录。导出入口明确格式和包含范围。
- **许可证**：未核验；README 仅出现 LICENSE 链接及动态许可徽章地址，本次未读取徽章图像或许可正文。
- **边界/去重**：保留本项目独立来源，不用它替代 Chatbot UI。第三方接入及区域限制相关内容仅见于 README，未执行、测试或采纳为 Climber 建议。

## 027 · chatgpt-web（描述 Go 后端须核验）

- **原名**：chatgpt-web（描述 Go 后端须核验）。
- **身份状态**：歧义；存在多个同名仓库。已定位并读取符合 Go 描述的 `869413421/chatgpt-web`，同时读取 `Chanzhaoyu/chatgpt-web` 作对照；原始清单未给 owner，保留身份未唯一确认。
- **实际查询词**：`chatgpt-web Go backend 869413421 github`。
- **实际读取 URL（Go 候选）**：https://raw.githubusercontent.com/869413421/chatgpt-web/main/README.md
- **实际读取 URL（同名对照）**：https://raw.githubusercontent.com/Chanzhaoyu/chatgpt-web/main/README.md
- **读取层级**：文档（两份作者 README）；Go 结论为文档级核验，未打开 Go 源码。
- **具体证据**：Go 候选“基于源码运行”明确写出 Go 语言与 `go run main.go`；功能表包含 AI 性格设定、Markdown、提问上下文；配置说明列出 `bot_desc`、模型、temperature、top_p 等参数。同名对照的 Backend Service 指向 `/service` 与 pnpm，手动部署正文明确写出 node 服务环境。
- **Climber 可采用点（建议）**：将角色描述、模型和生成参数组织成有说明的配置组，并在运行前展示本次有效配置摘要；对旧参数示例重新验证单位、取值和后端契约后再设计控件。
- **许可证**：Go 候选未核验到正式许可名称，实际 README 免责声明写出“代码仅用于演示和测试”及禁止商用提示。同名 Node 项目 README 明示 MIT，该声明仅适用于对照仓库，不转移给 Go 候选。
- **边界/去重**：Go 描述有明确候选证据；常见的 Chanzhaoyu 项目文档支持 Node 后端结论。二者分别保留 URL 与结论；UI 建议只使用 Go 候选明确列出的能力，未混入对照仓库的导入导出清单。

## 028 · Gemini-Next-Web

- **原名**：Gemini-Next-Web。
- **身份状态**：歧义；精确名称搜索未确认同名独立官方仓库，返回近名 Gemini Next Chat 线索。实际读取 `u14app/gemini-next-chat` 入口，正文标题现为 Neo Chat，并明确将原 Gemini-only 项目指向 `gemini-next-chat` 归档分支。
- **实际查询词**：`"Gemini-Next-Web" github`。
- **实际读取 URL（近名候选）**：https://raw.githubusercontent.com/u14app/gemini-next-chat/main/README.md
- **读取层级**：文档（候选 README）；原名定位停留在搜索层。
- **具体证据（仅候选现有正文）**：Why Neo Chat 描述可审阅研究计划、带引用报告、手动恢复、可编辑产物和 ZIP 备份；Your data 说明执行由前台编排，关页会中断，保存的运行需显式恢复；备份排除凭据及部分 Research 扩展数据。
- **Climber 可采用点（建议）**：长任务明确区分运行中、连接中断、已保存与可恢复；恢复入口说明前置条件；研究产物绑定来源引用。备份/导出操作直接展示包含及排除的数据范围。
- **许可证**：仅候选当前 README 明示 MIT；不把该结论写成原名 Gemini-Next-Web 的许可证。
- **边界/去重**：没有使用 024 NextChat 的 README 冒充本项。近名候选与原名的身份关系仍待原始清单补充；归档分支仅见链接，本次未打开，未将 Neo Chat 功能外推为历史 Gemini-only 分支功能。

## 029 · Claude Web UI

- **原名**：Claude Web UI。
- **身份状态**：歧义；名称同时可指多个社区 Web UI。实际读取候选为 `ArjunDivecha/claude-web-ui`，正文标题为 Arjun Claude；其安装段 clone 地址又指向另一 owner 的 `arjun-claude`，原始来源关系尚未确认。
- **实际查询词**：`"Claude Web UI" github`；补充精确核对 `"ArjunDivecha/claude-web-ui"`。
- **搜索限制**：通用查询返回多个 Claude Code Web UI；补充精确查询仍返回其他项目/包的结果，未建立候选归属证据。可访问候选正文与原名身份关系分别记录。
- **实际请求 URL（失败）**：https://raw.githubusercontent.com/sugamax/claude-webui/main/README.md
- **失败表现**：HTTP 404；该首次候选路径未获正文，无法据此确认项目存在或功能。
- **实际读取 URL（可访问候选）**：https://raw.githubusercontent.com/ArjunDivecha/claude-web-ui/main/README.md
- **读取层级**：文档（可访问候选 README）；另有失败层记录。
- **具体证据（仅候选）**：Features、Usage 描述 temperature 和 thinking budget 滑块；右侧面板放置模型返回的 thinking 展示与指标；指标包含输入/输出 token、响应耗时和单次/累计费用；Reset Chat 后累计费用继续保留至应用重启。
- **Climber 可采用点（建议）**：把回答正文与运行指标分区，费用和耗时明确标注单次或累计口径；重置会话时告知哪些统计仍被保留。仅展示后端实际提供且允许展示的推理摘要或状态。
- **许可证**：候选 README License 段写出 MIT；完整条款及候选上游关系未核验，结论仅属于所读候选声明。
- **边界/去重**：搜索还出现其他 Claude Code Web UI，本项未把它们的功能并入候选。README 的模型、预算和计费示例可能过时，未作为当前 API 能力或价格依据；不将第三方 thinking 宣传当作模型内部推理可见性的保证。

## 030 · Oobabooga

- **原名**：Oobabooga。
- **身份状态**：确认到社区通常以作者名指代的 `oobabooga/text-generation-webui` 入口；本次 README 标题为 TextGen，正文仓库链接为 `oobabooga/textgen`。保留作者昵称与实际产品名称的区别。
- **实际查询词**：`Oobabooga text generation webui github`。
- **实际读取 URL**：https://raw.githubusercontent.com/oobabooga/text-generation-webui/main/README.md
- **读取层级**：文档（官方 README 的 Chat & generation、Backends & API、命令行参数说明）。
- **具体证据**：正文区分 instruct、chat-instruct、chat 模式，描述消息编辑、消息版本切换、任意位置分支及独立 Notebook 文本生成页；后端与模型可切换；`--multi-user` 的说明明确该模式不保存或自动加载聊天历史。
- **Climber 可采用点（建议）**：为消息编辑及重新生成提供版本导航和分支来源；将自由文本产物编辑与对话轮次分区。运行模式变化时清晰显示持久化行为和可用能力的变化。
- **许可证**：未核验；实际打开的 README 自述开源，但未见具体许可名称或条款；不凭历史印象补写许可。
- **边界/去重**：本次只读项目自述，未运行本地模型、工具、扩展或 Agent。TextGen、text-generation-webui 与作者昵称只计本项一次，未把仓库改名计成新增项目。

## 对 Climber 的优先建议

1. **稳定运行状态与任务轨迹**：参考 021 的实时清单、022 的稳定活动行和轨迹字段；先定义运行、步骤、工具轮次与结果的标识，再验证队列和断线状态。
2. **正文与产物分区**：参考 024 的独立产物预览、022 的全屏与导出入口；桌面采用可展开结果区域，始终保留产物对应的消息和任务来源。
3. **上下文与配置可检查**：参考 024 的模板、025 的部署管理输入状态、027 的有效参数；新任务启动前显示模板与配置来源，并区分可编辑和部署锁定字段。

以上均为研究建议；本批只交付证据文档，不代表 Climber 已实现、已测试或已采用。
