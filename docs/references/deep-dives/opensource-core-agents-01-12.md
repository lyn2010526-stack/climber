# 开源核心 Agent 项目深挖 01-12

- 日期: 2026-10-01
- 范围: `docs/references/open-source-projects.md` 索引表 #1-12
- 目标: 为每个项目给出定位、机制精华、Climber 代码映射、落地状态和证据等级
- 对应代码:
  - `app/core/task_worker.py`
  - `app/core/task_state_machine.py`
  - `app/core/collaboration/`
  - `app/tools/builtins.py`

## 研究方法和证据原则

本报告的外部项目证据来自本会话实际获取的 12 个官方 GitHub 仓库 README/仓库元数据，本地证据来自直接阅读上述 Climber 文件及相应测试。GitHub API 对 `langchain-ai/langgraph` 和 `crewAIInc/crewAI` 核验成功，对另外 8 个仓库返回 403 限流；随后改用 raw README，12 个仓库均成功获取。本报告不虚构任何开源项目源码行号。

证据等级定义:

- `verified`: 该项目的定位、机制或映射有本会话直接获取的官方仓库信息或本地代码支撑。
- `inferred`: 该项目机制或 Climber 映射基于官方文档之外的既有知识、架构推断或代码近似对应得出，尚未完成逐文件核验。
- `unavailable`: 本会话没有获取到直接证据。

## 1. LangGraph

- 一句话定位: 低层有状态 Agent 编排框架，把执行建模为 `StateGraph + Pregel` 超步引擎，并提供 checkpoint、断点和 human-in-the-loop。
- 机制精华:
  1. `StateGraph` 用节点、边和 reducer 合并状态，`PregelEngine` 用超步模型并行激活节点并在步骤间路由消息。
  2. checkpoint 使用 `thread_id`、`checkpoint_id` 和 parent 关系保存执行状态，支持从指定断点恢复。
  3. `interrupt_before`/`interrupt_after` 与 `HITLManager` 支持人工审批和恢复。
  4. 执行层具备 retry policy、timeout policy、error handler 和 streaming events。
  5. `Command` 支持节点内动态路由而不是固定静态边。
- Climber 映射:
  - `task_state_machine.py`: `TaskState`、`TRANSITIONS` 显式状态转移矩阵、hook chain，是 LangGraph 状态模型的本地版本。
  - `app/core/collaboration/checkpoint.py`: `save_checkpoint`、`load_latest_checkpoint`、`resume_from_checkpoint`，覆盖会话和多 Agent checkpoint。
  - `app/core/engine/pregel/engine.py`: 本地 `StateGraph + PregelEngine`、checkpoint saver、`HITLManager`、retry/timeout 策略，是 LangGraph 最直接的对应实现。
  - `task_worker.py`: 任务提交、执行、重试和 `recover_pending_tasks` 提供持久化层，但尚未和任意运行中步骤的 checkpoint 打通。
- 落地状态: 已落地。状态机被 `session.py`、`auto_loop.py`、`execution/engine.py`、`react_loop.py` 等使用；Pregel 引擎、SQLite/InMemory checkpoint、HITL 和恢复测试存在。
- 证据等级: `verified`

## 2. CrewAI

- 一句话定位: 角色驱动的多 Agent 协作框架，用 `Agent/ Task/ Crew` 描述职责、能力和交付物，再按流程编排协作。
- 机制精华:
  1. Agent 由 role、goal、backstory、tools 和 capability 构成，任务显式分配给 Agent。
  2. 流程包括 sequential、hierarchical 和 group/parallel 协作；hierarchical 由 manager/coordinator 做委托和裁决。
  3. 任务间可声明依赖，前序任务的输出进入后序任务上下文。
  4. 提供 handoff、flow 和 agent-to-agent delegation，用于接力式多 Agent 工作。
  5. `kickoff` 统一入口返回协作结果，并支持观察执行过程。
- Climber 映射:
  - `app/core/collaboration/base.py`: `GroupCollaborationEngine` 按 process 分发 sequential、hierarchical、group_chat，对应 CrewAI 的 flow/process。
  - `app/core/collaboration/roles.py`: Agent 角色和预期输出模型，对应 role/goal/backstory 语义。
  - `app/core/collaboration/dependencies.py` 与 `deadlock.py`: 任务依赖排序和死锁检测，对应 CrewAI task dependencies。
  - `app/tools/builtins.py`: `run_group_tasks`、`handoff_task` 提供协作和交接工具入口。
  - `tests/core/test_collaboration_review45.py`、`test_collaboration_deadlock.py` 覆盖 ORM 协作、handoff、checkpoint 和环状依赖。
- 落地状态: 部分落地。sequential/hierarchical 和基础 DAG 有实现与测试；group_chat 共识、manager 调度复杂度和 handoff 协议仍需要更多覆盖。
- 证据等级: `verified`

## 3. smolagents

- 一句话定位: 轻量 Tool-Use Agent 框架，核心是把“选择工具再调函数”的 ReAct 方式收敛为代码优先的 `CodeAgent`。
- 机制精华:
  1. 官方明确推荐 `CodeAgent`，让模型生成可执行代码片段而非逐个 JSON tool call。
  2. Tool 通过 `@tool` 和 Tool 类暴露名字、描述、输入 schema，并可从包目录自动导入。
  3. 代码执行放入隔离 executor，agent 只暴露受控工具和运行时。
  4. 支持 ReActAgent 作为简单稳定场景的替代，并对运行历史、web search 等工具做统一管理。
  5. 保持模型无关，可接入 LiteLLM、OpenAI、Hugging Face 等后端。
- Climber 映射:
  - `app/tools/__init__.py`: `ToolRegistry`、`tool` 装饰器和 `register_builtins`，与 `@tool` 注册模型一致。
  - `app/tools/builtins.py`: 20+ 个工具覆盖计算、文件、网络、命令、图像和协作，并带路径、SSRF、命令 blocklist 校验。
  - `app/core/parallel.py`: `ParallelToolExecutor` 提供 execute_all/execute_sequential，接近工具级执行的轻量层。
  - `task_state_machine.py`: 工具调用对应任务状态链路，但本身不负责代码生成执行。
- 落地状态: 已落地。工具注册、内置工具集、安全校验和 `test_builtins_path_validation.py` 均存在；尚未提供 smolagents 式的通用代码生成 executor。
- 证据等级: `verified`

## 4. AgentScope

- 一句话定位: 面向分布式多 Agent 应用的全栈平台，覆盖单体开发、Agent 服务化、Team 协作和消息中间件。
- 机制精华:
  1. 提供 ReAct 风格 agent 循环和内置 agent 类，封装角色、工具和消息。
  2. Team 层支持 group chat、evacuation、broadcast 等协作模式，能按消息类型分发。
  3. 通过状态/事件驱动和组织化调度管理多个 agent 的执行时序。
  4. 支持 Agent Service 单独启动，客户端可远程调用 agent，适合横向扩展。
  5. 内置工具调用、动态配置和调度能力，降低应用级 Agent 开发成本。
- Climber 映射:
  - `app/core/collaboration/base.py`: 统一 `_dispatch_by_process_type`，向 sequential/hierarchical/group_chat 分发，对应 Team 调度。
  - `app/core/collaboration/group_chat.py` 和 `hierarchical.py`: 对应用户级协作和广播/委派模式。
  - `app/core/task_worker.py`: `TaskManager.slot()` 信号量控制并发，`settings.max_concurrent_subtasks` 默认 3、上限 18。
  - `app/config.py`: `_clamp_max_concurrent_subtasks` 对并发配置做安全钳制，`test_concurrency_limits.py` 明确验证默认和上限。
- 落地状态: 部分落地。并发控制、信号量、协作引擎和部分 group chat 已有；AgentScope 式独立 Agent Service 和边缘/分布式调度尚未成体系。
- 证据等级: `verified`

## 5. AutoGPT

- 一句话定位: 自主 Agent 平台的代表，核心是持续 “think-reasoning-act/observe” 的 long-running goal-to-result 循环，现在同时演化为 Agent 平台和可视化 builder。
- 机制精华:
  1. Agent 循环持续观察、推理、决策、调用工具并收集结果，直到目标完成。
  2. 任务被拆成多阶段计划，而不是一次大 prompt。
  3. 平台层将流程抽象为 blocks、agents、workflows，支持可视化拖拽构建。
  4. 记忆分为短期和长期知识结构，供后续步骤复用。
  5. 通过 event/stream 输出执行过程，便于 UI 实时展示。
- Climber 映射:
  - `app/core/task_worker.py`: `handle_factory_run` 实现 目标 -> `_build_factory_plan` -> `_parse_factory_plan` -> `_precheck_plan_steps` -> 顺序执行 -> 结果合成。
  - `_retry_or_fail` 和步骤级重试实现持续观察、失败恢复；副作用步骤豁免重试。
  - `app/core/task_state_machine.py`: pending/running/completed/failed 等状态由 `TaskStateMachine` 明确管理。
  - `tests/test_factory_plan_precheck.py` 与 `tests/test_factory_path_regressions.py` 覆盖计划预检和工具路径回归。
- 落地状态: 已落地。计划式工厂执行、步骤预检、副作用保护和合成路径都真实存在，但没有 AutoGPT 式的可视化 block builder。
- 证据等级: `verified`

## 6. Griptape

- 一句话定位: 模块化 Python Agent 框架，把 Agent 系统显式切成 Structures、Tasks、Engines、Tools、Memory、Drivers 多层。
- 机制精华:
  1. 最上层 Structures 分 `Agent`、`Pipeline`、`Workflow`、`AgentOrchestrator`，分别对应单一、链式、有向图和编排执行。
  2. Task 持有输入、工具、memory 和输出，可被 structure 调度。
  3. Engines 抽取 query、extraction、summarization、image generation 等核心能力，供不同 structure 复用。
  4. Drivers 抽象 model、file、image 等外部资源，便于替换后端。
  5. 提供 policies、observability 和自定义工具注册机制。
- Climber 映射:
  - `app/core/engine/` 的 `agent_engine`、`react_loop`、`parallel`、`subagent` 提供分层引擎，近似 Griptape Engines 位置。
  - `app/tools/builtins.py`: 文件、网络、计算、图片、命令等工具集合对应 Griptape Tools。
  - `app/core/collaboration/checkpoint.py` 与 engine/pregel checkpoint: 提供记忆和状态持久化，对应 Memory/Storage。
  - `app/core/task_worker.py`: 任务级和步骤级重试，但缺少 Griptape 风格的独立 Driver 接口。
- 落地状态: 已落地。引擎、工具、记忆/checkpoint 分层已有，但 Driver 抽象尚未统一整理。
- 证据等级: `inferred`

## 7. Haystack

- 一句话定位: 生产级 NLP/RAG 框架，核心是 components 与 pipeline，把数据处理、检索、Agent 和模型调用连接成可维护、可观测的图。
- 机制精华:
  1. 组件有严格输入/输出 schema，pipeline 在连接时做类型检查，避免运行时才知道接口错误。
  2. 支持条件分支、重试、错误转换和数据验证，使流水线可投入生产。
  3. 提供 Agent 和 Tool 组件，能把工具调用作为一个普通 pipeline 节点。
  4. 官方连接器覆盖模型、embedding、检索和数据库等供应商。
  5. 内建 tracing/logging，可对接 Langfuse 等观测后端。
- Climber 映射:
  - `app/core/task_worker.py`: `_retry_or_fail` 和步骤级 retry 构成双重重试语义。
  - `app/core/collaboration/agent_runner.py` 与 guardrails: 执行后返回、验证、重试和 fallback，接近 pipeline 错误处理。
  - `_precheck_plan_steps.py` 对应 pipeline 节点执行前的 schema/能力预验证。
  - `app/core/task_state_machine.py`: 状态转换 guard 和 hooks 起错误路由作用。
- 落地状态: 已落地。重试、预检、验证、hook 和状态机路径存在，并由回归测试覆盖；尚未实现 Haystack 式可视化 pipeline。
- 证据等级: `verified`

## 8. Prefect

- 一句话定位: durable workflow orchestration 框架，以 flows/tasks 描述有依赖、可重试、可调度、可观测的后台工作。
- 机制精华:
  1. Flow 是调用链，Task 是单元；task 间依赖形成调度图。
  2. 内置 retries、timeouts、exponential backoff 和并发限制。
  3. Work pools/queues 分配 worker，任务以 lease 方式领取执行。
  4. Deployments + schedules 支持长期运行、远程执行和指定参数启动。
  5. Events/automations 和 UI 提供生命周期洞察。
- Climber 映射:
  - `app/core/task_worker.py`: `TaskManager` 用 `slot()` 做并发门闩、claim 任务行、`_run_task`、`_retry_or_fail`、`recover_pending_tasks`。
  - `app/api/v1/routes/tasks.py`: POST 提交、GET 查询、POST `/cancel`，对应任务生命周期 API。
  - `app/core/task_state_machine.py`: 任务状态持久化和转换规则，是 Prefect flow/task state 的轻量版。
  - `tests/isolated/test_review6_task_recovery.py`: 覆盖 never-started pending 恢复路径。
- 落地状态: 部分落地。并发、重试、取消、状态和恢复已有；缺少 worker pool、队列租约延期、背压、调度和分布式引擎。
- 证据等级: `inferred`

## 9. OpenAgents

- 一句话定位: 当前是一个 coding agents collective 平台，核心是 agent loop、插件/评测生态和 durable sessions/tasks；早期版本则以工具调用和任务替代执行为主。
- 机制精华:
  1. 将 agent 运行、online judge/eval 和 worker 拆分，便于规模化评测和部署。
  2. agent 循环会记录 session 与 task，支持中断、恢复和结果查询。
  3. 插件以标准包结构复用，平台提供运行时和执行入口。
  4. 提供 Coder、Verse、Gym 等应用套件验证不同 agent 能力。
  5. 强调码流式日志和任务状态，而不是简单同步返回结果。
- Climber 映射:
  - `app/core/task_worker.py`: `AutoLoopTask` 持久化、`submit`、`emit_event`、`cancel`、`recover_pending_tasks` 构成任务生命周期。
  - `app/api/v1/routes/tasks.py`: `POST /tasks`、`GET /tasks/{id}`、`POST /tasks/{id}/cancel`。
  - `app/api/v1/routes/chat_commands.py`: `/retry` 重新执行最后一条用户消息。
  - `app/core/session.py` 与 `app/core/collaboration/checkpoint.py`: session/checkpoint 恢复支撑 durable 执行。
- 落地状态: 已落地。任务持久化、查询、取消、重试和部分恢复测试存在；插件市场/online judge 版块尚未落地。
- 证据等级: `verified`

## 10. TaskWeaver

- 一句话定位: 代码优先的数据分析 Agent，把用户请求转换成可执行代码，在受控 session 中验证并运行。
- 机制精华:
  1. Planner 生成代码、状态和说明文本，并维护整个 session 的执行计划。
  2. Recepta 在 session 内执行代码，自动补齐 API 片段和运行环境。
  3. 执行前做验证，识别未知函数、语法和风险，再决定是否放行。
  4. 执行失败后 reflection 回读错误并重试，形成状态化迭代。
  5. 数据分析过程以代码执行历史和数据帧为上下文，避免大文本重复传递。
- Climber 映射:
  - `app/core/task_worker.py`: `_precheck_plan_steps` 具备步骤级能力预检，但不生成任意 Python 代码。
  - `app/tools/builtins.py`: `run_command`、`stream_command`、`container_exec` 提供受控命令执行和危险命令 blocklist。
  - `app/core/task_state_machine.py`: 状态链路支撑“计划 -> 执行 -> 失败 -> 重试”的骨架。
  - 缺少通用沙箱 executor、未知函数检查、代码验证和 reflection 循环。
- 落地状态: 待落地。命令校验、计划预检和状态恢复已有雏形；TaskWeaver 式“计划代码 + 验证后执行 + 失败反思”尚未实现。
- 证据等级: `inferred`

## 11. Agno

- 一句话定位: Agent SDK/平台（原 Phidata），用 `Agent = Model + Tools + Knowledge + Memory` 构建轻量智能体，并提供 AgentOS 运行时方向。
- 机制精华:
  1. Agent 把模型、工具、知识和记忆组合成单个可运行对象，支持 stream、async 和附件。
  2. 工具可多轮调用，多个工具结果可并行执行并统一回灌模型。
  3. AgentTool 让一个 Agent 调用另一个 Agent，形成 team 而非只有工具调用。
  4. 提供 storage/sessions，使 agent 状态可恢复。
  5. AgentOS/Agent Controls 负责运行时和 UI 交互状态。
- Climber 映射:
  - `app/core/parallel.py`: `ParallelToolExecutor.execute_all` 已支持工具级并行或顺序执行。
  - `app/tools/__init__.py` 与 `app/tools/builtins.py`: 模型调用、工具注册和权限校验已拆分。
  - `app/core/engine/subagent.py`: 子 Agent 有并发上限，与 Agno team 运行有对应关系。
  - 缺少 AgentOS 式控件运行时，会议/议事式 UI 状态只有部分事件流。
- 落地状态: 部分落地。工具并行执行、子 Agent 并发和工具注册存在；AgentOS 控件运行时和交互状态机未落地。
- 证据等级: `inferred`

## 12. AutoGen / AG2

- 一句话定位: 多 Agent 对话编程框架，核心是 message-driven conversational agents；官方 AutoGen 已进入 maintenance mode，社区 AG2 继续维护该方向。
- 机制精华:
  1. Conversational agents 通过消息收发轮转执行，而非静态函数调用。
  2. GroupChat 由 Manager 选择下一发言者，管理多 Agent 对话轮次。
  3. AgentTool 允许一个 Agent 将另一个 Agent 作为工具调用，形成嵌套 agent。
  4. 支持 handoff/delegation 和终止条件，避免无限对话。
  5. 官方迁移方向是 Microsoft Agent Framework，但 AutoGen/AG2 的会话模式仍是重要参照。
- Climber 映射:
  - `app/core/collaboration/base.py`: `GroupCollaborationEngine` 分发 sequential/hierarchical/group_chat，对应对话流程调度。
  - `app/core/collaboration/group_chat.py`: 群聊发言选择和上下文管理，对应 GroupChatManager。
  - `app/core/collaboration/handoff.py` 与 `app/tools/builtins.py`: `HandoffRequest`、`HandoffMessage`、`handoff_task` 实现 Agent 交接。
  - `app/core/collaboration/a2a_protocol.py`: 以 A2A 消息协议承载多 Agent 通信。
- 落地状态: 部分落地。群聊、handoff、A2A 和死锁检测有实现及 `test_collaboration_deadlock.py`、`test_critical_regressions.py` 覆盖；终止条件、发言者策略和协议兼容仍需完善。
- 证据等级: `verified`

## 汇总

| # | 项目 | 落地状态 | 证据等级 |
|---|------|----------|----------|
| 1 | LangGraph | 已落地 | verified |
| 2 | CrewAI | 部分落地 | verified |
| 3 | smolagents | 已落地 | verified |
| 4 | AgentScope | 部分落地 | verified |
| 5 | AutoGPT | 已落地 | verified |
| 6 | Griptape | 已落地 | inferred |
| 7 | Haystack | 已落地 | verified |
| 8 | Prefect | 部分落地 | inferred |
| 9 | OpenAgents | 已落地 | verified |
| 10 | TaskWeaver | 待落地 | inferred |
| 11 | Agno | 部分落地 | inferred |
| 12 | AutoGen/AG2 | 部分落地 | verified |

统计: `verified: 8, inferred: 4, unavailable: 0`，共 12 个项目。

## 最优先实施建议

1. 打通 durable step checkpoint 与任务恢复：当前 `recover_pending_tasks` 只恢复从未启动的任务，running/retrying 行要求人工复查；应把 `handle_factory_run` 的每步结果写进 checkpoint，并用 `session.restore_checkpoint` 或 engine/pregel checkpoint 支持从具体步骤恢复。这是 LangGraph、Prefect、OpenAgents 三个项目共向给出的最高杠杆缺口。

2. 给副作用步骤增加 dry-run 和人工审批断点：`_precheck_plan_steps` 已能识别只读/副作用和未知工具，但 `_factory_permission_mode` 目前更多是跳过或放行；应把 LangGraph HITL 与 TaskWeaver 验证语义落成“执行前预览 + 通过/拒绝 + 恢复”的可选审批步骤。

3. 让独立 factory 步骤按有界并发并行执行：当前 factory 是顺序步骤，且 `ParallelToolExecutor` 已经能并行工具调用，但没有被 factory 编排使用；应沿用 `TaskManager.slot()` 和 `settings.max_concurrent_subtasks` 约束，对无依赖步骤并行执行，同时保留步骤级状态、重试和合成。这是 Agno、AgentScope 和 Pregel 超步模型提供的最直接增量。