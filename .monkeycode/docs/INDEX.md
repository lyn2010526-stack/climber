# Climber Agent 平台文档索引

> 统一 AI Agent 平台（Python FastAPI 后端 + React/Vite 前端）。

## 核心文档

- [架构总览](ARCHITECTURE.md) - 执行内核、持久化、多 Agent、权限、多租户、基础设施与前端工作区当前态与迁移路径
- [接口定义](INTERFACES.md) - 执行引擎、会话、checkpoint、Principal、API 契约
- [开发者指南](DEVELOPER_GUIDE.md) - 构建、测试、验收命令与项目约定
- [API 文档](API.md) - `/api/v1` 端点与认证
- [部署指南](DEPLOYMENT.md) - 环境变量、Docker、静态托管

## 规格

- `.monkeycode/specs/2026-08-05-unified-agent-platform/` - 统一架构规格（requirements/design/tasklist）
- `.monkeycode/specs/2026-08-04-agent-engine-enhancement/` - Agent 引擎增强历史规划
- `.monkeycode/specs/code-refactoring/` - 代码质量重构历史规划

## 目录结构

```
app/
├── main.py                     # FastAPI 入口：中间件、静态托管、DI 注册
├── api/v1/                     # 路由：generic 聚合 + routes/*.py 实现
├── core/
│   ├── agent_engine.py         # 主线执行引擎（async generator）
│   ├── session.py              # 统一 AgentSession + snapshot
│   ├── checkpoint.py           # checkpoint 完整持久化
│   ├── principal.py            # Principal 身份与 ContextVar
│   ├── engine/pregel/          # 图执行内核（已加固，待接入主线）
│   └── collaboration/          # GroupCollaborationEngine 协作主实现
├── schemas/api_v1/             # 命名 Pydantic 请求模型
├── middleware/                 # auth / rate_limit / security / metrics
└── storage/                    # SQLite 数据库与缓存

frontend-react/
├── src/App.tsx                 # Hash 路由真实入口
├── src/main.tsx
├── src/components/workspace/   # WorkspaceLayout / Sidebar / RightPanel
└── src/pages/                  # Chat / Agents / Workflows / Dashboard / Settings
```
