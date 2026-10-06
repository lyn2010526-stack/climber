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
| hitl_yield | yielded | 1 | 1 | 0 | 0 | 2 | milestone:2 incremental:2 | PASS |
| linear_complete | completed | 3 | 2 | 0 | 0 | 3 | incremental:3 | PASS |
| long_milestones | completed | 6 | 5 | 0 | 0 | 12 | incremental:6 | PASS |
| observe_block | running | 2 | 0 | 1 | 1 | 3 | incremental:2 | PASS |
| stall_rollback | running | 8 | 8 | 4 | 4 | 9 | incremental:8 milestone:1 | PASS |

## 任务报告摘要
- `hitl_yield` status=yielded outer_rounds=1 inner_turns=1 completed_tasks=1
- `linear_complete` status=completed outer_rounds=3 inner_turns=3 completed_tasks=3
- `long_milestones` status=completed outer_rounds=6 inner_turns=6 completed_tasks=6
- `observe_block` status=running outer_rounds=2 inner_turns=2 completed_tasks=1
- `stall_rollback` status=running outer_rounds=8 inner_turns=8 completed_tasks=4

## 记忆审计摘要
- `hitl_yield` 审计 2 条：add, merge
- `linear_complete` 审计 3 条：add, add, merge
- `long_milestones` 审计 12 条：add, add, add, add, add, merge, add, add, add, merge, merge, merge
- `observe_block` 审计 3 条：add, add, merge
- `stall_rollback` 审计 9 条：add, add, merge, add, merge, add, merge, add, merge

## 基线对照说明
本引擎（TAOR）在同等确定性场景下的实测指标见上表；对照列为参考特征（见 `baseline.py`），
差异点集中在：本引擎具备『连续无进展→回滚里程碑』守卫、双层快照、后台记忆精炼。