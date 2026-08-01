# 群组协作增强任务报告

**日期**: 2026-07-26  
**状态**: 已完成  
**测试结果**: 354 passed, 0 failed

## 任务目标

基于 CrewAI 和 AutoGen 开源项目的能力对标，补齐群组协作核心缺失能力，从"骨架可用"推进到"接近生产可用"。

## 完成范围

### 后端核心增强

#### 1. 数据模型扩展（`app/storage/models_groups.py`）

**AgentGroup 扩展字段**:
- `process_type`: 支持三种执行模式（sequential / hierarchical / group_chat）
- `manager_agent_id`: 分层模式下的 Manager 成员 ID
- `manager_llm`: Manager 使用的模型配置

**AgentGroupTask 扩展字段**:
- `context`: 任务依赖列表，支持链式上下文传递
- `guardrails`: 输出校验规则配置
- `human_review_required`: 人工审批开关
- `human_review_status`: 人工审批状态（pending/approved/rejected）
- `human_review_comment`: 人工审批备注
- `output_schema`: 结构化输出 JSON Schema
- `structured_output`: 解析后的结构化输出
- `step_callback`: 步骤级回调函数引用
- `task_callback`: 任务级回调函数引用
- `paused_at`: 暂停时间戳

**新增数据表**:
- `AgentGroupTaskCheckpoint`: 断点续跑持久化
- `AgentGroupMemory`: 短期/长期记忆存储
- `AgentGroupGuardrail`: 校验规则集中配置

#### 2. 编排引擎增强（`app/core/group_collaboration.py`）

**新增执行模式**:
- `_run_sequential_process`: 顺序执行，自动注入上游任务输出与记忆，每轮保存 checkpoint
- `_run_hierarchical_process`: Manager 规划子任务、委派给 Worker、最终验证输出
- `_run_group_chat_process`: 多 Agent 轮询讨论，基于共识关键词判定结束

**新增核心能力**:
- `_run_guardrails` / `_run_llm_guardrail` / `_run_function_guardrail`: 输出验证与自动重试
- `_save_checkpoint` / `_load_latest_checkpoint` / `_resume_from_checkpoint`: 断点续跑
- `_inject_memory` / `_store_memory`: 记忆检索与持久化
- `_invoke_step_callback` / `_invoke_task_callback`: 步骤与任务级回调
- `_wait_for_human_review`: 人工审批流程，超时 1 小时
- `_run_agent_with_retry`: Worker 失败自动重试 2 次 + 模型降级

#### 3. WebSocket 事件扩展（`app/core/group_ws_hub.py`）

新增 30+ 事件类型:
- guardrail_passed / guardrail_failed
- human_review_needed / human_review_response
- checkpoint_saved
- memory_injected
- manager_plan / manager_plan_created
- group_chat_message / consensus_reached
- system_message / reviewer_error

#### 4. API 层补齐（`app/api/v1/generic.py`）

- `create_task`: 支持 context / guardrails / human_review_required / output_schema
- `get_task`: 返回完整任务详情（含 final_output / structured_output / 时间戳 / callbacks）
- `_group_dict`: 返回 members 数组 + member_count + process_type + manager 配置
- `list_groups`: 通过 selectinload 预加载 members，避免 MissingGreenlet
- `get_group`: 显式加载 members 并传递到 _group_dict
- 新增 `selectinload` import

**修复的关键问题**:
- SQLAlchemy AmbiguousForeignKeysError: `members` 关系显式指定 `foreign_keys` + `primaryjoin`
- SQLAlchemy MissingGreenlet: `create_group` 后重新加载 members，避免在会话外访问懒加载属性
- AutoLoopSession 引用错误: 移除不存在的模型引用

### 前端 UI 增强

#### 1. TaskInput 组件增强（`frontend-react/src/components/collaboration/TaskInput.tsx`）

- 新增高级设置面板（可折叠）
- 执行流程选择：Sequential / Hierarchical / Group Chat
- 依赖任务上下文选择（checkboxes）
- Guardrails 可视化配置（名称 + 描述，支持添加/移除）
- Human-in-the-loop 开关
- 新增 `TaskOptions` 接口导出

#### 2. CollaborationConsole 组件增强（`frontend-react/src/components/collaboration/CollaborationConsole.tsx`）

- 新增 8 类 WebSocket 事件处理
- 新增 `availableTasks` prop 支持上下文任务选择
- `TaskOptions` 透传到 startTask
- 事件流 UI 反馈增强

#### 3. ClusterPage 组件增强（`frontend-react/src/pages/ClusterPage.tsx`）

- 任务卡片可点击展开详情面板
- 详情展示：流程类型、guardrail 状态、token 消耗、时间戳、最终输出、结构化输出
- 群组列表返回完整 members 数组和 member_count
- 新增 `availableTasks` 状态，进入自动协作时自动加载可用任务

#### 4. GroupRoom 组件增强（`frontend-react/src/components/group/GroupRoom.tsx`）

- 成员在线状态增强：脉冲动画 + 在线标签
- WebSocket `member_update` 实时同步成员状态
- 5 秒轮询刷新成员状态
- 成员列表视觉优化：在线/离线区分

## 技术债务与注意事项

### 已修复

1. SQLAlchemy 关系歧义问题
2. MissingGreenlet 懒加载错误
3. AutoLoopSession 不存在的模型引用
4. _group_dict 在会话外访问关系属性

### 待后续优化

1. `loop_sessions` 关系已移除，若需要 AutoLoopSession 功能需重新设计模型
2. Manager 代理的 `manager_agent_id` 目前仅为字符串，未做外键约束
3. Callback 注册机制为内存级，进程重启后丢失
4. Group Memory 的向量检索尚未接通 Chroma，当前为关键词匹配
5. Human-in-the-loop 超时处理需后端配合自动批准/拒绝逻辑

## 测试覆盖

- **全量测试**: 354 passed, 0 failed
- **关键链路**:
  - `test_groups_roundtrip`: 群组 CRUD 全链路
  - `test_new_routes`: 新增路由端点
  - `test_integration`: 集成测试
  - `test_e2e_frontend_paths`: 前端路径无桩代码

## 下一步建议

1. **立即做真正的端到端验证**: 启动后端 + 前端，手动跑通创建群组 → 添加成员 → 执行任务 → 查看结果全链路
2. AutoLoopSession 持久化接通
3. 对接开源 CrewAI 的 Tools/Knowledge 能力
4. 对照 AutoGen GroupChat 模式补全群组对话路由与记忆共享
5. 生产级 hardening：SQLite 并发写入优化、前端构建体积优化

## 关键文件清单

### 后端
- `app/storage/models_groups.py`: 群组数据模型
- `app/core/group_collaboration.py`: 群组协作编排引擎
- `app/core/group_ws_hub.py`: 群组 WebSocket Hub
- `app/api/v1/generic.py`: 群组相关 API 端点

### 前端
- `frontend-react/src/components/collaboration/TaskInput.tsx`: 任务输入组件
- `frontend-react/src/components/collaboration/CollaborationConsole.tsx`: 协作控制台
- `frontend-react/src/pages/ClusterPage.tsx`: 群组/集群主页
- `frontend-react/src/components/group/GroupRoom.tsx`: 群组聊天室
