# Agent Engine 核心增强实施计划

- [ ] 1. 基础设施与类型定义
  - 备注：`app/reflection/` 已创建（含 self_evaluation/improvement/reflection_engine）；`app/planning/` 与 `app/memory/` 扩展子模块未创建；共享类型 `ReflectionResult`、`ReasoningRequest`/`ReasoningResult` 已定义，`Plan`/`PlanStep`/`MemoryItem`/`SearchResult` 未定义
  - 创建 `app/planning/` 模块目录结构和 `__init__.py`
  - 创建 `app/reflection/` 模块目录结构和 `__init__.py`
  - 创建 `app/memory/` 扩展子模块（`vector_store.py`、`semantic_search.py`、`memory_compressor.py`、`forgetting.py`）
  - 定义共享数据类型：`Plan`、`PlanStep`、`ReflectionResult`、`MemoryItem`、`SearchResult`

- [x] 2. 实现 Planning 模块核心
  - [x] 2.1 实现 ReAct 规划器（`app/planning/react_planner.py`）
    - 备注：等价实现位于 `app/core/engine/react_loop.py`（`ReActLoopExecutor`，Thought-Action 循环）；清单指定路径 `app/planning/react_planner.py` 不存在
    - 定义 `ReActPlanner` 类，集成 Thought-Observation-Action 循环
    - 实现 `plan()` 方法：根据目标生成执行计划
    - 实现 `execute_step()` 方法：单步执行并收集观察
    - 实现 `replan()` 方法：基于观察动态调整计划

  - [x] 2.2 实现 Chain-of-Thought 推理（`app/planning/chain_of_thought.py`）
    - 备注：等价实现位于 `app/core/reasoning/strategies/deep_refine.py`（`DeepRefineStrategy`，生成-批判-反思-改进的链式推理）；清单指定路径不存在
    - 定义 `ChainOfThought` 类
    - 实现 `reason()` 方法：逐步推理生成中间结论
    - 实现 `verify()` 方法：验证推理链的逻辑一致性

  - [x] 2.3 实现 Tree-of-Thought 探索（`app/planning/tree_of_thought.py`）
    - 备注：等价实现位于 `app/core/reasoning/strategies/tree_of_thought.py`（`TreeOfThoughtStrategy.execute`，多路径探索与评估）
    - 定义 `TreeOfThought` 类
    - 实现 `explore()` 方法：BFS/DFS 搜索推理路径
    - 实现 `evaluate_path()` 方法：评估推理路径质量
    - 实现 `select_best()` 方法：选择最优推理路径

  - [ ] 2.4 实现计划监控与修正（`app/planning/monitor.py`）
    - 备注：未实现，未发现 `PlanMonitor`/`track_progress`/`detect_deviation`/`auto_correct` 等价代码
    - 定义 `PlanMonitor` 类
    - 实现 `track_progress()` 方法：跟踪执行进度
    - 实现 `detect_deviation()` 方法：检测执行偏差
    - 实现 `auto_correct()` 方法：触发自动修正

  - [ ]* 2.5 为 Planning 模块编写单元测试（`tests/modules/test_planning.py`）
    - 备注：`tests/modules/` 目录不存在
    - ReAct 规划器单元测试
    - Chain-of-Thought 推理单元测试
    - Tree-of-Thought 探索单元测试
    - 计划监控单元测试

- [ ] 3. 检查点 - 确保 Planning 模块测试通过
  - 备注：`tests/modules/test_planning.py` 不存在，模块级测试未编写

- [x] 4. 实现 Memory 模块扩展
  - [x] 4.1 实现向量存储集成（`app/memory/vector_store.py`）
    - 备注：等价实现位于 `app/core/vector_memory.py`（`VectorMemoryService`，ChromaDB 后端 add/search/delete/get/count）；清单指定路径 `app/memory/vector_store.py` 不存在
    - 定义 `VectorStore` 抽象基类
    - 实现 `ChromaVectorStore`：ChromaDB 后端适配
    - 实现 `QdrantVectorStore`：Qdrant 后端适配
    - 实现 `InMemoryVectorStore`：内存存储用于测试

  - [x] 4.2 实现语义搜索（`app/memory/semantic_search.py`）
    - 备注：等价实现位于 `app/core/vector_memory.py`（`search` 向量检索）与 `app/core/persistent_memory.py`（`search_archival_memories`、`retrieve_memories`）
    - 定义 `SemanticSearch` 类
    - 实现 `search()` 方法：基于语义相似度检索
    - 实现 `hybrid_search()` 方法：混合关键词+语义搜索
    - 实现 `filter_by_metadata()` 方法：元数据过滤

  - [x] 4.3 实现记忆压缩（`app/memory/memory_compressor.py`）
    - 备注：等价实现位于 `app/core/metacognition/memory_pruner.py`（`LongTermMemoryPruner`，含 `_merge_similar` 合并、`_extract_patterns` 提取关键模式、`prune` 移除低价值记忆）
    - 定义 `MemoryCompressor` 类
    - 实现 `compress()` 方法：摘要压缩冗余记忆
    - 实现 `merge_similar()` 方法：合并相似记忆
    - 实现 `extract_key_facts()` 方法：提取关键事实

  - [x] 4.4 实现遗忘策略（`app/memory/forgetting.py`）
    - 备注：等价实现位于 `app/core/persistent_memory.py`（`decay_recency_scores` 时间衰减、`cleanup_old_memories`/`auto_archive_old_memories` 遗忘归档）及 `app/core/metacognition/memory_pruner.py`（重要性评分淘汰）
    - 定义 `ForgettingStrategy` 抽象基类
    - 实现 `LRUForgetting`：最近最少使用淘汰
    - 实现 `ImportanceBasedForgetting`：基于重要性评分淘汰
    - 实现 `DecayBasedForgetting`：基于时间衰减淘汰

  - [ ]* 4.5 为 Memory 模块编写单元测试（`tests/modules/test_memory.py`）
    - 备注：`tests/modules/` 目录不存在
    - 向量存储单元测试
    - 语义搜索单元测试
    - 记忆压缩单元测试
    - 遗忘策略单元测试

- [ ] 5. 检查点 - 确保 Memory 模块测试通过
  - 备注：`tests/modules/test_memory.py` 不存在，模块级测试未编写

- [x] 6. 实现 Reflection 模块
  - [x] 6.1 实现自我评估（`app/reflection/self_evaluation.py`）
    - 备注：`app/reflection/self_evaluation.py` 已存在，含 `SelfEvaluator.evaluate`（多维评估返回 `EvaluationResult`/`QualityScore`）
    - 定义 `SelfEvaluator` 类
    - 实现 `evaluate()` 方法：对执行结果进行多维度评估
    - 实现 `score_quality()` 方法：质量打分（0-100）
    - 实现 `identify_issues()` 方法：识别问题点

  - [x] 6.2 实现改进建议（`app/reflection/improvement.py`）
    - 备注：`app/reflection/improvement.py` 已存在，含 `ImprovementAdvisor.analyze`/`add_suggestion`（按 priority 排序改进项）
    - 定义 `ImprovementAdvisor` 类
    - 实现 `suggest()` 方法：基于评估结果生成改进建议
    - 实现 `prioritize()` 方法：按影响排序改进项
    - 实现 `apply_feedback()` 方法：应用反馈到下一轮执行

  - [x] 6.3 实现反思引擎（`app/reflection/reflection_engine.py`）
    - 备注：`app/reflection/reflection_engine.py` 已存在，含 `ReflectionEngine.reflect`（返回 `ReflectionResult`）
    - 定义 `ReflectionEngine` 类
    - 实现 `reflect()` 方法：执行后反思主流程
    - 实现 `analyze_error()` 方法：错误根因分析
    - 实现 `adjust_strategy()` 方法：策略调整建议

  - [ ]* 6.4 为 Reflection 模块编写单元测试（`tests/modules/test_reflection.py`）
    - 备注：`tests/modules/` 目录不存在
    - 自我评估单元测试
    - 改进建议单元测试
    - 反思引擎单元测试

- [ ] 7. 检查点 - 确保 Reflection 模块测试通过
  - 备注：`tests/modules/test_reflection.py` 不存在，模块级测试未编写

- [ ] 8. 增强 Agent Engine 核心
  - 备注：Memory/Reflection 已集成（`agent_engine.py` 中 `PersistentMemoryService`、`_inject_memory_context`、`_trigger_memory_reflection`）；Planning 注入与 `coordinate_agents`/`distribute_task`/`aggregate_results` 多 Agent 协作接口未发现，部分完成
  - [ ] 8.1 增强 `app/core/agent_engine.py` 集成新模块
    - 集成 `PlanningModule`：注入规划能力
    - 集成 `MemoryModule`：增强记忆系统（短期/长期/工作记忆）
    - 集成 `ReflectionModule`：添加反思机制
    - 实现多 Agent 协作接口：`coordinate_agents()`、`distribute_task()`、`aggregate_results()`

  - [x] 8.2 实现工作记忆（`app/core/memory/working_memory.py`）
    - 备注：等价实现位于 `app/core/engine/memory_blocks.py`（`MemoryBlockStore`，add/get/update/remove/list 工作记忆块、`MemoryConsolidator` 整理归档）；清单指定路径 `app/core/memory/working_memory.py` 不存在
    - 定义 `WorkingMemory` 类
    - 实现 `store()` 方法：存储当前任务上下文
    - 实现 `retrieve()` 方法：检索相关上下文
    - 实现 `clear()` 方法：任务完成后清理

  - [x] 8.3 实现工具动态发现与恢复（`app/core/tool_discovery.py`）
    - 备注：等价实现位于 `app/core/metacognition/capability_discovery.py`（`CapabilityDiscovery.discover`，基于现有工具组合生成缺失能力）；`generate_params`/`parse_result`/`recover_error` 无精确对应方法
    - 定义 `ToolDiscovery` 类
    - 实现 `discover()` 方法：动态发现可用工具
    - 实现 `generate_params()` 方法：智能参数生成
    - 实现 `parse_result()` 方法：结果解析
    - 实现 `recover_error()` 方法：错误恢复策略

  - [ ]* 8.4 为增强的 Agent Engine 编写单元测试（`tests/modules/test_agent_engine_enhanced.py`）
    - 备注：`tests/modules/` 目录不存在
    - 多 Agent 协作用务测试
    - 工作记忆单元测试
    - 工具发现与恢复单元测试

- [ ] 9. 检查点 - 确保 Agent Engine 增强测试通过
  - 备注：`tests/modules/test_agent_engine_enhanced.py` 不存在，模块级测试未编写

- [ ] 10. 集成测试
  - 备注：`tests/integration/test_agent_engine_e2e.py` 未创建；全量测试已通过（41 passed），该项部分完成
  - [ ]* 10.1 编写端到端集成测试（`tests/integration/test_agent_engine_e2e.py`）
    - 完整 ReAct 循环集成测试
    - 多 Agent 协作端到端测试
    - 记忆系统全链路测试
    - 反思机制集成测试

  - [x]* 10.2 运行全量测试套件确保通过
    - 备注：`pytest tests/ -q` 实际 41 passed
    - 运行 `pytest tests/ -v --tb=short`
    - 确保所有测试通过
    - 检查覆盖率达标

- [ ] 11. 代码质量检查
  - 备注：`ruff check app/` 通过（All checks passed）；`mypy app/` 因 `app/api/v1/api_keys.py` 模块路径解析重复报 1 个错误（"Source file found twice under different module names"），类型检查未完全通过
  - 运行 `ruff check app/` 确保代码风格合规
  - 运行 `mypy app/` 确保类型检查通过
  - 修复所有 lint 和类型错误
