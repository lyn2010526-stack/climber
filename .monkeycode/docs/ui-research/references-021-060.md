# UI 资料核验：021–060

核验日期：2026-09-25。目标：Climber。范围：用户清单 021–060。

## 核验口径

- 已读取 `.monkeycode/MEMORY.md` 全文和 `references-001-020.md` 第 1–200 行，沿用其逐项证据结构。本批只新增本文件；应用、已有文档、记忆文件均保持原样；没有 commit/push、安装依赖、安装或运行第三方 Agent。
- URL 通过真实联网打开读取；搜索只用于定位。每项标明实际可见的正文段落，未把链接列表、截图占位符或搜索摘要当成已读实现。未运行远端产品、演示或测试，未复制源码、图标和品牌资产。
- “官方文档”包括仓库作者自己的 README；它表示材料来源，与某商业组织的官方背书分开判断。“确认”可以是确认到主项目中的 UI 子功能，并在边界里说明。
- 所有“Climber 可采用点”均为研究建议。本批没有复核 Climber 应用源码或运行状态，因此没有新增任何“Climber 已实现”声明；记忆和旧报告中的实现、测试结论也没有升级为本批验证结果。
- 保持桌面优先、无新增登录流程、克制视觉。建议中的停止、恢复、审批、回放等操作必须先核对 Climber 后端契约，界面仅呈现真实可用动作。
- 许可证只记录本次可见正文或明示徽章；只有 LICENSE 链接而未见许可名称时写“未核验”。未逐条审查许可条款，不作法律结论。
- 默认分支会变化；访问日期表示本次取证日期，联网工具可能使用缓存，未锁定提交或证明内容在该日期之前的历史版本。历史标签另标明。无 stars 数字、热度排名和未经验证的最新版本判断。

## 021 · Open WebUI

- **原名**：Open WebUI。
- **身份状态**：确认；`open-webui/open-webui`。
- **定位方式**：直接打开精确仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/open-webui/open-webui/main/README.md
- **读取层级与具体证据**：官方文档，Key Features、连接排错、License；支持 Ollama 与 OpenAI-compatible API，模型可绑定指令/工具/知识，文档列出实时 checklist 和响应期间消息排队；排错明确容器访问宿主 Ollama 的连接问题。
- **Climber 可采用点（建议）**：提供“服务可达、凭据有效、模型可用”分层前置检测；发送中显示稳定任务状态行，排队消息单独标识。
- **许可证**：README 明示多许可证构成，包含要求保留 Open WebUI 品牌的 Open WebUI License 和历史贡献原许可；未读完整 LICENSE/HISTORY，禁止简化为 MIT。
- **边界/去重**：034 的历史标题确认属于本项目旧名，见该项；本项未实测自动发现、任务队列或工具运行。

## 022 · LibreChat

- **原名**：LibreChat。
- **身份状态**：确认；`danny-avila/LibreChat`。
- **定位方式**：直接读取仓库 README。
- **实际读取 URL**：https://raw.githubusercontent.com/danny-avila/LibreChat/main/README.md
- **读取层级与具体证据**：官方文档，What's New、Features；Trace Viewer 按角色、Agent、工具轮次、预览和费用展示有序步骤；活动保持单一稳定行；列出模型搜索虚拟化、会话分叉和流式 Markdown。
- **Climber 可采用点（建议）**：任务活动行与详细 trace 分层；用 run/message/tool-call 标识关联结果；大型模型列表加搜索和分组，先验证实际列表规模再决定虚拟化。
- **许可证**：未核验，已读范围未见明确许可名称。
- **边界/去重**：所读 README 将 attached workspaces 标为高度实验性；版本标题仅为所读材料标识，未判断最新版本。

## 023 · LobeChat

- **原名**：LobeChat。
- **身份状态**：确认到 `lobehub/lobe-chat` 路径现有 LobeHub 文档。
- **定位方式**：打开原仓库路径，读取 Features、Plugins、License。
- **实际读取 URL**：https://raw.githubusercontent.com/lobehub/lobe-chat/main/README.md
- **读取层级与具体证据**：官方文档；当前正文使用 LobeHub 名称，区分 Pages、Schedule、Project、Workspace；memory 描述为结构化可编辑；插件扩展 function calling 和消息结果呈现。
- **Climber 可采用点（建议）**：工作区内将会话、任务产物和运行历史区分；提供可检查的上下文来源，结果卡由 Climber 自有组件实现。
- **许可证**：README 末尾明示 LobeHub Community License；未读取完整条款。
- **边界/去重**：001–020 的 011 为 UI 组件库候选；本项为应用。当前正文不能直接证明旧版 LobeChat 的全部行为。

## 024 · NextChat

- **原名**：NextChat。
- **身份状态**：确认；`ChatGPTNextWeb/NextChat`。
- **定位方式**：直接读取 README 的 Features、Roadmap。
- **实际读取 URL**：https://raw.githubusercontent.com/ChatGPTNextWeb/NextChat/main/README.md
- **读取层级与具体证据**：官方文档；列出流式响应、浏览器本地存储、mask 提示模板、自动压缩历史；Artifacts 独立窗口在 Roadmap 标为完成，本地知识库仍未勾选。
- **Climber 可采用点（建议）**：产物预览与对话分栏；压缩上下文前后保留明确提示与来源边界；模板作为可编辑起点。
- **许可证**：未核验，已读范围未见许可名称。
- **边界/去重**：企业版权限、审计描述独立于社区功能表；不混算。028 与其界面描述相似，保持独立候选证据。

## 025 · Chatbot UI

- **原名**：Chatbot UI。
- **身份状态**：确认；`mckaywrigley/chatbot-ui`。
- **定位方式**：读取仓库 README 的本地部署与 Secrets。
- **实际读取 URL**：https://raw.githubusercontent.com/mckaywrigley/chatbot-ui/main/README.md
- **读取层级与具体证据**：官方文档；解释由浏览器存储转到 Supabase 的动机；明确配置环境变量后会禁用设置页对应输入；Ollama URL 为可选本地模型配置。
- **Climber 可采用点（建议）**：配置项显示“环境配置/用户设置”的来源与覆盖关系；禁用字段同时解释原因，前置检测区分数据库、模型端点与凭据。
- **许可证**：未核验，已读范围未见明确许可。
- **边界/去重**：只借鉴配置可解释性；文档中的认证部署流程不作为 Climber 新增登录的建议。

## 026 · BetterChatGPT

- **原名**：BetterChatGPT。
- **身份状态**：确认；`ztjhz/BetterChatGPT`。
- **定位方式**：读取 README 的 Features、Usage。
- **实际读取 URL**：https://raw.githubusercontent.com/ztjhz/BetterChatGPT/main/README.md
- **读取层级与具体证据**：官方文档；聊天文件夹与过滤、token/价格显示、消息编辑/重排/插入、自动本地保存、Markdown/JSON 导出。
- **Climber 可采用点（建议）**：用搜索和语义化分组整理历史；运行费用标明估算或结算来源；编辑历史应分叉并保留原始执行记录。
- **许可证**：未核验，README 已见动态许可徽章链接，但可见文本没有名称。
- **边界/去重**：价格和免费服务描述未经核验；不采纳其中绕过区域限制的建议，也未访问或执行相关服务。

## 027 · chatgpt-web（用户描述 Go 后端）

- **原名**：chatgpt-web（Go 后端）。
- **身份状态**：确认到符合 Go 描述的 `869413421/chatgpt-web`；泛称仍存在同名项目。
- **实际查询词**：`github "chatgpt-web" "Go" backend`；`"chatgpt-web" "golang" github`；`"chatgpt-web" "Go后端"`；`chatgpt web golang backend github Go`。前几次结果未唯一定位，最后找到 Go 包线索后读取仓库。
- **实际读取 URL**：https://raw.githubusercontent.com/869413421/chatgpt-web/main/README.md
- **读取层级与具体证据**：官方文档；源码运行段明确 `go run main.go`；配置示例有 model、api_url、max_tokens、temperature；功能列出 Markdown、上下文和可配置参数。
- **Climber 可采用点（建议）**：启动前展示必填配置缺口；常用参数与高级采样参数分组，保留重置入口和说明。
- **许可证**：未核验；未用搜索摘要中的许可替代正文证据。
- **边界/去重**：不以常见 Node 项目 Chanzhaoyu/chatgpt-web 代替 Go 描述；所读更新记录主要来自 2023 年，现代工具调用与 trace 未在本次材料确认。

## 028 · Gemini-Next-Web

- **原名**：Gemini-Next-Web。
- **身份状态**：确认；`blacksev/Gemini-Next-Web`。
- **定位方式**：直接读取名称对应 README。
- **实际读取 URL**：https://raw.githubusercontent.com/blacksev/Gemini-Next-Web/main/README.md
- **读取层级与具体证据**：官方文档，Features、开发计划、最新动态；自述 Gemini Pro/Pro Vision 的流式对话和图片识别；模板、本地历史与压缩列于功能表，插件机制仍未勾选。
- **Climber 可采用点（建议）**：模型列表明确文本/图片/工具能力；附件入口由模型能力驱动，并提示不支持的原因。
- **许可证**：未核验，已读段落未见名称。
- **边界/去重**：文本含大量与 NextChat 相似的功能描述，本批未核查 fork 元数据，不宣布重复；旧模型名仅作历史文档证据。

## 029 · Claude Web UI

- **原名**：Claude Web UI。
- **身份状态**：歧义；已读候选 `matalvernaz/claude-web`，用户原名无法唯一定位。
- **实际查询词**：`github "Claude Web UI"`。
- **实际读取 URL（候选）**：https://raw.githubusercontent.com/matalvernaz/claude-web/main/README.md
- **读取层级与具体证据**：官方文档（候选 README 首段与 Trust model）；SSE 同时传文本和工具调用，每次调用有单次允许/会话允许/拒绝，复用 CLI JSONL 会话。明确工具按服务进程权限执行，审批并未提供沙箱隔离。
- **Climber 可采用点（建议）**：工具确认卡展示参数、作用域和授权持续时间；用户决定绑定 call ID，执行结果独立更新。
- **许可证**：未核验。
- **边界/去重**：候选是 Claude Code 的社区界面，Anthropic 官方产品身份未确认；没有安装、运行 CLI 或候选应用。

## 030 · Oobabooga

- **原名**：Oobabooga。
- **身份状态**：确认到通常所指的 `oobabooga/text-generation-webui`；保留用户拼写，仓库 owner 拼作 oobabooga。
- **定位方式**：直接读取对应仓库旧路径的 README。
- **实际读取 URL**：https://raw.githubusercontent.com/oobabooga/text-generation-webui/main/README.md
- **读取层级与具体证据**：官方文档；所读标题已为 TextGen，内部指向 `oobabooga/textgen`；列出消息版本切换、会话分叉、多后端/模型切换、工具调用、GGUF 文件放入模型目录后自动发现。
- **Climber 可采用点（建议）**：模型就绪与下载/发现状态分开；切换模型时保留会话与提示模板信息，暴露能力差异。
- **许可证**：未核验，已读范围未见名称。
- **边界/去重**：035 对应同一仓库，作为重复记录；桌面入口和浏览器安装入口在同一 README 中分别说明。

## 031 · SillyTavern

- **原名**：SillyTavern。
- **身份状态**：确认；`SillyTavern/SillyTavern`。
- **定位方式**：README 指向文档站，再实际打开首页。
- **实际读取 URL**：https://raw.githubusercontent.com/SillyTavern/SillyTavern/release/README.md
- **实际读取 URL（文档）**：https://docs.sillytavern.app/
- **读取层级与具体证据**：官方文档，What do I need、Character Cards、Key Features；界面依赖独立推理后端，角色卡保存提示配置；欢迎页可直接输入以检查连接；支持群聊与生成设置。
- **Climber 可采用点（建议）**：空状态给出最小连接测试；Agent 角色以可审查配置卡表达，群聊消息保留发言者和所属任务。
- **许可证**：AGPL-3.0；README 与文档 License 明示。
- **边界/去重**：仅取可用性与配置范式；主题背景、角色素材及娱乐化装饰不纳入 Climber 建议。

## 032 · Jan

- **原名**：Jan。
- **身份状态**：确认；`janhq/jan`。
- **定位方式**：读取仓库 README Features。
- **实际读取 URL**：https://raw.githubusercontent.com/janhq/jan/main/README.md
- **读取层级与具体证据**：官方文档；本地模型下载、云提供商接入、自定义助手、本地 OpenAI-compatible API 及 MCP 分列。
- **Climber 可采用点（建议）**：模型列表区分本地和云端来源；配置检测区分服务启动、模型加载与网络权限；下载进度与运行进度各自显示。
- **许可证**：未核验，已读范围未见明确许可名称。
- **边界/去重**：本项是桌面应用参考，未确认为同名独立浏览器 UI 项目。

## 033 · LM Studio Web UI

- **原名**：LM Studio Web UI。
- **身份状态**：歧义；已读候选 `nicholasegurley/docker-simple-LMStudio-web-ui`。
- **实际查询词**：`github "LM Studio Web UI"`；`"LM Studio" "web ui" github`。
- **实际读取 URL（候选）**：https://raw.githubusercontent.com/nicholasegurley/docker-simple-LMStudio-web-ui/main/README.md
- **读取层级与具体证据**：官方文档（候选 README）；开头明确 unofficial、personal project，与 LM Studio 无隶属或背书关系；列出动态刷新模型、persona、持久会话、复制反馈。
- **Climber 可采用点（建议）**：模型列表提供刷新、加载中、空列表和连接错误的独立状态；复制结果给短暂文字反馈。
- **许可证**：未核验，已读范围未见许可名称。
- **边界/去重**：LM Studio 本体和第三方 Web 前端分开记录；本次没有确认“LM Studio 官方 Web UI”身份。

## 034 · Ollama Web UI

- **原名**：Ollama Web UI。
- **身份状态**：重复；按已读原作者历史材料，属于 021 Open WebUI 的旧名。
- **实际查询词**：`Open WebUI formerly Ollama WebUI official`；随后直接打开历史标签。
- **实际读取 URL（历史）**：https://raw.githubusercontent.com/open-webui/open-webui/v0.1.102/README.md
- **读取层级与具体证据**：官方历史 README；标题直接写明 `Open WebUI (Formerly Ollama WebUI)`，Features 描述聊天输入的 `#` 文档和 `/` 提示预设。
- **Climber 可采用点（建议）**：输入区用明确触发字符打开带标签的上下文选择器，已选择资料以可移除条目呈现。
- **许可证**：本历史版本未核验；当前版本许可信息见 021，不能跨版本互推。
- **边界/去重**：不计为新增独立项目；若原名另指其他 Ollama 前端，仍需具体仓库来区分。

## 035 · Text Generation WebUI

- **原名**：Text Generation WebUI。
- **身份状态**：重复；与 030 对应同一个 `oobabooga/text-generation-webui`。
- **定位方式**：共用本次实际读取的同仓库正文，而非依据名称相似。
- **实际读取 URL**：https://raw.githubusercontent.com/oobabooga/text-generation-webui/main/README.md
- **读取层级与具体证据**：官方文档；标题 TextGen，Installation 明确浏览器 Web UI 入口，Features 中有 Notebook 自由生成和 Chat 多种模式。
- **Climber 可采用点（建议）**：模式切换应解释输入与上下文差异；默认保持单一任务对话，专业生成选项折叠。
- **许可证**：未核验。
- **边界/去重**：与 030 共用 200-word 来源摘要预算，未重复计算独立项目。

## 036 · FastChat Web UI

- **原名**：FastChat Web UI。
- **身份状态**：确认到 `lm-sys/FastChat` 的 Web GUI 子功能。
- **定位方式**：读取 README Serving with Web GUI、Chatbot Arena。
- **实际读取 URL**：https://raw.githubusercontent.com/lm-sys/FastChat/main/README.md
- **读取层级与具体证据**：官方文档；部署分 controller、model worker、Gradio web server；要求 worker 加载完成并注册后检查；另有并排模型比较 UI。
- **Climber 可采用点（建议）**：依赖检测显示调度端、执行端、模型各自健康；列表缺模型时提供针对性诊断，避免只显示通用失败。
- **许可证**：未核验；README 出现的 Llama 模型许可不当作 FastChat 应用许可。
- **边界/去重**：评测 UI 与任务编排用途分别处理；未启动任何 worker 或测试请求。

## 037 · Quivr UI

- **原名**：Quivr UI。
- **身份状态**：歧义；确认主项目 `QuivrHQ/quivr`，当前 README 主要说明 quivr-core，独立 UI/版本未唯一确认。
- **定位方式**：读取主仓库 README，并核查其当前产品范围。
- **实际读取 URL**：https://raw.githubusercontent.com/QuivrHQ/quivr/main/README.md
- **读取层级与具体证据**：官方文档（主项目候选）；正文称其为 Quivr.com 的 core；YAML workflow 区分 filter_history、rewrite、retrieve、generate_rag，末节点用于流式回答，包含重排配置。
- **Climber 可采用点（建议）**：知识问答 trace 可显示重写、检索、重排和生成阶段；结果保留来源与配置版本。
- **许可证**：Apache 2.0，主仓库 README License 明示；未确认的独立 UI 不继承此结论。
- **边界/去重**：未将核心库的终端示例描述成浏览器可视界面；UI 交互仍未确认。

## 038 · AnythingLLM

- **原名**：AnythingLLM。
- **身份状态**：确认；`Mintplex-Labs/anything-llm`。
- **定位方式**：读取 README Product Overview、Cool Features。
- **实际读取 URL**：https://raw.githubusercontent.com/Mintplex-Labs/anything-llm/master/README.md
- **读取层级与具体证据**：官方文档；按 workspace 使用文档和 Agent；拖放上传与来源引用；列出模型路由、MCP、计划任务；多用户和可嵌入 widget 标注 Docker-only。
- **Climber 可采用点（建议）**：把上传、解析、索引、可检索分为状态；回答引用可回到资料；显示路由实际选中的模型。
- **许可证**：未核验，已读范围未见许可名称。
- **边界/去重**：桌面与 Docker 能力范围按正文分别记录；性能和生产质量宣传未验证。

## 039 · Dify

- **原名**：Dify。
- **身份状态**：确认；`langgenius/dify`。
- **定位方式**：读取 README 平台介绍、Quick start、Key features。
- **实际读取 URL**：https://raw.githubusercontent.com/langgenius/dify/main/README.md
- **读取层级与具体证据**：官方文档；模型管理、可观测性、可视化 workflow 及测试、Prompt IDE、RAG ingestion 分别介绍；部署列出资源与 Compose 前置条件。
- **Climber 可采用点（建议）**：编辑态配置校验与运行态追踪独立；模型、知识库、工具缺配置时给具体修复入口；节点状态以文字/图标并用。
- **许可证**：未核验，所读段落未见完整许可名称或条款。
- **边界/去重**：没有从平台功能概述推断节点事件协议或已验证生产可靠性。

## 040 · Flowise AI UI

- **原名**：Flowise AI UI。
- **身份状态**：确认到 `FlowiseAI/Flowise` 的 React UI。
- **定位方式**：读取 README 顶部与 Developers。
- **实际读取 URL**：https://raw.githubusercontent.com/FlowiseAI/Flowise/main/README.md
- **读取层级与具体证据**：官方文档；标题说明可视化构建 Agent，结构分 server、ui、components 和 API 文档；本次正文顶部出现 `Flowise has been archived` 并给讨论入口。
- **Climber 可采用点（建议）**：节点定义、画布表现和执行事件适配分层；组件参数缺失要在提交前就地提示，视觉强调错误和运行焦点。
- **许可证**：未核验，已读范围仅见 License 目录项。
- **边界/去重**：归档仅记录本次 README 自述，未打开讨论核对时间和后续维护安排；本批把它作为交互资料，不推荐直接引入运行时。
