# 开源参考项目优点挖掘与差距清单

> 生成时间：2026-08-30
> 方法：4 个研究子代理对 17 个参考项目逐项挖掘招牌能力，并在 Climber 代码库中逐条核实等价实现（证据到文件与行号）。
> 状态判定：missing / partial（缺什么）/ exists（证据）。

## 一、合并后的优先级差距清单（Top 12）

按"价值 × 落地成本 × 多源交叉验证"排序。同一主题被多个项目独立印证的排在前面。

| # | 差距 | 来源项目 | 状态 | 落地成本 | 关键证据 |
|---|------|---------|------|---------|---------|
| 1 | **工作流韧性与错误处理**：节点级重试、失败策略与恢复 | Dify + Mastra | exists | 已完成 | app/workflow/engine.py:190-230、268-300 已执行 retry 与 failure strategy；提交 460a9dce |
| 2 | **评估体系升级**：scorer 抽象与 CI 门禁 | Mastra + OpenHands + AutoGPT | exists | 已完成 | app/core/eval_scorers.py 提供 Scorer 协议与 4 类 scorer；app/core/evaluation.py:16-42 执行 gates；提交 fe2b6e4e |
| 3 | **Guardrails 接入主 agent loop**：输入、输出与可选审计 | openai-agents-python | exists | 已完成 | app/core/agent_engine.py:709、956、1202 已接入 input/output guardrails 与 OutputAuditor；提交 eeae9837 |
| 4 | **LSP 代码智能感知**：编码 agent 拿不到类型错误/编译诊断，只能靠跑测试间接验证 | opencode | exists | 已完成 | app/core/language_service.py 管理 stdio JSON-RPC、文档同步和诊断；app/tools/code_intelligence_tools.py 提供统一工具；提交 ecc9d970 |
| 5 | **Repo 级知识包与确定性触发注入**：keyword/path 触发与会话去重 | OpenHands microagents | exists | 已完成 | app/skills/registry.py:43-47、127-146；app/skills/repo_knowledge.py；提交 b35dbde3 |
| 6 | **Time-travel 引擎层**：精确恢复、历史查询与 checkpoint fork | LangGraph | exists | 已完成 | pregel/engine.py:334-376 与 graph.py:294-324 暴露 history/fork；提交 c8db612e |
| 7 | **LLM 驱动的 speaker selection**：动态选择与确定性回退 | AutoGen | exists | 已完成 | app/core/group_collaboration.py:1277、1801-1848；提交 c9eb43c8 |
| 8 | **SOP 结构化文档工件流**：无 PRD/设计稿 Artifact 类型系统与阶段门控接力 | MetaGPT | exists | 已完成 | app/core/artifacts.py 提供版本、lineage、stage gate 与 handoff audit；group checkpoint 可恢复 FINAL Artifact；提交 640badd0 |
| 9 | **画布组件可扩展模型**：节点类型前后端双向硬编码（后端 7 类/前端 5 类且不对齐），无注册机制、无类型化端口、无单节点运行 | Langflow + Dify | exists | 已完成 | app/workflow/registry.py 统一节点元数据与类型化端口；前端由元数据驱动并支持单节点运行；提交 0d3c2896 |
| 10 | **Delegation 工具注入**：agent 在 ReAct 循环中自主委派/问询同事 | CrewAI | exists | 已完成 | app/engine/hierarchical.py:49-106、225-255、530-574；提交 a16bb32d |
| 11 | **Cache-First 完整闭环**：前缀稳定已有，缺仅追加历史约束 + stale snip + 缓存命中率埋点 | deepseek-reasonix | exists | 已完成 | cache_first.py 提供 credential-scoped singleflight；PrefixCache 有条目、字节和 stale 上限；模型 adapter 暴露缓存 token 指标；提交 7712ff6d |
| 12 | **统一通道 Gateway + DM 配对安全**：仅 Telegram bot 单点，无配对/白名单；注意 channels.py 是 StateGraph 数据通道，命名误导 | openclaw | exists | 已完成 | channel_gateway.py 实施默认关闭、显式配对、TTL 与 pending 容量；外部 session deny-all tools；提交 e8e8fb02 |

## 二、次优先差距（中低价值）

| 差距 | 来源 | 状态 | 说明 |
|------|------|------|------|
| Workspace 执行环境抽象 + 远程 agent-server runtime | OpenHands | partial | 沙箱是工具级组件，决策/执行未分层；工程量大 |
| RAG 检索调优（混合权重/rerank 模型/召回测试 UI） | Dify | partial | enhanced_rag.py:85-97 RRF 无生产调用点；分块固定 500/50 |
| 子图嵌套（Command.PARENT 会被路由过滤） | LangGraph | missing | command.py:50-53 有原语但 engine.py:465-470 过滤 __parent__ |
| Send API 动态扇出（map-reduce） | LangGraph | missing | 仅静态 goto 列表 |
| 节点内 interrupt() 原语 | LangGraph | partial | 当前中断粒度是节点边界 |
| stateful 多语言 REPL（Jupyter 式内核跨消息存活） | open-interpreter | partial | 主链路无 run_python 工具 |
| GitHub resolver 自动化闭环（issue→修复→PR） | OpenHands | missing | 取决于产品定位 |
| Computer API 统一抽象 + OS 模式闭环 | open-interpreter | partial | vision_pipeline 原语在，未见闭环集成证据 |
| Prompt IDE（版本管理 + 即时调试面板） | Dify | partial | 模板 CRUD 在，无版本历史/调试面板 |
| 工作流 DSL 导出 + 版本回滚 + MCP 工具暴露 | Dify | partial | Workflow 模型无 version 字段 |
| TUI 交互模式 | opencode | missing | cli.py 是 argparse 一次性命令 |
| Session 分享链接 | opencode | missing | 无分享/公开 token 端点 |
| Onboarding 向导 | openclaw | missing | 仅 MCP server 添加向导 |
| Swarm 拓扑可选（hierarchical/mesh/adaptive） | ruflo | partial | emergent/swarm.py 固定 5 bee 且默认关闭 |
| 生命周期 hooks 扩展（27 个钩子点） | ruflo | partial | 中间件仅 5 个钩子点 |
| 分布式 actor runtime（跨进程 RPC） | agentscope | missing | worker_executor 进程内 |
| Tool-Call Repair（残缺 JSON 修复） | deepseek-reasonix | missing | json_schema.py 只校验不修复 |
| Agentic 训练数据导出（SFT/RL 格式） | hermes-agent | partial | 轨迹存储在，无批量生成与导出 |
| 多模态 RAG 索引 | agentscope | partial | 文本 only |
| Browsing rrweb 录制回放 | OpenHands | partial | 基础浏览工具在 |
| 共识协议形式化（Raft/Byzantine） | ruflo | partial | majority_vote 启发式 |

## 三、已确认优势项（exists，无需动作）

- 事件溯源事件流（OpenHands Event Stream 等价）
- CodeAgent code-as-action + 安全执行器（smolagents 等价，code_agent.py 注明灵感来源）
- ManagedAgent 层级委派、周期规划 replan（smolagents 等价）
- Tracing 三件套（OTel 风格 span 层级 + OTLP 导出，openai-agents 等价）
- Sessions 自动历史持久化、HITL 中断/恢复（openai-agents 等价）
- 安全确认流（PermissionController + 四级权限模式，超过 open-interpreter）
- StateGraph 图运行时（节点/条件边/Command 路由/checkpoint 多后端，LangGraph 等价）
- ConversableAgent 结构化消息协议 + HMAC 签名（AutoGen 等价且更强）
- role/goal/backstory 三要素 + sequential/hierarchical process（CrewAI 等价）
- Task guardrails 链（CrewAI 等价）
- 四层记忆 + 反思（超过 CrewAI/Mastra 分层）
- Executable feedback loop（MetaGPT 等价）
- 多 provider 抽象（ModelGateway + 熔断 + fallback，opencode 等价）
- 可视化工作流 builder（React Flow，AutoGPT 等价）
- 40+ 工具生态、轨迹结构化存储、skill 自创建（hermes-agent 等价）
- 推理过程可视化（ReasoningPage，不逊 reasonix）

## 四、意外发现（审查副产物）

1. **工作流恢复未接线（已解决）**——提交 460a9dce 已将节点重试与失败策略接入 WorkflowEngine
2. **输出审计未接线（已解决）**——提交 eeae9837 已将 OutputAuditor 接入主 agent loop，并保持默认关闭
3. **channels.py 命名陷阱**——实为 StateGraph 数据通道（LastValue/DeltaChannel），不是消息通道
4. **两套图引擎并存**——app/core/state_graph.py（旧，不支持循环图）与 app/core/engine/pregel/（新，功能完整），对外 API 暴露哪套未逐端点验证
5. **TaskAssignment.guardrails 字段声明后未在执行中消费**——声明了但没用
6. **enhanced_rag.py RRF 实现无生产调用点**——写好的混合检索没接线

## 五、参考项目覆盖度说明

17 个项目全部完成挖掘。其中 Top 12 高优先级差距已全部闭环；其余候选能力继续按产品定位和收益排序推进。
