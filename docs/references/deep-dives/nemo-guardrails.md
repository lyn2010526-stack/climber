# NeMo Guardrails 深挖（五类 Rails 对话防护分层）

> 核验日期：2026-10-01。结论仅来自本会话已确认的仓库内文档（`docs/references/opensource-eval-42-50.md` #49 与借鉴优先级、`docs/references/open-source-projects.md` #49）。本次未读取 NeMo Guardrails 源码，超出下文记录范围的内容一律标注"未核验"。

## 仓库状态/许可证

- 地址：`https://github.com/NVIDIA-NeMo/Guardrails`，本次核验确认可访问。
- 分支与版本：develop 分支为开发线；最新发布版本公布为 0.24.1（以官方页面为准）。
- 维护状态：仓库可访问；维护强度未核实。
- 许可证：未核验（本次核验未记录其 LICENSE 信息）。

## 源码入口与调用链（含 URL）

- 已确认入口：`https://github.com/NVIDIA-NeMo/Guardrails`（官方仓库，README 为本次能力清单的依据）。
- README 层面确认的能力分层：input、dialog、retrieval、execution、output 五类 rails。
- 内部源码入口与调用链：未核验（本次未克隆、未读取源码，rails 的注册、匹配、执行顺序实现均无证据）。

## 核心机制拆解

README 层面确认的五类 rails 概念（内部实现细节未核验）：

1. **Input rails**：用户输入进入对话流前的校验层。
2. **Dialog rails**：对话流本身的路由与边界控制。
3. **Retrieval rails**：检索内容进入上下文前的校验层。
4. **Execution rails**：工具/动作执行环节的拦截层。
5. **Output rails**：模型输出返回用户前的校验层。

要点：五类 rails 构成"输入→对话→检索→工具执行→输出"的分层防护链，每层独立可组合。各 rail 的配置语法（Colang 等）、执行引擎与组合顺序实现未核验。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系 |
| --- | --- |
| `app/core/collaboration/guardrails.py` | 当前唯一校验承载：`run_guardrails()` 遍历 task.guardrails，支持 `llm`（`run_llm_guardrail`）与 `function`（`run_function_guardrail`）两类，输出校验问题列表反馈给群协作流程；限群协作输出校验，未覆盖通用对话流 |
| `app/core/engine/validation.py` | `_check_permission_rules` 每次工具调用 DENY/ASK/ALLOW 判定，与 execution rails 概念同位 |
| `app/core/task_worker.py` | `_SIDE_EFFECT_TOOLS` 冻结集合 + `_step_has_side_effects()` 副作用步骤豁免重试，对应"工具执行前契约检查"模式 |
| `app/core/permission_rules.py` | 三级权限硬拦截（read_only 只放行 `_PLAN_READ_TOOLS` 白名单），对应 input/execution 层的本地实现 |
| `app/core/instruction/understanding.py` | 确定性解析主目标/约束/歧义/置信度，可视为 input rail 的语义前置层 |

## 可借鉴/不采用结论

- **可借鉴**：rail 分层设计——五层防护链的划分方式作为对话流与工具执行层的设计参考，对应 `docs/references/opensource-eval-42-50.md` 借鉴优先级第 1 类"近期可落地"。Climber 当前缺口明确：`guardrails.py` 仅覆盖群协作输出，通用对话流与工具执行 rail 层待评估（见 `docs/references/open-source-projects.md` #49）。
- **待评估**：将 output rail 扩展到通用对话流、将 execution rail 对齐到 `agent_engine`/`task_worker` 工具链，均列为待评估项。
- **不采用**：直接引入 NeMo Guardrails 依赖与其 Colang 配置体系（依赖体积与现有群协作校验边界冲突，本次会话无引入证据）。
- 阶段定位（见 `docs/references/open-source-projects.md` #49）：📋 待落地。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、可访问、develop 开发线、0.24.1 最新发布、五类 rails 能力清单 | 已核验（本会话公开页面确认，记录于 `docs/references/opensource-eval-42-50.md`） |
| Climber `app/core/collaboration/guardrails.py` 两类 guardrail、`app/core/engine/validation.py` 权限判定、`app/core/task_worker.py` 副作用契约 | 已核验（本仓只读调研，记录于 `docs/audits/cache-sandbox-review.md` 与本会话文件读取） |
| 许可证、维护强度、rails 内部实现（Colang 语法、执行引擎、组合顺序） | 未核验 |
