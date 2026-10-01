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
| 13 | ReasonWorld | https://github.com/ReasonWorld/reasonworld | LLM 世界模型、多假设并行置信打分 | 多假设置信度博弈算法（设计 4.2.1） | 🧪 |
| 14 | SocraticAgents | https://github.com/socratica | 自省元认知、检测推理内部矛盾 | 原生元认知回路（设计 3.3） | 🧪 |

> 注：设计文档在此节后截断，第 15–50 号项目需后续补充录入（见 `docs/DESIGN.md` 完整版或用户后续提供）。

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

## 阶段路线对照（设计文档第八节）

- **阶段 1 基座工程**：上表 ✅/🔧 项 + 迁移链修复 + 死代码清理 ← 当前进行中
- **阶段 2 画像算法**：时序加权衰减、增量在线聚类、特征嵌入降维、弱监督校准（`app/core/profile/` 扩展）
- **阶段 3 遗传进化过渡**：提示词 & 参数种群进化（`app/core/prompts/` + 评估器）
- **阶段 4 agi-core**：世界模型 + 因果挖掘 + 神经进化（`ReasonWorld`/`SocraticAgents` 等结构参考）
