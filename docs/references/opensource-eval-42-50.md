# 开源项目核验：42-50 与 Zep

> 核验日期：2026-10-01。维护状态只记录本次公开页面可确认的事实；未获得明确证据的项目标记为“未核实”。本文件不记录未经核验的 star 数。

## 一行结论

42. **EvoGPT**：`https://github.com/evo-gpt/EvoGPT` 返回 404，真实仓库、许可证和维护状态均未核实；暂作线索，不纳入依赖。
43. **PromptEvolver (EvoPrompt)**：`https://github.com/beeevita/EvoPrompt` 可访问，README 明确为 ICLR 2024 官方实现，提供 GA/DE 提示词进化实验；借鉴 population、evaluator、selection 契约，作为阶段 3 基线。
44. **PyEvolution**：`https://github.com/PyEvolution/PyEvolution` 返回 404，真实仓库、许可证和维护状态均未核实；暂缓拓扑进化借鉴。
45. **E2B-Sandbox**：`https://github.com/e2b-dev/E2B` 可访问，定位为云端隔离沙箱并提供 JS/Python SDK；借鉴沙箱生命周期和资源边界，Climber 当前子进程隔离仍标注能力差异。
46. **OpenSandbox**：真实地址为 `https://github.com/opensandbox-group/OpenSandbox`，可访问且持续有仓库活动，提供本地到 Kubernetes 的沙箱运行时；借鉴统一生命周期 API、网络出口策略和凭据保险库。
47. **Guardrails-AI**：`https://github.com/guardrails-ai/guardrails` 可访问，提供输入/输出 Guards、结构化数据和 Hub validators；借鉴校验器组合与失败策略，保留 Climber 群协作校验的边界。
48. **HyperAgents**：`https://github.com/facebookresearch/HyperAgents` 可访问，README 定位为可自我改进的 Agent，代码规模较小且带明确的执行不可信生成代码警示；借鉴元 Agent 评估循环，先隔离实验和审计。
49. **NeMo Guardrails**：`https://github.com/NVIDIA-NeMo/Guardrails` 可访问，develop 分支为开发线并公布 0.24.1 最新发布版本，支持 input/dialog/retrieval/execution/output rails；借鉴对话流与工具执行 rail 分层。
50. **Rebuff**：`https://github.com/protectai/rebuff` 可访问但 GitHub 明确标记 2025-05-16 归档；借鉴启发式、LLM、向量和 canary 的分层检测概念，不引入其代码或依赖。

## Zep 结论

Zep 主仓库 `https://github.com/getzep/zep` 当前明确声明它是 Zep Cloud 的示例、集成和工具仓库，不是 Zep 产品本体；Community Edition 已弃用并移入 `legacy/`。产品入口为 `https://www.getzep.com/`，文档为 `https://help.getzep.com/`，开源时序知识图谱引擎为 `https://github.com/getzep/graphiti`。Climber 继续保留 Zep 的时序记忆参考项，借鉴事实有效期、关系召回和评估 harness；接入决策需要单独评估托管服务依赖、数据边界和 Graphiti 自托管成本。

## 借鉴优先级

1. **近期可落地**：EvoPrompt 的评估与选择契约、Guardrails-AI 的 validator 组合、NeMo Guardrails 的 rail 分层。
2. **阶段性架构参考**：E2B 与 OpenSandbox 的隔离生命周期、网络出口策略、凭据隔离。
3. **画像与记忆参考**：Zep/Graphiti 的时序事实和关系召回，先接入评估设计再决定运行形态。
4. **研究原型参考**：HyperAgents 的元 Agent 评估循环，置于隔离实验环境。
5. **历史或待确认项目**：Rebuff 仅作归档参考；EvoGPT、PyEvolution 等待真实地址和维护证据。

## 工具清点

`app/tools/` 当前有 45 个 `@tool` 定义：`builtins.py` 27 个、`native_tools.py` 12 个、`browser_tools.py` 6 个。`DEPRECATED_TOOL_NAMES` 仅提供迁移盘点元数据，所有工具继续注册和可执行。

弃用集合：`native_read_file`、`native_write_file`、`native_list_dir`、`native_web_search`。这些条目与通用内置文件/目录/搜索能力存在重叠，集合本身不改变注册行为。

## 核验边界

- 地址以项目官方 GitHub 页面或官方项目页面为准。
- 页面未明确给出维护结论时使用“未核实”，不以 star、fork 或搜索摘要推断维护质量。
- 本次未执行 git 操作，也未修改 `app/` 下除 `app/tools/__init__.py` 之外的文件。
