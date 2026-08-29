# 需求实施计划

- [x] 1. 配置开关与全局门控
  - 在 `app/config.py` 的 `Settings` 中新增字段：`enable_arch_v2`（默认 False）及各模块开关 `enable_plugin_kernel`、`enable_trace_log`、`enable_four_layer_memory`、`enable_skill_store`、`enable_self_learning`、`enable_capability`、`enable_long_context`、`enable_integration`（均默认 False）
  - 定义模块激活判断：`active = enable_arch_v2 and enable_<module>`，封装为 `is_arch_v2_active(name)` 辅助方法
  - 在 `.env.example` 中补充这 9 个开关变量的注释与默认值
  - 引用：Requirement 1、Requirement 10

- [x]* 1.1 配置开关验证
  - 验证默认全 False；master 开+per-module 开才激活；master 关则全部失效

- [x] 2. 插件内核（Plugin Kernel）
  - 新建 `app/core/plugin_kernel/`：
    - `types.py`：`PluginMeta`、`PluginContext`、`Plugin` 基类（id/version/dependencies、on_mount/on_unmount、meta()）
    - `event_bus.py`：`TypedEventBus`（subscribe/publish、request/response、trace_sink 自动落日志、get_history）
    - `kernel.py`：`PluginKernel`（register/mount/unmount/shutdown、依赖拓扑排序、级联卸载、服务冲突检测、卸载回滚零孤儿、set_profile/profile_delta）
    - `profiles.py`：`MINIMAL_PROFILE`/`COMPLETE_PROFILE`/`OFFLINE_PROFILE`/`DEVELOPER_PROFILE`、`ProfileConfig`（mode/overrides/disabled_plugins/resolve/all_plugin_ids）
  - 引用：Requirement 2、Requirement 7

- [x]* 2.1 编写插件内核单元测试（`tests/test_plugin_kernel.py`）
  - 验证依赖按序挂载、缺失/循环依赖报错、服务冲突报错、发布/订阅、卸载清理订阅（无孤儿）、请求-响应、热替换、shutdown 全部卸载、trace_sink 收事件

- [x] 3. 事件追溯日志（Trace Log）
  - 新建 `app/core/trace_log/trace_log.py`：
    - 10 类事件常量（system_prompt/reasoning/tool_call/tool_result/screenshot/decision/model_switch/subagent/context_injection/skill_load）
    - `TraceLog`：append（append-only JSONL，按会话分文件）、按文件大小轮转、read（start_sequence/event_type 过滤）、search、fork、replay、trajectory
    - 轨迹归档用重命名 `.archived` 后缀而非删除，保留可回滚性
  - 引用：Requirement 3

- [x]* 3.1 编写事件日志单元测试（`tests/test_trace_log.py`）
  - 验证 append-only、read 过滤、search、fork、replay、trajectory

- [x] 4. 四层记忆（Four-Layer Memory）
  - 新建 `app/core/four_layer_memory/`：
    - `short_term.py`：`Turn` + `ShortTermMemory`（window_size=10、add/recent/evicted/drain_evicted）
    - `medium_term.py`：`TaskMemory` + `MediumTermMemory`（begin_task/add_record/finish_task/promote）
    - `long_term.py`：`LongTermMemory`（base_dir 下 MEMORY.md/USER.md、freeze/propose_change 生成 diff、approve/reject 后 apply_change）
    - `fts5_index.py`：`FTS5Index`（BM25 检索 + FTS5 语法错误自动退化为 LIKE）
  - 引用：Requirement 4

- [x]* 4.1 编写四层记忆单元测试（`tests/test_four_layer_memory.py`）
  - 验证滑动窗口、evicted 出窗、任务归档/提升、长期记忆冻结快照+diff 批准、FTS5 检索与 LIKE 回退

- [x] 5. 技能库（Skill Store）
  - 新建 `app/core/skill_store/`：
    - `skill_store.py`：`SkillMetadata`/`Skill`/`SkillStore`（三级加载：metadata 常驻、内容按需、引用按需；record_usage 统计；success_rate<60% 自动 needs_optimization）
    - `skill_market.py`：`SkillMarket`（.skill zip 打包、敏感权限扫描、导入需授权）
  - 引用：Requirement 5

- [x]* 5.1 编写技能库单元测试（`tests/test_skill_store.py`）
  - 验证三级加载、统计标记 needs_optimization、打包/扫描/安装

- [x] 6. 自学习（Self-Learning）
  - 新建 `app/core/self_learning/`：
    - `l1_realtime_fix.py`：`FixRecord`（版本历史可回滚）+ `RealtimeFixer`（坐标空格规范化/元素缺失加验证提示补丁，max 3 次重试）
    - `l2_distill.py`：`OperationRecord`/`DistillResult` + `BackgroundDistiller`（>=3 步且含非通用动词才生成技能）
    - `l3_steward.py`：`StewardAction`/`StewardReport` + `SkillSteward`（合并重复/归档30天未用/更新过期/needs_optimization 进 L1 队列 + 可回滚报告 + 状态文件）
  - 引用：Requirement 6

- [x]* 6.1 编写自学习单元测试（`tests/test_self_learning.py`）
  - 验证 L1 补丁+重试+回滚、L2 蒸馏触发条件、L3 合并/归档/优化/报告

- [x] 7. 能力抽象（Capability）
  - 新建 `app/core/capability/`：
    - `capability.py`：`CapabilityMeta`（含成本画像/前置/副作用）+ `WrappedCapability`
    - `adapters.py`：Mcp/Skill/Http/SubAgent/Model/Perception 六类包装器
    - `registry.py`：按 0.5*成功率+0.3*成本+0.2*用户偏好 排序路由 + 失败 fallback 最多 3 个 + 调用统计
    - `market.py`：.cap 打包/扫描/安装、核心 10 能力、懒加载+LRU 容量 50
    - `evolution.py`：success_rate<0.6 标记优化
  - 引用：Requirement 7

- [x]* 7.1 编写能力抽象单元测试（`tests/test_capability.py`）
  - 验证路由排序、fallback、统计、打包/安装、懒加载

- [x] 8. 超长上下文（Long Context）
  - 新建 `app/core/long_context/`：
    - `budget.py`：`ContextBudget`/`ContextBudgetManager`（总 32768、PRIORITY_ORDER 裁剪、estimate_tokens 字符/4）
    - `sliding_window.py`：窗口 10 步+每 5 条出窗触发摘要（无 summarize_fn 时提取式回退）
    - `compression.py`：`CompressionPipeline`（tool_result 单行 JSON/screenshot VLM 描述/ui_tree 过滤不可见/code 截断/text 提炼要点）
    - `external_tools.py`：search_memory/read_skill/get_task_history/query_log/get_app_state 占位
    - `prefix_cache.py`：`PrefixCache`（固定前缀稳定序 system→memory→skills→tools）
    - `rag.py`：余弦相似度检索，embed_fn 缺省 sha256 回退，sqlite-vec 探测
  - 引用：Requirement 8

- [x]* 8.1 编写超长上下文单元测试（`tests/test_long_context.py`）
  - 验证预算裁剪次序、滑动窗口摘要、压缩管线、前缀缓存顺序、RAG 检索回退

- [x] 9. 集成层（Integration）
  - 新建 `app/core/integration/`：
    - `protocol_router.py`：`ProtocolRouter`（按协议路由/默认协议映射）
    - `event_sourcing.py`：`EventSourcedStore`（投影重建 + 时间旅行 upto）+ `EventSourcingManager`（多 store 共享事件流）
  - 引用：Requirement 9

- [x]* 9.1 编写集成层单元测试（`tests/test_integration_layer.py`）
  - 验证协议路由、事件源投影、时间旅行

- [x] 10. 启动接线与全局回退
  - 在 `app/main.py` lifespan 启动中：若 `enable_arch_v2`，调用 `_init_arch_v2()` 实例化激活的模块并保存 handles 到 `app.state.arch_v2`；关闭时先 `_stop_arch_v2()`（PluginKernel.shutdown）
  - 实现一键全局关闭：master 开关关闭时，系统运行在纯 v1 模式，无 v2 代码路径激活
  - 引用：Requirement 10

- [x]* 10.1 接线验证
  - 验证全部模块开关打开时 `_init_arch_v2` 可正常实例化全部模块、`_stop_arch_v2` 正常关停

- [x] 11. 全量回归与最终验证
  - 全量回归结果：1963 passed, 16 skipped, 1 failed（预存失败 `test_chat_applies_model_override_to_in_memory_session`，由历史未提交的 chat.py 重构引起，与本次 arch-v2 无关）
  - 8 个新测试文件全部通过（56 passed）
  - ruff lint 全部通过
  - 引用：Requirement 10、设计「Test Strategy」