# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [运维部署|构建方法|测试方法|排错调试|工作流协作|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条

[项目知识摘要]
- Date: 2026-07-27
- Context: Agent 在执行 Phase 5-7 及 Global 功能实现时发现
- Category: 测试方法
- Instructions:
  - 后端测试命令：`python3 -m pytest tests/ -q --ignore=tests/test_integration.py --ignore=tests/test_e2e_frontend_paths.py`
  - 测试结果稳定在 358 passed（含 12 个新增 task_dag 测试）
  - 前端构建命令：`cd frontend-react && npm run build`（需确保 node 在 PATH 中）
  - 前端构建存在预存 TypeScript 严格模式错误，非本次变更引入
  - 文档测试需使用 `data` 参数发送 form data，搜索端点需使用 `params` 发送 query 参数
  - `file_index_service` 是全局单例，测试间会保留状态，需在 cleanup 中重置或设计为可缓存

[项目知识摘要]
- Date: 2026-07-27
- Context: Agent 在执行 Phase 5-7 及 Global 功能实现时发现
- Category: 构建方法
- Instructions:
  - Node 路径：`/root/.nvm/versions/node/v20.20.2/bin/node`
  - 前端构建时需将 node 加入 PATH：`export PATH="/root/.nvm/versions/node/v20.20.2/bin:$PATH"`
  - 前端 TypeScript strict 模式已开启，新增代码需通过 `tsc --noEmit` 检查

[项目知识摘要]
- Date: 2026-07-27
- Context: Agent 在执行 Phase 5-7 及 Global 功能实现时发现
- Category: 工作流协作
- Instructions:
  - Phase 5 实现：TaskDAG（拓扑排序 + 循环检测）+ HandoffMessage + group_collaboration DAG 执行器
  - Phase 6 实现：apply_patch / stream_command / container_exec 三个新工具 + CodeSandbox AST 检查
  - Phase 7 实现：FileIndexService（SHA256 + timestamp 增量索引）+ auto_decompose_task 工具
  - Global 实现：EventBus 发布/订阅事件总线 + json_schema 严格结构化输出验证
  - 每 Phase 完成后运行完整测试套件确认无回归

[项目知识摘要]
- Date: 2026-07-31
- Context: Agent 在执行 AGI P6 Collaboration Layer 实现时发现
- Category: 工作流协作
- Instructions:
  - P6 实现：collaboration 子包（a2a_protocol / handoff / roles / aggregation / api）
  - A2A 协议：JSON wire format + HMAC-SHA256 签名 + protocol_version 字段
  - Handoff：HandoffManager 支持 request/accept/reject 全生命周期 + 能力匹配 + 审计追踪
  - Roles：AgentRole 枚举（PLANNER/EXECUTOR/AUDITOR/RESEARCHER/COMMUNICATOR/GUARD）+ RoleRegistry 权限校验
  - Aggregation：ResultAggregator 支持 majority_vote / weighted_average / best_confidence 策略 + 分歧检测
  - API：FastAPI router 前缀 /api/v1/collaboration，所有端点需 auth
  - 测试：tests/test_agi_p6_collaboration.py，74 tests 全部通过

## 条目

[按上述格式记录的记忆条目]
