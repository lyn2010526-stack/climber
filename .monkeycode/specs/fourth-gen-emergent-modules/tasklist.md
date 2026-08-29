# 需求实施计划

- [ ] 1. 配置开关与全局门控
  - 在 `app/config.py` 的 `Settings` 中新增字段：`enable_fourth_gen`（默认 False）、`enable_autodiscovery`、`enable_meta_agent`、`enable_goal_centered`、`enable_swarm`（均默认 False）
  - 定义模块激活判断：`active = enable_fourth_gen and enable_<module>`，封装为 Settings 辅助方法（如 `is_fourth_gen_active()` / `is_module_active(name)`）
  - 在 `.env.example` 中补充这 5 个开关变量的注释与默认值
  - 引用：Requirement 1.1-1.5、设计「Settings (config)」

- [ ]* 1.1 编写配置开关单元测试
  - 验证默认全 False；master 开+per-module 开才激活；master 关则全部失效
  - 引用：Requirement 1.1、1.3

- [ ] 2. 硬安全防护层
  - 新建 `app/core/security/hard_guard.py`：`HighRiskActionGuard` 单例，含 `HIGH_RISK_PATTERNS`（batch_click、delete_file、bulk_network、rm -rf 等），提供 `async assert_allowed(action, payload)`
  - 提供模块级 `hard_guard` 单例与 `get_hard_guard()` 访问器；EventBus 与 SandboxExecutor 以引用方式注入、不可被替换
  - 提供快照前置守卫函数：`async require_snapshot_before(change) -> SnapshotGuard`，确保任何结构变更先快照、快照失败则中止变更
  - 引用：Requirement 2.1-2.5、Requirement 7.1-7.5、设计「Hard Security Layer」

- [ ]* 2.1 编写硬防护层单元测试
  - 验证高危动作无论来自哪个模块都被阻断；不可变性（无法从模块修改守卫）；快照前置不变量
  - 引用：Requirement 2.2、2.4、7.3

- [ ] 3. 模块A：自主能力发现器（Autodiscovery）
  - 新建 `app/core/emergent/autodiscovery.py`：
    - `AutodiscoveryConfig`（enabled、sandbox_steps_max=50、success_threshold=0.8、approval_required=True）
    - `DiscoveredCapability` 数据类（包装 `ComposedCapability` + 尝试次数/成功数/成功率/来源沙箱）
    - `AutodiscoveryEngine`：`explore(goal, primitives)` 仅在 `SandboxExecutor` 内反复执行原子原语序列并观测因果；`request_approval(capability)` 提交用户审核；`commit(capability)` 先快照再写入 `CapabilityDiscovery` 注册表并发布 `capability_committed` 事件
  - 探索步骤上限 `sandbox_steps_max` 强制终止；成功率低于阈值直接丢弃；高于阈值且 approval_required 时挂起待审核
  - 引用：Requirement 3.1-3.9、设计「Module A: Autodiscovery」

- [ ]* 3.1 编写 Autodiscovery 单元测试
  - 验证仅沙箱内探索、阈值门控、审核门、丢弃路径（低成功率静默丢弃）
  - 引用：Requirement 3.1、3.4、3.5、3.7、3.8

- [ ] 4. 模块B：Meta-Agent 元自重构
  - 新建 `app/core/emergent/meta_agent.py`：
    - `MetaProposal`（summary、graph_diff、applied、snapshot_id）
    - `MetaAgent`：`start_monitoring()` 订阅现有 EventBus 指标事件（tool_result、node_end、iteration_*、session_complete）；`analyze()` 检测失败模式/死循环/token 浪费/超时/重复动作；`propose()` 仅输出建议并等待用户确认；`apply()` 先快照→过 `HighRiskActionGuard` 过滤→更新图定义；`rollback(snapshot_id)` 一键回滚
  - 明确禁止：自动应用（必须用户批准）、修改硬安全层/事件总线/沙箱/其他模块开关
  - 引用：Requirement 4.1-4.9、Requirement 8.1-8.2、设计「Module B: Meta-Agent」

- [ ]* 4.1 编写 Meta-Agent 单元测试
  - 验证指标采集、提案生成、仅审核后生效、回滚、硬层不可改
  - 引用：Requirement 4.3、4.4、4.6、4.8、4.9

- [ ] 5. 模块C：目标-状态推演（Goal-Centered）
  - 新建 `app/core/emergent/goal_centered.py`：
    - `GoalState`（目标条件 dict）、`PlanStep`（原子原语名+参数）
    - `GoalCenteredPlanner`：`try_registry_first(goal)` 优先查 Capability 注册表；`plan(current, goal, max_seconds=10.0)` 在注册表未命中时才启动有界状态推演，输出原子动作变换序列；超时返回 None
  - 超时回退：调用方在 `plan` 返回 None 时回退传统工具调用路径；成功推演结果写回注册表缓存
  - 引用：Requirement 5.1-5.7、Requirement 8.3、设计「Module C: Goal-Centered」

- [ ]* 5.1 编写 Goal-Centered 单元测试
  - 验证注册表优先、推演上限与回退、成功结果缓存
  - 引用：Requirement 5.2、5.3、5.6、5.7

- [ ] 6. 模块D：局部蜂群（Swarm）
  - 新建 `app/core/emergent/swarm.py`：
    - `SwarmBee` Protocol（name、`handle(task, bus)`）
    - 5 种 bee：意图解析、状态校验、失败审查、安全校验、设备执行
    - `SwarmCoordinator`：`run_subtask(subtask)` 汇总结果；`activate(load)` 动态激活/休眠 bee；bee 崩溃视为降级态（重试一次后继续），顶层协调器始终存在
  - 蜂群仅通过 EventBus 广播通信；仅限子任务范围，不替换全局协调
  - 引用：Requirement 6.1-6.6、Requirement 8.4、设计「Module D: Local Swarm」

- [ ]* 6.1 编写 Swarm 单元测试
  - 验证协调器存在、bee 隔离、崩溃降级、动态激活
  - 引用：Requirement 6.1、6.4、6.5

- [ ] 7. 快照与回滚集成
  - 复用 `SessionSnapshotManager`（`app/core/session_snapshot.py`），新增注册表/图定义/开关状态快照 sidecar（`snapshots/{ts}.json`）
  - 实现 `apply_structural_change(change, snap)`：在能力入库、图修改、配置变更前自动快照；保留最近 N 个快照（默认 5），自动裁剪更旧快照
  - 集成到 `HighRiskActionGuard.require_snapshot_before` 调用链
  - 引用：Requirement 7.1-7.5、设计「Correctness Properties #3」

- [ ]* 7.1 编写快照/回滚单元测试
  - 验证结构变更前快照、一键回滚恢复精确状态、快照裁剪
  - 引用：Requirement 7.4、7.5

- [ ] 8. 检查点 - 核心模块单元测试全部通过
  - 运行 `pytest tests/test_hard_guard.py tests/test_emergent_*.py` 确认核心逻辑测试通过，如有疑问请询问用户

- [ ] 9. 启动接线与全局回退
  - 在 `app/main.py` lifespan 启动中：若 `enable_fourth_gen`，实例化激活的模块并启动后台循环（如 `meta_agent.start_monitoring()`）；关闭顺序在 `watchdog.stop()` 之前停止模块循环
  - 实现一键全局关闭：所有模块开关关闭时，系统运行在纯三代模式，无四代代码路径激活
  - 引用：Requirement 1.2、1.4、设计「Wiring (app/main.py)」

- [ ] 10. 集成测试与最终验证
  - 扩展 `tests/test_integration.py`：新增用例启用全部模块后验证可运行；关闭全部开关后验证回退到三代模式
  - 运行完整相关套件（settings、integration、emergent、hard_guard）与 `ruff check app/`，确保全部通过
  - 引用：Requirement 1.5、设计「Test Strategy」
