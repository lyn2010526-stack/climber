# EvoPrompt 深挖（LLM 即算子的提示词进化框架）

> 核验日期：2026-10-01。结论仅来自本会话已核验的 beeevita/EvoPrompt 公开仓库信息与源码结论，以及本仓只读调研（`app/core/prompts/evolution.py`）。本文按已核验结论撰写，机制要点均为文件级定位（行号级未记录），超出下文范围的内容一律标注"未核验"。

## 仓库状态/许可证

- 地址：`https://github.com/beeevita/EvoPrompt`。
- 定位：ICLR 2024 论文（Automatic Prompt Engineering with EvoPrompt）官方实现，出自 Microsoft。
- 规模：22 commits / 253 stars。
- 许可证：MIT。

## 源码入口与调用链（含 URL）

- 仓库入口：`https://github.com/beeevita/EvoPrompt`。
- 核心源码（文件级入口）：
  - `https://github.com/beeevita/EvoPrompt/blob/main/run.py` — 命令行入口；注意 `elif args.evo_mode in 'de'` 是对字符串做子串匹配而非成员判断，属潜在 bug（含 d/e 字符的其他取值会被误判进 DE 分支）。
  - `https://github.com/beeevita/EvoPrompt/blob/main/evoluter.py` — `Evoluter` 基类 + `GAEvoluter`/`DEEvoluter`/`ParaEvoluter` 三个实现。
  - `https://github.com/beeevita/EvoPrompt/blob/main/evaluator.py` — 任务评测：cls 用 acc、sim 用 SARI、sum 用 ROUGE。
  - `https://github.com/beeevita/EvoPrompt/blob/main/utils.py` — 共享工具（prompt/群体读写等）。
  - `https://github.com/beeevita/EvoPrompt/blob/main/llm_client.py` — LLM 调用封装，供进化算子生成子代使用。
- 调用链（文件级）：`run.py` 解析参数并按 evo_mode 构造 `GAEvoluter`/`DEEvoluter` → 进化循环内以模板驱动 `llm_client.py` 生成子代 → `evaluator.py` 打分并写入全局缓存 → 每代经 `utils.py` 落盘 `step{N}_pop.txt` → 固定代数结束后对 top-3 个体跑 held-out 测试集。

## 核心机制拆解

1. **prompt 纯字符串表示 + 全局分数缓存**：个体即 prompt 字符串；全局 dict `evaluated_prompts` 以 prompt 字符串为键缓存分数，重复个体直接复用，不重复评估。
2. **LLM 即算子**：交叉/变异全部外挂为 LLM 模板——GA 用两亲代模板、DE 用三 donor 模板，由 LLM 按模板生成子代 prompt。
3. **GA 三种选择算子**：wheel（轮盘赌，默认）/ random / tour（锦标赛）。
4. **DE replace-if-better**：子代仅在与父代比较更优时替换；历史 best 作为第三 donor 参与子代生成。
5. **固定 budget、无早停**：默认 10 代固定预算跑满。
6. **每代落盘**：每代写 `step{N}_pop.txt`，天然支持断点续跑。
7. **两阶段评估防过拟合**：进化全程用开发集打分，结束后仅对 top-3 个体跑 held-out 测试集。
8. **已知实现瑕疵**：GA 轮盘赌选择取 `scores[0]`，而种群更新排序用 `scores[-1]`，两处优劣口径不一致。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 与 EvoPrompt 的对照 |
| --- | --- |
| `app/core/prompts/evolution.py` | Climber 已有进化框架：`PromptGenome` dataclass 承载个体、代码级算子（零 LLM）、种子化锦标赛选择、精英保留、`min_improvement` 早停、SQLAlchemy 持久化 |
| 同上·选择算子 | EvoPrompt wheel/random/tour 三选一 vs Climber 种子化锦标赛：模板外挂选择可作参考，Climber 现实现更可控 |
| 同上·终止策略 | EvoPrompt 固定 budget 无早停 vs Climber `min_improvement` 早停：Climber 已优 |
| 同上·持久化 | EvoPrompt `step{N}_pop.txt` 文本落盘 vs Climber SQLAlchemy 持久化：Climber 已优，按代落盘的断点续跑语义可借鉴 |

## 可借鉴/不采用结论（可迁移机制排序）

1. **LLM-as-operator 模板外挂算子**（首选）：把交叉/变异从代码级扩展为可选 LLM 模板算子，与 Climber 现有代码级算子并存、按预算开关。
2. **prompt 分数缓存去重**：以 prompt 字符串为键的全局分数缓存，可直接移植到 `app/core/prompts/evolution.py` 的评估路径去重。
3. **budget 断点续跑**：按代落盘 + 固定预算的续跑语义，可叠加到现有 SQLAlchemy 持久化上。
4. **DE replace-if-better**：贪心替换策略可作 Climber 精英保留之外的补充算子。
5. **paraphrase 种子扩充**：`ParaEvoluter` 用复述扩充种子的思路，可用于冷启动种群多样性。
6. **来源 mark 追踪**：子代记录来源（亲代/算子）便于回溯进化谱系。
7. **两阶段评估**：开发集进化 + held-out 测试集只评 top-3 的防过拟合流程，与 Climber 评估设计互补。

- **不采用**：固定 budget 无早停（Climber 的 `min_improvement` 早停更优）；`args.evo_mode in 'de'` 一类子串判断写法；轮盘赌 `scores[0]`/`scores[-1]` 口径不一致的实现（借鉴轮盘赌时须先修正口径）。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、ICLR 2024 官方实现（Microsoft）、MIT、22 commits/253 stars | 已核验（本会话公开仓库信息核验） |
| run.py/evoluter.py/evaluator.py/llm_client.py 文件职责、机制要点 1-7、已知实现瑕疵 | 已核验（本会话源码核验，文件级定位） |
| 机制要点的行号级定位 | 未核验（本次未记录行号） |
| `app/core/prompts/evolution.py` 现状（PromptGenome/代码级算子/种子化锦标赛/精英保留/min_improvement 早停/SQLAlchemy 持久化） | 已核验（本仓只读调研） |
