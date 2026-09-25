# 科学仿真 Agent 参考实现（Open-Source Lineage）

> 本文档记录 Climber 科学仿真实验 Agent（`app/simulation/`）所借鉴的 5 个开源参考项目。
> 它们全部遵循同一条设计路线：**Agent 负责实验规划 + 调用外部仿真/计算工具 + 校验迭代**，
> 与 Climber + MCP + Harness 的闭环架构完全对齐。Climber 不自研专用工业级仿真求解器
> （OpenFOAM/SPICE/DFT），但内置了一组轻量可真实计算的数值实验模型用于闭环演示与测试。

## 0. 内置可运行实验后端

为了让 workflow/harness 的闭环"真的能跑出数值结果"，`app/simulation/experiments.py`
提供纯 numpy 的数值实验后端，通过内置工具 `simulate_experiment` 注册进全局 `ToolRegistry`：

- **heat**：1-D 显式有限差分热传导。CFL 违反时真实发散（NaN / 物理量级爆炸），
  输出 `converged=false` + `nan=true` + 含 `divergence` 的 error，驱动 harness
  的 dispatch → probe → review → adjust → retry 闭环。
- **oscillator**：阻尼受迫谐振子，返回 settling_time / max_displacement /
  damping_ratio / resonance_ratio 等工程指标。
- **logistic**：逻辑斯蒂增长，`r*dt` 过大时真实发散，返回 final_population / overshoot。

设计要点：

- 输出为结构化 JSON（长度有界、含 `elapsed_ms`），探针可直接解析命名指标。
- `converged=true` 表示数值积分成功完成；稳态另用 `steady_state` 字段表达，
  避免 t_final 小于扩散时间常数时误判未收敛。
- 外部 MCP 仿真工具仍按原路径经 `ToolRegistry` 接入；内置后端是"开箱即用"的默认实现。
- 关键文件：`app/simulation/experiments.py`、`app/tools/builtins.py`
  （`simulate_experiment`）、`app/multi_agent/flow.py`（模板默认值）、
  `app/api/v1/workflows.py`（模板列表）、`app/workflow/engine.py`
  （`_resolve_registry` 让 Flow/API 运行自动使用全局工具注册表）。


## 1. AgentLaboratory

- **仓库**: https://github.com/SamuelSchmidgall/AgentLaboratory
- **核心**: 多角色科研 Agent 闭环（文献研究员、实验设计师、代码工程师、评审校验员）
- **模仿重点**:
  - 角色拆分（规划 / 执行 / 校验分离）
  - 实验日志持久化（全链路可复现记录）
  - 结果校验与迭代
- **已落地到 Climber**:
  - `ScienceSimulationAgent` 总指挥（工具选择 → 实验设计 → 执行 → 聚合评审 → 重新规划）
  - `LLMReviewer` 评审子 Agent（校验合理性，可拒绝/重试）
  - `app/simulation/ledger.py` 实验全链路 JSONL 持久化
- **不用抄**: 论文生成与 LaTeX 排版细节

## 2. MatSciAgent

- **仓库**: https://github.com/lanl/matsci-agent
- **核心**: 材料发现 Agent，调用 Materials Project 数据库 + ASE 做第一性原理计算
- **模仿重点**:
  - 自然语言材料需求 → 生成候选结构 → 批量提交仿真任务
  - 读取能量/能带结果 → 调整参数下一轮搜索
  - 参数空间搜索策略、工具返回结果解析
- **已落地到 Climber**:
  - `LLMExperimentPlanner`：自然语言需求 → 参数扫描计划（sweep/base）
  - `ParallelToolExecutor` + `asyncio.Semaphore` 批量并发调度仿真
  - `app/simulation/planner.py` 参数空间 Cartesians 展开与上限控制
- **不用抄**: ASE/DFT 底层计算代码（Climber 通过 MCP 调用外部仿真后端）

## 3. OpenFOAM-Agent（WindAgent）

- **仓库**: https://github.com/openfoam-agent/openfoam-agent
- **核心**: CFD 流体仿真自动化 Agent，自动生成 OpenFOAM 算例、改网格参数、提取升阻数据、迭代外形
- **模仿重点**:
  - 监控仿真收敛、识别发散报错
  - 自动调整参数重跑
- **已落地到 Climber**:
  - `app/simulation/probes.py`：发散标记 / 错误标记 / NaN-Inf / 数值提取 / 收敛探针
  - `app/simulation/adjuster.py`：有界确定性参数调整（自动重试）
  - `SimulationHarness`：探针 → 评审 → 调整 → 重试的工作流
- **不用抄**: OpenFOAM 网格与边界条件的底层实现（Climber 内置 heat/oscillator/logistic 数值后端用于闭环，工业级 CFD 走 MCP 外部工具）

## 4. Safe-Lab-Agents

- **仓库**: https://github.com/MaxNaeg/safe_lab_agents
- **核心**: 带安全隔离沙箱的科学 Agent，MCP 接口、参数白名单、资源限制
- **模仿重点**:
  - 工具调用前置参数校验、资源限额、危险参数拦截、沙箱生命周期管理
- **已落地到 Climber**:
  - `ParameterPolicy`：参数白名单（允许名/范围/禁用项/必填项）前置校验，违规工具不触发
  - `app/workflow/safe_code.py` + `code_sandbox.py`：代码节点沙箱隔离
  - 工具节点能力白名单 `app/core/engine/tool_capabilities.py`（默认拒绝写文件/shell/docker）
  - LLM 规划输出按工具 schema 清洗，未知参数丢弃
- **不用抄**: 其化学实验领域专用工具集

## 5. CircuitAgent（SPICE 仿真自动化）

- **仓库**: https://github.com/silicon-agent/circuit-agent
- **核心**: EDA 电路 Agent，自然语言需求生成 SPICE 网表，批量参数扫描，提取功耗/频响，定位失效点
- **模仿重点**:
  - 把抽象工程指标翻译成仿真参数
  - 批量遍历参数空间、自动做良率分析
- **已落地到 Climber**:
  - 指标 → 仿真参数的转换（LLM 规划 → 受控 sweep）
  - `ExperimentPlan` 批量扫描调度
  - 评审聚合（accepted/rejected 判定 → 下一轮 refine）
- **不用抄**: SPICE 仿真内核

## 借鉴汇总

| 参考项目 | 抄入 Climber 的能力 |
|----------|---------------------|
| AgentLaboratory | 多角色评审闭环、实验日志持久化、评审子 Agent |
| MatSciAgent | 批量仿真调度、参数空间搜索、结果解析 |
| OpenFOAM-Agent | 收敛探针、发散判定、自动调参重跑 |
| Safe-Lab-Agents | MCP 沙箱参数校验、权限熔断、白名单拦截 |
| CircuitAgent | 指标 → 仿真参数转换、批量扫描调度、良率/聚合评审 |

## 一条模仿提示词（喂给 AI 复现此路线）

> 模仿 AgentLaboratory 的多角色评审闭环 + Safe-Lab-Agents 的 MCP 沙箱参数校验，
> 参考 openfoam-agent 的仿真收敛判断逻辑，构建科学仿真智能体。
> Agent 作为总指挥，接收自然语言工程需求，拆实验，调用 MCP 仿真工具，读取结果，
> Harness 校验合理性，自动迭代参数，完整日志持久化，工业级仿真不自研求解器；
> 开箱即用场景使用内置 heat/oscillator/logistic 数值实验后端。
