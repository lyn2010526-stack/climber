# AGI P0 后端源码证据

核查日期：2026-10-02。证据范围为当前工作区及公开 GitHub API/tree/raw；只读取第三方源码与 README，全程未安装、启动第三方 Agent，未创建演示站，未读取 Agent 环境模型 Key，未 commit。

## 当前代码核查

| 研究断言 | 实际证据 | 本轮处理 |
|---|---|---|
| gap-analysis 第 118/151 行称评估整体缺失 | 开工时已有未跟踪 `app/core/evaluation/{models,runner,judges,baseline,scenarios,report_store}.py` | 沿用并补齐，保留已有工作 |
| sub_agent 使用 len(goal)*10 / iterations=3 | 开工时已有注入 executor 与 real_execution；仅关闭开关分支仍生成假成功 | 移除假执行分支，禁用/缺 executor/空输出/超预算明确 failed |
| hypothesis 完全静态 | 已有 WorldState、HypothesisBelief、verifier 与 causal observation | 保留启发式，增加 model_judgment / heuristic / experiment 独立标签 |
| conclude 产出更新提案 | `MetacognitionOrchestrator.conclude` 返回 AttributionResult，无自动提案发布协议 | 增加显式双集 `evaluate_proposal` 门禁；本轮未接生产自动激活 |
| engine/subagent.spawn 可以直接跑真实任务 | spawn 接受 runner 回调，自身负责生命周期与限制；实际执行依赖 caller | 通过现有 create_session/run 公共接口构造注入适配，engine 文件只读 |
| active-plan 第 114 行允许失败降级 | 子任务执行失败必须保留 failed；模型可保留标注 heuristic 的估计 | 失败估计与真实执行结果独立记录 |

已只读核对 `agent_engine.create_session`、`engine/subagent.spawn`、Principal ContextVar 与 AgentSession.stop。执行适配保留 user_id、Principal、权限配置、真实 DONE token、session iteration；每个候选使用新 session。工具权限校验继续由已有引擎负责。

## 获取协议

每仓库先访问 `https://api.github.com/repos/{owner}/{repo}`，再访问 `/git/trees/{default_branch}?recursive=1`，记录响应 SHA。随后访问固定 SHA 的 raw 文件。树响应均为 `truncated=false`。下列链接全部为本轮实际读取的固定版本；行号以该版本为准。

### LangGraph

SHA `157a06dda988d85afeb8751ff27b35ab3f4f8bf4`。

- [README](https://raw.githubusercontent.com/langchain-ai/langgraph/157a06dda988d85afeb8751ff27b35ab3f4f8bf4/README.md)：39-41 声明持久执行、HITL、记忆。
- [checkpoint/base](https://raw.githubusercontent.com/langchain-ai/langgraph/157a06dda988d85afeb8751ff27b35ab3f4f8bf4/libs/checkpoint/langgraph/checkpoint/base/__init__.py)：读取 checkpoint saver 定义与存取协议，持久状态是独立存储契约。
- [types.py](https://raw.githubusercontent.com/langchain-ai/langgraph/157a06dda988d85afeb8751ff27b35ab3f4f8bf4/libs/langgraph/langgraph/types.py)：215-229 checkpoint 包含 state/parent/tasks；460-523 TimeoutPolicy 区分总时限与 idle 时限，明确协作式取消约束。
- [pregel/_retry.py](https://raw.githubusercontent.com/langchain-ai/langgraph/157a06dda988d85afeb8751ff27b35ab3f4f8bf4/libs/langgraph/langgraph/pregel/_retry.py)：59-107 超时解析与每次 attempt 的 task/thread/run 身份。
- 映射：采用显式 attempt/状态/超时口径；本轮保持本地 engine 持久化实现。

### AutoGen

SHA `027ecf0a379bcc1d09956d46d12d44a3ad9cee14`。

- [README](https://raw.githubusercontent.com/microsoft/autogen/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/README.md)：当前标注 maintenance mode。
- [base_group_chat](https://raw.githubusercontent.com/microsoft/autogen/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py)：680-746 pause/resume 给参与者和管理者发送 RPC；748 起 save_state。恢复能力依赖参与者协议。
- [user_proxy_agent](https://raw.githubusercontent.com/microsoft/autogen/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/src/autogen_agentchat/agents/_user_proxy_agent.py)：184 起取消感知输入，204/210 消息处理入口。
- [memory_controller](https://raw.githubusercontent.com/microsoft/autogen/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/experimental/task_centric_memory/memory_controller.py)：135-189 train/test 分离；173 执行 callback，176 grader 判断，成功数来自逐次试验。
- 映射：评估执行器与裁判分离，samples 与 k 分离；记忆学习属于实验性扩展，未声称普遍有效。

### Hermes Agent

SHA `10c6188de188871f64a88dd95bc6b262adb0c307`。

- [README](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/README.md)：19-30 宣称技能学习、跨会话用户建模和并行委派；作为产品声明单独标注。
- [session_persistence](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/agent/session_persistence.py)：1-3 SQLite transcript 去重与轨迹导出；34-60 过滤临时 recovery scaffolding 与写入 marker。
- [memory_manager](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/agent/memory_manager.py)：317-332 memory-context 包装；336 起多 provider 管理，533 sync，602 flush。包装中的“authoritative reference”仅说明源码行为，不作为本地实验可信度依据。
- [retry_utils](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/agent/retry_utils.py)：30 Retry-After 解析，121 jittered_backoff。
- [verify/runner](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/agent/verify/runner.py)：35/72 PhaseResult/VerifyResult，93 命令执行，209 run_verify；只读，未执行其命令或 readiness 服务。
- [skill_manager_tool](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/tools/skill_manager_tool.py)：42 创建开关，94/100 mutation lock，147 frontmatter 验证，350 guarded write。技能可更新机制与更新收益验证分别记账。
- [Honcho dialectic](https://raw.githubusercontent.com/NousResearch/hermes-agent/10c6188de188871f64a88dd95bc6b262adb0c307/plugins/memory/honcho/dialectic.py)：树中存在，raw 返回 HTTP 429；画像算法未取得正文证据。

### OpenHands

用户给定旧地址 `All-Hands-AI/OpenHands` 的 API 重定向到 `OpenHands/OpenHands`。SHA `2414d6ee5e31bede2e78211f72b58e9949575a75` 当前是 Agent Canvas，树中没有旧 Python agent controller。

- [README](https://raw.githubusercontent.com/All-Hands-AI/OpenHands/2414d6ee5e31bede2e78211f72b58e9949575a75/README.md)：当前 control center 与外部 backend 定位。
- [pause-event](https://raw.githubusercontent.com/All-Hands-AI/OpenHands/2414d6ee5e31bede2e78211f72b58e9949575a75/src/types/agent-server/core/events/pause-event.ts)：PauseEvent 类型契约，证据只覆盖类型。
- [with-retry](https://raw.githubusercontent.com/All-Hands-AI/OpenHands/2414d6ee5e31bede2e78211f72b58e9949575a75/src/api/with-retry.ts)：4-25 有界指数退避 API 包装。
- [旧 controller 缺失链接](https://raw.githubusercontent.com/All-Hands-AI/OpenHands/2414d6ee5e31bede2e78211f72b58e9949575a75/openhands/controller/agent_controller.py)：HTTP 404。本轮未将旧路径当成现版本目标循环证据。

### OpenAgentKernel

SHA `959fa2ab007fa9a6ceb46bf42f5a09b765a841b9`。

- [README](https://raw.githubusercontent.com/TencentCloudBase/OpenAgentKernel/959fa2ab007fa9a6ceb46bf42f5a09b765a841b9/README.md)：会话、审批、用户记忆持久化 SDK。
- [create-agent](https://raw.githubusercontent.com/TencentCloudBase/OpenAgentKernel/959fa2ab007fa9a6ceb46bf42f5a09b765a841b9/src/public/create-agent.ts)：4 底层 Claude SDK，59-64 session/resume/HITL 协议；93-103 新 session 要求 userId；106-118 resume 依赖 store。源码中的 resumed 占位值未移植。
- [in-memory permission driver](https://raw.githubusercontent.com/TencentCloudBase/OpenAgentKernel/959fa2ab007fa9a6ceb46bf42f5a09b765a841b9/src/permissions/drivers/in-memory-driver.ts)：18-55 project/conversation/toolUse 组合键与 decision 查询。
- [持久审批 driver](https://raw.githubusercontent.com/TencentCloudBase/OpenAgentKernel/959fa2ab007fa9a6ceb46bf42f5a09b765a841b9/src/permissions/drivers/cloudbase-db-driver.ts)：174 put、210 get，projectKey 贯穿。
- [session driver](https://raw.githubusercontent.com/TencentCloudBase/OpenAgentKernel/959fa2ab007fa9a6ceb46bf42f5a09b765a841b9/src/session-store/drivers/cloudbase-db-driver.ts)：146 projectKey/sessionId 索引，335/365 session summary 与 userId。
- [user-memory](https://raw.githubusercontent.com/TencentCloudBase/OpenAgentKernel/959fa2ab007fa9a6ceb46bf42f5a09b765a841b9/src/user-memory/index.ts)：39 写入用户记忆文件接口。该证据覆盖文件存储协议，画像算法仍待独立核查。

### AgentScope

旧 `alibaba/agentscope` API 重定向 `agentscope-ai/agentscope`。SHA `72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6`。

- [README](https://raw.githubusercontent.com/alibaba/agentscope/72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6/README.md)：当前 AgentScope 2.0。
- [agent](https://raw.githubusercontent.com/alibaba/agentscope/72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6/src/agentscope/agent/_agent.py)：970 关闭 unfinished tool calls；1135-1180 reasoning/acting 循环，1151 HITL parked，1165 检测无进展 busy loop。
- [subagent HITL projector](https://raw.githubusercontent.com/alibaba/agentscope/72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6/src/agentscope/app/_service/_projectors/_subagent_hitl.py)：78 entry_id(worker_session_id, reply_id)，93 projection，198 resolve。
- [agentic memory middleware](https://raw.githubusercontent.com/alibaba/agentscope/72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6/src/agentscope/middleware/_longterm_memory/_agentic_memory/_middleware.py)：513-566 有预算的 MEMORY.md 系统上下文，709 文件检索。画像相关文本出现在 memory 使用说明中，未证明独立画像学习收益。

### OpenAI Agents Python

SHA `a575a6e637feb9aea1b591237b007dd4991ddfba`。

- [README](https://raw.githubusercontent.com/openai/openai-agents-python/a575a6e637feb9aea1b591237b007dd4991ddfba/README.md)：HITL/session/guardrail 为独立概念。
- [session](https://raw.githubusercontent.com/openai/openai-agents-python/a575a6e637feb9aea1b591237b007dd4991ddfba/src/agents/memory/session.py)：53-91 get/add/pop/clear 存储协议。
- [run_state](https://raw.githubusercontent.com/openai/openai-agents-python/a575a6e637feb9aea1b591237b007dd4991ddfba/src/agents/run_state.py)：790-845 可序列化 pause/resume 边界，审批/usage/history，默认 max_turns=10；pending write 恢复避免重跑工具。
- [session_persistence](https://raw.githubusercontent.com/openai/openai-agents-python/a575a6e637feb9aea1b591237b007dd4991ddfba/src/agents/run_internal/session_persistence.py)：699 保存，889 pending write 恢复，997 rewind，1104 等待清理。
- [retry](https://raw.githubusercontent.com/openai/openai-agents-python/a575a6e637feb9aea1b591237b007dd4991ddfba/src/agents/retry.py)：117 RetryDecision 分离 retry 与 unsafe replay approval；143 policy context；默认副作用重试需独立授权。
- [run.py](https://raw.githubusercontent.com/openai/openai-agents-python/a575a6e637feb9aea1b591237b007dd4991ddfba/src/agents/run.py)：tree 存在，raw read timeout；目标循环正文证据本轮未取得，max_turns 证据来自 run_state。

### CrewAI

旧 `joaomdmoura/crewAI` 当前 README 指向 `crewAIInc/crewAI`。SHA `8078f9130c35a47be95d4a55bf1d73b3fd44fc88`。

- [README](https://raw.githubusercontent.com/joaomdmoura/crewAI/8078f9130c35a47be95d4a55bf1d73b3fd44fc88/README.md)：Crews 与 Flows 的自治/事件控制定位。
- [checkpoint_listener](https://raw.githubusercontent.com/joaomdmoura/crewAI/8078f9130c35a47be95d4a55bf1d73b3fd44fc88/lib/crewai/src/crewai/state/checkpoint_listener.py)：113 写 checkpoint，219 事件触发配置，247 注册 handler。
- [unified_memory](https://raw.githubusercontent.com/joaomdmoura/crewAI/8078f9130c35a47be95d4a55bf1d73b3fd44fc88/lib/crewai/src/crewai/memory/unified_memory.py)：76-110 LLM 分析、scope/category/importance 与语义/时效/重要性权重；属于记忆检索机制证据。
- [llms/retry](https://raw.githubusercontent.com/joaomdmoura/crewAI/8078f9130c35a47be95d4a55bf1d73b3fd44fc88/lib/crewai/src/crewai/llms/retry.py)：100 backoff，124/166 sync/async retry，138/180 防嵌套重试。
- [human_feedback](https://raw.githubusercontent.com/joaomdmoura/crewAI/8078f9130c35a47be95d4a55bf1d73b3fd44fc88/lib/crewai/src/crewai/flow/human_feedback.py)：149 feedback result、218 pre-review、226 distilled lessons、337 distill/store；更新载体与收益验证分开。

## 缺失与访问异常

唯一确认 404 的文件为 OpenHands 旧 controller，完整链接见上。Hermes Honcho 为 HTTP 429；OpenAI run.py 为读取超时；这两项均属于正文访问未完成。LangGraph 初次 TLS 超时、部分 README、Hermes session_persistence、OAK create-agent、CrewAI memory 首次超时，后续重试均读取成功。路径存在、访问失败、算法缺失三种情况分别记录。

## 本轮实现与验证边界

- 评估：注入 runner/judge、每候选超时与 token 检查、失败轨迹强制不过、Rubric any/essential/veto、空规则 fail-closed、LLM boolean 严格解析、稳定场景 ID、轨迹报告、samples/k 分离与 pass@k 估计、观察到的 Pass^k。
- 回归：保留 passed 布尔基线，避免同分 veto 退化漏检；双集门禁要求边界/保留集逐候选通过及 baseline 无退化，输出审计结果，不自行激活。
- 子任务：注入结构化执行结果/兼容已存在 tuple 协议；真实报告的 token/iteration，禁用与失败明确 failed，完成释放容量，取消执行协程和 pending 队列，保留总预算与 timeout。
- 证据：模型判断 `model_judgment`；启发式 `heuristic`；显式实验 callback 的观测为 `experiment`。实验 callback 必须返回 success/observed_state/evidence；可信性仍依赖调用方提供的执行器和环境。
- 生产接线边界：提供 `make_engine_agent_fn` / `make_engine_subtask_executor` / `MetacognitionOrchestrator.run_experiment` 注入入口。本轮保持 engine/API/frontend 只读；生产主循环尚需调用方显式注入用户模型/runner。默认不配置凭据时 fail-closed。
- 数据集边界：现有三个 builtin 样例用于结构测试，未取得生产 WS 轨迹，未声称构造 20-50 个真实边界样本。

定向 pytest 使用 `--noconftest -o addopts=''`，避开根 conftest 的共享数据库 DELETE 清理。新增测试均为 scripted/fake；现有 cycle/causal 为确定性单测。真实模型与真实工具任务验证待用户自备项目凭据与评估数据。

## 最终定向验证

- 2026-10-02：`python3 -m pytest --noconftest -o addopts='' tests/core/test_evaluation_p0.py tests/core/test_metacognition_real_execution.py tests/core/test_metacognition_cycle.py tests/core/test_causal_observations.py -q`，27 passed。新增覆盖非有限/越界模型置信度拒绝，以及超预算和取消时引擎异步事件流关闭。
- 对 evaluation、四个本轮 metacognition 文件和两个新增测试运行 Ruff 全规则检查，仍有 30 项诊断，涉及类型导入、异常组织、未使用兼容参数和简化建议；完整 Ruff 尚未通过。E/F/I 子集检查结果为 `All checks passed!`，覆盖语法、名称、导入和行宽。
- 工作区包含大量既有 API、engine、frontend 和其他模块修改。本轮保留这些改动；验证范围为上述四个测试文件，全仓回归和生产主循环接线仍待后续验证。
