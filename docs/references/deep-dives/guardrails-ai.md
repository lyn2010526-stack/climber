# Guardrails AI 深挖（LLM 输出的可重问校验框架）

> 核验日期：2026-10-01。结论仅来自本会话已核验的 guardrails-ai/guardrails 公开仓库信息与源码结论，以及本仓只读调研（`app/core/collaboration/guardrails.py`）。本文行号对应 0.11.0 版本源码。

## 仓库状态/许可证

- 地址：`https://github.com/guardrails-ai/guardrails`。
- 许可证：Apache-2.0。
- 版本：0.11.0（本文行号基准）；注意 ReAsk 基类在外部包 `guardrails-ai-types>=0.4.0`，仓库内 `actions/reask.py` 只承载具体 ReAsk 类型。

## 源码入口与调用链（含 URL）

- 仓库入口：`https://github.com/guardrails-ai/guardrails`。
- 核心源码（行号对应 0.11.0）：
  - `https://github.com/guardrails-ai/guardrails/blob/main/guardrails/guard.py` — `class Guard` :86、`for_pydantic` :384、`use` :834、`_execute` :485、`validate` :872、远程调用 `_single_server_call` :884。
  - `https://github.com/guardrails-ai/guardrails/blob/main/guardrails/validator_base.py` — `class Validator` :92、`validate` :206、`validate_stream` :266、`register_validator` :527、`validator_factory` :515、`hub://` 前缀延迟导入 `try_to_import_from_hub` :570。
  - `https://github.com/guardrails-ai/guardrails/blob/main/guardrails/run/runner.py` — `Runner.__call__` :143、`validate_prompt` :350、`step` :205、`num_reasks` 预算 :168。
  - `https://github.com/guardrails-ai/guardrails/blob/main/guardrails/actions/reask.py` — `FieldReAsk` :19、`SkeletonReAsk` :33、`NonParseableReAsk` :43、`get_reask_setup` :450、`merge_reask_output` :584。
  - `https://github.com/guardrails-ai/guardrails/blob/main/guardrails/hub/install.py` — `install` :37。
  - 运行器家族：`AsyncRunner`/`StreamRunner`/`AsyncStreamRunner`，与 `Runner` 同属 `guardrails/run/` 运行器家族（具体文件名未核验）。
- 失败载体：`FailResult`（`validation_result.py` :45）+ on-fail 枚举动作（`Filter`/`Refrain`）。
- 调用链（行号级）：`Guard.for_pydantic`/:384 构造 → `use`/:834 装配 validator → `_execute`/:485 进入 `run/runner.py` 的 `Runner.__call__`/:143 → `step`/:205 逐 validator 校验、`num_reasks`/:168 控制重问预算 → 校验失败产生 `FailResult` → `actions/reask.py` 的 `get_reask_setup`/:450 构造 ReAsk、LLM 重答后 `merge_reask_output`/:584 合并 → `Guard.validate`/:872 返回最终结果；`hub://` 前缀 validator 经 `validator_base.py` 的 `try_to_import_from_hub`/:570 延迟导入，由 `hub/install.py` 的 `install`/:37 安装；远程模式走 `guard.py` 的 `_single_server_call`/:884。

## 核心机制拆解

1. **Guard 门面 + 声明式装配**：`for_pydantic` 用 Pydantic 模型声明输出 schema，validator 以 `use` 挂载。
2. **Runner 循环 + num_reasks 预算**：校验-重问循环由 `Runner.step` 驱动，重问次数受 `num_reasks` 预算硬约束。
3. **ReAsk 载体家族**：字段级 `FieldReAsk`、骨架级 `SkeletonReAsk`、不可解析 `NonParseableReAsk`；ReAsk 基类在外部包 `guardrails-ai-types>=0.4.0`。
4. **FailResult + 枚举动作**：校验失败统一以 `FailResult` 承载，on-fail 动作枚举化（`Filter`/`Refrain`），fail-closed。
5. **Validator 插件体系**：`register_validator`/`validator_factory` 注册与工厂化；`hub://` 前缀延迟导入 + 远程 Hub 安装。
6. **运行器家族**：同步 `Runner` 与 `AsyncRunner`/`StreamRunner`/`AsyncStreamRunner` 变体，覆盖异步与流式输出场景。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对照与差异 |
| --- | --- |
| `app/core/collaboration/guardrails.py` | 判定方式：Climber 用关键词子串匹配判定（`guardrails.py:99`）；guardrails-ai 用 Pydantic schema + Validator 的 `FailResult` 判定 |
| 同上·失败语义 | Climber 在 LLM/function 校验异常时 fail-open（`guardrails.py:94-96`、`guardrails.py:141-143`）；guardrails-ai fail-closed（`FailResult` + `Filter`/`Refrain` 枚举动作） |
| 同上·动作模型 | Climber 无枚举化 on-fail 动作；guardrails-ai 的 Filter/Refrain/ReAsk 动作模型可对照补齐 |
| 同上·校验载体 | Climber 校验对象为 LLM 审查输出与外部 function；guardrails-ai 校验对象为结构化输出（Pydantic schema） |

## 可借鉴/不采用结论（接入差异）

- **协作管线优先**：若接入，以 `app/core/collaboration/` 管线为第一落点，tool 校验次之。
- **fail-open 可配置化建议**：Climber 现为异常时 fail-open（`guardrails.py:94-96`、`guardrails.py:141-143`），建议保留默认行为、新增 strict 开关引入 fail-closed 语义，与 guardrails-ai 的 `FailResult` + 枚举动作模型对照补齐。
- **工具校验同步接口限制**：guardrails-ai `Validator.validate` 为同步接口（`validate_stream` 另有流式变体），Climber 工具校验为异步路径，直接接入会阻塞事件循环，需线程池包装或限定同步场景。
- **流式输出需先聚合再校验**：流式场景下必须先聚合完整输出再走校验，与 Climber 流式输出路径的接缝需单独处理。
- **暂缓**：`hub://` 远程依赖与 Guard Server 远程模式（`_single_server_call`）涉及外部服务依赖，暂缓。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、Apache-2.0、0.11.0 版本、ReAsk 基类在外部包 `guardrails-ai-types>=0.4.0` | 已核验（本会话公开仓库信息核验） |
| guard.py/validator_base.py/runner.py/reask.py/install.py 类与函数定位（行号级）、`FailResult`（`validation_result.py` :45）、on-fail 动作 Filter/Refrain | 已核验（本会话源码核验，行号级定位） |
| 运行器家族具体文件名 | 未核验（仅确认 `AsyncRunner`/`StreamRunner`/`AsyncStreamRunner` 属 `guardrails/run/` 运行器家族） |
| `app/core/collaboration/guardrails.py` 现状（:99 关键词子串匹配、:94-96/:141-143 fail-open） | 已核验（本仓只读调研） |
| fail-open 可配置化改造的具体设计 | 未核验（仅列为建议方向） |
