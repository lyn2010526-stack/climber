# Rebuff 深挖（多层 prompt 注入检测）

> 核验日期：2026-10-01。结论仅来自本会话已核验的 protectai/rebuff 公开仓库信息与源码结论，以及本仓只读调研（`app/core/metacognition/safety_gate.py`）。机制要点均为文件级定位（行号级未记录），超出下文范围的内容一律标注"未核验"。

## 仓库状态/许可证

- 地址：`https://github.com/protectai/rebuff`。
- 许可证：Apache-2.0（借鉴须保留归属与许可声明）。
- 维护状态：2025-05-16 已归档（read-only）；最后实质提交 2024-01-25（`4d2fe06`）；1.5k stars。
- 上游停更意味着只能抄逻辑重建，不可依赖上游迭代与修复。

## 源码入口与调用链（含 URL）

- 仓库入口：`https://github.com/protectai/rebuff`。
- SDK 目录：`https://github.com/protectai/rebuff/tree/main/python-sdk`。
- 四层检测 + SDK 编排（`python-sdk/rebuff/` 内）：
  - `https://github.com/protectai/rebuff/blob/main/python-sdk/rebuff/detect_pi_heuristics.py` — 启发式注入检测层。
  - `https://github.com/protectai/rebuff/blob/main/python-sdk/rebuff/detect_pi_openai.py` — LLM 判定层。
  - `https://github.com/protectai/rebuff/blob/main/python-sdk/rebuff/detect_pi_vectorbase.py` — 向量检索层。
  - `https://github.com/protectai/rebuff/blob/main/python-sdk/rebuff/sdk.py` — SDK 编排 + canary 机制。
- 调用链：`sdk.py` 编排四层检测，判定语义为 OR——任一层分数超过各自阈值即判定为注入并拦截。

## 核心机制拆解

1. **启发式层 `detect_pi_heuristics.py`**：7700 条注入短语组合（11 动词 × 7 形容词 × 20 宾语 × 5 介词）；滑动窗口打分 `base=0.5 + 0.5*min(matched/5, 1)`；默认阈值 0.75；纯 `re` + `difflib` 实现，零模型依赖。
2. **LLM 层 `detect_pi_openai.py`**：7 个 few-shot 示例 + gpt-3.5-turbo 打分，阈值 0.9；缺陷：`float()` 直接解析 LLM 返回文本，非纯数字直接抛 `ValueError` 且无捕获；另存在二阶注入风险（待检测文本本身进入判定 prompt）。
3. **向量层 `detect_pi_vectorbase.py`**：Pinecone + ada-002，top_k=20，阈值 0.90；已知 bug：`count_over_max_vector_score` 场景下首个最高分不计入；冷启动空索引恒 0 分（漏检）。
4. **canary 层 `sdk.py`**：`secrets.token_hex` 生成 canary（4 字节熵）；以 HTML 注释形式插入；精确子串匹配检测泄漏；检测到泄漏时将事件回写 Pinecone，形成自强化闭环（SDK 侧实现）。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系与移植方案 |
| --- | --- |
| `app/core/metacognition/safety_gate.py` | 风险域不同：rebuff 防用户 prompt 注入（读入路径），safety_gate 防写入路径危险内容；两者互补，移植后是新增检测维度 |
| 同上·启发式层 | 并入 `_RISK_DEFINITIONS`，新增 `prompt_injection_phrase` 条目，权重 0.6，走现有累积 penalty 语义 |
| 同上·LLM 层 | 必须外置为 adapter（rebuff 硬编码 OpenAI）；移植时修复 `float()` 解析缺陷（非纯数字走回退路径，无捕获异常直接抛出） |
| 同上·向量层 | 用 Climber 本地向量设施替代 Pinecone；需自建注入短语向量库解决冷启动空索引恒 0 分问题 |
| 同上·canary | 纯函数部分（token 生成、HTML 注释插入、精确子串匹配）可直接移植；泄漏事件转 penalty 提升接入现有评分 |

## 局限与不采用结论

- **上游停更**：2025-05-16 归档只读，只能抄逻辑重建，不能依赖上游迭代与修复。
- **英文中心**：7700 条短语组合全部为英文模式，中文覆盖近零，直接移植对中文输入几乎无效，需自行扩展中文词表。
- **语义标定**：rebuff 四层 OR 语义（任一层超阈值即拦截）与 Climber 累积 penalty 语义不同，并入 `_RISK_DEFINITIONS` 时需重新标定权重与阈值。
- **上游自述**：cannot provide 100% protection——定位为纵深防御的一层，不可作为唯一防线。
- **合规**：Apache-2.0 要求保留归属与许可声明。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、Apache-2.0、归档时间（2025-05-16）、最后实质提交（4d2fe06）、1.5k stars | 已核验（本会话公开仓库信息核验） |
| 四层检测文件职责与机制要点（含 float 解析缺陷、count_over_max_vector_score bug、冷启动恒 0 分） | 已核验（本会话源码核验，文件级定位） |
| `app/core/metacognition/safety_gate.py` 现状（`_RISK_DEFINITIONS`、累积 penalty） | 已核验（本仓只读调研） |
| 各层阈值/参数的行号级定位 | 未核验（本次未记录行号） |
| 中文词表扩展与本地向量库的具体设计 | 未核验（仅列为待办方向） |
