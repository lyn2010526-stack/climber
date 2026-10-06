# 世界模型参考项目 #13-20 深挖（ReasonWorld / SocraticAgents / CausalGraphGen / PyMC / SymbolicAI / miniWORLD / Self-Consistency / ThinkAgent）

> 核验日期：2026-10-01。
> 方法：只读研究，不修改代码。先核验 `docs/references/open-source-projects.md` 中 #13-20 给出的 8 个仓库地址；可访问仓库只读 README 与关键源码文件，不可访问仓库不虚构源码或行号。
> 证据口径：
> - `verified`：本会话实际访问外部仓库/源码，或实际读取本仓文件。
> - `unavailable`：给定仓库地址 404，未取得该仓库源码。
> - `inferred`：依据已掌握知识、公开论文摘要或设计文档推演，未取得对应仓库源码。
> 网络核验结果：8 个给定地址中仅 #16 PyMC 返回 200；#17/#18 存在可访问的相近公开仓库；#13/#14/#15/#19/#20 返回 404 且未找到可信替代源码。

## 核验记录

| # | 项目 | 给定地址 HTTP | 本次核验结论 |
| --- | --- | --- | --- |
| 13 | ReasonWorld | 404 | 无可用源码；未找到可信替代仓库 |
| 14 | SocraticAgents | 404 | 搜索仅出现 `SocraticAgents/special-guide`，与索引描述不匹配；无可用源码 |
| 15 | CausalGraphGen | 404 | 搜索仅出现 `L-F-Z/CausalGraphGenerator`（CEE 网页项目），与索引描述不匹配；无可用源码 |
| 16 | PyMC | 200 | 官方仓库 `pymc-devs/pymc` 可访问，README 与关键源码文件已只读核验 |
| 17 | SymbolicAI | 404 | 可访问相近公开仓库 `Xpitfire/symbolicai`，README 标题为 A neuro-symbolic perspective on LLMs；搜索结果同时出现 `ExtensityAI/symbolicai` |
| 18 | miniWORLD | 404 | 可访问相近公开仓库 `Farama-Foundation/Miniworld`，是 3D 环境模拟器，不是已训练世界模型 |
| 19 | Self-Consistency | 404 | 无官方仓库源码；论文为 ICLR 2023 Self-Consistency Improves Chain of Thought Reasoning in Language Models，公开摘要已核验 |
| 20 | ThinkAgent | 404 | 搜索未发现与索引描述匹配的仓库；无可用源码 |

## Climber 元认知模块现状（本仓只读核验）

| 文件 | 已确认接口/机制 |
| --- | --- |
| `app/core/metacognition/monitor.py` | `MetaCognitionMonitor.record_call/record_token_usage/analyze`；检测冗余调用、上下文超限、目标漂移、工具误用、能力缺口，输出 `MonitoringResult.health_score` |
| `app/core/metacognition/causal.py` | `CausalAttribution.log_event/analyze/_build_chain`；把执行日志建成线性因果链，按错误/幻觉/能力/上下文/规划做启发式根因分类 |
| `app/core/metacognition/hypothesis.py` | `HypothesisSimulator.simulate/_generate_paths/_estimate_success/_score_path`；生成 direct/explore_first/parallel/iterative 4 类执行路径，按估算 token 和成功率选路径 |
| `app/core/metacognition/orchestrator.py` | `MetacognitionOrchestrator.initialize/pre_action/post_action/conclude/adjust_goal`；已串联 monitor、causal、hypothesis、goal_adjuster，但 attribution 没有回灌下一轮假设 |
| `app/core/metacognition/goal_adjuster.py` | `GoalDynamicAdjuster.assess_feasibility/adjust/_generate_alternatives`；按失败次数、能力缺口、目标宽度建议改小范围或替代路径 |
| `app/core/reasoning/` | 已有 `ReasoningPipeline`、`CandidateScorer.score/select_best`、`SelfRefineLoop`、`ReflectionMemory`；是现有 eval/反思接点 |
| `tests/` | 本次检索未发现 monitor/causal/hypothesis/orchestrator/goal_adjuster 的直接测试引用；仅检索到 judgment/safety_gate/canary 等元认知测试 |

## #13 ReasonWorld（LLM 世界模型）

- 定位：设计索引描述为 LLM 世界模型、多假设并行置信打分；给定仓库 404，无法源码核验。
- 机制精华（inferred）：环境观测编码为状态；对候选下一状态/行动后果生成多条假设；前向推演后按似然或一致性打分；高不确定时主动探测；收到真实观测后更新置信度。实现细节无源码证据。
- Climber 映射：
  - `app/core/metacognition/hypothesis.py` 的 `HypothesisSimulator.simulate` 是最接近原型，但当前假设对象是执行路径，不是世界状态。
  - `app/core/metacognition/orchestrator.py` 的 `MetacognitionOrchestrator.initialize/post_action` 可承载“预测-观测-更新”，目前没有观测回灌。
- 已实现原型：多路径生成、token/成功率估计、路径排序选择。
- 缺失闭环：无 `WorldState` 表示；无下一状态预测；无后验置信更新；无主动探测触发；无观测与预测误差回灌。
- 下一步接法：扩展 `HypothesisSimulator`，增加 `predict_next_state` 与 `update_belief`；在 `MetacognitionOrchestrator.post_action` 中把工具结果作为观测，比较预测状态并更新假设权重；高不确定性时通过 `pre_action` 返回探测动作。
- 证据等级：仓库 `unavailable`；机制 `inferred`；Climber 映射 `verified`。

## #14 SocraticAgents（自省元认知 / 矛盾检测）

- 定位：设计索引描述为自省元认知、检测推理内部矛盾；给定仓库 404，无源码核验。
- 机制精华（inferred）：通过苏格拉底式追问暴露假设、收集证据、检查不同陈述之间的逻辑矛盾，再修正结论。内部实现无源码证据。
- Climber 映射：
  - `app/core/metacognition/monitor.py` 的 `MetaCognitionMonitor.analyze` 已检测冗余调用、幻觉模式、目标漂移，但缺少跨语句/跨候选的逻辑一致性检查。
  - `app/core/reasoning/components/self_refine.py` 已有 critique 结构，可作为矛盾检测的载体。
- 已实现原型：`MonitoringResult` 输出缺陷列表和健康分；`SelfRefineLoop` 已有批判-修正循环。
- 缺失闭环：没有把多次回答/多条候选抽取为可比较命题；没有矛盾判定；没有“自我质疑-收集证据-修正”的原生回路。
- 下一步接法：在 `MetaCognitionMonitor` 增加 `_check_contradictions(candidates)`，复用 `app/core/reasoning/base.py` 的 `Candidate`/`CritiqueResult` 契约；`MetacognitionOrchestrator.conclude` 用矛盾项驱动下一轮 `HypothesisSimulator.simulate`。
- 证据等级：仓库 `unavailable`；机制 `inferred`；Climber 映射 `verified`。

## #15 CausalGraphGen（时序交互数据自动挖掘因果图）

- 定位：设计索引描述为从时序交互数据自动挖掘因果图；给定仓库 404，无源码核验。
- 机制精华（inferred）：变量/动作/状态作为节点，时间上先后的动作-结果形成有向边；从交互序列统计边置信度；新观测到达时增量更新；支持查询“该动作在此状态下最可能产生什么结果”。实现细节无源码证据。
- Climber 映射：
  - `app/core/metacognition/causal.py` 的 `CausalAttribution.log_event/analyze` 是最近原型，但它只建线性失败链，不做图学习。
  - `app/core/metacognition/orchestrator.py` 的 `post_action` 已把工具调用写入 `CausalAttribution.log_event`，是训练因果图所需的原始数据来源。
- 已实现原型：失败根因分类、`CausalNode.causal_chain`、`AttributionResult.confidence`。
- 缺失闭环：无因果图数据结构；无边的自动发现；无边置信度与衰减；无“状态+动作→结果”查询接口。
- 下一步接法：在 `app/core/metacognition/causal.py` 增加 `CausalGraph` 与 `update_graph`；`post_action` 记录 `(state, action, next_state, outcome)`；`_analyze_failure` 改为查询图路径而非只匹配启发式关键词；`goal_adjuster` 使用图置信度判断目标是否可行。
- 证据等级：仓库 `unavailable`；机制 `inferred`；Climber 映射 `verified`。

## #16 PyMC（概率编程 / 不确定性度量）

- 定位：官方仓库 `pymc-devs/pymc` 可访问，README 明确是 Bayesian statistical modeling 的 Python 包，底层依赖 PyTensor，提供 MCMC 采样与变分推断。
- 机制精华（verified，文件级）：`Model` 上下文（`pymc/model/core.py` 的 `Model`/`register_rv`/`add_coord`）定义随机变量；`Distribution`/`Continuous`/`Discrete`（`pymc/distributions/distribution.py`）描述分布；`sample`（`pymc/sampling/mcmc.py`，含 `draws/chains/cores`）做后验采样；`sample_prior_predictive`/`sample_posterior_predictive`（`pymc/sampling/forward.py`）做前验/后验预测与校准。
- Climber 映射：
  - `app/core/metacognition/hypothesis.py` 的 `estimated_success_rate` 是单点启发式，可用后验分布替代。
  - `app/core/metacognition/causal.py` 的 `AttributionResult.confidence` 是固定启发式置信度，可改为因果后验。
  - `app/core/metacognition/monitor.py` 的 `health_score` 可用概率区间表达，避免单一阈值误判。
- 已实现原型：无 PyMC 依赖，无贝叶斯不确定性模块。
- 缺失闭环：假设成功率不是分布；因果根因没有置信区间；监控健康分没有校准。
- 下一步接法：先抽象 `UncertaintyEstimator` 接口，把 `HypothesisSimulator._estimate_success` 与 `CausalAttribution.confidence` 接到该接口；需要真实概率编程引擎时用 PyMC 实现贝叶斯版本，不把 PyMC 调用散落到各模块。
- 证据等级：仓库与源码入口 `verified`；Climber 集成方案 `inferred`；Climber 现状 `verified`。

## #17 SymbolicAI（符号-神经混合可解释表征）

- 定位：给定 `xorbitsai/symbolicai` 404；可访问 `Xpitfire/symbolicai`，README 定位为 neuro-symbolic framework，把 Python 编程与 LLM 的可编程性结合。
- 机制精华（verified，README/源码入口）：`Symbol` 对象区分 syntactic/semantic 两种行为；`Expression` 继承 `Symbol`（`symai/symbol.py` 的 `Expression`/`__call__`）；README 强调 Design by Contract，对 LLM 输出做数据模型与校验约束，失败可自动补救。
- Climber 映射：
  - `app/core/metacognition/causal.py` 的 `CausalNode` 是可解释符号层雏形，但没有组合算子。
  - `app/core/reasoning/components/self_refine.py` 的 `_CRITIQUE_SCHEMA` 与 `CritiqueResult` 已是轻量“契约校验”载体。
  - `app/core/metacognition/hypothesis.py` 的 `ExecutionPath.steps` 可表达为符号表达式，当前仍是普通 dict。
- 已实现原型：无符号-神经混合表征；现有结构化 critique 是最接近契约校验的实现。
- 缺失闭环：无 `Symbol`/`Expression` 抽象；无“LLM 输出必须满足声明式约束”的强制层。
- 下一步接法：在 `app/core/metacognition/` 增加轻量 `CausalFact`/`HypothesisExpression` 数据契约，复用 `CritiqueResult` 做类型化校验；SymbolicAI 只作设计参考，不直接引入依赖。
- 证据等级：可访问仓库与源码入口 `verified`；Climber 集成方案 `inferred`；Climber 现状 `verified`。

## #18 miniWORLD（仿真世界模型 / 环境模拟器）

- 定位：给定 `mini-world-ai/miniworld` 404；可访问 `Farama-Foundation/Miniworld`，README 定位为 minimalistic 3D interior environment simulator for RL and robotics，是 Gymnasium 环境。
- 机制精华（verified，源码入口）：`MiniWorldEnv(gym.Env)`（`miniworld/miniworld.py`）提供 `reset/step/render`，`action_space` 为 `Discrete`，`observation_space` 为 `Box`；`miniworld/envs/__init__.py` 注册 `MiniWorld-Hallway-v0` 等环境。它是提供观测与真实动力学的模拟器，不是可学习的预测世界模型。
- Climber 映射：
  - `app/core/metacognition/hypothesis.py` 需要 `(observation, action) -> predicted_next_state`，当前无此接口。
  - `app/core/metacognition/causal.py` 需要 `(state, action, next_state)` 三元组做因果学习，当前只记录 `(iteration, action, outcome)`。
  - `app/core/metacognition/monitor.py` 需要真实观测与预测的误差，当前只比较文本/工具痕迹。
- 已实现原型：无环境适配层、无世界状态结构。
- 缺失闭环：没有仿真环境接入；没有观测-动作-下一观测轨迹生成；没有预测误差评估。
- 下一步接法：建立 `EnvironmentAdapter` 抽象，MiniWorld 仅作为合成 benchmark：生成轨迹喂给 `CausalAttribution.update_graph`，用预测状态与 `MiniWorldEnv.step` 真实状态计算 `monitor.prediction_error`；不把 MiniWorld 作为 Climber 运行时依赖。
- 证据等级：仓库与源码入口 `verified`；Climber 集成方案 `inferred`；Climber 现状 `verified`。

## #19 Self-Consistency（多条推理路径比对）

- 定位：给定 `yizhongw/self-consistency` 404，无官方仓库源码；论文为 ICLR 2023 Self-Consistency Improves Chain of Thought Reasoning in Language Models，公开摘要已核验。
- 机制精华（inferred，基于公开论文摘要）：用 CoT 提示；采样多条多样化推理路径；把推理路径边际化，按答案一致性选择最一致答案。
- Climber 映射：
  - `app/core/metacognition/hypothesis.py` 的 `_generate_paths` 生成固定 4 类路径，不做随机采样；`_score_path` 按启发式分数选路径，不做答案一致性聚合。
  - `app/core/reasoning/components/scorer.py` 的 `CandidateScorer.select_best` 是多候选选择接点，但当前不统计答案投票。
- 已实现原型：多路径生成与选择已有，但路径是“执行策略”而非“推理答案”。
- 缺失闭环：无 temperature 采样；无答案抽取；无多数票/加权一致性；无分歧不确定性。
- 下一步接法：为 `HypothesisSimulator` 增加 `sample_answers(goal)` 与 `aggregate_by_consistency(candidates)`；在 `MetacognitionOrchestrator.conclude` 返回一致性证据；`CandidateScorer` 可增加一致性维度。
- 证据等级：仓库 `unavailable`；机制 `inferred`（论文摘要已核验，源码未核验）；Climber 映射 `verified`。

## #20 ThinkAgent（反思回路 / 自我质疑修正结论）

- 定位：给定 `thinkagent-ai/thinkagent` 404，搜索未发现匹配仓库，无源码核验。
- 机制精华（inferred）：计划-执行-观测-自我批判-修正结论的反思回路；自我质疑找出矛盾或错误，再以新结论/新计划重跑。
- Climber 映射：
  - `app/core/metacognition/orchestrator.py` 已串联 `post_action -> monitor`、`conclude -> causal`、`adjust_goal -> goal_adjuster`，是最近接点。
  - `app/core/reasoning/components/self_refine.py` 与 `app/core/reasoning/components/reflection_memory.py` 已提供批判-修正和跨轮反思记忆。
- 已实现原型：监控反馈、失败根因、目标调整三环已接；反思记忆独立存在于 reasoning 管线。
- 缺失闭环：`AttributionResult` 未回灌 `HypothesisSimulator`；`ReflectionMemory` 未接入 `MetacognitionOrchestrator`；没有“质疑上一结论并产出修订结论”的正式状态。
- 下一步接法：在 `MetacognitionOrchestrator` 增加 `reflect()`，把 `monitor.analyze`、`causal.analyze`、`CandidateScorer.score`、`ReflectionMemory.add_reflection` 合并为一条反思记录，再触发 `GoalDynamicAdjuster.adjust` 与下一轮 `HypothesisSimulator.simulate`。
- 证据等级：仓库 `unavailable`；机制 `inferred`；Climber 映射 `verified`。

## 组成完整世界模型闭环的最小设计

目标不是一次性引入所有外部依赖，而是让现有元认知模块形成可运行的 `causal graph + hypothesis + monitor + eval` 闭环。最小落地顺序如下：

1. 世界状态与假设：在 `app/core/metacognition/hypothesis.py` 扩展 `HypothesisSimulator`，新增 `WorldState`、`predict_next_state(state, action, graph)`、`update_belief(observation)`；保留现有 `simulate/selected_path`，把“选执行路径”升级为“选最可能世界状态与行动方案”。
2. 因果图：在 `app/core/metacognition/causal.py` 扩展 `CausalAttribution`，新增 `update_graph(state, action, next_state, outcome)` 与 `query_effect(state, action)`；`CausalNode` 只保留为图上的可解释路径，`analyze` 改为从图边回溯根因。
3. 监控与预测误差：在 `app/core/metacognition/monitor.py` 扩展 `MetaCognitionMonitor`，新增 `check_prediction_error(predicted_state, actual_state)` 与 `check_contradictions(candidates)`，并入 `analyze`；`MonitoringResult` 增加预测误差与一致性指标。
4. 编排闭环：在 `app/core/metacognition/orchestrator.py` 的 `MetacognitionOrchestrator` 增加 `reflect()`；`post_action` 同时写 hypothesis 观测、causal graph、monitor 误差；`conclude` 调用 `app/core/reasoning/components/scorer.py` 的 `CandidateScorer.score/select_best` 作为 eval；`reflect()` 把 attribution、eval、reflection 输入 `GoalDynamicAdjuster.adjust`，再触发下一轮 `HypothesisSimulator.simulate`。
5. 最小验收口径：预测误差 = 预测状态与真实观测差异；因果图正确率 = 图边预测结果与后续真实结果一致率；假设一致性 = 多条候选答案/路径的一致程度；最终输出 = `CandidateScorer` 加权评分。先用 MiniWorld 或现有工具执行日志做合成轨迹，再让各指标回写 `MonitoringResult`。

## 证据等级汇总

- 外部仓库/源码可访问性：`verified` 3（#16/#17/#18），`unavailable` 5（#13/#14/#15/#19/#20）。
- 外部机制/论文依据：`verified` 3（PyMC、SymbolicAI、MiniWorld 的 README/源码；Self-Consistency 公开论文摘要另行核验，不作为源码机制证据），`inferred` 5（ReasonWorld、SocraticAgents、CausalGraphGen、ThinkAgent 的机制，以及 Self-Consistency 仓库内实现）。
- Climber 本地现状：`verified` 8（8 个项目的本地映射均实际读取本仓文件）。
- 集成方案与下一步：`inferred` 8。
- 总计：`verified` 14，`unavailable` 5，`inferred` 13。
