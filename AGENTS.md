# Climber Agent 开发治理

本文件是 Climber 仓库中 Agent 和协作者的执行入口。规则以当前仓库事实为准：核心运行时是 Python 3.11+、FastAPI、SQLAlchemy、Pydantic 和 pytest；`app/static/` 当前只有少量 HTML；仓库另有独立的 `frontend-react/`，前端规则仅在明确扩展该目录或新增前端表面时启用。仓库没有 uni-app 目录或配置，任何任务都不得据此假设项目采用 uni-app。

## 开发前检查

每项开发任务开始前必须完成以下检查，并在任务记录或 PR 描述中写出影响范围：

1. 阅读本文件、`docs/DEVELOPMENT_RULES.md`、`docs/DESIGN_SYSTEM.md` 及与任务相关的现有文档。
2. 查看 `git status --short`，保留其他协作者的改动，不覆盖或回滚未参与的变更。
3. 识别目标模块、公共边界、测试入口和文档归属；先确定文件归属，再编辑文件。
4. 判断任务是否涉及前端扩展。仅修改 FastAPI、API、模型、存储、工具或测试时，不引入前端组件库决策。
5. 为需求拆成一个或多个 8 个治理子任务边界内的工作包；每个工作包应有清晰的文件集合和验证命令。

## 8 个子任务边界与文件归属

一个工作包只能由一个主责任人或 Agent 负责。跨边界依赖通过接口、测试或文档交接，禁止多人同时编辑同一文件。

| 边界 | 责任范围 | 默认文件归属 |
| --- | --- | --- |
| 1. API 合约 | 路由、请求响应 schema、错误响应、版本注册 | `app/api/`、`app/schemas/`、API 测试 |
| 2. Agent 核心 | 执行循环、推理、权限、会话、恢复和安全门禁 | `app/core/` |
| 3. 领域与模型 | LLM adapter、领域模型、业务编排 | `app/models/`、`app/workflow/`、`app/multi_agent/` |
| 4. 存储与迁移 | ORM、repository、数据库连接、迁移 | `app/storage/`、`alembic/` |
| 5. 集成与工具 | MCP、外部客户端、内置工具、网络边界 | `app/integrations/`、`app/tools/`、相关 `app/utils/` |
| 6. Web 表面 | `app/static/` HTML、明确纳入范围的 `frontend-react/` UI | `app/static/`；前端扩展时才使用 `frontend-react/` |
| 7. 测试与质量 | pytest、Vitest、Playwright、lint、类型检查、快照 | `tests/`、`frontend-react/**/__tests__/`、测试配置 |
| 8. 文档与治理 | 规则、设计 Token、文档索引、贡献说明 | `AGENTS.md`、`docs/`、`.monkeycode/` |

任务若跨越多个边界，先拆成独立工作包并指定交接顺序。配置文件改动归入受影响的边界；跨模块配置由边界 8 记录并由相关边界复核。

## 开发后检查

完成实现后必须：

- 检查变更是否仍落在声明的文件归属内，清理无关改动和临时文件。
- 更新受影响的文档索引、测试说明或 Token 说明。
- 执行适用的测试、lint、类型检查、构建和 UI 快照检查；命令与结果必须真实记录。
- 只声明已执行且有输出证据的检查。失败、跳过、未安装依赖和未覆盖范围必须明确写出。
- 再次查看 `git diff --check` 和 `git status --short`。本规则不授权 commit 或 push。

## 文档与治理任务

仅修改文档时也必须按事实对账：先检查生产代码、测试配置和当前工作树，再更新能力声明、风险等级和验证命令。文档任务的默认边界是 8（文档与治理），生产代码和测试保持只读；安全结论必须注明配置前提、测试范围和剩余未覆盖项。历史报告应保留历史日期，同时用当前复核章节覆盖仍然有效的结论。

文档任务至少执行并记录：

```bash
git diff --check
git status --short
```

涉及安全门禁、认证、网络出口或权限的文档更新，应执行相关的定向测试；只引用本次实际运行且有输出证据的结果。文档任务不自动执行 commit 或 push。

## 文档入口

- `docs/DEVELOPMENT_RULES.md`：日常开发、验证、重复组件、目录归位和 Agent 协作规则。
- `docs/DESIGN_SYSTEM.md`：当前设计 Token、HTML 约束、前端扩展时的组件库决策流程。
- `docs/DEVELOPMENT_RULES.md` 的“相关文档与来源”章节：现有治理文档索引和新增文档登记位置。
- `SECURITY_AUDIT_REPORT.md`：历史审计与当前复核结果，当前风险以复核日期和证据为准。
- `docs/DEAD_CODE_DOCUMENTATION_AUDIT.md`：未接线模块、能力声明和文档事实对账。
- `docs/DEPENDENCY_AUDIT.md`：Python/npm 依赖检查、供应链覆盖范围和已知限制。
- `CONTRIBUTING.md`：仓库已有的贡献流程；与本文件冲突时，以本文件的项目事实和验证要求为准。

## 来源

本治理结构参考以下成熟开源协作规范和官方文档：

- OpenAI Cookbook Repository Guidelines: https://github.com/openai/openai-cookbook/blob/main/AGENTS.md
- GitHub CODEOWNERS 文档: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- GitHub Contributing 指南: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors
- FastAPI 贡献指南: https://fastapi.tiangolo.com/contributing/
