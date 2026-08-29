# Climber 全面优化计划

## Overview

基于全仓库扫描和 LangGraph、CrewAI、AutoGen、Dify、OpenHands、PenguinHarness 对标结果，按风险和依赖顺序优化 Climber 的运行稳定性、API 契约、生产部署、质量验证和平台化能力。

## Architecture Decisions

- 优先修复已有明确证据的运行时和契约问题，保持最小改动。
- 保留当前无登录页面的产品体验；资源归属校验通过现有认证依赖逐步接入。
- 将生产 Compose 与开发服务器分离，生产使用构建后的静态资源。
- 认证、沙箱、MCP 注册和统一 Run 数据模型属于高风险或跨模块改造，先设计和测试，再分批实施。
- 核心引擎拥有统一 Run、Message、Event 和 Trace 协议；API、Web 与未来 CLI 只通过稳定契约接入。
- Agent、Skill、Prompt、评测配置和优化快照采用可审计、可版本化的文件表达，运行数据继续进入持久化存储。
- 每个批次完成定向测试、静态检查和相关回归后再进入下一批次。

## Task List

### Phase 1: Runtime Reliability

- [ ] 修复 OpenAI 非流式 `chat()` 对增量和累计内容的重复聚合，并补充回归测试。
- [ ] 修复 Ollama streaming HTTP response 生命周期，确保响应消费发生在 stream context 内，并补充测试。
- [ ] 将数据库初始化失败变成明确的启动失败或 readiness 降级状态，补充测试。

### Checkpoint: Runtime Reliability

- [ ] 模型适配器定向测试通过
- [ ] 数据库初始化定向测试通过
- [ ] Ruff 和 `git diff --check` 通过

### Phase 2: API Contract And Frontend Data

- [ ] 实现任务列表 `status` 服务端过滤并补充 API 测试。
- [ ] 将前端缓存按认证上下文隔离，并补充身份变化清理测试。
- [ ] 统一 Settings API 使用认证依赖提供的用户身份，补充契约测试。
- [ ] 逐步补齐 Agent、Group、Task、Document 和 checkpoint 的资源归属校验；每组独立验证。

### Checkpoint: API Contract

- [ ] 前后端任务筛选契约一致
- [ ] 缓存不会跨认证上下文复用
- [ ] 设置 API 按当前用户读写
- [ ] 关键资源授权测试通过

### Phase 3: Production Delivery

- [ ] 将 Compose 前端改为生产静态资源服务，开发 Vite 服务移入开发配置。
- [ ] 统一 Chroma 架构，明确本地 PersistentClient 或 HTTP 服务方案，并同步健康检查与卷配置。
- [ ] 将 Python 依赖收敛到可复现的锁定输入。
- [ ] 增加 readiness 健康端点，CI 执行构建和有界运行时冒烟。
- [ ] 修正 README、部署文档和实际目录/脚本之间的差异。

### Checkpoint: Production Delivery

- [ ] 干净环境前端构建通过
- [ ] Dockerfile 静态检查通过
- [ ] Compose 配置和健康检查契约测试通过
- [ ] 文档命令与仓库脚本一致

### Phase 4: Platform Foundations

- [ ] 设计统一 Run、Checkpoint、Event、Trace 关联模型。
- [ ] 定义保留 provider 原始载荷的统一 Message envelope，确保 stream、replay、resume 和 Trace 信息无损。
- [ ] 将持久化 checkpoint 设为 Agent/Workflow/Crew 的默认运行路径。
- [ ] 统一 interrupt、resume、cancel、retry 和 fork 语义。
- [ ] 将 Eval 接入真实 Agent Run、Trace 和基线对比。
- [ ] 建立 benchmark、evaluation、optimization、snapshot、rollback 的自优化闭环，并隔离目标 Agent 与隐藏评分标准。
- [ ] 将 Agent、Skill、Prompt 与优化产物收敛为可审计文件契约，记录每轮变更原因和版本。
- [ ] 为 MCP 建立真实连接、发现、健康和工具 schema 生命周期。
- [ ] 建立 Workspace、Artifact 和版本发布模型。
- [ ] 提取稳定 Core SDK 边界，让 API、Web、CLI 和桌面壳共享同一执行引擎与数据目录约束。

## Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 认证与资源归属改动触及现有固定身份模式 | High | 先补测试和兼容 service 参数，再逐域切换 |
| Compose 架构变更影响本地开发 | High | 生产 Compose 与开发 override 分离 |
| Chroma 本地与 HTTP 模式混用造成数据迁移风险 | High | 先确认实际部署目标，建立迁移和回滚方案 |
| 统一 Run 模型涉及多个执行器 | High | 先定义状态机和事件契约，再垂直切片实施 |
| Python 依赖锁定引入平台兼容问题 | Medium | 在 CI 使用 Python 3.11 并保留可更新流程 |

## Open Questions

- 生产环境的向量存储目标是 API 内置本地 Chroma 还是独立 Chroma 服务？
- 多用户认证正式启用时，当前固定 `default-user` 数据是否需要迁移到用户主体？
- 统一 Run 模型是否允许对现有 Task/Session API 做版本化扩展？
