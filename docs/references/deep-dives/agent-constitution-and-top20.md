# Agent Constitution 仓库与 Top 20 产品提示词深挖

> 核验日期：2026-10-01。
> 研究目标：对照 4 个 Agent 宪法/提示词仓库与 20 个顶级 AI 产品的提示词结构，为 `app/core/prompts/registry.py` 的 `core.system v1.2.0` 提供可迁移结构建议。
> 证据原则：只提炼“结构、契约、可复制模式”，不复制任何仓库或产品的提示词原文。每项记录均标 `已核验 / 本会话只读核验 / 当前不可达 / 推断`。
> 关联文件：现有索引 `docs/references/prompt-repos.md`，当前实现 `app/core/prompts/registry.py`。

## 1. 结论速览

1. 用户提供的 3 个原始仓库 URL 返回 404：`RedHatOfficial/spec-kit`、`jasonalmaturner/agent-maxxing`、`icolajar/agency-agents`。`Hmbown/CodeWhale` 可访问。
2. 已找到并经本会话核验的实际/替代仓库：`github/spec-kit`、`msitarzewski/agency-agents`；`agent-maxxing` 检索到至少两个同名候选 `subhansh-dev/agent-maxxing` 与 `HakanBabus/AgentMaxxing`，两候选均在线，但都不足以证明是原始仓库重命名，故双列并标注“候选”。
3. 改变 Agent 行为的最高杠杆不是单一提示词长度，而是五层结构：`领域/环境上下文 -> 角色 -> 工作流 -> 工具/权限契约 -> 输出验证`。
4. `core.system v1.2.0` 的九 section 主体已经覆盖“验证、工具、授权、范围、进度”等工程契约；本次研究最能补强的是“针对模式/环境的上下文层、产品域角色配置、以及外部可版本化的宪法文件”。
5. 20 个产品提示词入口中，直接可访问的约 14 个；4 个 `x1xhlol/...` 目录路径在本次核验中返回 404 或超时，另几个聚合库链接超时。报告只把“产物结构”标为 `已核验 via prompt-repos 索引 + 产品公开描述`，不虚构精确原文。

## 2. 原始仓库可达性与替代定位

| 仓库 | 原始 URL（用户提供） | 原始 URL 核验 | 本会话采用的核验落点 | 结论 |
| --- | --- | --- | --- | --- |
| Spec Kit | `https://github.com/RedHatOfficial/spec-kit` | 404 | `https://github.com/github/spec-kit` | 原始 URL 不可达；采用同名下可用仓库核验 |
| AgentMaxxing | `https://github.com/jasonalmaturner/agent-maxxing` | 404 | `https://github.com/subhansh-dev/agent-maxxing`、`https://github.com/HakanBabus/AgentMaxxing` | 原始 URL 不可达；无法确定唯一改名目标，双候选核验 |
| Agency Agents | `https://github.com/icolajar/agency-agents` | 404 | `https://github.com/msitarzewski/agency-agents` | 原始 URL 不可达；采用公开同名仓库核验 |
| CodeWhale | `https://github.com/Hmbown/CodeWhale` | 200 | 仓库本体 + 关键文档 | 原始仓库可访问 |

## 3. 四类仓库的“每仓库精华”

### 3.1 `github/spec-kit`（Spec Kit Constitution）

- 定位：本地、离线优先的 Spec-Driven Development CLI；把仓库治理写成可版本化 Constitution。
- 已核验文件：`.specify/memory/constitution.md`（v1.0.0）。
- 已核验结构：五条宪法原则 + 安全/跨平台约束 + 开发质量门禁 + 治理条款。
  - I. 代码质量与架构纪律：分层架构、单一注册表、来源唯一、命名/类型纪律。
  - II. 测试背书（不可协商）：合并硬门禁、完整性不变量、安全与幂等测试、网络 mock。
  - III. CLI 与用户体验一致性：共享动词、一致输出格式、可预测错误、安全幂等操作。
  - IV. 离线优先与资源纪律：离线可用、网络延迟加载、缓存降级、幂等文件写入。
  - V. 最小依赖与安全文件操作：零默认新依赖、路径越界拒绝、错误链、SemVer。
- 概念关键点：宪法是“门禁”，不是普通提示词；变更必须先过 `Constitution Check`，冲突由改 spec/plan/tasks 解决，而不是稀释原则。
- 可迁移结论：Climber 若引入“宪法”，应与 `core.system` 解耦，做成项目可检查的版本化规则文件，由 review/research 流程引用。

### 3.2 `agent-maxxing`（候选双仓库）

- A 候选：`subhansh-dev/agent-maxxing`
  - 已核验（仓库页）：95+ agent skills、19 UI 组件、7 个系统提示词，面向 Claude Code/Codex/Cursor/OpenCode 等多 Agent 的“自我微调”方式。
  - 结构价值：把系统提示词、skills、工作流、工具清单、组件分开维护，避免“一个巨大提示词承载所有能力”。
- B 候选：`HakanBabus/AgentMaxxing`
  - 已核验（README/技能结构）：主 Agent 保留目标/决策/验收，LUNA workers 承载有界实现；阶段图、worker packet、验收门、紧密交接格式。
  - 结构价值：`大小评估 -> 阶段拆分 -> packet 下发 -> 验收 -> 修正/reject` 是清晰的多 Agent 提示词契约。
- 概念关键点：两者共同点都是“上下文隔离、有界任务、验收证据”，但代表不同问题域：A 是技能/提示词素材库，B 是编排工作流。
- 可迁移结论：Climber 已有 `TASK_BODIES` 的 implementation/review/research 分类，可补充“delegation packet”模板，把子任务的目标、输入范围、必须/禁止改动、验收标准、返回格式显式化。

### 3.3 `msitarzewski/agency-agents`

- 定位：一个大型专家 Agent 目录，覆盖工程/设计/营销/销售/安全等多个 division。
- 已核验（仓库 README）：每个 Agent 文件的标准结构为：
  - 身份与人格特征
  - 核心使命与工作流
  - 技术交付物与代码示例
  - 成功指标与沟通风格
- 结构价值：不是单 Agent 提示词，而是“专业 Agent 配方”：`身份/人格 + 使命 + 工作流 + 交付物 + 指标 + 沟通风格`。
- 可迁移结论：`core.system` 保持通用底座，`TASK_BODIES` 是最小的 task-type 分层；如需专业角色，可增加“角色配置文件层”，避免把每种专业背景都塞进同一个 system prompt。

### 3.4 `Hmbown/CodeWhale`

- 定位：本地运行、自主编辑/运行命令/自我检查任务的开源 Agent；README 明确“本地运行时 + 权限配置”。
- 已核验文档：
  - `docs/AGENT_ETHOS.md`：先核验事实再行动；子 Agent 输出只是证据，父 Agent 负责最终决策；最小验证、可逆变更、禁止未批准发布。
  - `docs/AUTHORIZATION_ORDER.md`：README 将其称为 exact policy stack，是权限/授权的权威入口；本会话已核验文件存在，具体层级以该文档为准。
  - `docs/FLEET.md`：Fleet 只负责身份/成员/选择；运行时权限、文件系统、网络、secret、审批、沙箱、工具边界单独由 Runtime 钳制，无法钳制则 fail closed。
- 概念关键点：CodeWhale 没有把“宪法”做成单一系统提示词；而是拆为 `身份/伦理 -> 权限栈 -> 运行契约 -> 成员/模型选择` 多层，且强调“证据高于叙述、父 Agent 对子 Agent 输出负责”。
- 可迁移结论：Climber 的 `AUTHORIZATION_AND_RISK` 和 `VALIDATION_AND_RECOVERY` 已有对应原则；可增加“子任务证据交接格式”和“外部权限宪法文件”两类资产，不必改动 `core.system` 的固定主文案。

## 4. Top 20 产品五维结构对照

> 说明：以下内容依据 `docs/references/prompt-repos.md` 的摘要和本会话可达性核验整理；对未直接抓取原文的字段标 `当前来源为索引/推断`。产物结构不是原厂提示词原文。

| # | 产品 | 角色 | 工作流 | 工具契约 | 约束 | 结构 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Cursor | IDE 内编码助手 | 读仓库规则、理解项目、小步修改、反馈迭代 | 编辑器/搜索/终端按需调用，先读后改 | 尊重仓库级 rules，不越界改无关文件 | 仓库级持久指令 + 会话上下文分层 |
| 2 | Claude Code | 高质量工程协作者 | 读上下文、规划、执行、验证、报告 | 声明式工具 schema，避免无实际作用的密集调用 | 最小 diff、诚实报告、安全边界 | 主提示词 + 语气 + 限制规则 + 工具策略 |
| 3 | Devin AI | 真实软件工程师角色 | 端到端任务：理解、复现、实现、测试、交付 | shell/编辑器/浏览器/PR 流程 | 完成必须有证据，不把猜测当结论 | 长角色定义 + 工作流 + 输出/PR 契约 |
| 4 | Replit Agent | 特定环境内自主程序员 | 环境感知、直接构建、运行验证、修复 | 复用 Replit 环境执行与反馈 | 面向该环境的约束 | 环境特定角色 + 执行循环 |
| 5 | v0 (Vercel) | 组件化 UI 生成工程师 | 需求 -> 结构/组件拆分 -> 生成代码 -> 设计还原 | 前端工程工具链 | 控制修改范围，保持视觉与代码一致 | 领域模板 + 组件/设计输出约束 |
| 6 | Windsurf Agent | 项目感知编码 Agent | 先建立代码导航与项目上下文，再编辑 | 编辑器/搜索/终端 | 理解影响范围后再行动 | 上下文 + 导航 + 执行规则 |
| 7 | GitHub Copilot | 规划/开发双模式助手 | plan-mode 先拆问题与步骤，再进入实现 | 编辑器/检索/工具调用 | 内容政策、不确定处不冒充事实 | 模式化 system prompt + 政策层 |
| 8 | Manus | 自主任务执行 Agent | 目标 -> 计划 -> 持久任务状态 -> 执行直到交付 | 浏览器/终端/文件操作 | 进度可见、状态可持续、目标导向 | agent loop + 持久任务状态 |
| 9 | Same.dev | 全栈产品构建 Agent | 从需求生成可运行应用、持续迭代 | 浏览器/终端/框架工具 | 交付真正可运行产品，不报假进度 | system prompt 与内部工具定义同源维护 |
| 10 | Lovable | UI/UX + 代码生成产品 Agent | 需求 -> 设计建议 -> 代码生成 -> 迭代 | 前端生成与验证工具 | 保持产品页面设计和体验一致 | 设计建议层 + 代码生成层 |
| 11 | Perplexity | 检索增强研究助手 | 查询 -> 搜索/检索 -> 综合答案 | Web 检索工具 | 必须引用来源，来源不足时明示 | 检索 + 答案合成 + 引用输出 |
| 12 | NotionAI | 知识库/文档助手 | 读取笔记、文档、数据库上下文再写作 | Notion 内容/结构工具 | 跟随页面结构与语气 | 产品上下文 + 写作提示词 |
| 13 | OpenAI GPT-5 Thinking | 深度推理助手 | 拆解问题、分步推理、自我检查、输出答案 | 原生工具/结构化参数 | 推理过程与用户输出边界清晰 | 推理提示 + 工具 schema |
| 14 | Anthropic Claude | 有帮助且诚实的通用 Agent | 分析请求、必要时调用工具、约束内回答 | 工具 schema、多模态/AI 能力 | 诚实、安全、拒绝不适请求并给替代 | 安全准则 + 帮助性定义 |
| 15 | Google Gemini | 多模态通用助手 | 理解文本/图像/多模态输入并产出结构化结果 | 多模态与工具链 | 事实准确、输出格式明确 | 能力提示 + 结构化输出 |
| 16 | xAI Grok | 强人格搜索/对话 Agent | 结合上下文、个性化表达 | 平台搜索/对话能力 | 风格鲜明但事实不能编造 | 人格/语气 + 事实约束 |
| 17 | Kilo Code | 编辑器内多模式编码 Agent | 按模式工作：研究 -> 方案 -> 实施 -> 验证 | IDE/终端/工具化工作流 | 模式决定能否改文件 | 模式行为 + 工具化工作流 |
| 18 | Augment Code | 代码上下文增强 Agent | 索引仓库、向 IDE 注入精确上下文、做补全 | 仓库检索/上下文字段 | 只给相关上下文，避免泛化补全 | 上下文注入 + 精确输出 |
| 19 | VSCode Agent | IDE 交互 Agent | 感知编辑器状态、调用编辑器 API、执行任务 | 编辑器 API/终端/文件 | 权限与影响范围清晰 | 环境集成 + agent loop |
| 20 | Trae AI | 面向中文开发者的本地编码 Agent | 用本地化表达理解需求、诊断、修改、运行、解释 | 编辑器/终端 | 中文表达与本地生态适配 | 本地化角色 + 工具控制 |

## 5. 20 条可提炼中文大白话提示词条目

> 这些是本报告直接生成的中文大白话提炼，供 reviewer/开发任务快速转写，不是任何产品提示词原文。

| # | 产品 | 中文大白话提示词条目 |
| --- | --- | --- |
| 1 | Cursor | 先读懂仓库的持久规则和项目语境，再动手；每次改动最小，并说明改了什么。 |
| 2 | Claude Code | 先读关键文件再规划；只调用能推进工作的工具；改完检查 diff，禁止用假结果或空注释装完成。 |
| 3 | Devin AI | 像真实软件工程师做完整闭环：先理解，再复现或调查，再实现、测试、验证，结果都要有证据。 |
| 4 | Replit Agent | 把当前环境当工作台：先摸清项目结构，然后直接实现、运行、修复，别把问题留给用户。 |
| 5 | v0 | 把自然语言需求转成界面和代码都成型的组件；先给结构和视觉方向，再生成可运行代码。 |
| 6 | Windsurf Agent | 先建立整个项目的代码路径和影响范围，再改文件；不了解上下文就不轻易改。 |
| 7 | GitHub Copilot | plan 模式先拆出可验证步骤和不确定项，实现模式再改代码；没有依据的结论要明确标出来。 |
| 8 | Manus | 把任务当持续执行链路：目标、计划、当前状态、下一步始终可见，逐步完成直到交付。 |
| 9 | Same.dev | 从需求做到真正可运行的应用；持续用工具验证，不把“看起来像完成”当成“已完成”。 |
| 10 | Lovable | 先把体验方向和界面设计说清楚，再生成代码；迭代时保持设计一致，不随意推倒重来。 |
| 11 | Perplexity | 只用检索到的来源回答问题；关键结论给出处，来源不足就明说不足。 |
| 12 | NotionAI | 先读当前笔记、文档或数据库上下文再动笔；回答保持该页面结构和语气。 |
| 13 | OpenAI GPT-5 Thinking | 先做推理再给最终答案；拆问题、分步检查，推理过程不进用户可见答案。 |
| 14 | Anthropic Claude | 要既有帮助又诚实：不迎合错误前提，不做危险或欺骗性操作，拒绝时给替代方案。 |
| 15 | Google Gemini | 充分利用多模态输入；按请求输出结构化内容，并把事实和推断分清楚。 |
| 16 | xAI Grok | 保持鲜明且准确的个人语气；有趣不等于编造，重要事实仍然要站得住。 |
| 17 | Kilo Code | 按当前模式工作：plan 只研究和给方案，develop 才改代码；工具调用保持可追踪。 |
| 18 | Augment Code | 先索引和理解仓库，再做针对性补全；只给出真正需要的上下文，避免泛泛而谈。 |
| 19 | VSCode Agent | 熟悉当前编辑器状态和 API；用最小权限完成任务，调用前先确认会改变什么。 |
| 20 | Trae AI | 用中文开发者熟悉的表达理解需求；在本地环境里完成诊断、修改、运行和解释。 |

## 6. 与 `core.system v1.2.0` 的重合与增量

当前 `core.system v1.2.0` 的核心结构见 `app/core/prompts/registry.py:61-71`：`ROLE_AND_SCOPE`、`TASK_WORKFLOW`、`TOOL_CONTRACT`、`PROGRESS_REPORTING`、`VALIDATION_AND_RECOVERY`、`SAFE_OUTPUT`、`AUTHORIZATION_AND_RISK`、`ENGINEERING_DISCIPLINE`、`RESEARCH_AND_KNOWLEDGE`；同时有 `TASK_BODIES`（implementation/review/research）与 `MODEL_ADAPTATIONS`。

| 外部仓库/产品结构 | Climber 现状 | 对照结论 |
| --- | --- | --- |
| Spec Kit 宪法原则 | `VALIDATION_AND_RECOVERY`、`ENGINEERING_DISCIPLINE`、`AUTHORIZATION_AND_RISK` | 高度重合；增量是“把原则做成可检查的外部宪法文件并版本化” |
| AgentMaxxing 子任务 packet | `TASK_WORKFLOW` + `TASK_BODIES` | 已有基础；可增加“任务 packet”字段：输入范围、必须/禁止改动、验收标准、返回格式 |
| Agency Agents 专业角色配方 | `ROLE_AND_SCOPE` + `TASK_BODIES` | 通用底座已具备；增量是“按角色拆成可配置 profile”，不进主 system prompt |
| CodeWhale 权限栈/运行时钳制 | `AUTHORIZATION_AND_RISK`、`TOOL_CONTRACT` | 已有近似原则；增量是“AUTHORIZATION_ORDER”式外部权威文档和 fail-closed 可执行边界 |
| Top 20 产品的模式/环境上下文 | `MODEL_ADAPTATIONS` | Climber 只做模型适配，未做“环境模式适配”；可增加 `plan/develop/operate` 或 `research/review/implementation` 的上下文层 |
| Top 20 产品的持久状态/进度 | `PROGRESS_REPORTING` | 已强；可再加“任务状态快照”，让外部 planner/reviewer 可读取 |
| Top 20 产品的返回格式契约 | `SAFE_OUTPUT` | 已强；可增加“按任务类型声明的返回字段”范本 |

## 7. 可落地建议（不直接修改 registry）

1. 新增 `CONSTITUTION` 外部层：项目根 `.climber/constitution.md` 或 registry 可选读取的文件，给原则打版本，`review`/`research` task 在输出中做 `Constitution Check`。
2. 新增 `TASK_PACKETS` 模板：参考 AgentMaxxing worker packet，为多 Agent 子任务生成 `目标/输入/改动范围/禁止改动/验收/验证/返回格式`。
3. 新增 `ROLE_PROFILES` 配置层：参考 Agency Agents，把专业角色定义为可替换 profile，避免把角色细节硬编码进 `core.system`。
4. 新增 `AUTHORIZATION_ORDER` 文档：参考 CodeWhale，把权限等级与 fail-closed 边界从提示词提为仓库可读文档，`core.system` 只引用它。
5. 为 task types 增加“环境上下文断言”：在 `TASK_BODIES` 中声明每次执行前应读取的环境状态，例如当前 branch、target 文件、测试命令、允许的工具面。
6. 不照搬任何 Top 20 产品的原始提示词；优先复用现有九 section 的契约，只补充缺失的上下文与配置层。

## 8. Top 20 链接可达性核验

核验时间：2026-10-01；方法：`curl -sSL -o /dev/null --max-time 20 -w "%{http_code}"`。

| # | 产品 | 当前来源/URL | 本次核验 |
| --- | --- | --- | --- |
| 1 | Cursor | `x1xhlol/.../Cursor Prompts` | 200 |
| 2 | Claude Code | `gregkonush/claude-system-prompts` | 200 |
| 3 | Devin AI | `x1xhlol/.../Devin AI/Prompt.txt` | 200 |
| 4 | Replit Agent | `x1xhlol/.../Replit Agent/Prompt.md` | 404 |
| 5 | v0 | `x1xhlol/.../v0 Prompts and Tools/v0.MD` | 404 |
| 6 | Windsurf Agent | `x1xhlol/.../Windsurf Agent` | 404 |
| 7 | GitHub Copilot | `agenticloops-ai/.../plan-mode/system-prompt.md` | 200 |
| 8 | Manus | `x1xhlol/.../agent loop.md` | 超时 |
| 9 | Same.dev | `x1xhlol/.../Same.dev` | 超时 |
| 10 | Lovable | `x1xhlol/.../Lovable` | 200 |
| 11 | Perplexity | `x1xhlol/.../Perplexity` | 200 |
| 12 | NotionAI | `EliFuzz/awesome-system-prompts` | 超时 |
| 13 | OpenAI GPT-5 Thinking | `EliFuzz/awesome-system-prompts` | 超时 |
| 14 | Anthropic Claude | `gregkonush/claude-system-prompts` | 200 |
| 15 | Google Gemini | `EliFuzz/awesome-system-prompts` | 超时 |
| 16 | xAI Grok | `caifyoca/CL4R1T4S` | 200 |
| 17 | Kilo Code | `Kilo-Org/kilocode` | 200 |
| 18 | Augment Code | `x1xhlol/.../Augment Code` | 200 |
| 19 | VSCode Agent | `x1xhlol/.../VSCode Agent` | 200 |
| 20 | Trae AI | `x1xhlol/.../Trae` | 200 |

> 说明：404 表示本次该路径不可用；超时是 20 秒网络超时，不代表仓库永久下线。产品结构判断不能只用可达性判定，无法访问的 4 个条目标注为 `当前来源为索引/推断`。

## 9. 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 4 个原始仓库 URL 的 404/200 状态 | 已核验（本会话 HTTP 核验） |
| `github/spec-kit` 宪法文档结构与五原则 | 已核验（本会话读取 `.specify/memory/constitution.md` v1.0.0） |
| `subhansh-dev/agent-maxxing`、`HakanBabus/AgentMaxxing`、`msitarzewski/agency-agents` 仓库页与 README 结构 | 已核验（本会话公开页面核验） |
| `Hmbown/CodeWhale` 的 AGENT_ETHOS/FLEET/README 与 AUTHORIZATION_ORDER 文件存在性 | 已核验（本会话公开文档核验） |
| `CodeWhale` 内部“九级权限/`.codewhale/constitution.json` 具体配置” | 未直接核验（如后续实现，需以 `docs/AUTHORIZATION_ORDER.md` 或运行时源码为准） |
| Top 20 五维结构 | `已核验 via prompt-repos 索引 + 已核验链接/推断`，不含原厂原文 |
| 20 条中文大白话条目 | 本报告生成，可基于公开产品角色复用 |
| `core.system v1.2.0` 九 section/getting-started 等现状 | 已核验（本仓只读调研） |