# 代码质量重构实施计划

## 目标：代码质量评分 >= 90/100

- [ ] 1. 提取公共工具模块
  - 备注：`app/api/v1/common.py`（DEFAULT_USER、parse_request_payload、get_or_404、entities_to_dicts）与 `app/core/exceptions.py`（AgentEngineError 异常体系）已实现；但 `app/api/v1/schemas/response.py`（统一响应模型）未创建，该项部分完成
  - 创建 `app/api/v1/common.py`，提取通用辅助函数
    - 提取 `_payload()` 请求体解析函数
    - 提取 `DEFAULT_USER` 常量
    - 提取通用的数据库查询辅助函数（`_get_or_404`、`_list_to_dict`）
    - 提取通用的错误响应格式
  - 创建 `app/api/v1/schemas/response.py`，定义统一响应模型
    - 定义 `ApiResponse[T]` 泛型响应类型
    - 定义 `PaginatedResponse[T]` 分页响应类型
    - 定义 `ErrorResponse` 错误响应类型
  - 创建 `app/core/exceptions.py`，定义统一异常体系
    - 定义 `BaseAppException` 基类
    - 定义 `NotFoundException`、`ValidationException`、`ConflictException`
    - 定义全局异常处理器注册函数

- [x] 2. 拆分 generic.py — Agents 路由
  - 创建 `app/api/v1/routes/agents.py`
    - 迁移 agents 相关端点（list_agents, create_agent, get_agent, delete_agent）
    - 添加完整的 docstring 和返回类型注解
    - 使用 `_get_or_404` 辅助函数简化查询逻辑
    - 确保每个函数不超过 30 行
  - 更新 `app/api/v1/generic.py`，移除已迁移的 agents 端点
  - 在 `app/api/v1/__init__.py` 中注册新路由

- [x] 3. 拆分 generic.py — Workflows 路由
  - 创建 `app/api/v1/routes/workflows.py`
    - 迁移 workflows 相关端点（list_workflows, create_workflow, get_workflow, update_workflow, delete_workflow, run_workflow, list_workflow_runs）
    - 提取 `_workflow_dict()` 辅助函数
    - 将 `run_workflow` 中超过 50 行的逻辑拆分为 `_execute_workflow` 和 `_record_workflow_run` 子函数
    - 添加完整的 docstring 和返回类型注解
  - 更新 `app/api/v1/generic.py`，移除已迁移的 workflows 端点

- [x] 4. 拆分 generic.py — Crews 路由
  - 创建 `app/api/v1/routes/crews.py`
    - 迁移 crews 相关端点（list_crews, create_crew, delete_crew, run_crew）
    - 提取 `_crew_dict()` 辅助函数
    - 将 `run_crew` 中超过 50 行的逻辑拆分为 `_execute_crew_tasks` 和 `_record_crew_run` 子函数
    - 添加完整的 docstring 和返回类型注解
  - 更新 `app/api/v1/generic.py`，移除已迁移的 crews 端点

- [x] 5. 拆分 generic.py — Skills 路由
  - 创建 `app/api/v1/routes/skills.py`
    - 迁移 skills 相关端点（list_skills, create_skill, enable_skill, disable_skill, delete_skill）
    - 提取 `_skill_dict()` 辅助函数
    - 添加完整的 docstring 和返回类型注解
  - 更新 `app/api/v1/generic.py`，移除已迁移的 skills 端点

- [x] 6. 拆分 generic.py — Groups 路由
  - 创建 `app/api/v1/routes/groups.py`
    - 迁移 groups 相关端点（list_groups, create_group, get_group, delete_group, add_group_member, remove_group_member, update_group_member, list_group_messages）
    - 提取 `_group_dict()`、`_member_dict()` 辅助函数
    - 将 `create_group` 中重复的成员序列逻辑提取为 `_build_member_dicts` 函数
    - 添加完整的 docstring 和返回类型注解
  - 更新 `app/api/v1/generic.py`，移除已迁移的 groups 端点

- [x] 7. 拆分 generic.py — Tasks 路由
  - 创建 `app/api/v1/routes/tasks.py`
    - 迁移 tasks 相关端点（list_tasks, create_task, get_task, run_task, pause_task, resume_task, stop_task）
    - 添加完整的 docstring 和返回类型注解
  - 更新 `app/api/v1/generic.py`，移除已迁移的 tasks 端点

- [x] 8. 拆分 generic.py — 其余路由
  - 创建 `app/api/v1/routes/misc.py`
    - 迁移 cluster、traces、plugins、scheduler、mcp、eval、cost、search、stats、profile、models、tools 相关端点
    - 提取各领域的 dict 转换函数
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/api/v1/routes/websocket.py`
    - 迁移 WebSocket 端点（ws_endpoint, ws_group_endpoint）
    - 添加完整的 docstring 和返回类型注解
  - 更新 `app/api/v1/generic.py`，确保所有端点已迁移完毕

- [x] 9. 检查点 - 确保 generic.py 拆分后所有测试通过
  - 运行 `pytest tests/ -x -q` 确认无回归
  - 如有问题请询问用户

- [x] 10. 重构 group_collaboration.py — 提取基类和公共逻辑
  - 创建 `app/core/collaboration/base.py`
    - 提取 `GroupCollaborationEngine` 的初始化逻辑和共享状态管理
    - 提取 `_resolve_api_key`、`_resolve_base_url` 辅助函数
    - 提取 `CALLBACK_REGISTRY` 和 `register_callback`
    - 提取常量 `TASK_TIMEOUT`、`MAX_RETRIES`、`FALLBACK_MODELS`
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/memory.py`
    - 提取 `_inject_memory`、`_store_memory` 方法
    - 提取 `_build_context_from_dependencies`、`_merge_context` 方法
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/prompts.py`
    - 提取所有 prompt 构建方法（`_build_initial_prompt`、`_build_sequential_prompt`、`_build_group_chat_prompt` 等共 8 个）
    - 添加完整的 docstring 和返回类型注解

- [x] 11. 重构 group_collaboration.py — 拆分流程类型
  - 创建 `app/core/collaboration/sequential.py`
    - 提取 `_run_sequential_process` 方法
    - 将超过 100 行的方法拆分为 `_execute_worker_turn`、`_execute_reviewer_turn`、`_finalize_sequential_task` 子函数
    - 确保嵌套深度不超过 5 层
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/hierarchical.py`
    - 提取 `_run_hierarchical_process` 方法
    - 将方法拆分为 `_plan_subtasks`、`_delegate_subtasks`、`_validate_output` 子函数
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/group_chat.py`
    - 提取 `_run_group_chat_process` 方法
    - 将方法拆分为 `_execute_chat_round`、`_check_consensus`、`_summarize_discussion` 子函数
    - 添加完整的 docstring 和返回类型注解

- [x] 12. 重构 group_collaboration.py — 拆分辅助功能
  - 创建 `app/core/collaboration/guardrails.py`
    - 提取 `_run_guardrails`、`_run_llm_guardrail`、`_run_function_guardrail`、`_validate_structured_output` 方法
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/checkpoint.py`
    - 提取 `_save_checkpoint`、`_load_latest_checkpoint`、`_resume_from_checkpoint` 方法
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/callbacks.py`
    - 提取 `_invoke_step_callback`、`_invoke_task_callback`、`_wait_for_human_review` 方法
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/collaboration/agent_runner.py`
    - 提取 `_run_agent`、`_run_agent_simple`、`_run_agent_with_retry` 方法
    - 提取 `_get_fallback_model` 方法
    - 将 `_run_agent_with_retry` 中重复的 agent 调用逻辑提取为 `_try_run_agent` 辅助函数
    - 添加完整的 docstring 和返回类型注解

- [x] 13. 重构 group_collaboration.py — 主文件精简
  - 重写 `app/core/group_collaboration.py`
    - 保留 `GroupCollaborationEngine` 类作为 facade，组合各子模块
    - 保留 `run_task`、`run_group_tasks`、`handoff_task`、`cancel_task` 等公共 API
    - 保留 review state 管理方法
    - 确保主文件不超过 300 行
    - 移除模块级 singleton 初始化代码（`group_collaboration_engine = _get_engine_synchronously()`）
    - 改为懒加载模式，通过 `get_group_collaboration_engine()` 统一获取
    - 添加完整的 docstring 和返回类型注解

- [x] 14. 检查点 - 确保 group_collaboration.py 重构后所有测试通过
  - 运行 `pytest tests/ -x -q` 确认无回归
  - 如有问题请询问用户

- [x] 15. 重构 agent_engine.py — 拆分 AgentSession 初始化
  - 备注：`app/core/session.py` 已创建（含 `AgentSession`、`SessionConfig` dataclass、`_SessionMemory` 类）；`session_memory.py` 未单独创建，`_SessionMemory` 位于 session.py 内
  - 创建 `app/core/session.py`
    - 提取 `AgentSession` 类到独立文件
    - 将 `__init__` 中超过 30 行的初始化逻辑拆分为 `_init_permission_system`、`_init_sandbox`、`_init_state_machine` 子方法
    - 使用 dataclass 封装会话配置参数（超过 7 个参数的用 `SessionConfig` dataclass）
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/session_memory.py`
    - 提取 `_SessionMemory` 类
    - 添加完整的 docstring 和返回类型注解

- [x] 16. 重构 agent_engine.py — 拆分 AgentEngine 核心逻辑
  - 创建 `app/core/engine/validation.py`
    - 提取 `_validate_tool_call` 方法
    - 将超过 60 行的方法拆分为 `_check_plan_mode`、`_check_permission_rules`、`_check_permission_overlay`、`_check_schema_validation`、`_check_sandbox` 子函数
    - 确保嵌套深度不超过 3 层
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/engine/persistence.py`
    - 提取 `_persist_message` 方法
    - 添加完整的 docstring 和返回类型注解
  - 创建 `app/core/engine/tools.py`
    - 提取 `_build_tools` 方法
    - 添加完整的 docstring 和返回类型注解

- [ ] 17. 重构 agent_engine.py — 精简主文件
  - 备注：拆分后的 `app/core/agent_engine.py` 仍有 883 行，超过 300 行目标，未达标
  - 重写 `app/core/agent_engine.py`
    - 保留 `AgentEngine` 类作为 facade
    - 将 `_run_locked` 中超过 150 行的核心循环拆分为 `_prepare_session_context`、`_run_iteration_loop`、`_handle_tool_execution`、`_create_checkpoint` 子函数
    - 确保嵌套深度不超过 5 层
    - 移除未使用的 `import asyncio`（在 `stop` 方法内重复导入）
    - 添加完整的 docstring 和返回类型注解
    - 确保主文件不超过 300 行

- [x] 18. 检查点 - 确保 agent_engine.py 重构后所有测试通过
  - 运行 `pytest tests/ -x -q` 确认无回归
  - 如有问题请询问用户

- [ ] 19. 统一错误处理和日志格式
  - 备注：`app/core/error_handlers.py` 不存在，统一 FastAPI 异常处理器未实现
  - 创建 `app/core/error_handlers.py`
    - 实现全局 FastAPI 异常处理器
    - 统一 HTTP 错误响应格式
    - 统一日志输出格式（使用 structlog 的 `logger.error/warning/info` 标准化）
  - 更新所有路由文件，使用统一的错误处理模式
  - 确保所有 `except` 块使用结构化日志（包含 context 参数）

- [ ] 20. 最终检查点 - 全面质量验证
  - 备注：pytest 41 passed、`ruff check app/` 通过，但 `app/core/agent_engine.py` 883 行超过 500 行目标，该项部分达标
  - 运行 `pytest tests/ -x -q` 确认所有测试通过
  - 运行 `ruff check app/` 确认无 lint 错误
  - 确认所有文件不超过 500 行
  - 确认所有函数不超过 50 行
  - 确认所有公共函数有 docstring
  - 确认所有函数有返回类型注解
  - 确认嵌套深度不超过 5 层
  - 确认函数参数不超过 7 个
