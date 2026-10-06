# 报告审计 hygiene 与死代码清理 — 分类清单

- 日期：2026-10-02
- 范围：`app/core/engine/safety.py`、`app/core/engine/validation.py`（仅追加常量）、`app/core/engine/tool_capabilities.py`
- 来源：858 条报告扫描项 `/tmp/climber-report-items.txt`（按行号引用）
- 约束：删除类操作一律不执行；`app/core/agent_engine.py`、`validation.py` 既有逻辑、engine 其他文件、exceptions、collaboration、api/v1、group_ws_hub、前端均禁改

## A. 本次已修复

1. [报告 #135-136] COMMAND_TOOLS/FILE_TOOLS 双源重复（safety.py 105 行是 validation.py 235 行的复制粘贴变体）
   - `validation.py` 追加公开常量 `COMMAND_TOOLS` / `FILE_TOOLS`，成为常量唯一定义点；canonical 私有表 `_COMMAND_TOOLS` / `_FILE_TOOLS`（归一化查找用）保留。
   - `safety.py` 不删除，改为从 validation re-export 两个常量（`__all__` 同步），其 legacy 函数 `setup_default_permissions` / `validate_tool_call` 原样保留。
   - `tool_capabilities.py` 的沙箱段 import 由 `app.core.engine.safety` 改指向 `app.core.engine.validation`。
   - 行为逐位一致：公开表镜像 safety.py 原值（含 `stream_command` / `container_exec` 原始名），`tests/core/test_workflow_tool_capabilities.py:122-123` 的断言继续成立；`agent_engine.py:73-75` 导入的 `_COMMAND_TOOLS` / `_FILE_TOOLS` 私有名继续存在。

## B. 保留到 backlog 的条目（删除/行为变更类，本次不执行）

1. [报告 #136 后半句] 删除 `safety.py` 整个文件
   - 文件删除超出本次"禁止删除文件"约束，已改为 re-export 兼容壳。
   - 事实核查：`safety.setup_default_permissions` 与 `safety.validate_tool_call`（旧 6 参签名，sandbox 在前）生产代码零引用，仅 `tests/core/test_reported_security_regressions.py:10,107` 引用，属测试专用 legacy API。
   - 后续执行需先迁移该测试到 `validation.validate_tool_call`（新 session-first 签名），再删文件。

2. [报告 #1529-1530] canonical `_FILE_TOOLS` 对 `list_files` 的权限覆盖存在参数键缺口
   - 核查：`normalize_tool_name("list_files") -> "list_directory"`（permission_rules.py:67 别名表）已覆盖名称；但 `list_files` 的真实参数名是 `directory`（builtins.py:194-195），canonical 表值 `("dir", "read")` 的参数键取不到 → `_check_sandbox` 对 `list_files` 跳过 `validate_file_access`，overlay 阶段 resource 落到 `"*"`，受限路径下确实存在报告所述绕过面。
   - 修复需给 canonical 表/沙箱检查补 `directory` 参数键（行为变更类），非 hygiene，本次不落地。

3. [报告 #234] `engine/subagent.py:192-193` 返回值被丢弃的 no-op 死代码
   - 文件在 engine/ 其他文件，本次禁改。

4. [报告 #1010] `engine/run_storage.py:85-100`、`engine/react_loop.py:106` 死代码
   - 文件在 engine/ 其他文件，本次禁改。

5. 同名私有常量收敛候选（低优先级）
   - `permission_rules.py:85,93` 的 `_COMMAND_TOOLS` / `_FILE_TOOLS`（frozenset，归一后比较）与 `validation.py` 同名不同形（set / dict canonical）。
   - 已核实无实际冲突：permission_rules.py:140,190,255 调用点均先 `normalize_tool_name`，注释明确"tool_name 已是规范名"，两边语义一致，仅命名撞车。
   - 收敛需改 `permission_rules.py`（本次禁改），仅记录。

## C. 已核实为无需处理的项

1. `tool_capabilities.py` 无死代码：`FILE_WRITE_TOOLS` / `SHELL_TOOLS` / `DOCKER_TOOLS` 被 `DEFAULT_DENIED_TOOLS` 汇聚使用；`DEFAULT_DENIED_TOOLS` / `DEFAULT_ALLOWED_TOOLS` / `build_workflow_tool_validator` 被 `app/workflow/engine.py:308,570` 与 `tests/workflow/test_simulation_node.py`、`tests/core/test_workflow_tool_capabilities.py` 消费；`_parse_tool_capabilities` / `is_tool_allowed` 模块内使用。
2. `validation.py` 全部符号在用：`_check_*` 系列由 `validate_tool_call` 调用；`_approval_key` 另被 `tool_exec.py:16` 与 `tests/test_permission_rules_strict.py:293,307` 引用。
3. `app/` 生产代码对 `engine.safety` 的 import 已清零（rg 零命中），残留两个测试文件 import 经 re-export 继续兼容。

## 验证记录（2026-10-02）

- `rg` 复核：生产代码无 `engine.safety` 引用残留；safety re-export 与 validation 常量为同一对象（冒烟 import + `is` 断言通过）；`app.core.agent_engine` 导入链完好。
- 测试：`tests/test_permission_rules_strict.py`、`tests/test_native_tools_resource_limits.py`、`tests/test_settings_cluster_review.py`（任务指定路径在 `tests/core/` 下不存在，实际位于 `tests/` 根目录，按真实路径执行）+ 与本次改动直接相关的 `tests/core/test_workflow_tool_capabilities.py`、`tests/core/test_reported_security_regressions.py`、`tests/workflow/test_simulation_node.py`。
- `ruff check`：仅对本次三个改动文件执行（全仓 ruff 有既有基线错误，不做全仓断言）。
