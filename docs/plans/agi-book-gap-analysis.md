# Climber 与《AI Agent 实战》十书差距分析

> 依据：/tmp/opencode/ai-agent-book/book/ 全部 12 个文件（7476 行，引言 + 十章 + 后记）与当前 Climber 代码树逐章比对。
> 目的：回答两个质疑——"AGI 计划没做好、认知闭环没做透"，并给出按 AGI 杠杆排序的可落地清单。
> 证据等级：所有"已实现"结论均落到 文件:行号 或测试证据；无代码证据的领域一律记为缺失。

---

## 一、全书方法论提炼（每章 3-5 条工程要点）

### 引言：Agent = LLM + 上下文 + 工具
1. Model–Harness 二分：模型负责"能做事"，Harness 负责"不做错事"（约束、验证、纠正）；评估对象是两者组合体，评价 Harness 单独也能显著拉分。
2. 工程演进主线：提示工程 → 上下文工程 → Harness 工程 → Loop 工程 → Graph 工程（2026-07），命名永远滞后于实践。
3. 飞轮论：Harness 的每段兜底代码都是"模型此刻还做不稳的地方"的记录；模型逐层内化这些能力，Harness 向新前沿迁移，永不消失。

### 第 1 章：Agent 的骨架
1. Agent = LLM + 上下文 + 工具的三层理解（实现层/直觉层/学术层）；编排光谱从工作流到自主 Agent。
2. 5 功能闭环：上下文、工具（能做事）+ 约束、验证、纠正（不做错事）。
3. Claude Code 的 Harness 典范机制：流程状态管理、多层上下文压缩、权限分类、熔断器、错误恢复。

### 第 2 章：上下文工程
1. 上下文质量大于模型能力；系统状态栏技术（把动态系统状态放进 system prompt）是低成本高收益手段。
2. 工具定义质量与工具检索：渐进式披露（OpenAI `defer_loading`、Anthropic `tool_reference`、Codex BM25 `tool_search` 默认开启）。
3. KV Cache 只增不改：前缀要稳定、append-only；压缩必须带引用（[COMPRESSED] 溯源）防重复膨胀。
4. 生产级五层压缩：工具结果预算控制 → 噪声直接删除 → API 层微压缩 → 归档式摘要 → 全量压缩带熔断器。
5. 压缩的三个动机（控制长度、提升思考质量、缓解上下文焦虑）与四条设计原则（信息价值非均匀分布、语义完整性等）。

### 第 3 章：用户记忆和知识库
1. 用户记忆与知识库是两个尺度：个体记忆 vs 集体知识库，存储、索引、验证目标都不同。
2. 记忆提取是额外 LLM 调用，遵循三条规则：选择性提取、抽象化、结构化。
3. 检索谱系：BM25 稀疏检索 → 混合检索 → 检索质量评估（LoCoMo 基准）。
4. 结构化知识提取：从非结构化文档到实体关系（CAIL2018 案例、因子重要性层次模型 + 聚类）。
5. 多模态记忆两条思路：原始数据 + 文本索引，或嵌入入上下文。

### 第 4 章：工具
1. 五类工具按"调用方向 + 作用对象"划分：感知、执行、协作、用户沟通、事件触发。
2. 感知工具要控制输出体积；执行工具要分层防护：输入验证（快速失败）→ 权限控制（黑名单 + 语义解析）→ 提议者-审核者（事前审批/事后验证）。
3. 多模态三范式：原生多模态、提取为文本、工具化多模态分析（analyze_image 等专用分析工具）。

### 第 5 章：Coding Agent 与通用 Agent
1. 通用 Agent = Coding Agent + 文件系统；coding 是元能力（能造新工具、改系统）。
2. 七个核心工具：code interpreter、bash、read、write、edit、glob、grep；四种编辑方案（旧字符串替换、行号定位、类 Vim、字符串首尾匹配）。
3. 安全"致命三要素"（Willison：私有数据 + 不受信内容 + 外部通信）+ 第 4 维：持久记忆是攻击放大器。
4. 四边界：数据边界、输入信任边界、输出影响边界、跨会话边界；OpenClaw 全权限模式是反面教材。
5. 自适应日志解析（self-evolving frontend）、生产日志智能诊断（回归测试重放 + GitHub issue via MCP）、生成式 UI/A2UI。

### 第 6 章：交互
1. 用"模态 + 执行时机"两根轴扩展观察/动作空间；回合制是模型与接口的约定，并非环境固有属性。
2. 时间尺度表：异步事件（秒-天）、语音（10ms-1s）、Computer Use（亚秒-秒）、机器人（毫秒）。
3. 语音三范式：级联 → 端到端 Omni → 全双工；快慢分离是让交互能力与智能上限分别演进的模块化选择。
4. Computer Use 视觉定位三条路线：结构化元素索引（DOM/Accessibility Tree）优先，纯视觉标注（SoM），纯坐标预测（需分辨率匹配 + 双向坐标缩放）。
5. 共享原语：唤醒、安全点、取消、抢占、快慢分离；四节共享同一控制骨架（持续感知 → 判断 → 选择 → 输出 → 观察反馈 → 继续/修正/停止）。

### 第 7 章：评估
1. 评估是 Harness 中"验证"功能的核心；评估对象是模型 + Harness 组合体；区分"模型能力不足"与"Harness 设计缺陷"（模型替换实验 vs 消融实验）。
2. 指标口径：Pass@k（能力上限）vs Pass^k（业务可靠性，连续 k 次全过 + 一票否决）；报告必须写清 k 的口径。
3. 评估环境五要素：数据集、环境状态（可重置）、工具接口（两侧原子操作）、评分标准（Rubric）、执行协议。
4. 数据集设计：验证器深度（FAIL_TO_PASS/PASS_TO_PASS）、难度分层、防泄漏（组合检索/参数化模板/金丝雀标识）、质量控制（SWE-bench Verified 淘汰 71%）。
5. 生产评估三件套：Rubric 四准则（专家指导/全面覆盖/加权/自包含）+ LLM-as-a-Judge（防长度偏差、多源异构评判）+ 失败归因（定位首个错误、结构化记录）。
6. 回归两层：端到端回归任务 + 轨迹前缀回归任务（答案 = 可接受动作集合）。
7. 内部评估五组件：消融基础设施、AB 测试方法论（机制指标 vs 目标指标）、双层特性开关、提示词敏感性评估（确定性渲染 + 版本化快照 + 回归）、隐私感知分析。

### 第 8 章：模型后训练
1. 四阶段：预训练 → Mid-training → SFT → RL；分别处理底座、协议、策略；SFT 与预训练数学上同任务（loss masking 是唯一实质区别）。
2. 诊断顺序：先排除不用改权重的方案 → 测 pass@k 判断能力支持 → SFT 立协议（不硬塞知识）→ 只在有探索空间时上 RL。
3. 数据和环境比算法重要：Mid-training 语料、示范数据、仿真环境与奖励决定成败；很多场景数据到位就不需要 RL。
4. LoRA 工程默认：全权重矩阵覆盖、学习率约 10 倍全参、SFT rank 64-256 / RL rank 8-32。
5. 样本效率是 RL 主要瓶颈：On-Policy Distillation（学生采样 + 教师 token 级分布）、RLVP（奖励结果、惩罚路径）、训练-推理数值一致性（logprob 漂移监控）是三个关键工程点。
6. 评估数据集到训练用法的映射：端到端回归 → RLVR/RFT；轨迹前缀 → DPO/边界示范；失败归因 → PRM 负标签/RLVP 路径惩罚；Rubric → 向量奖励/GRM。

### 第 9 章：持续进化
1. 保存经历不等于从经历中学习：学习发生在"评价、对照、归纳、验证"之后。
2. 四种更新载体按能力表示性质路由：经验知识（事实）、Prompt/Skill（可语言表达的判断）、程序/Harness（可确定执行的约束）、模型参数（高维能力）。
3. 三层轨迹验证：结果验证器（事情办成）→ 过程验证器（以允许的方式办成）→ 质量验证器（用户舒服）；输出必须含维度结论 + 证据位置 + 失败标签 + 拒绝评分权。
4. 更新提案必须是可证伪的变更契约（失败证据、根因、归属组件、预期修复 + 可能受损 + 双向验证用例）；待验证版本在触发失败的边界集 + 正常的保留集上双测。
5. 三道安全边界：证据与指令隔离、待验证能力与正式能力隔离、安全机制不可自我修改。
6. 元层进化：从修改产物内容 → 修改上下文构造方法 → 修改 Harness 代码 → 修改优化器代码；Dream-RSI 发现树回放用历史筛选探索策略。
7. 分层评估指标：更新提案有效率、产物激活率、遵循成功率、保留任务集增益——区分 harness-updating 与 harness-benefit 两种能力。

### 第 10 章：多 Agent 协作
1. 核心判据一条：协作是否引入单 Agent 生成时无法获得的新信息；同模型自审无效，执行反馈/视觉反馈/工具反馈有效。
2. 两维度设计：上下文共享与否 + 拓扑（对等/管理者/去中心化）；通信即 IPC（共享内存 ↔ 共享文件系统；消息传递 ↔ 工具参数/消息总线）。
3. 虚拟文件系统四区域：Agent 专属 scratchpad、共享空间（乐观锁/worktree）、外部挂载资源、系统内置资源；文件路径是通用接口。
4. 控制平面：消息信封、状态查询（轨迹持久化 + 约定进度文件 + 卡死检测）、优雅/强制终止、级联取消、资源预算与抢占。
5. 六大失败模式：并发冲突（简单/语义）、错误级联、同质趋同、互相扯皮、循环失控、理解债与认知投降。
6. 多 Agent 也有代价：token 成本数倍到十倍，需预算感知（BAVT）与"第一个已验证成功"的幂等结算。

### 后记：两朵乌云
1. 乌云一：流式实时交互（快慢分离 + 把推理做快两条路并行）。
2. 乌云二：从成功与失败中持续积累经验（小世界假设 vs 大世界假设之争）。
3. 模型与 Agent 共同演进：应用层用 Harness 补位 → 补位记录变成训练信号 → 模型内化后删 Harness 代码。

---

## 二、逐章对照表（Climber 现状 vs 书中要求）

| 章节 | 领域 | Climber 现状 | 证据（文件:行号） | 判定 |
|---|---|---|---|---|
| 1 | Model–Harness 结构、编排光谱 | engine/ 8 模块拆分 + dual_loop + react_loop；metacognition 编排接入主循环 | app/core/engine/runner.py、app/core/engine/iteration.py、active-plan.md:72 | 已实现 |
| 2 | 上下文压缩 | ContextCompressor（truncate/sliding/summarize/budget）+ MemoryPressureManager 多策略 | app/core/compressor.py:25-109、app/core/engine/memory_pressure.py:22-91 | 部分实现 |
| 2 | KV Cache 稳定前缀、append-only、带引用压缩 | 无 KV cache 命中率统计、无 [COMPRESSED] 溯源、压缩历史为摘要整块替换 | grep `kv_cache\|cache_control` 全仓无结果；compressor.py:62 `_summarize` | 缺失 |
| 2 | 系统状态栏（动态系统状态入 prompt） | prompts/registry.py core.system 静态版本；无运行时状态栏注入 | active-plan.md:22；prompt_engine/engine.py | 部分实现 |
| 2 | 工具检索/渐进式披露 | skills 有目录式组织；工具全集默认暴露，无 defer_loading/BM25 tool_search | app/tools/native_tools.py:44、app/skills/ | 部分实现 |
| 3 | 用户记忆（持久 + 向量 + 画像） | persistent_memory、vector_memory、core_memory、memory/lifecycle+persona、profile/ 画像闭环、memfs git 版本化 | app/core/persistent_memory.py、app/core/memfs/store.py:3-14、app/core/profile/loop.py:387 | 已实现 |
| 3 | 记忆提取（额外 LLM 调用 + 选择性/抽象化/结构化） | memory_reflection.py 有反思；提取规则未按书三条规则显式建模 | app/core/memory_reflection.py | 部分实现 |
| 3 | 检索质量评估（LoCoMo 类基准） | 无记忆质量评估集；enhanced_rag 有 BM25+RRF 无评估 | app/core/enhanced_rag.py:10-85 | 缺失 |
| 4 | 五类工具分类 + 权限分层 | 工具全集 + permission_rules + safety_gate + sandbox；分类未按"调用方向+作用对象"显式建模 | app/core/permission_rules.py、app/core/metacognition/safety_gate.py、app/core/security_sandbox.py | 部分实现 |
| 4 | 提议者-审核者（工具层） | collaboration 有 reviewer process；工具执行前无独立审核者环节 | app/core/collaboration/roles.py、active-plan.md:91 | 部分实现 |
| 4 | 多模态三范式 | vision.py 数据 URL 解析；无 analyze_image 等工具化多模态分析 | app/api/v1/vision.py（active-plan.md:104 修复记录） | 缺失 |
| 5 | 七核心工具 + 编辑方案 | read/write/edit（old_string 预览/校验/统一 diff）、bash 命令、file_index、file_patch、checkpoint | app/core/file_patch.py:38-159、app/core/checkpoint.py:23-114 | 已实现 |
| 5 | 安全四边界 + 致命三要素 | sandbox、security/、principal、api_key_crypto；跨会话边界与记忆放大器防护未显式建模 | app/core/security_sandbox.py、app/core/principal.py | 部分实现 |
| 5 | 错误恢复/熔断 | error_analyzer、error_handlers、exceptions、watchdog、resilience、recovery | app/core/watchdog.py、app/core/resilience.py | 已实现 |
| 6 | Computer Use（截图→思考→动作闭环） | browser_navigate/screenshot/click/type/extract（Playwright + selector 定位） | app/tools/browser_tools.py:36-103 | 部分实现 |
| 6 | 视觉定位（SoM/DOM 索引/坐标缩放） | 仅 CSS selector；无 SoM 标注、无 DOM 树枚举编号、无分辨率双向映射 | app/tools/browser_tools.py:62,73 | 缺失 |
| 6 | 语音（级联/全双工/ASR/TTS） | 无任何语音栈 | grep `tts\|asr\|speech` 无真实实现 | 缺失 |
| 6 | 异步事件驱动（唤醒/事件队列/中途引导） | task_worker、parallel、scheduler（croniter）+ WS 事件推送；无事件队列优先级语义、无 mid-turn steering | app/core/scheduler.py:24-90、app/core/group_ws_hub.py（active-plan.md:95） | 部分实现 |
| 6 | 世界模型（动作后果预测） | HypothesisSimulator 启发式打分（静态复杂度成本表），无真实下一状态预测 | app/core/metacognition/hypothesis.py:66-121 | 部分实现 |
| 7 | 评估体系（Rubric/LLM-as-a-Judge/评估环境） | 无生产评估设施；pytest 单元测试覆盖组件行为 | grep `rubric\|pass@k` 全仓无结果 | 缺失 |
| 7 | 失败归因（首个错误定位 + 结构化记录） | CausalAttribution 因果归因（边权衰减 + 根因分类），无轨迹级首错定位与 JSON 归因记录 | app/core/metacognition/causal.py:16-153 | 部分实现 |
| 7 | 回归两层（端到端 + 轨迹前缀） | 仅 profile 消费者的确定性回归信号；无轨迹前缀回归任务集 | app/core/profile/loop.py:387-390 | 缺失 |
| 7 | 可观测性（trace/span） | TraceCollector span 树 + audit + emergency_stop + DB 采样 | app/core/observability/trace.py:18-152 | 已实现 |
| 7 | 特性开关/消融 | metacognition enabled 开关 + evolution 可注入 evaluator；无编译时开关/曝光事件去重/AB 平台 | app/core/metacognition/orchestrator.py:72-78、active-plan.md:70 | 部分实现 |
| 8 | 后训练（Mid-training/SFT/RL/LoRA/蒸馏） | 无任何训练基础设施 | grep `LoRA\|GRPO\|PPO\|DPO` 仅命中提示词文本 | 缺失 |
| 9 | 持续进化四载体（知识/Prompt/程序/参数） | 前三载体有实现；参数载体缺失 | app/core/prompts/evolution.py:199-267、app/core/engine/dual_loop.py:53-137 | 部分实现 |
| 9 | 认知闭环（观测→假设→因果→监控→选择→记录） | MetacognitionOrchestrator 全闭环接入主循环（pre_action 阻断 + post_action 回填 CHECKPOINT） | app/core/metacognition/orchestrator.py:59-298、active-plan.md:72、tests/core/test_engine_metacognition_wiring.py 38 passed | 已实现 |
| 9 | 提示词遗传进化（种群/适应度/replace-if-better） | PromptEvolutionEngine + PromptGenome + 短路惩罚审计 + 可注入异步 evaluator | app/core/prompts/evolution.py:42-267 | 已实现 |
| 9 | 待验证/正式能力隔离 + 三道安全边界 | canary.py 金丝雀 + safety_gate.py；证据与指令隔离、安全机制不可自我修改未显式建模 | app/core/metacognition/canary.py、app/core/metacognition/safety_gate.py | 部分实现 |
| 9 | 睡眠学习五步周期 / 发现树回放 | 无触发门控的离线整合进程、无发现树回放模拟器 | 全仓无匹配 | 缺失 |
| 10 | 多 Agent 协作全家桶 | a2a_protocol（签名/验证/请求）、group_chat、hierarchical、handoff、deadlock、guardrails、progress 卡死检测、crew/flow | app/core/collaboration/ 17 文件、app/multi_agent/crew.py、active-plan.md:91 | 已实现 |
| 10 | 虚拟文件系统四区域 | memfs git 版本化存储；scratchpad/共享空间/外部挂载/只读资源四区域未显式划分 | app/core/memfs/store.py:3-14 | 部分实现 |
| 10 | 预算感知与级联终止 | resource_limits + token_budget（8000）+ subagent 孤儿回收；无步骤级价值评估 | app/core/resource_limits.py、app/core/metacognition/orchestrator.py:62、app/core/engine/subagent.py:305 | 部分实现 |

统计：已实现 9 项，部分实现 17 项，缺失 8 项。

---

## 三、对"AGI 计划没做好"的回应

### 3.1 其实做了的（有代码证据）

1. **认知闭环已接入主循环**：`MetacognitionOrchestrator` 在 `_iteration_loop` 初始化，工具执行前 `pre_action`（可阻断），执行后 `post_action` 回填 `CHECKPOINT.metacognition`，闭环含 观测→模拟→因果→矛盾/风险监控→选择→记录（app/core/metacognition/orchestrator.py:79-292），并有专门接线测试（tests/core/test_engine_metacognition_wiring.py，38 passed）。
2. **提示词进化有真实现**：`PromptEvolutionEngine` 不是摆设——PromptGenome 种群、复合适应度、变异、replace-if-better、短路惩罚审计、可注入异步 evaluator、按 prompt 缓存与历史恢复（app/core/prompts/evolution.py:170-267）。
3. **双循环骨架存在**：在线执行（profile_context 注入 + record_run_outcome 记录）与离线进化（evolution_tick，可解析进化入口）分离（app/core/engine/dual_loop.py:53-189），与第九章"在线记录证据、离线生成提案"结构同构。
4. **多 Agent 与协作治理成体系**：A2A 签名协议、层级编排、死锁检测、guardrail fail-closed、进度卡死检测（app/core/collaboration/ 全目录；active-plan.md:91-95 报告组 102 passed）。
5. **错误处理与可观测性扎实**：统一异常树、span 树 trace、审计、急停（app/core/observability/trace.py:18-152、active-plan.md:92）。

### 3.2 真差距（按 AGI 杠杆排序）

| 优先级 | 差距 | 现状 | 书中做法 | 落地建议 | 工作量 |
|---|---|---|---|---|---|
| P0 | **评估与失败归因体系整体缺失**（第 7 章） | 无 Rubric、无 pass@k、无评估环境、无轨迹前缀回归；仅 pytest 组件测试 | Rubric 四准则 + LLM-as-a-Judge（多源异构）+ 评估环境五要素 + 失败归因（首个错误 + 结构化 JSON 记录）+ 端到端/轨迹前缀回归双层 | ① 先建最小评估集（20-50 个边界用例，答案=可接受动作集合）；② 为 metacognition 提案加"边界集 + 保留集"双测门禁；③ 从 WS 轨迹日志做失败归因沉淀回归用例 | 大 |
| P0 | **认知闭环的"模拟桩"深度问题**（第 6/9 章） | HypothesisSimulator 用静态成本表启发式打分；sub_agent 执行为模拟数据（tokens_used = len(goal) × 10，iterations = 3）；causal 图只记录边权不预测状态 | 世界模型预测"动作后状态差异"；子 Agent 真实并行执行（fork/cancel 语义）；VLA 式动作后确认 | ① sub_agent 接入真实 engine runner（复用 engine/subagent.py:159 spawn）；② hypothesis 打分改为"历史成功轨迹统计 + causal 图查询"替代静态成本表；③ 每步动作后增加状态确认（verify_state） | 中 |
| P1 | **后训练载体缺失**（第 8 章） | 四载体只实现三个（知识/Prompt/程序） | SFT/RFT（拒绝采样 + 验证器过滤）→ LoRA（全权重矩阵、10x 学习率）→ RL；评估数据集映射到训练用法 | 不必自建训练集群：先用"失败归因记录 → 偏好对构造（rejected/chosen）"把数据管线建好，训练可外接；最小落地是 DPO 数据导出格式 | 大 |
| P1 | **KV Cache 与工具披露工程债**（第 2 章） | 压缩为摘要整块替换；工具全集常驻 | 前缀 append-only + [COMPRESSED] 带引用 + 工具结果预算分层 + BM25 tool_search | ① compressor 增加带引用压缩与工具结果 token 预算；② 工具 >20 个时启用按需加载索引 | 中 |
| P2 | **交互深水区**（第 6 章） | selector 式浏览器操作；无 SoM、无语音、无事件优先级 | DOM 枚举编号（browser-use 四步）、语音级联栈、事件队列语义优先级 | 优先 DOM 枚举编号（成本低、定位稳定）；语音与 mid-turn steering 依赖模型能力，暂缓 | 中 |
| P2 | **持续进化安全边界**（第 9 章） | canary + safety_gate 存在但未覆盖三道边界 | 证据与指令隔离、待验证/正式能力隔离、安全机制不可自我修改 | 把 safety_gate 升级为三层：不可信证据不进 Skill、新能力先入待验证区、批准器对进化系统只读 | 小 |
| P2 | **记忆与检索质量评估**（第 3 章） | enhanced_rag 有 BM25+RRF 无评估 | LoCoMo 类基准 + 提取三规则 | 建一个小型记忆评估集（60 题三档：基础回忆/多会话消歧/跨会话关联），复用第 7 章评估设施 | 小 |

---

## 四、实施步骤（编号，按依赖排序）

1. **[P0] 建立最小评估集与 Rubric**：从现有 WS 轨迹日志抽 20-50 个真实边界用例（含用户纠正、点踩、事后审计发现的问题），按"可接受动作集合"定义答案；写第一个 Rubric（事实正确性 essential / 完整性 important / 幻觉 veto 一票否决）。
2. **[P0] metacognition 提案接双集门禁**：`MetacognitionCycleResult.conclude`（orchestrator.py:259）产出的更新提案，必须在边界集（触发失败的用例）+ 保留集（正常用例）双测通过才落盘——复用 `PromptEvolutionEngine` 已有的 evaluator 注入点。
3. **[P0] 子 Agent 真实化**：`metacognition/sub_agent.py:111-123` 的模拟执行改为调用 `engine/subagent.py:159` 的真实 spawn，token/迭代数从模拟常量改为真实执行结果回填。
4. **[P1] 失败归因结构化**：在 `CausalAttribution`（causal.py:121-153）基础上增加"首个错误步骤定位"——事实锚点比对（陈述 vs 工具返回逐条对齐）+ 轨迹前缀二分；归因记录输出 JSON（任务、首错步号、错误类别、根因责任方、原文证据、主因/次因）。
5. **[P1] 带引用压缩 + 工具结果预算**：`ContextCompressor._summarize`（compressor.py:62）输出带 `[COMPRESSED: 来源引用]` 标记；`compress_with_budget`（compressor.py:109）增加工具结果单独预算层。
6. **[P1] DPO 数据导出**：失败归因记录 → 截取首错前缀 → rejected（错误行为）/ chosen（先验证再下结论）偏好对导出，为将来外接训练准备数据资产。
7. **[P2] DOM 枚举编号定位**：browser_tools 增加 DOM 可交互元素枚举 + 编号 + 截图标注，定位从 CSS selector 升级为 ID 选择。
8. **[P2] safety_gate 三道边界升级**：按第九章"证据与指令隔离 / 待验证隔离 / 安全机制不可自我修改"补齐权限面。
9. **[P2] 记忆评估集**：60 题三档记忆基准，复用步骤 1 的 Rubric 设施，为 enhanced_rag 提供质量回归信号。

---

## 五、进度锚点与验证方式

- 每完成一步在 active-plan.md 勾选并附提交号；评估类工作必须附"边界集 + 保留集"双测结果。
- 回归基线：`python3 -m pytest tests/ -q`（分批跑，整仓单进程会卡死，见 active-plan.md:103）。
- 本文档为研究产出，不改代码；后续实施按第三、四节优先级单独开工单。

## 六、总体结论

Climber 在**多 Agent 协作、提示词进化、错误恢复、可观测性**四个领域已达到书中的工程水位，且认知闭环的结构是完整的（接入主循环 + 有测试）。

三处结构性短板决定它离书中的"可靠工作 Agent"还有距离：

1. **没有评估，进化就没有方向**——第九章闭环的"验证"环节（第七章）整体缺失，更新提案目前只能靠组件测试自证，无法回答"这次改动真的让系统变好了吗"。
2. **认知闭环的关键执行环节是模拟的**——假设模拟用静态成本表、子 Agent 用假数据，闭环"转得起来"但输出的判断质量受限于启发式。
3. **能力只能写进三个载体**——参数载体缺失，高维能力（风格、隐式策略）无法沉淀，这是第四朵乌云（持续积累经验）在 Climber 的直接映射。

把 P0 两项（评估体系 + 认知闭环真实化）做完，Climber 的持续进化闭环才能从"结构正确"升级为"结论可信"。
