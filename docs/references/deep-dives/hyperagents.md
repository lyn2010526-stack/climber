# HyperAgents 深挖（Meta 可自我改进 Agent 研究原型）

> 核验日期：2026-10-01。结论仅来自本会话已确认的仓库内文档（`docs/references/opensource-eval-42-50.md` #48 与借鉴优先级、`docs/references/open-source-projects.md` #48）。本次未读取 HyperAgents 源码，超出下文记录范围的内容一律标注"未核验"。

## 仓库状态/许可证

- 地址：`https://github.com/facebookresearch/HyperAgents`，本次核验确认可访问。
- 代码规模：较小（本次公开页面可确认）。
- 维护状态：仓库可访问；维护强度未核实。
- 许可证：未核验（本次核验未记录其 LICENSE 信息；organization 归属 facebookresearch 本身不构成许可证证据）。

## 源码入口与调用链（含 URL）

- 已确认入口：`https://github.com/facebookresearch/HyperAgents`（官方仓库，README 为本次定位依据）。
- README 层面确认的定位：可自我改进的 Agent。
- README 层面确认的安全警示：明确警告执行不可信模型生成的代码。
- 内部源码入口与调用链：未核验（本次未克隆、未读取源码，元 Agent 循环的评估器、执行器实现均无证据）。

## 核心机制拆解

README 层面确认的机制概念（内部实现细节未核验）：

1. **自我改进 Agent**：Agent 对自身行为/Skill 做改进的元级循环。
2. **元 Agent 评估循环**：改进动作先经过评估再采纳，形成"尝试→评估→保留/回滚"回路。
3. **执行不可信代码警示**：README 明确要求隔离执行模型生成的代码，不可在主环境直接运行。

实现细节（评估指标、改进策略、隔离执行方式）未核验；本会话仅确认上述概念存在于 README 定位与警示中。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系 |
| --- | --- |
| `app/core/metacognition/self_refactor.py` | Skill 自我精简/合并原型：`SkillPerformance`（total_uses/successes/avg_tokens_used/avg_iterations）与 `efficiency_score`（成功率 0.5 + token 因子 0.25 + 迭代因子 0.25）构成低性能 Skill 淘汰、高性能优化的本地评估基础，对应 HyperAgents 评估循环概念 |
| `app/core/metacognition/orchestrator.py` | monitor→causal→goal_adjuster 复盘回路串联，对应元 Agent 循环的本地编排层 |
| `app/core/metacognition/safety_gate.py` | 元认知安全门（本次会话确认存在于 `app/core/metacognition/`，内部机制未核验），对应"执行不可信代码"警示的本地拦截候选 |
| `app/simulation/experiments.py` | 实验承载文件（见 `docs/audits/cache-sandbox-review.md` 3.2 提及、未逐一深入），隔离实验环境的现成入口 |

## 可借鉴/不采用结论

- **可借鉴**：元 Agent 评估循环概念。对应 `docs/references/opensource-eval-42-50.md` 借鉴优先级第 4 类"研究原型参考，置于隔离实验环境"。
- **前置约束（沿用 README 警示）**：任何自我改进实验必须先隔离并审计——在 `app/simulation/experiments.py` 承载的隔离环境内进行，执行模型生成的代码前过安全门，禁止在主执行路径直接运行。
- **不采用**：直接引入 HyperAgents 代码或依赖（研究原型、代码规模小、无维护证据）；将自我改进循环接入生产 `task_worker`/`agent_engine` 链路。
- 阶段定位（见 `docs/references/open-source-projects.md` #48）：🔧 部分。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、可访问、README 定位（可自我改进 Agent）、执行不可信代码警示、代码规模较小 | 已核验（本会话公开页面确认，记录于 `docs/references/opensource-eval-42-50.md`） |
| Climber `app/core/metacognition/self_refactor.py` 评估字段与效率公式、`orchestrator.py` 复盘回路 | 已核验（本仓只读调研，记录于 `docs/references/open-source-projects.md` 与本会话文件读取） |
| `app/core/metacognition/safety_gate.py`、`app/simulation/experiments.py` | 存在已核验（本会话目录清点/审计提及），内部机制未核验 |
| 许可证、维护强度、元 Agent 循环内部实现 | 未核验 |
