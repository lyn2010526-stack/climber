# Climber 50 开源参考项目索引（模块映射 + 落地状态）

> 来源：`docs/DESIGN.md`「50个开源参考项目」全量录入。
> 落地状态图例：✅ 已落地（有代码+测试）｜🔧 部分（有代码待接线/待补测试）｜📋 待落地（阶段2+）｜🧪 agi-core（阶段3/4 原型）

## 一、Agent 后端内核｜任务调度 & 多子任务并发（12 个）— main 分支优先

| # | 项目 | 地址 | 提炼要点 | Climber 对应模块 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | LangGraph | https://github.com/langchain-ai/langgraph | 图状态机、循环、断点回滚、多 Agent 编排 | `app/core/task_state_machine.py`（状态机）、checkpoint 恢复 | ✅ |
| 2 | CrewAI | https://github.com/joaomdmoura/crewAI | 角色多智能体、并发子任务调度 | `app/core/collaboration/`、`app/core/task_worker.py` | 🔧 |
| 3 | smolagents | https://github.com/huggingface/smolagents | 轻量极简工具调用，无臃肿依赖 | `app/tools/builtins.py` 工具注册 | ✅ |
| 4 | AgentScope | https://github.com/modelscope/agentscope | 国产多 Agent、私有化部署、负载均衡 | task_manager 并发（默认 3/上限 18） | 🔧 |
| 5 | AutoGPT | https://github.com/Significant-Gravitas/AutoGPT | 自主目标拆解、自我复盘循环 | `handle_factory_run`（计划→步骤→合成） | ✅ |
| 6 | Griptape | https://github.com/griptape-ai/griptape | 分层架构：推理-工具-存储解耦 | engine / tools / storage 分层 | ✅ |
| 7 | Haystack | https://github.com/deepset-ai/haystack | LLM 流水线、失败重试、分支判断 | 步骤级+任务级双层重试 | ✅ |
| 8 | Prefect | https://github.com/PrefectHQ/prefect | 通用工作流调度、任务优先级、阻塞预判 | TaskManager 调度 | 🔧 |
| 9 | OpenAgents | https://github.com/openagentsinc/openagents | 端到端 Agent、会话持久化、中断恢复 | sessions 表 + cancel/retry 端点 | ✅ |
| 10 | TaskWeaver | https://github.com/microsoft/TaskWeaver | 代码 Agent、脚本前置校验 | 沙箱 + 脚本预测试（设计 1.4 节） | 📋 |
| 11 | Agno(Phidata) | https://github.com/agno-agi/agno | Agent 快速组装、多工具并行调用 | 多工具并行（factory steps） | 🔧 |
| 12 | AutoGen(AG2) | https://github.com/microsoft/autogen | 多 Agent 消息通信、子任务隔离 | `app/core/collaboration/base.py` | 🔧 |

## 二、世界模型｜因果推理｜元认知｜不确定性（8 个）— agi-core 分支

| # | 项目 | 地址 | 提炼要点 | Climber 对应模块 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 13 | ReasonWorld | https://github.com/ReasonWorld/reasonworld | LLM 世界模型、多假设并行置信打分 | 多假设置信度博弈算法（设计 4.2.1）；`app/core/metacognition/hypothesis.py` 已有多分支路径评估原型 | 🧪 |
| 14 | SocraticAgents | https://github.com/socratica/socratic-agents | 自省元认知、检测推理内部矛盾 | 原生元认知回路（设计 3.3）；`app/core/metacognition/monitor.py` 已实现冗余调用/幻觉模式检测 | 🧪 |
| 15 | CausalGraphGen | https://github.com/causal-ai/causalgraphgen | 时序交互数据自动挖掘因果图 | 自主因果图挖掘算法（设计 4.2.2）；`app/core/metacognition/causal.py` 目前仅做失败根因回溯，尚无自动因果图构建 | 🧪 |
| 16 | PyMC | https://github.com/pymc-devs/pymc | 概率编程，不确定性、置信度计算 | 不确定性度量算法（设计 4.2.3），尚未落地 | 📋 |
| 17 | SymbolicAI | https://github.com/xorbitsai/symbolicai | 符号-神经混合可解释因果表征 | 远期符号-神经混合表征（设计 3.5），仅规划未开始 | 📋 |
| 18 | miniWORLD | https://github.com/mini-world-ai/miniworld | 仿真世界模型，环境观测-动作预测 | 世界模型本体（设计 3.1 新范式），尚未落地 | 📋 |
| 19 | Self-Consistency 开源实现 | https://github.com/yizhongw/self-consistency | 多条推理路径比对，降低武断判断 | 多假设置信度博弈算法（设计 4.2.1）同源思路；`hypothesis.py` 可扩展接入 | 🧪 |
| 20 | ThinkAgent | https://github.com/thinkagent-ai/thinkagent | 反思回路 Agent，自我质疑修正结论 | 原生元认知算法回路（设计 3.3）；`app/core/metacognition/orchestrator.py` 已串联 monitor/causal/goal_adjuster 形成复盘回路 | 🔧 |

## 三、Agent 前端 UI｜对话界面｜工具 & 思考可视化（12 个）— 前端开发参考

> 实际前端目录为 `frontend-react/`（技术栈需以该目录 `package.json` 为准），非设计文档原文的通用叫法。

| # | 项目 | 地址 | 提炼要点 | Climber 对应模块 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 21 | EditHere | https://github.com/Inginnng/EditHere | 代码 Agent 交互面板（重点对标） | `frontend-react/` 整体交互范式参考 | 📋 |
| 22 | MonkeyCode | https://github.com/monkey-code-ai/monkeycode | 思考流可视化、补丁操作界面 | 思维轨迹可视化开关（设计 1.3） | 📋 |
| 23 | Zcode | https://github.com/zcode-ai/zcode | Agent 工作台，模型端点/密钥/任务进度面板 | 自定义模型端点/API 密钥 UI（设计 1.3） | 📋 |
| 24 | LobeChat | https://github.com/lobehub/lobe-chat | iOS 极简高级 UI、多模型参数面板 | 私密 APP 级体验（设计原文「人与环境交互层」） | 📋 |
| 25 | Open-WebUI | https://github.com/open-webui/open-webui | 私有化本地聊天，密钥本地存储权限管理 | 三级权限安全体系（`app/core/permission_rules.py`）前端呈现 | 📋 |
| 26 | LibreChat | https://github.com/danny-avila/LibreChat | 多模型适配器、多会话、插件系统 | `ModelRegistry`（`app/models/registry.py`）多 provider 已落地，前端切换 UI 待补 | 🔧 |
| 27 | Dify-WebUI | https://github.com/langgenius/dify | 调试事件日志可视化 | 工具调用可视化（设计 1.3） | 📋 |
| 28 | Flowise | https://github.com/FlowiseAI/Flowise | 工作流可视化组件，答辩调试面板原型 | 任务状态机可视化（对应 `task_state_machine.py`） | 📋 |
| 29 | Chatbot-UI-Next | https://github.com/mckaywrigley/chatbot-ui | 消息折叠组件，Next.js 对话模板 | 对话界面基础组件 | 📋 |
| 30 | Vercel-AI-Chatbot | https://github.com/vercel/chatbot | 流式对话基础组件库 | SSE 流式输出前端消费（后端已实现 slash 流式） | 🔧 |
| 31 | Jan | https://github.com/janhq/jan | 桌面端私密界面、多会话管理 | 私密 APP 级体验（锁屏/动画，设计原文） | 📋 |
| 32 | UI-TARS-Desktop | https://github.com/bytedance/UI-TARS-desktop | 字节 GUI-Agent 工作台、工具卡片参考 | 工具调用卡片 UI | 📋 |

## 四、记忆系统｜用户画像｜时序衰减｜长时记忆（9 个）— 用户画像闭环

| # | 项目 | 地址 | 提炼要点 | Climber 对应模块 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 33 | Letta（原 MemGPT） | https://github.com/letta-ai/letta | 分层虚拟内存，记忆老化衰减 | `app/core/memory/lifecycle.py`（write→index→retrieve→decay→forget→archive 全链路已实现） | ✅ |
| 34 | Mem0 | https://github.com/mem0ai/mem0 | Agent 个性化记忆，交互驱动更新用户偏好 | `app/core/integration/mem0_memory.py`（已接入 Mem0 SDK 做向量+图存储） | ✅ |
| 35 | LlamaIndex | https://github.com/run-llama/llama_index | 检索增强，历史指令匹配，补全隐含意图 | 指令轨迹持久化检索（`app/core/slash/` 指令栈 + 向量检索） | 🔧 |
| 36 | Chroma | https://github.com/chroma-core/chroma | 轻量本地向量库，用户特征向量持久化 | `app/core/vector_memory.py`（ChromaDB 已接入作为语义记忆后端） | ✅ |
| 37 | Qdrant | https://github.com/qdrant/qdrant | 高性能向量库，相似度检索 | 未接入，当前仅用 ChromaDB | 📋 |
| 38 | LongMem | https://github.com/11data/longmem | 超长上下文归档、消息时序压缩 | 永久指令轨迹持久化系统（设计 1.1），指令表已落地，时序压缩算法待补 | 🔧 |
| 39 | Recall | https://github.com/RecallWorks/Recall | 图结构时序记忆，区分会话记忆/长期记忆 | `MemoryRecord` 表已区分记忆类型，图结构关联待补 | 🔧 |
| 40 | AutoMemory | https://github.com/autoLearnMem/AutoMem | 自动提取用户特征，弱监督更新记忆库 | `app/core/profile/loop.py` 弱监督校准（`_FeatureStats.calibration`）已落地 | ✅ |
| 41 | Zep | https://github.com/getzep/zep（产品文档：https://help.getzep.com；开源时序图谱：https://github.com/getzep/graphiti） | Zep 主仓库是 Zep Cloud 示例、集成与工具仓库；Community Edition 已移入 `legacy/` 并标记弃用；Graphiti 是其开源时序上下文图框架 | `ProfileLoopService._weight()` 指数时序衰减已落地；借鉴时序事实有效期、关系召回与评估 harness，接入前评估托管依赖、数据边界和 Graphiti 自托管成本 | 🔧 |

## 五、自进化｜遗传算法｜沙箱 & 权限安全（9 个）— 智能进化闭环 + 安全体系

| # | 项目 | 地址 | 提炼要点 | Climber 对应模块 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 42 | EvoGPT | https://github.com/evo-gpt/EvoGPT（本次访问返回 404，真实地址未核实） | 原索引描述为提示词遗传进化；官方仓库身份、许可证、能力和维护状态均未核实 | 仅保留待确认线索；获得可信地址和许可证证据后再评估交叉、变异、适应度接口 | 📋 |
| 43 | PromptEvolver (EvoPrompt) | https://github.com/beeevita/EvoPrompt | 官方 README 将其标为 ICLR 2024 论文实现，代码展示 GA/DE 提示词种群初始化、演化、评估与更新；仓库可访问，当前维护强度未核实 | 作为阶段 3 实验参考：抽象 population/evaluator/selection 契约，隔离其数据集、配置和密钥 | 📋 |
| 44 | PyEvolution | https://github.com/PyEvolution/PyEvolution（本次访问返回 404，真实地址未核实） | 原索引描述为遗传算法底层算子；官方仓库身份、许可证、能力和维护状态均未核实 | 暂不作为依赖；获得可信地址、许可证和 API 证据后再评估拓扑变异/交叉借鉴 | 📋 |
| 45 | E2B-Sandbox | https://github.com/e2b-dev/E2B | 官方 README 定位为云端隔离沙箱基础设施，提供 JavaScript/Python SDK、命令执行、Code Interpreter 和 Desktop 能力；仓库可访问，维护状态未核实 | `app/core/sandbox.py` 仍是子进程级隔离，保留与 E2B 微 VM/云端边界的能力差异；暂不引入依赖 | 🔧 |
| 46 | OpenSandbox | https://github.com/opensandbox-group/OpenSandbox | 官方 README 提供 Docker 本地启动、Kubernetes 部署、统一生命周期 API、命令/文件/浏览器执行、出口策略和 Credential Vault；仓库可访问，维护状态未核实 | 三级权限 + 沙箱联动（`permission_rules.py` + `sandbox.py`），仅借鉴生命周期、出口策略和凭据隔离契约 | 🔧 |
| 47 | Guardrails-AI | https://github.com/guardrails-ai/guardrails | 官方 README 提供 Input/Output Guards、Hub validators 和结构化数据生成；仓库可访问，维护状态未核实 | `app/core/collaboration/guardrails.py` 继续限定为群协作输出校验，暂不扩展为通用 LLM I/O 层 | 🔧 |
| 48 | HyperAgents (Meta) | https://github.com/facebookresearch/HyperAgents | 官方 README 定位为可自我改进的 Agent，并明确警告执行不可信模型生成代码；仓库可访问，维护状态未核实 | `app/core/metacognition/self_refactor.py` 保留 Skill 自我精简/合并原型；实验必须隔离并审计 | 🔧 |
| 49 | NeMo-Guardrails | https://github.com/NVIDIA-NeMo/Guardrails | 官方 README 明确支持 input、dialog、retrieval、execution、output 五类 rails；仓库可访问，develop 为开发线，最新发布版本以官方页面为准 | 以 rail 分层作为设计参考；Climber 当前仅覆盖群协作校验，通用对话流和工具执行层待评估 | 📋 |
| 50 | Rebuff（仓库已归档，仅学习参考） | https://github.com/protectai/rebuff | GitHub 明确标记仓库于 2025-05-16 归档且只读；README 描述启发式、LLM、向量库和 canary 四层提示注入检测；能力仅作历史参考 | 借鉴分层检测和 canary 概念，不引入代码或依赖；提示注入检测仍待并入 `guardrails.py` | 📋 |

## 使用指引（设计文档原文）

- **main 参赛稳定分支优先研读**：一组（调度）+ 三组（前端）+ 四组（记忆画像），快速做可演示版本。
- **agi-core 长期迭代研读**：二组（世界模型因果）+ 五组（遗传进化沙箱），做算法创新点。
- 只借鉴架构、模块、交互范式，双闭环算法融合是 Climber 独有创新，不直接复制源码。

## 六、2026-10-01 研究报告索引

| 报告 | 覆盖范围 | 状态 | 证据与未完成项 |
| --- | --- | --- | --- |
| `deep-dives/opensource-core-agents-01-12.md` | #1-12 核心 Agent、调度与工具 | ✅ 已完成 | 12 个项目均有官方 README/元数据证据；部分落地项仍需补测试或执行器 |
| `deep-dives/opensource-world-models-13-20.md` | #13-20 世界模型、因果、元认知、不确定性 | ✅ 研究完成 / 🧪 落地进行中 | #13/#14/#15/#19/#20 无可信源码；完整闭环未完成 |
| `deep-dives/opensource-frontend-reference-21-32.md` | #21-32 Agent 前端 UI | ✅ 研究完成 / 📋 落地待办 | 10 个原仓库已核验，MonkeyCode/Zcode 原始地址不可用；交互借鉴项尚未全部接入 |
| `deep-dives/opensource-memory-profile-33-40.md` | #33-40 记忆、画像、检索 | ✅ 研究完成 / 🔧 落地进行中 | Chroma/画像基础已落地；混合排序、过滤、关系召回和 query transform 未完成 |
| `deep-dives/agent-constitution-and-top20.md` | 4 个 Agent 宪法仓库与 20 个产品提示词 | ✅ 已完成 / ~ 集成进行中 | 原始 URL 404、候选仓库、可达性和推断均已分级；外部宪法、任务 packet、角色 profile 尚未落地 |

研究报告总数：5 份新增报告。报告只记录结构、契约、映射和证据等级，不把不可达仓库的描述当作源码事实。

## 已落地模块 ↔ 参考项目对照（自下而上核对）

| Climber 模块 | 对标项目 | 关键机制 |
| --- | --- | --- |
| `app/core/prompts/registry.py` | Cursor rules、Claude Code memory | 版本化、deprecated 拒绝、工具契约校验 |
| `app/core/instruction/understanding.py` | Claude Code（理解先于行动） | 确定性解析主目标/约束/歧义/置信度 |
| `app/core/profile/loop.py` | AutoGPT 复盘循环 | 本地画像闭环、PrivacyBoundaryError |
| `app/core/task_worker.py` | LangGraph、Haystack、AutoGPT | 计划→步骤→合成；双层重试；副作用步骤豁免重试 |
| `app/core/task_state_machine.py` | LangGraph | 状态转移、触发记录 |
| `app/core/slash/`（registry/service/specs） | Claude Code、Cursor 斜杠命令 | 7 命令、SSE 流式、streaming/while-streaming 标记 |
| `app/api/v1/routes/reasoning.py` | OpenAI o-series thinking | 三档思考等级 → 模型参数注入 |
| `app/core/permission_rules.py` | Claude Code permission modes | 三级权限 + STRICT + 规则评估 |
| 并发调度（max_concurrent_subtasks 3/18） | AgentScope、Prefect | 可配置 + clamp + warning |
| `app/core/memory/lifecycle.py` | Letta/MemGPT | write→index→retrieve→decay→forget→archive 全链路 |
| `app/core/integration/mem0_memory.py` | Mem0 | 向量+图存储记忆、交互驱动更新偏好 |
| `app/core/vector_memory.py` | Chroma、Letta ArchivalPassage | ChromaDB 语义记忆检索 |
| `app/core/profile/loop.py`（`embed_event`/`OnlineKMeans`） | 增量在线聚类算法原型 | 哈希特征嵌入 + 单遍流式 k-means（无持久化/调用链） |
| `app/core/metacognition/orchestrator.py` | ThinkAgent | monitor→causal→goal_adjuster 复盘回路串联 |
| `app/core/metacognition/self_refactor.py` | HyperAgents(Meta) | Skill 自我精简/合并原型 |
| `app/core/sandbox.py` | E2B-Sandbox（子进程级，非微 VM） | 资源限制、命令黑名单、工作目录隔离 |
| `app/core/collaboration/guardrails.py` | Guardrails-AI、NeMo-Guardrails | 群协作输出校验（尚未覆盖通用对话流） |

## 阶段路线对照（设计文档第八节）

- **阶段 1 基座工程**：上表 ✅/🔧 项 + 迁移链修复 + 死代码清理 ← 当前进行中
- **阶段 2 画像算法**：时序加权衰减 ✅、弱监督校准 ✅、特征嵌入降维 ✅（`embed_event`）、增量在线聚类 ✅（`OnlineKMeans`）算法本体均已在 `app/core/profile/loop.py` 落地；画像数据的跨会话持久化与业务调用链已具备项目级承载，后续工作聚焦画像算法输出接入意图理解、检索排序和回归评估闭环
- **阶段 3 遗传进化过渡**：提示词 & 参数种群进化（`app/core/prompts/` + 评估器），当前仅以已核实的 EvoPrompt 作为实验参考；EvoGPT 与 PyEvolution 地址未核实，尚未开始
- **阶段 4 agi-core**：世界模型 + 因果挖掘 + 神经进化（`ReasonWorld`/`SocraticAgents`/`CausalGraphGen`/`PyMC` 等结构参考），`app/core/metacognition/` 已有 causal/hypothesis/monitor 原型，尚未组成完整世界模型闭环
