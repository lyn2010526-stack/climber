# 需求文档

## 简介

统一 Agent Run 协议为 Climber 的 Agent Chat 提供一致的运行、消息、事件、追踪和检查点语义。首个切片复用现有 Session、Turn、Message、Trace 和 Checkpoint 存储，通过兼容适配层维持 `/api/v1/sessions/{session_id}/chat` 及 SSE 事件契约。

## 术语

- **Run**：一次可独立追踪、恢复和终止的执行实例。首个切片中的 Run 对应一个 Chat Turn。
- **RunRuntime**：拥有 Run 生命周期、事件排序、持久化关联和恢复语义的核心模块。
- **Message Envelope**：统一消息封装，包含标准内容、来源、关联标识和可选 Provider 原始载荷引用。
- **Run Event**：Run 产生的有序事实记录，包含稳定标识、序号、类型、时间和关联标识。
- **Trace**：Run 内模型调用、工具调用和其他操作的层级观测记录。
- **Checkpoint**：Run 在特定迭代的可恢复状态快照。
- **Compatibility Adapter**：将统一 Run Event 转换为现有 AgentEvent 和 SSE 格式的适配器。
- **Raw Payload Policy**：控制 Provider 原始载荷保存级别、加密方式和保留时间的配置策略。

## 需求

### 需求 1：统一 Run 生命周期

**用户故事：** 作为平台开发者，我希望所有 Chat Turn 使用统一 Run 生命周期，以便后续让 Workflow 和 Group Task 复用相同执行语义。

#### 验收标准

1. WHEN Agent Chat 接收有效消息时，RunRuntime SHALL 创建具有唯一 `run_id` 的 Run。
2. WHILE Run 正在执行时，RunRuntime SHALL 将 Run 状态维护为 `running`。
3. WHEN Run 正常结束时，RunRuntime SHALL 将 Run 状态原子更新为 `completed` 并记录完成时间。
4. IF Run 执行发生异常，RunRuntime SHALL 将 Run 状态原子更新为 `failed` 并记录结构化错误。
5. WHEN 调用方取消 Run 时，RunRuntime SHALL 将 Run 转换为 `cancelled` 并停止该 Run 的后续写入。

### 需求 2：统一 Message Envelope

**用户故事：** 作为运行时维护者，我希望消息具有统一封装，以便模型适配器、回放和 Trace 使用同一数据语义。

#### 验收标准

1. WHEN Run 接收或生成消息时，RunRuntime SHALL 创建包含 `message_id`、`run_id`、`session_id`、`role`、`content` 和 `created_at` 的 Message Envelope。
2. WHEN 消息表示工具调用或工具结果时，Message Envelope SHALL 保存 `tool_call_id`、`tool_name` 和结构化内容。
3. WHEN Provider 返回模型专有字段时，Message Envelope SHALL 在标准字段之外保存原始载荷引用或摘要。
4. WHEN Message Envelope 被序列化后再次解析时，解析结果 SHALL 保持所有标准字段和关联标识一致。

### 需求 3：有序 Run Event

**用户故事：** 作为前端用户，我希望断线重连后继续接收有序事件，以便恢复完整执行进度。

#### 验收标准

1. WHEN Run 产生事件时，RunRuntime SHALL 为事件分配 Run 内单调递增的 `sequence`。
2. WHEN 客户端按游标请求回放时，RunRuntime SHALL 返回相同 Run 中序号大于游标的事件。
3. WHEN 同一 Run 的事件被实时推送和回放时，RunRuntime SHALL 使用相同的 `event_id`、`sequence` 和事件数据。
4. IF 请求游标早于最早保留事件，RunRuntime SHALL 返回可识别的回放缺口信息。
5. WHEN Run 结束时，RunRuntime SHALL 生成一个终态事件，并使终态事件成为该 Run 的最后一个业务事件。

### 需求 4：Trace 与 Checkpoint 关联

**用户故事：** 作为诊断人员，我希望从 Run 定位 Trace 和 Checkpoint，以便回放执行过程并分析失败位置。

#### 验收标准

1. WHEN Run 启动时，RunRuntime SHALL 创建或绑定唯一的 `trace_id`。
2. WHEN Run 保存 Checkpoint 时，RunRuntime SHALL 将 `checkpoint_id` 与 `run_id`、`session_id` 和迭代序号关联。
3. WHEN Run 产生模型或工具 Span 时，Trace SHALL 保存 `run_id` 关联信息。
4. WHEN 查询 Run 详情时，系统 SHALL 返回 Run 的当前状态、`trace_id`、最新 `checkpoint_id` 和事件游标范围。
5. IF Checkpoint 与目标 Run 的关联不一致，RunRuntime SHALL 拒绝恢复并返回结构化关联错误。

### 需求 5：原始载荷策略

**用户故事：** 作为平台运维人员，我希望控制 Provider 原始载荷保留范围，以便平衡回放能力、隐私和存储成本。

#### 验收标准

1. WHERE Raw Payload Policy 为 `standard`，系统 SHALL 保存标准字段和原始载荷摘要。
2. WHERE Raw Payload Policy 为 `debug`，系统 SHALL 加密保存完整原始载荷并记录过期时间。
3. WHEN 原始载荷到达保留期限时，系统 SHALL 将完整载荷转换为摘要保留状态。
4. WHEN 原始载荷包含凭据字段时，系统 SHALL 在持久化前应用字段级脱敏规则。
5. WHEN Raw Payload Policy 配置缺失时，系统 SHALL 使用 `standard` 策略。

### 需求 6：现有 Chat 契约兼容

**用户故事：** 作为现有前端用户，我希望统一协议上线后继续使用当前 Chat 页面，以便平滑迁移。

#### 验收标准

1. WHEN 客户端调用现有 Chat 端点时，Compatibility Adapter SHALL 接受当前请求体字段。
2. WHEN RunRuntime 产生 Run Event 时，Compatibility Adapter SHALL 输出当前前端识别的 SSE 事件名和数据字段。
3. WHEN 客户端调用现有 replay 端点时，Compatibility Adapter SHALL 保持当前响应字段并补充 `run_id`。
4. WHEN 新增统一 Run 查询接口时，现有 Session 和 Message 查询接口 SHALL 保持当前路径与响应结构。

### 需求 7：失败恢复与幂等性

**用户故事：** 作为平台开发者，我希望 Run 写入具有幂等和 fencing 语义，以便重试与服务恢复保持一致结果。

#### 验收标准

1. WHEN 同一 `event_id` 被重复写入时，RunRuntime SHALL 保留单条事件记录。
2. WHEN 终态 Run 收到普通事件写入时，RunRuntime SHALL 拒绝写入并返回状态冲突。
3. WHEN 服务从 Checkpoint 恢复 Run 时，RunRuntime SHALL 从最后持久化序号继续分配事件序号。
4. IF 恢复请求携带过期执行令牌，RunRuntime SHALL 拒绝状态写入。

### 需求 8：可验证性与可观测性

**用户故事：** 作为质量工程师，我希望统一协议具有明确验证入口，以便证明实时、回放、恢复和兼容行为一致。

#### 验收标准

1. WHEN 执行单元测试时，测试套件 SHALL 覆盖 Run 状态机的允许转换和冲突转换。
2. WHEN 执行集成测试时，测试套件 SHALL 验证实时 SSE 与 replay 事件的一致性。
3. WHEN 执行恢复测试时，测试套件 SHALL 验证 Checkpoint 归属、序号连续性和终态 fencing。
4. WHEN 执行隐私测试时，测试套件 SHALL 验证原始载荷策略、脱敏和过期转换。
