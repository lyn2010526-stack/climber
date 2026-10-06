# TAOR 引擎评测报告

| 维度 | 原版 claw-code | 原版 Hermes-Agent | 本引擎(TAOR) |
|---|---|---|---|
| 循环上限 | maxTurns/maxBudgetUsd 外部预算 | planner 递归任务数上限 | 见 run 度量 |
| 工具循环 | 同程 while（结果回写后继续） | 工具调用循环 + 评估 | 见 run 度量 |
| 无进展守卫 | 依赖预算兜底 | 高层决策兜底 | 见 run 度量 |
| 记忆持久化 | transcript 附带 | 向量/关系记忆召回 | 见 run 度量 |
| 回滚语义 | 无里程碑回滚 | 无里程碑回滚 | 见 run 度量 |
| 结构化输出重试 | ≤5 次（MAX_STRUCTURED_OUTPUT_RETRIES） | 未固定 | 见 run 度量 |

## 场景结果
| 场景 | 状态 | rounds | tools | retries | rollbacks | audits | 快照 | 结果 |
|---|---|---|---|---|---|---|---|---|
| linear_complete | completed | 3 | 2 | 0 | 0 | 4 | incremental:12 | PASS |
| hitl_yield | yielded | 1 | 1 | 0 | 0 | 2 | milestone:4 incremental:4 | PASS |

## 任务报告摘要
- `linear_complete` status=completed outer_rounds=3 inner_turns=3 completed_tasks=3
- `hitl_yield` status=yielded outer_rounds=1 inner_turns=1 completed_tasks=1

## 记忆审计摘要
- `linear_complete` 审计 4 条：add, merge, add, merge
- `hitl_yield` 审计 2 条：add, merge

## 基线对照说明
本引擎（TAOR）在同等确定性场景下的实测指标见上表；对照列为参考特征（见 `baseline.py`），
差异点集中在：本引擎具备『连续无进展→回滚里程碑』守卫、双层快照、后台记忆精炼。