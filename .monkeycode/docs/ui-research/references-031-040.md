# UI 参考研究 031–040

研究日期：2026-09-25。范围：用户给定的 10 个原名；每项均独立联网搜索，并实际打开项目所有者的 README 或官方文档。

## 研究口径

- 本文件为独立复核批次，仅新增本文件；既有 `references-021-060.md` 只用于候选发现及 021、030 的编号对照，正文证据均在本轮重新联网读取。
- 层级定义：**源码**为实际实现文件；**文档**为 README、官方说明、条款及明确标注的仓库元数据；**搜索**为检索结果摘要；**失败**为访问未返回可用正文。本轮主要达到文档层，没有把 README 内代码示例或图片链接算作已读实现源码或已审阅截图。
- 搜索记录包含实际查询词及搜索工具 request_id。第三方检索结果仅作定位线索，产品事实以列出的第一方正文为据。候选作者自己的仓库文档属于候选的一手资料，其官方性范围止于该候选。
- `main`、`master`、`release` 为访问时浮动分支；034 的 `v0.1.102` 为固定历史标签。本轮没有保存 commit 快照，结论代表访问时读到的内容。
- 状态分布：确认 6 项，歧义 2 项，重复 2 项，纯未确认 0 项。歧义项仍有部分身份未确认；覆盖 10 项与确认 10 个独立开源 Web UI 是不同统计口径。
- 许可证仅登记实际看见的名称及适用范围；没有看见名称时字段留空并说明。本文件提供观察记录，代码复用前仍需审阅目标版本完整许可。
- Climber 建议依据本地 README 的本地优先、多 Agent、模型调度、任务恢复和可观测性定位，以及已有桌面优先、无登录、只借鉴交互范式的协作约束。所有“建议”均为本次设计推导，实施状态为未实施。
- 全程仅检索、阅读和写文档；未安装、运行第三方 Agent，未启动所研究应用，未 commit/push。

## 031 · SillyTavern

- **编号 / 原名**：31 / SillyTavern。
- **身份状态**：确认，项目为 `SillyTavern/SillyTavern`；定位是依赖独立推理后端的本地 LLM 界面。
- **真实搜索**：`SillyTavern official github SillyTavern README`；request_id `421010`，返回官方文档首页。
- **实际读取 URL A / 层级**：https://raw.githubusercontent.com/SillyTavern/SillyTavern/release/README.md ，文档，成功。
- **实际读取 URL B / 层级**：https://docs.sillytavern.app/ ，文档，成功。
- **具体证据**：A 将产品定位为高级用户的 LLM 前端并链接 B。B 的 Character Cards 说明角色卡保存行为提示配置；欢迎页输入可直接测试连接并创建空白 Assistant。Key Features 列出生成参数、群聊和文档 RAG；后端依赖在单独章节解释。
- **用于 Climber 的设计建议**：首次进入会话时提供一条最小连接测试；Agent 卡片展示职责、模型和提示配置摘要，允许之后完善。多 Agent 发言持续显示 Agent 名与任务归属，把高级生成参数收进可展开配置区。
- **许可证**：AGPL-3.0；A 的 License 和 B 的 License 均明确写出该名称。
- **边界 / 去重**：确认的是 SillyTavern 独立项目；角色素材、背景图和第三方扩展均未审阅。建议限于配置与会话范式，素材和源码复用另行核验。
- **失败 / 替代读取**：无访问失败；A 较简短，因此继续打开其指向的 B 获取交互证据。

## 032 · Jan

- **编号 / 原名**：32 / Jan。
- **身份状态**：确认，项目为 `janhq/jan`；本次确认的交付形态是跨平台桌面应用。独立同名浏览器 UI 没有得到确认。
- **真实搜索**：`Jan janhq jan github open source desktop`；request_id `421011`。检索返回第三方介绍，身份及能力采用以下官方 README 核验。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/janhq/jan/main/README.md ，文档，成功。
- **具体证据**：Installation 列出各桌面平台安装包；Features 分别说明本地模型下载运行、云供应商连接、自定义助手、本地兼容 API 服务和 MCP。Build from Source 提到 Tauri；License 段明确许可名称。
- **用于 Climber 的设计建议**：模型选择器同时标注模型名、供应商及本地/远程来源；连接检测分开显示服务可达、模型已加载、工具可用。Agent 配置与底层模型配置各有明确入口，避免切换模型时误以为助手职责也被重置。
- **许可证**：Apache 2.0；依据本轮 README 的 License 段。
- **边界 / 去重**：作为桌面产品交互参考计入确认项；其本地运行能力和可选云连接分别记录，具体请求的数据去向应随配置展示。README 的兼容声明没有经过运行验证。
- **失败 / 替代读取**：无访问失败；本轮直接读取官方 raw README。

## 033 · LM Studio Web UI

- **编号 / 原名**：33 / LM Studio Web UI。
- **身份状态**：歧义；“官方独立开源 Web UI”未确认。已确认 LM Studio 桌面本体及一个明确声明非官方的第三方浏览器前端候选，两者分开归档。
- **真实搜索**：`"LM Studio Web UI" github`；request_id `421004`。结果包含语音前端、插件和扩展等不同对象，原名无法唯一映射；下面的第三方候选来自既有研究线索，本轮重新打开正文。
- **实际读取 URL A / 层级**：https://lmstudio.ai/docs/app ，文档，成功；用于核实官方应用与服务接口的定位。
- **实际读取 URL B / 层级**：https://lmstudio.ai/terms ，文档，成功；正文为桌面应用条款，标明版本 2026-08-23。
- **实际读取 URL C / 层级**：https://raw.githubusercontent.com/nicholasegurley/docker-simple-LMStudio-web-ui/main/README.md ，文档，成功；一手归属为候选作者，非 LM Studio 官方。
- **具体证据**：A 说明桌面安装包、模型管理和本地 API。B 的授权、使用限制与权利归属章节提供专有桌面软件许可依据；本体按闭源/专有桌面产品处理。C 开头明确个人、非官方及无隶属/背书关系；列出模型刷新、persona、持久会话和复制反馈，并在 Usage 描述历史侧栏、主对话区和底部输入区。
- **用于 Climber 的设计建议**：模型列表刷新后分别呈现成功、空列表和连接失败状态；保存 Base URL 前提供连接测试。复制响应给短暂文字反馈；会话历史与当前任务分区，配置抽屉中明确上下文范围。
- **许可证**：候选 C 的 README License 明示 MIT，仅适用于该第三方仓库；LM Studio 本体为上述自有桌面服务条款。官方开源 Web UI 的许可证字段保留未确认状态。
- **边界 / 去重**：C 的开源许可与 LM Studio 本体分别登记；SDK、CLI 或文档公开也各自属于独立范围。本项保留歧义身份，正式采用前需锁定原清单所指 owner/repo。
- **失败 / 替代读取**：https://lmstudio.ai/docs 返回 `307`，层级为失败，未取得该请求正文；随后改读 A 成功，完成一次官方文档替代尝试。

## 034 · Ollama Web UI

- **编号 / 原名**：34 / Ollama Web UI。
- **身份状态**：重复；按本轮官方历史证据，应与既有 021 Open WebUI 合并计数，旧名书写为 Ollama WebUI。
- **真实搜索**：`Open WebUI formerly Ollama WebUI official github`；request_id `421012`。搜索结果仅作线索，结论由固定历史 README 确认。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/open-webui/open-webui/v0.1.102/README.md ，文档，成功；读取的是历史版本。
- **具体证据**：标题明确为 `Open WebUI (Formerly Ollama WebUI)`；迁移章节进一步说明名称、镜像和原数据的迁移关系。Features 描述 `#` 选择文档/网页上下文、`/` 选择提示预设，以及会话标签和再生成历史。
- **用于 Climber 的设计建议**：输入框提供带类型标签的上下文选择器；已选文档以可移除条目展示，发送前看得见作用范围。任务提示模板与资料引用分成不同入口，并保留键盘触发方式和可发现的按钮入口。
- **许可证**：MIT；仅依据已读 `v0.1.102` README 的 License 段，适用范围为该历史版本的文档声明。当前版本许可未在本项重新核验。
- **边界 / 去重**：该历史项目与 Open WebUI 是同一产品谱系，不增加独立产品数。若原名泛指其他 Ollama 前端，需另给明确仓库。历史功能描述保留版本标签；当前版本能力需另核验。
- **失败 / 替代读取**：无访问失败；直接读取官方 raw 历史标签并成功取得正文。

## 035 · Text Generation WebUI

- **编号 / 原名**：35 / Text Generation WebUI。
- **身份状态**：重复；与既有 030 Oobabooga 对应同一仓库谱系。用户原名保留，当前仓库显示 TextGen。
- **真实搜索**：`Text Generation WebUI oobabooga official github TextGen`；request_id `421024`。搜索返回旧仓库名称线索，另直接打开以下官方仓库入口核验当前归属。
- **实际读取 URL A / 层级**：https://raw.githubusercontent.com/oobabooga/text-generation-webui/main/README.md ，文档，成功。
- **实际读取 URL B / 层级**：https://github.com/oobabooga/text-generation-webui ，文档/仓库元数据，成功；实际重定向到 https://github.com/oobabooga/textgen 。
- **具体证据**：A 标题为 TextGen，安装及文档链接采用 `oobabooga/textgen`；B 的实际重定向与仓库标题提供同仓库连续性证据。README 列出消息编辑、版本切换、会话分叉和 Notebook；Installation 明确保留浏览器运行方式，顶部介绍同时包含桌面形态。
- **用于 Climber 的设计建议**：把重试结果组织为同一节点/消息的版本；从检查点分叉时展示父任务、起点和配置差异。默认任务对话保持简洁，实验性自由生成模式以独立标签进入，并说明上下文与执行范围。
- **许可证**：AGPL-3.0；B 的仓库导航实际显示该许可标记。本项未逐条审阅 LICENSE 正文。
- **边界 / 去重**：Oobabooga、Text Generation WebUI、当前 TextGen 按同一项目谱系处理；当前桌面入口与保留的 Web UI 能力分开描述。030 原记录使用的旧路径继续能取得当前 README。
- **失败 / 替代读取**：无访问失败；旧 raw 路径成功，另打开仓库入口直接核验重定向。

## 036 · FastChat Web UI

- **编号 / 原名**：36 / FastChat Web UI。
- **身份状态**：确认，定位到 `lm-sys/FastChat` 中的 Web GUI/Gradio 子功能；独立命名产品未单独确认。
- **真实搜索**：`FastChat Web UI lm-sys FastChat github Serving Web GUI`；request_id `421028`。检索返回教程线索，采用官方 README 作证据。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/lm-sys/FastChat/main/README.md ，文档，成功。
- **具体证据**：Serving with Web GUI 说明 controller、model worker、Gradio web server 三类组件，并要求等待模型加载和注册。Chatbot Arena 章节给出并排比较界面；高级选项还说明可使用含 Arena 的多标签服务器。
- **用于 Climber 的设计建议**：模型诊断按调度端、执行端、模型加载分段显示状态与修复入口；比较同一任务的两次运行时并排展示输入、输出、模型和配置差异。只有上下文一致的运行才进入可直接比较视图。
- **许可证**：
- **许可核验说明**：所读 README 没有给出 FastChat 仓库许可名称，留空。Vicuna 段中的 Llama 模型许可仅描述权重，不能用于填写 Web UI 应用许可。
- **边界 / 去重**：确认 Web GUI 为仓库内子功能；在线 Arena 服务的当前架构、隐私和性能尚未验证。建议借鉴诊断和比较结构，未启动模型 worker 或执行评测。
- **失败 / 替代读取**：无访问失败；官方 raw README 成功。

## 037 · Quivr UI

- **编号 / 原名**：37 / Quivr UI。
- **身份状态**：歧义；`QuivrHQ/quivr` 主项目确认，原名所指的具体 UI 仓库/历史版本未确认。当前第一方材料主要描述 quivr-core。
- **真实搜索**：`Quivr UI official github QuivrHQ quivr frontend`；request_id `421032`。检索摘要混有完整应用和核心框架描述，以下第一方正文用于收窄结论。
- **实际读取 URL A / 层级**：https://raw.githubusercontent.com/QuivrHQ/quivr/main/README.md ，文档，成功。
- **实际读取 URL B / 层级**：https://core.quivr.com/ ，文档，成功；为 A 指向的官方核心文档。
- **具体证据**：A 和 B 均说明 quivr-core 是 Quivr 的核心。A 的示例以 Python Brain 和终端对话为主；YAML 顺序包含历史过滤、问题重写、检索及生成，并单列重排配置。B 继续提供核心包与文件问答示例，未补足明确的浏览器布局证据。
- **用于 Climber 的设计建议**：把知识问答 trace 按重写、检索、重排、生成分段；来源片段与配置版本进入运行详情。该建议从流水线语义推导，具体 UI 布局应由 Climber 自行设计并验证。
- **许可证**：Apache 2.0；A 的 License 段明确给出，登记范围为该主仓库。尚未确认的独立 UI 许可保持未确认。
- **边界 / 去重**：将当前核心库、历史前端和托管产品分开研究；本轮没有浏览器源码或截图审阅证据。保留 UI 歧义，后续需要具体版本/仓库再建立视觉参考。
- **失败 / 替代读取**：无传输失败；A 未能唯一确认 UI 后追加 B 复核，依然只能确认核心库范围。

## 038 · AnythingLLM

- **编号 / 原名**：38 / AnythingLLM。
- **身份状态**：确认，项目为 `Mintplex-Labs/anything-llm`，同时提供桌面和自托管形态。
- **真实搜索**：`AnythingLLM Mintplex-Labs anything-llm github official`；request_id `421039`，返回官方版本文档和第三方介绍；正文核验使用以下仓库 README。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/Mintplex-Labs/anything-llm/master/README.md ，文档，成功。
- **具体证据**：Features 列出 workspace 内 Agent、拖放文档和来源引用、按规则模型路由，以及记忆和计划任务。多用户与嵌入组件标明 Docker 版本范围。Technical Overview 区分前端、服务端和文档采集器；隐私章节说明遥测关闭入口及仍可能发生的外部服务连接。
- **用于 Climber 的设计建议**：资料面板显示上传、解析、索引、可检索的状态，并把回答引用链接到原文片段。每次运行展示实际模型和回退原因；本地工作区中明确标注外部调用来源与资料范围。
- **许可证**：MIT；本轮 README 顶部许可徽标和末尾授权声明均可见。
- **边界 / 去重**：桌面与 Docker 能力按文档分别记录；本地部署、遥测设置与模型外部连接分别呈现。计划任务属于所读功能证据，本次没有安装或执行相关调度。
- **失败 / 替代读取**：无访问失败；官方 raw README 成功，宣传中的速度、成本和生产可靠性没有实测。

## 039 · Dify

- **编号 / 原名**：39 / Dify。
- **身份状态**：确认，项目为 `langgenius/dify`；本项研究其应用构建、工作流与运行观察界面。
- **真实搜索**：`Dify langgenius dify official github workflow`；request_id `421042`。检索结果为第三方索引，采用实际打开的官方 README 核验。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/langgenius/dify/main/README.md ，文档，成功。
- **具体证据**：Key features 分别说明可视画布构建/测试流程、Prompt IDE、模型供应商、文档摄取到检索的 RAG 和 LLMOps。LLMOps 段说明利用日志、性能、生产数据和标注持续改进；License 段指出 Apache 2.0 基础之上存在附加条件。
- **用于 Climber 的设计建议**：编辑视图聚焦节点配置与提交前校验，运行详情聚焦当前节点、输入输出、耗时与失败原因；两种状态明确切换。把模型、知识库或工具缺配置的问题链接到对应设置项；保存运行所用配置版本以便比较和复现。
- **许可证**：Dify Open Source License；README 明示基于 Apache 2.0 且有附加条件。本次记录许可原名，附加条件正文尚未逐条审阅。
- **边界 / 去重**：该名称指整个 Dify 平台，研究范围聚焦 UI 范式；具体事件协议、组件实现和可访问性仍需源码或运行验证。本批未增加安装、迁移或后端依赖。
- **失败 / 替代读取**：无访问失败；官方 raw README 成功。

## 040 · Flowise AI UI

- **编号 / 原名**：40 / Flowise AI UI。
- **身份状态**：确认，定位到 `FlowiseAI/Flowise` 的 React UI；维护状态单独标记为“本轮 README 自述已归档”。
- **真实搜索**：`Flowise AI UI FlowiseAI Flowise official github`；request_id `421044`。检索返回第三方工具介绍，产品和维护状态采用以下官方 README 核验。
- **实际读取 URL / 层级**：https://raw.githubusercontent.com/FlowiseAI/Flowise/main/README.md ，文档，成功。
- **具体证据**：正文顶部出现 `Flowise has been archived`，并给出后续讨论入口；产品标题强调可视化构建。Developers 分别列出 React 的 ui、处理 API 的 server、第三方节点 components 和接口文档模块，开发说明也标出 packages/ui 与 packages/server。
- **用于 Climber 的设计建议**：画布保留节点与连接的任务结构，选中节点后在侧栏编辑参数；执行详情单独展示工具调用与结果。缺失参数在节点与参数区同步提示，运行高亮与选中高亮使用不同视觉状态。上述布局和校验细节为建议，README 仅支撑其可视化及模块分工方向。
- **许可证**：Apache License Version 2.0；本轮 README 末尾 License 段明确给出。
- **边界 / 去重**：作为已归档项目的交互参考保留；归档具体日期、迁移安排与讨论内容未核验，讨论链接未计为实际读取 URL。依赖引入需要单独评估维护状况。
- **失败 / 替代读取**：无访问失败；官方 raw README 成功。文档中的安装命令仅阅读，未执行。

## 覆盖校验与可用范式

| 校验项 | 本批结果 |
| --- | --- |
| 编号及原名 | 031–040 连续 10 项，原名全部保留 |
| 逐项真实搜索 | 10/10，均记录实际查询词与 request_id |
| 第一方正文阅读 | 10/10；033 分开记录本体官方资料与候选作者 README |
| 状态 | 确认：031、032、036、038、039、040；歧义：033、037；重复：034、035 |
| 未确认的子结论 | 033 官方独立开源 Web UI；037 原名所指 UI/历史版本 |
| 访问失败及替代 | 033 文档根路径 307；改读应用文档成功 |
| 源码和运行验证 | 本轮均未开展；证据主要为文档，035 另有仓库元数据 |
| 许可观察空缺 | 036 未见仓库许可名称，字段留空；其余按所见名称和范围登记 |

1. **可审查的会话配置**：Agent 角色卡、模型来源标签、最小连接测试与可见上下文引用，优先用于 Climber 会话入口和配置抽屉；研究依据见 031、032、033、034。
2. **可比较的运行记录**：保留版本/分叉、运行模型及配置差异，提供一致上下文下的双栏比较和分层诊断；研究依据见 035、036、038。
3. **编辑与执行分离**：画布配置与运行 trace 分开，资料处理阶段和引用来源可追溯，失败能定位到节点或设置项；研究依据见 037、038、039、040。

以上三类范式均为 Climber 的设计建议，保留桌面优先和无登录的现有约束；本文件没有引入任何第三方实现、运行时、图标或品牌素材。
