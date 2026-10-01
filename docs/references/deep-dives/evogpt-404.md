# EvoGPT 与 PyEvolution 深挖（404 证据存档）

> 核验日期：2026-10-01。结论仅来自本会话已确认的仓库内文档（`docs/references/opensource-eval-42-50.md` #42/#44 与借鉴优先级、`docs/references/open-source-projects.md` #42/#44 与阶段 3 现状）。本文为 404 证据存档，超出下文记录范围的内容一律标注"未核验"。

## 仓库状态/许可证

### EvoGPT

- 访问地址：`https://github.com/evo-gpt/EvoGPT`，本次核验（2026-10-01）返回 404。
- 真实仓库、许可证、维护状态均未核实。
- 原索引描述（`docs/references/open-source-projects.md` #42）：提示词遗传进化。该描述来自设计文档录入，无仓库证据支撑。

### PyEvolution

- 访问地址：`https://github.com/PyEvolution/PyEvolution`，本次核验（2026-10-01）返回 404。
- 真实仓库、许可证、维护状态均未核实。
- 原索引描述（`docs/references/open-source-projects.md` #44）：遗传算法底层算子。该描述同样无仓库证据支撑。

## 源码入口与调用链（含 URL）

- EvoGPT：仅存 404 线索地址 `https://github.com/evo-gpt/EvoGPT`；无任何可用源码入口与调用链证据。
- PyEvolution：仅存 404 线索地址 `https://github.com/PyEvolution/PyEvolution`；无任何可用源码入口与调用链证据。
- 两者均无替代真实地址：本次核验未通过搜索或页面交叉获得可信新地址，不可凭搜索摘要推断。

## 核心机制拆解

无仓库证据，禁止编造机制拆解。仅记录原索引描述与已核验对照项：

1. **原索引描述**：EvoGPT 对应提示词遗传进化（交叉、变异、适应度接口）；PyEvolution 对应遗传算法底层算子（拓扑变异/交叉借鉴）。两条均为待确认线索，无实现证据。
2. **已核验对照项（EvoPrompt）**：`https://github.com/beeevita/EvoPrompt` 可访问，README 明确为 ICLR 2024 官方实现，提供 GA/DE 提示词进化实验（population 初始化、演化、评估与更新）。阶段 3 的实验参考以 EvoPrompt 为准，EvoGPT/PyEvolution 保留为待确认线索。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系 |
| --- | --- |
| `app/core/prompts/evolution.py` | 阶段 3 本地实现（本次会话读取确认）：`PromptGenome`（候选提示词+模型参数集）、`FitnessWeights`（任务成功率/隐喻理解/元认知纠错加和，安全惩罚项做减法）、种子化 `random.Random` 确定性复现、零 LLM 调用、进化核心零 I/O、`save_population`/`load_population` 委托存储层；EvoGPT/PyEvolution 的可借鉴接口（交叉、变异、适应度）在获得可信地址后与该文件对照评估 |
| `app/core/prompts/registry.py` | 提示词版本化、deprecated 拒绝、工具契约校验（见 `docs/references/open-source-projects.md` 已落地对照表） |
| 阶段 3 定位 | 提示词 & 参数种群进化（`app/core/prompts/` + 评估器）当前仅以已核实的 EvoPrompt 作为实验参考；EvoGPT 与 PyEvolution 地址未核实，尚未开始（见 `docs/references/open-source-projects.md` 阶段路线） |

## 可借鉴/不采用结论

- **不采用**：EvoGPT 与 PyEvolution 均不纳入依赖、不作借鉴来源。404 状态下无许可证、无维护证据、无源码证据，任何接口借鉴均无从谈起。
- **保留**：两者作为待确认线索存档；获得可信地址、许可证证据后再评估（EvoGPT：交叉/变异/适应度接口；PyEvolution：拓扑变异/交叉借鉴）。
- **替代路径**：阶段 3 遗传进化以已核验的 EvoPrompt 为实验参考，抽象 population/evaluator/selection 契约，隔离其数据集、配置和密钥，与本地 `app/core/prompts/evolution.py` 对照。
- 阶段定位（见 `docs/references/open-source-projects.md` #42/#44）：📋 待落地。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| EvoGPT `https://github.com/evo-gpt/EvoGPT` 404（2026-10-01） | 已核验（本会话访问记录于 `docs/references/opensource-eval-42-50.md` #42） |
| PyEvolution `https://github.com/PyEvolution/PyEvolution` 404（2026-10-01） | 已核验（本会话访问记录于 `docs/references/opensource-eval-42-50.md` #44） |
| EvoPrompt 可访问、ICLR 2024 官方实现、GA/DE 能力 | 已核验（本会话公开页面确认，记录于 `docs/references/opensource-eval-42-50.md` #43） |
| Climber `app/core/prompts/evolution.py`、`app/core/prompts/registry.py` 现状 | 已核验（本会话文件读取 + 本仓只读调研） |
| EvoGPT/PyEvolution 真实地址、许可证、维护状态、原索引描述的能力真实性 | 未核验 |
